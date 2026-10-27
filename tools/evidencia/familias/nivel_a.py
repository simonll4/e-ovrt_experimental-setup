"""Estado por persona (Tabla 52): Nivel A en imágenes (PER-01/02) y en video (PER-03).

PER-01/02: las 18 corridas de `docs/operacion/datos/83-fase-d-nivel-a-runner.py` (por estrato,
1 E-IND con `eind_v1` + una corrida por variante E-DIR de `edir_v1`, cada frase sola en su
caption) y el scorer pre-registrado `run_fase_d_nivel_a.py` (calibra en la mitad A, reporta
en la B, misma semilla).

PER-03: detecciones de los 13 clips del estrato B (reusa la prueba de obra real en escena) y
de los 4 clips del piloto (corrida nueva), puntuadas con `score_clip_person_state.py` en el
punto de operación desplegado, 1 de cada 15 cuadros. Como en la generación 1 (doc 110), los
XML y las fichas de los 17 clips tienen que estar en UNA carpeta: el driver la arma con
copias (y sus huellas), sin tocar las fuentes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ..catalogo import Prueba
from ..comparar import proponer
from ..huellas import armar_prompts, sha256_archivo
from ..registro import Carpeta
from . import Contexto, familia, preparar_modelo
from .imagenes import TIMEOUT_S, _correr_trabajos, _media_cfg


def _trabajos_nivel_a(ctx: Contexto, prueba: Prueba) -> tuple[list[tuple[str, dict]], dict, dict]:
    """(trabajos, metadatos por clave para runs.json, constancia de prompts)."""
    r = prueba.receta
    trabajos, meta, constancias = [], {}, {}
    eind_prompts, constancias["eind"] = armar_prompts(r["eind"]["prompts"], ctx.ent.repo)
    edir = r["edir"]
    for estrato in r["estratos"]:
        eid = estrato["id"]
        clave = f"eind_{eid}"
        trabajos.append((clave, _media_cfg(ctx, prueba, clave, estrato["imagenes"], eind_prompts)))
        meta[clave] = {"arm": "eind", "variant": "eind_v1_full", "condition": "both", "stratum": eid,
                       "prompt_set_id": r["eind"]["prompts"]["set_id"]}
        for variante in edir["variantes"]:
            if variante["condicion"] not in estrato["condiciones"]:
                continue  # sin GT a nivel persona de esa condición, no se corre (runner 83)
            spec = {"set_id": edir["set_id"], "fuente": edir["fuente"], "clases": [variante["id"]],
                    "frozen": edir.get("frozen")}
            prompts, constancias[variante["id"]] = armar_prompts(spec, ctx.ent.repo)
            clave = f"edir_{variante['id']}_{eid}"
            trabajos.append((clave, _media_cfg(ctx, prueba, clave, estrato["imagenes"], prompts)))
            meta[clave] = {"arm": "edir", "variant": variante["id"], "condition": variante["condicion"],
                           "strategy": variante.get("estrategia"), "stratum": eid,
                           "prompt_set_id": edir["set_id"]}
    return trabajos, meta, constancias


def aplanar_gate(metrics: dict) -> dict:
    """Lo que decide el §8: F1 de E-IND, mejor variante E-DIR y su F1, por estrato/condición."""
    valores = {}
    for clave, g in (metrics.get("gate") or {}).items():
        for campo in ("f1_eind", "best_edir_variant", "f1_edir", "ratio", "edir_below_half"):
            valores[f"{clave}.{campo}"] = g.get(campo)
    return valores


@familia("nivel_a")
def correr_nivel_a(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    objetivo = None if ctx.reagregar else preparar_modelo(ctx, r, carpeta)
    trabajos, meta, constancias = _trabajos_nivel_a(ctx, prueba)
    carpeta.escribir("configuracion.json", {"prompts": constancias, "modelo_cargado": objetivo,
                                            "trabajos": [c for c, _ in trabajos]})
    pendientes = _correr_trabajos(ctx, prueba, carpeta, trabajos, float(r.get("timeout_s", TIMEOUT_S)))
    if pendientes:
        carpeta.resultado({"familia": "nivel_a", "estado": "parcial", "pendientes": pendientes})
        return {"estado": "parcial", "pendientes": pendientes}

    corridas = carpeta.corridas()
    runs = [{**meta[c], "run_id": corridas[c]["media_run_id"], "status": "succeeded",
             "units_processed": corridas[c].get("unidades"),
             "total_detections": corridas[c].get("detecciones_totales")} for c, _ in trabajos]
    runs_path = carpeta.escribir("evals/runs.json", runs)
    scorer = ctx.ent.scripts_datasets / "bench" / "run_fase_d_nivel_a.py"
    sc = r.get("scorer") or {}
    cmd = [sys.executable, str(scorer), "--runs", str(runs_path), "--out", str(carpeta.dir / "evals"),
           "--seed", str(sc.get("seed", 20260803)), "--bootstrap", str(sc.get("bootstrap", 1000))]
    carpeta.comando(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    (carpeta.dir / "logs").mkdir(parents=True, exist_ok=True)
    (carpeta.dir / "logs" / "scorer_nivel_a.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"run_fase_d_nivel_a.py rc={proc.returncode}: {proc.stderr[-400:]}")
    metrics = json.loads((carpeta.dir / "evals" / "metrics.json").read_text(encoding="utf-8"))
    actual = aplanar_gate(metrics)
    ref_archivo = (prueba.gen1.get("referencia") or {}).get("archivo")
    ref = aplanar_gate(json.loads((ctx.ent.repo / ref_archivo).read_text())) if ref_archivo else None
    resumen = []
    for clave, g in (metrics.get("gate") or {}).items():
        resumen.append({"clave": f"{clave}/f1_eind", "nombre": f"F1 E-IND por persona — {clave}",
                        "valor": g.get("f1_eind"), "unidad": None,
                        "gen1": (ref or {}).get(f"{clave}.f1_eind")})
        resumen.append({"clave": f"{clave}/f1_edir", "nombre": f"F1 mejor E-DIR ({g.get('best_edir_variant')}) — {clave}",
                        "valor": g.get("f1_edir"), "unidad": None,
                        "gen1": (ref or {}).get(f"{clave}.f1_edir")})
    datos = {"familia": "nivel_a", "estado": "completo", "metricas": actual, "resumen": resumen,
             "veredicto": proponer(actual, prueba, ref)}
    carpeta.resultado(datos)
    return {"estado": "completo", "veredicto": datos["veredicto"]["propuesto"]}


# --- PER-03: Nivel A sobre video ------------------------------------------------------


def _armar_insumos(ctx: Contexto, prueba: Prueba, clips_banco: list[str], clips_piloto: list[str]) -> tuple[Path, Path, dict]:
    r = prueba.receta
    base = ctx.ent.trabajo / prueba.id / "insumos"
    xml_dir, info_dir = base / "xml", base / "info"
    for d in (xml_dir, info_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    huellas = {}
    origenes = [(c, ctx.ent.datasets / r["banco"]["xml"], ctx.ent.datasets / r["banco"]["info"]) for c in clips_banco]
    origenes += [(c, ctx.ent.datasets / r["piloto"]["xml"], ctx.ent.datasets / r["piloto"]["videos"]) for c in clips_piloto]
    for clip, dxml, dinfo in origenes:
        for origen, destino in ((dxml / f"{clip}.xml", xml_dir), (dinfo / f"{clip}.info.json", info_dir)):
            if not origen.is_file():
                raise FileNotFoundError(f"falta {origen}")
            shutil.copy2(origen, destino / origen.name)
            huellas[str(origen.relative_to(ctx.ent.datasets))] = sha256_archivo(origen)
    return xml_dir, info_dir, huellas


@familia("nivel_a_video")
def correr_nivel_a_video(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    origen = ctx.corridas_completas(r["reusa"])
    clips_banco = list(r["banco"]["clips"])
    faltan = [c for c in clips_banco if c not in origen]
    if faltan:
        raise RuntimeError(f"{r['reusa']} no tiene corridas OK de {faltan}")
    clips_piloto = list(r["piloto"]["clips"])
    prompts, constancia = armar_prompts(r["prompts"], ctx.ent.repo)
    pendientes_previos = [c for c in clips_piloto if not carpeta.corrida_ok(c)]
    objetivo = preparar_modelo(ctx, r, carpeta) if pendientes_previos and not ctx.reagregar else None
    trabajos = []
    for clip in clips_piloto:
        video = ctx.ent.datasets / r["piloto"]["videos"] / f"{clip}.mp4"
        if not video.is_file():
            raise FileNotFoundError(f"falta el clip del piloto {video} (viene en el paquete privado)")
        trabajos.append((clip, {
            "ingest": {"plugin": "video_file", "config": {"path": ctx.ent.ruta_medios(video), "source_id": clip}},
            "prompts": prompts,
            "run": {"name": f"gen2_{prueba.id.lower().replace('-', '')}_{clip}", "save_previews": False},
        }))
    carpeta.escribir("configuracion.json", {"prompts": constancia, "modelo_cargado": objetivo,
                                            "clips_banco": clips_banco, "clips_piloto": clips_piloto})
    pendientes = _correr_trabajos(ctx, prueba, carpeta, trabajos, float(r.get("timeout_s", 3600)))
    if pendientes:
        carpeta.resultado({"familia": "nivel_a_video", "estado": "parcial", "pendientes": pendientes})
        return {"estado": "parcial", "pendientes": pendientes}

    corridas = carpeta.corridas()
    runs_map = {c: origen[c]["media_run_id"] for c in clips_banco}
    runs_map.update({c: corridas[c]["media_run_id"] for c in clips_piloto})
    runs_map_path = carpeta.escribir("evals/runs-map.json", runs_map)
    xml_dir, info_dir, huellas = _armar_insumos(ctx, prueba, clips_banco, clips_piloto)
    carpeta.escribir("evals/insumos.sha256.json", huellas)
    salida = carpeta.dir / "evals" / "nivel_a_video.json"
    scorer = ctx.ent.scripts_datasets / "bench" / "score_clip_person_state.py"
    cmd = [sys.executable, str(scorer), "--clips", ",".join(sorted(runs_map)), "--runs-map", str(runs_map_path),
           "--xml-dir", str(xml_dir), "--info-dir", str(info_dir), "--out", str(salida),
           "--stride", str(r.get("stride_puntaje", 15))]
    carpeta.comando(" ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    (carpeta.dir / "logs").mkdir(parents=True, exist_ok=True)
    (carpeta.dir / "logs" / "scorer_nivel_a_video.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"score_clip_person_state.py rc={proc.returncode}: {proc.stderr[-400:]}")
    metrics = json.loads(salida.read_text(encoding="utf-8"))

    def aplanar(m: dict) -> dict:
        return {f"{cond}.{k}": v for cond, d in (m.get("agregado") or {}).items()
                for k, v in d.items() if k in ("tp", "fp", "fn", "n_gt", "n_gt_positive", "precision", "recall", "f1")}

    actual = aplanar(metrics)
    ref_archivo = (prueba.gen1.get("referencia") or {}).get("archivo")
    ref = aplanar(json.loads((ctx.ent.repo / ref_archivo).read_text())) if ref_archivo else None
    resumen = []
    for cond in ("CR-01", "CR-02"):
        for k, nombre in (("f1", "F1"), ("precision", "Precisión"), ("recall", "Recall")):
            resumen.append({"clave": f"{cond}/{k}", "nombre": f"{nombre} por persona-cuadro — {cond}",
                            "valor": actual.get(f"{cond}.{k}"), "unidad": None,
                            "gen1": (ref or {}).get(f"{cond}.{k}")})
    datos = {"familia": "nivel_a_video", "estado": "completo", "metricas": actual, "resumen": resumen,
             "clips": len(runs_map), "veredicto": proponer(actual, prueba, ref)}
    carpeta.resultado(datos)
    return {"estado": "completo", "veredicto": datos["veredicto"]["propuesto"]}
