"""Campañas sobre el banco temporal de clips (Tabla 53 y filas de densidad de la Tabla 54).

Misma cadena que los runners de la generación 1 (`docs/operacion/datos/81-…`, `85-…`,
`87-…`, `88-…`, `89-…`, `96-…`, `102-…`), pero por el runner de la consola:

    inferencia: media (video_file, prompts congelados) → control replay → evaluate-alerts
    reuso:      detecciones de otra prueba → control replay (otra granularidad o densidad)
    fusion:     fusión E-IND + E-DIR de otras dos pruebas → control replay (H1)

y al final `aggregate_clip_campaign.aggregate_campaign` contra el GT CORREGIDO del banco
(`datasets/processed/clip_bench/gt/`). Cada clip es un experimento; la campaña se retoma
donde quedó.

Diferencia deliberada con la generación 1: la granularidad por sujeto no rastrea post-hoc
(`track_event_stream` + `tracked.jsonl`) sino con la identidad de la plataforma
(`input.track_persons: true`, `sources/tracking.py`), que usa el mismo `SimpleIoUTracker`.
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from ..catalogo import Prueba
from ..comparar import proponer
from ..herramientas import (
    clips_de,
    cuadros_esperados,
    escribir_yaml,
    evaluar_alertas,
    importar_datasets,
    resumen_media,
    ruta_video,
)
from ..huellas import armar_prompts, sha256_archivo
from ..registro import Carpeta, ahora
from . import Contexto, familia, preparar_modelo

TIMEOUT_S = 3600.0
TOLERANCIA_STRIDE = 2  # mismo guard que 96-costo-tiempo-real-runner.py

CAMPOS_POSITIVOS = (
    "episodes_total",
    "episodes_censored",
    "episodes_evaluable",
    "matched",
    "missed",
    "false_positives",
    "re_alerts",
    "sub_threshold",
    "recall_micro",
    "precision_micro",
    "f1_micro",
)

RESUMEN = (
    # (clave, nombre, campo de metrics, unidad, escala)
    ("f1", "F1 por episodio (micro)", ("positives", "f1_micro"), None, 1),
    ("precision", "Precisión", ("positives", "precision_micro"), None, 1),
    ("recall", "Recall", ("positives", "recall_micro"), None, 1),
    ("episodios_evaluables", "Episodios evaluables", ("positives", "episodes_evaluable"), None, 1),
    ("aciertos", "Alertas que acertaron un episodio", ("positives", "matched"), None, 1),
    ("perdidos", "Episodios sin alerta", ("positives", "missed"), None, 1),
    ("falsas_alarmas_en_positivos", "Falsas alarmas en clips con episodios", ("positives", "false_positives"), None, 1),
    ("falsas_alarmas", "Falsas alarmas en clips sin infracción", ("negatives", "false_positives"), None, 1),
    ("re_alertas", "Re-alertas (no son falsas alarmas)", ("positives", "re_alerts"), None, 1),
    ("t_alert_s", "Tiempo hasta la alerta desde el inicio del episodio", ("positives", "t_alert_system_ms"), "s", 0.001),
    ("ttfd_ms", "Tiempo hasta la primera detección", ("positives", "ttfd_ms"), "ms", 1),
    ("sdr", "Proporción de detección sostenida (SDR)", ("positives", "sdr"), None, 1),
)
_GEN1_CAMPO = {
    "f1": "f1_micro",
    "precision": "precision_micro",
    "recall": "recall_micro",
    "episodios_evaluables": "episodes_evaluable",
    "aciertos": "matched",
    "perdidos": "missed",
    "falsas_alarmas_en_positivos": "false_positives",
    "falsas_alarmas": "neg_false_positives",
    "re_alertas": "re_alerts",
}


def valores_campana(metrics: dict) -> dict:
    """Los 12 campos que compara GT-02 (V1): 11 de positivos + FP en negativos."""
    pos = metrics.get("positives") or {}
    return {
        **{k: pos.get(k) for k in CAMPOS_POSITIVOS},
        "neg_false_positives": (metrics.get("negatives") or {}).get("false_positives"),
    }


def resumen(metrics: dict, gen1_valores: dict | None) -> list[dict]:
    filas = []
    for clave, nombre, (bloque, campo), unidad, escala in RESUMEN:
        valor = (metrics.get(bloque) or {}).get(campo)
        if isinstance(valor, (int, float)) and escala != 1:
            valor = round(valor * escala, 3)
        gen1 = (gen1_valores or {}).get(_GEN1_CAMPO.get(clave, ""))
        filas.append({"clave": clave, "nombre": nombre, "valor": valor, "unidad": unidad, "gen1": gen1})
    return filas


def _nombre(prueba: Prueba, clip: str, sufijo: str = "") -> str:
    base = f"gen2_{prueba.id.lower().replace('-', '')}"
    return f"{base}_{sufijo}_{clip}" if sufijo else f"{base}_{clip}"


def _config_control(ctx: Contexto, spec: dict, nombre: str, descripcion: str) -> tuple[dict, Path]:
    patrones = ctx.ent.patrones / f"{spec['patrones']}.yaml"
    if not patrones.is_file():
        raise FileNotFoundError(f"pattern set inexistente: {patrones}")
    entrada: dict = {"type": "media_jsonl", "path": "(la completa el runner de la consola)"}
    if spec.get("track_persons"):
        entrada["track_persons"] = True
    config = {
        "run": {"id": None, "scenario": "DBE", "name": nombre, "description": descripcion},
        "input": entrada,
        "patterns": {"file": str(patrones), "active_ids": list(spec.get("activos") or ["CR-01", "CR-02"])},
        "outputs": {
            "base_dir": str(ctx.ent.control_runs),
            "save_pattern_events_jsonl": True,
            "save_alerts_jsonl": True,
            "save_metrics_jsonl": True,
            "save_errors_jsonl": True,
            "save_summary_json": True,
        },
        "logging": {"level": "WARNING"},
    }
    return config, patrones


def slug_de(prueba: Prueba) -> str:
    """Todos los experimentos de una prueba comparten su slug (`gen2_alr01`): la consola los
    agrupa por slug. El `experiment_id` explicito, con la hora y la clave, los distingue."""
    return f"gen2_{prueba.id.lower().replace('-', '')}"


def experiment_id_de(nombre: str) -> str:
    return f"exp_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{nombre}"


def _manifiesto(prueba: Prueba, clip: str, nombre: str, runs: dict, gt: Path, timeout_s: float) -> dict:
    return {
        "schema_version": "experiment.manifest.v1",
        "slug": slug_de(prueba),
        "experiment_id": experiment_id_de(nombre),
        "runs": runs,
        "sequencing": "media_first",
        "clip_id": clip,
        "ground_truth": str(gt),
        "timeout_s": timeout_s,
        "changes": f"generación 2 — prueba {prueba.id} ({prueba.titulo})",
    }


def _replay(
    ctx: Contexto,
    prueba: Prueba,
    carpeta: Carpeta,
    clip: str,
    *,
    nombre: str,
    runs_media: dict,
    control_spec: dict,
    detecciones,
    evals_dir: Path,
    timeout_s: float,
) -> dict:
    """Dispara un experimento (inferencia o reuso) y evalúa sus alertas. Devuelve el registro."""
    ent = ctx.ent
    gt = ent.gt_banco / f"{clip}.json"
    dir_gen = ent.generados / prueba.id / nombre
    control_cfg, patrones = _config_control(
        ctx, control_spec, nombre, f"Generación 2, {prueba.id}: {prueba.titulo} — {clip}"
    )
    control_path = escribir_yaml(dir_gen / "control.yaml", control_cfg)
    runs = {
        "media": runs_media,
        "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
    }
    manifiesto = _manifiesto(prueba, clip, nombre, runs, gt, timeout_s)
    escribir_yaml(dir_gen / "manifest.yaml", manifiesto)
    carpeta.guardar_ejemplo(dir_gen)
    carpeta.comando(f"POST /api/experiments/run  manifiesto={dir_gen / 'manifest.yaml'}")
    t0 = time.monotonic()
    inicio = ahora()
    estado = ctx.consola.correr(manifiesto, timeout_s=timeout_s)
    registro = {
        "estado": "ok" if estado.get("ok") else "fallo",
        "experiment_id": estado.get("experiment_id"),
        "media_run_id": estado.get("media_run_id"),
        "control_run_id": estado.get("control_run_id"),
        "media_status": estado.get("media_status"),
        "control_status": estado.get("control_status"),
        "inicio": inicio,
        "fin": ahora(),
        "segundos": round(time.monotonic() - t0, 1),
        "media_config": runs_media.get("config"),
        "control_config": str(control_path),
        "sha256": {"control_config": sha256_archivo(control_path), "patrones": sha256_archivo(patrones)},
    }
    if runs_media.get("config") and Path(runs_media["config"]).is_file():
        registro["sha256"]["media_config"] = sha256_archivo(Path(runs_media["config"]))
    if not estado.get("ok"):
        registro["error"] = estado.get("error") or (
            f"media={estado.get('media_status')} control={estado.get('control_status')}"
        )
        return registro
    alertas = ent.control_runs / registro["control_run_id"] / "alerts.jsonl"
    det = detecciones(registro) if callable(detecciones) else Path(detecciones)
    salida = evals_dir / f"eval_{clip}.json"
    cmd = evaluar_alertas(ent, alertas=alertas, gt=gt, detecciones=det, patrones=patrones, salida=salida)
    carpeta.comando(" ".join(cmd))
    registro["detecciones"] = str(det)
    registro["eval"] = str(salida.relative_to(carpeta.dir))
    registro["sha256"]["gt"] = sha256_archivo(gt)
    return registro


@familia("clips")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    tipo = r.get("tipo", "inferencia")
    ent = ctx.ent
    clips = clips_de(ent, r["clips"])
    if ctx.solo:
        clips = [c for c in clips if c in ctx.solo]
    timeout_s = float(r.get("timeout_s", TIMEOUT_S))
    evals_dir = carpeta.dir / "evals"
    stride = int((r.get("medios") or {}).get("stride", 1))

    objetivo = None
    prompts_payload = constancia_prompts = None
    origen: dict = {}
    if tipo == "inferencia":
        prompts_payload, constancia_prompts = armar_prompts(r["medios"]["prompts"], ent.repo)
        if not ctx.reagregar:
            objetivo = preparar_modelo(ctx, r, carpeta)
    elif tipo == "reuso":
        origen = ctx.corridas_completas(r["reusa"])
    elif tipo == "fusion":
        origen = {
            "eind": ctx.corridas_completas(r["fusion"]["eind"]),
            "edir": ctx.corridas_completas(r["fusion"]["edir"]),
        }
    else:
        raise ValueError(f"{prueba.id}: tipo de receta inválido {tipo!r}")
    carpeta.escribir("configuracion.json", {
        "tipo": tipo,
        "clips": clips,
        "prompts": constancia_prompts,
        "modelo_cargado": objetivo,
        "control": r["control"],
        "variantes": r.get("variantes") or [],
        "stride": stride,
    })

    variantes = r.get("variantes") or []
    for i, clip in enumerate(clips, 1):
        previo = carpeta.corridas().get(clip) or {}
        hecho = previo.get("estado") == "ok"
        variantes_hechas = all(
            (previo.get("variantes") or {}).get(v["nombre"], {}).get("estado") == "ok" for v in variantes
        )
        if hecho and variantes_hechas:
            continue
        if ctx.reagregar:
            continue
        ctx.avisar(f"  [{i}/{len(clips)}] {prueba.id} {clip}")
        if not hecho:
            registro = _correr_clip(ctx, prueba, carpeta, clip, tipo=tipo, stride=stride,
                                    prompts_payload=prompts_payload, origen=origen,
                                    evals_dir=evals_dir, timeout_s=timeout_s)
            carpeta.guardar_corrida(clip, registro)
            if registro["estado"] != "ok":
                ctx.avisar(f"      FALLÓ: {registro.get('error')}")
                continue
            previo = registro
        for variante in variantes:
            hechas = previo.setdefault("variantes", {})
            if hechas.get(variante["nombre"], {}).get("estado") == "ok":
                continue
            nombre = _nombre(prueba, clip, variante["nombre"])
            reg = _replay(
                ctx, prueba, carpeta, clip, nombre=nombre,
                runs_media={"service": "media-plane", "config": previo.get("media_config"),
                            "mode": "run", "reuse_run_id": previo["media_run_id"]},
                control_spec=variante["control"],
                detecciones=previo["detecciones"],
                evals_dir=carpeta.dir / "variantes" / variante["nombre"] / "evals",
                timeout_s=timeout_s,
            )
            hechas[variante["nombre"]] = reg
            carpeta.guardar_corrida(clip, previo)
            if reg["estado"] != "ok":
                ctx.avisar(f"      variante {variante['nombre']} FALLÓ: {reg.get('error')}")

    return _cerrar(ctx, prueba, carpeta, clips, variantes)


def _correr_clip(ctx, prueba, carpeta, clip, *, tipo, stride, prompts_payload, origen, evals_dir, timeout_s):
    ent = ctx.ent
    r = prueba.receta
    nombre = _nombre(prueba, clip)
    dir_gen = ent.generados / prueba.id / nombre
    if tipo == "inferencia":
        # Una campaña dura horas: si alguien cambió la instancia activa desde la consola a
        # mitad de camino, el resto de los clips mediría otro modelo. Se verifica por clip.
        cargado = ((ctx.consola.objetivo().get("model") or {}).get("ref"))
        if r.get("modelo") and cargado != r["modelo"]:
            return {"estado": "fallo",
                    "error": f"el modelo cargado cambió a {cargado!r} (la prueba pide {r['modelo']!r})"}
        run = {"name": nombre, "save_previews": False}
        if stride != 1:
            run["stride"] = stride
        media_cfg = {
            "ingest": {"plugin": "video_file", "config": {
                "path": ent.ruta_medios(ruta_video(ent, clip)), "source_id": clip}},
            "prompts": prompts_payload,
            "run": run,
        }
        media_path = escribir_yaml(dir_gen / "media.yaml", media_cfg)
        runs_media = {"service": "media-plane", "config": str(media_path), "mode": "run"}

        def detecciones(reg):
            return ent.media_runs / reg["media_run_id"] / "detections.jsonl"
    elif tipo == "reuso":
        fuente = origen.get(clip)
        if not fuente:
            return {"estado": "fallo", "error": f"{r['reusa']} no tiene una corrida OK de {clip}"}
        runs_media = {"service": "media-plane", "config": fuente.get("media_config"),
                      "mode": "run", "reuse_run_id": fuente["media_run_id"]}
        detecciones = fuente["detecciones"]
    else:  # fusion
        eind, edir = origen["eind"].get(clip), origen["edir"].get(clip)
        if not eind or not edir:
            return {"estado": "fallo", "error": f"falta la corrida E-IND o E-DIR de {clip}"}
        merge = importar_datasets(ent, "bench.merge_dual_run")
        fusion_dir = ent.trabajo / prueba.id / f"fusion_{clip}"
        fusion_dir.mkdir(parents=True, exist_ok=True)
        det = fusion_dir / "detections.jsonl"
        clases = tuple(r["fusion"].get("clases_directas") or ("cr01_spec", "cr02_obs"))
        stats = merge.merge_detection_streams(Path(eind["detecciones"]), Path(edir["detecciones"]), det, clases)
        carpeta.comando(
            f"merge_detection_streams({eind['detecciones']}, {edir['detecciones']}, {det}, {clases})"
        )
        (fusion_dir / "summary.json").write_text(json.dumps({
            "run_id": fusion_dir.name,
            "status": "succeeded",
            "fusion": {"eind_media_run_id": eind["media_run_id"], "edir_media_run_id": edir["media_run_id"],
                       "clases_directas": list(clases), **stats},
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        runs_media = {"service": "media-plane", "config": eind.get("media_config"),
                      "mode": "run", "reuse_run_dir": str(fusion_dir)}
        detecciones = det

    registro = _replay(ctx, prueba, carpeta, clip, nombre=nombre, runs_media=runs_media,
                       control_spec=r["control"], detecciones=detecciones,
                       evals_dir=evals_dir, timeout_s=timeout_s)
    if tipo == "inferencia" and registro.get("estado") == "ok":
        resumen_m = resumen_media(ent, registro["media_run_id"])
        registro["unidades"] = resumen_m.get("units_processed")
        registro["fps_efectivos"] = resumen_m.get("fps_effective")
        registro["modelo"] = resumen_m.get("model_name")
        if stride > 1:
            esperado = cuadros_esperados(ent, clip, stride)
            unidades = registro["unidades"] or 0
            if abs(unidades - esperado) > TOLERANCIA_STRIDE:
                registro["estado"] = "fallo"
                registro["error"] = (
                    f"guard de stride: {unidades} cuadros procesados, se esperaban ~{esperado} "
                    f"(stride {stride}): la corrida no midió la densidad declarada"
                )
    return registro


def _agregar(ctx: Contexto, prueba: Prueba, evals_dir: Path, nombre_variante: str | None = None) -> dict:
    agg = importar_datasets(ctx.ent, "bench.aggregate_clip_campaign")
    campana = {
        "prueba": prueba.id,
        "titulo": prueba.titulo,
        "variante": nombre_variante,
        "config": prueba.datos.get("config"),
        "gt": "datasets/processed/clip_bench/gt (corregido, revisión dirigida 2026-10-26)",
    }
    return agg.aggregate_campaign(evals_dir, ctx.ent.gt_banco, campana)


def _comparar_por_clip(ctx: Contexto, prueba: Prueba, evals_dir: Path, clips: list[str]) -> dict | None:
    """Clip a clip contra las evaluaciones publicadas de la gen 1 (GT anterior): un clip cuyo GT
    no cambió debería dar idéntico; uno de los 8 corregidos, no necesariamente."""
    rel = prueba.gen1.get("evals")
    if not rel:
        return None
    dir_gen1 = ctx.ent.repo / rel
    if not dir_gen1.is_dir():
        return {"nota": f"no está {rel} en este workspace"}
    corregidos = set(prueba.gen1.get("clips_gt_corregido") or [])
    campos = ("matched_alerts_count", "missed_alerts_count", "unexpected_alerts_count", "re_alerts_count",
              "avg_latency_ms_from_episode_start")
    iguales, distintos = [], []
    for clip in clips:
        a, b = evals_dir / f"eval_{clip}.json", dir_gen1 / f"eval_{clip}.json"
        if not (a.is_file() and b.is_file()):
            continue
        ea, eb = json.loads(a.read_text()), json.loads(b.read_text())
        difs = {k: [ea.get(k), eb.get(k)] for k in campos if ea.get(k) != eb.get(k)}
        if difs:
            distintos.append({"clip": clip, "gt_corregido": clip in corregidos, "diferencias": difs})
        else:
            iguales.append(clip)
    return {"campos": list(campos), "iguales": len(iguales), "distintos": distintos,
            "distintos_sin_gt_corregido": [d["clip"] for d in distintos if not d["gt_corregido"]]}


def _cerrar(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, clips: list[str], variantes: list[dict]) -> dict:
    corridas = carpeta.corridas()
    pendientes = [c for c in clips if (corridas.get(c) or {}).get("estado") != "ok"]
    pendientes_var = [
        f"{c}:{v['nombre']}" for c in clips for v in variantes
        if ((corridas.get(c) or {}).get("variantes") or {}).get(v["nombre"], {}).get("estado") != "ok"
    ]
    base = {
        "familia": "clips",
        "corridas": {"total": len(clips), "ok": len(clips) - len(pendientes)},
        "pendientes": pendientes + pendientes_var,
    }
    if pendientes or pendientes_var:
        carpeta.resultado({**base, "estado": "parcial",
                           "nota": "faltan clips: volvé a correr la prueba para retomarla"})
        return {"estado": "parcial", "pendientes": base["pendientes"]}

    metrics = _agregar(ctx, prueba, carpeta.dir / "evals")
    carpeta.escribir("metrics.json", metrics)
    valores = valores_campana(metrics)
    gen1_valores = ((prueba.gen1.get("referencia") or {}).get("valores")) or {}
    datos = {
        **base,
        "estado": "completo",
        "metricas": valores,
        "resumen": resumen(metrics, gen1_valores),
        "veredicto": proponer(valores, prueba),
        "por_clip_vs_gen1_publicada": _comparar_por_clip(ctx, prueba, carpeta.dir / "evals", clips),
    }
    if variantes:
        datos["variantes"] = {}
        for v in variantes:
            m = _agregar(ctx, prueba, carpeta.dir / "variantes" / v["nombre"] / "evals", v["nombre"])
            carpeta.escribir(f"variantes/{v['nombre']}/metrics.json", m)
            datos["variantes"][v["nombre"]] = {
                "metricas": valores_campana(m),
                "resumen": resumen(m, (v.get("gen1") or {}).get("valores")),
                "gen1": v.get("gen1"),
            }
    carpeta.resultado(datos)
    return {"estado": "completo", "f1": valores.get("f1_micro"), "veredicto": datos["veredicto"]["propuesto"]}
