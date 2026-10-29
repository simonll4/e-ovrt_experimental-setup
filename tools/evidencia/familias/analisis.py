"""Análisis sin GPU sobre lo que dejaron otras pruebas: DEN-07, GT-01, GT-02 y, desde el
2026-10-29 (doc 137), ERR-01, ERR-02 y SEG-01 (módulo `errores`).

- DEN-07: ganancia por identidad por densidad, bootstrap pareado por clip — transcripción de
  la sección 1 de `docs/operacion/datos/96-critica-verificacion.py` (10.000 remuestreos,
  semilla 96, mismos contrastes).
- GT-01: concordancia entre la marca del operador al recortar cada toma (`episode_draft` de
  `datasets-videos/<clip>.clip.yaml`) y el inicio del episodio en el GT corregido.
- GT-02: sensibilidad de cada conclusión a los bordes de la referencia — transcripción de
  `docs/operacion/datos/134-piloto-gt02-sensibilidad-bordes/gt02_{sensibilidad,todas}.py`
  (perturbación U(−J, +J) por borde, evaluador y agregador oficiales, comparación pareada),
  sobre las alertas de la generación 2.
"""
from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from statistics import mean

import yaml

from ..catalogo import Prueba
from ..comparar import proponer
from ..herramientas import clips_de, importar_datasets
from ..huellas import sha256_archivo
from ..registro import Carpeta
from . import Contexto, errores, familia

# --- DEN-07 ---------------------------------------------------------------------------


def _cargar_evals(ctx: Contexto, prueba_id: str) -> dict:
    """clip -> conteos, como `cargar()` del 96-critica (desde la carpeta de la gen 2)."""
    ctx.corridas_completas(prueba_id)  # exige que la prueba esté completa
    out = {}
    for p in sorted((ctx.ent.resultados / prueba_id / "evals").glob("eval_*.json")):
        e = json.loads(p.read_text(encoding="utf-8"))
        cid = e.get("scenario_id") or p.stem.replace("eval_", "")
        out[cid] = {
            "matched": e["matched_alerts_count"],
            "missed": e["missed_alerts_count"],
            "fp": e["unexpected_alerts_count"],
            "t_alert": e.get("avg_latency_ms_from_episode_start"),
            "aplicable": e.get("applicability_state") == "computed",
        }
    return out


def _f1_micro(rows) -> float | None:
    m = sum(r["matched"] for r in rows)
    mi = sum(r["missed"] for r in rows)
    fp = sum(r["fp"] for r in rows)
    if m + mi == 0 or 2 * m + mi + fp == 0:
        return None
    return 2 * m / (2 * m + mi + fp)


def _boot_delta(a: dict, b: dict, clips: list[str], n_boot: int, semilla: int):
    rng = random.Random(semilla)
    obs = _f1_micro([b[c] for c in clips]) - _f1_micro([a[c] for c in clips])
    deltas = []
    for _ in range(n_boot):
        sample = [clips[rng.randrange(len(clips))] for _ in clips]
        fa, fb = _f1_micro([a[c] for c in sample]), _f1_micro([b[c] for c in sample])
        if fa is not None and fb is not None:
            deltas.append(fb - fa)
    deltas.sort()
    lo = deltas[int(0.025 * len(deltas))]
    hi = deltas[int(0.975 * len(deltas))]
    p_le0 = sum(1 for d in deltas if d <= 0) / len(deltas)
    return obs, lo, hi, p_le0


def _den07(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    data = {etiqueta: _cargar_evals(ctx, pid) for etiqueta, pid in r["campanas"].items()}
    referencia = next(iter(r["campanas"]))
    clips = sorted(c for c in data[referencia] if all(data[k].get(c, {}).get("aplicable") for k in data))
    n_boot, semilla = int(r.get("n_boot", 10_000)), int(r.get("semilla", 96))
    filas = {}
    for nombre, a, b in r["contrastes"]:
        obs, lo, hi, p = _boot_delta(data[a], data[b], clips, n_boot, semilla)
        filas[nombre] = {"obs": obs, "ic95": [lo, hi], "p_le0": round(p, 4), "excluye_0": lo > 0 or hi < 0}
    carpeta.escribir("evals/bootstrap.json", {"n_boot": n_boot, "seed": semilla, "clips": clips, "bootstrap": filas})
    metricas = {}
    for nombre, f in filas.items():
        metricas[f"{nombre}.obs"] = round(f["obs"], 6)
        metricas[f"{nombre}.excluye_0"] = f["excluye_0"]
    resumen = [{"clave": n, "nombre": f"ΔF1 {n}", "valor": round(f["obs"], 3), "unidad": None,
                "ic95": [round(f["ic95"][0], 3), round(f["ic95"][1], 3)], "excluye_0": f["excluye_0"],
                "gen1": ((prueba.gen1.get("referencia") or {}).get("valores") or {}).get(f"{n}.obs")}
               for n, f in filas.items()]
    return {"metricas": metricas, "resumen": resumen, "clips_apareados": len(clips)}


# --- GT-01 ----------------------------------------------------------------------------


def _gt01(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    umbrales = [float(u) for u in r.get("umbrales_s", [0.5, 1.0])]
    pares = []
    for clip in clips_de(ctx.ent, r.get("clips", "rodaje")):
        ficha = yaml.safe_load((ctx.ent.datasets / "datasets-videos" / f"{clip}.clip.yaml").read_text())
        gt = json.loads((ctx.ent.gt_banco / f"{clip}.json").read_text())
        for borrador in ficha.get("episode_draft") or []:
            if not borrador.get("condition"):
                continue  # toma negativa: no hay marca de inicio que comparar
            candidatos = [e for e in gt["episodes"] if e.get("condition_id") == borrador["condition"]]
            if not candidatos:
                pares.append({"clip": clip, "condicion": borrador["condition"], "marca_ms": borrador["onset_ms"],
                              "gt_ms": None, "delta_s": None})
                continue
            mejor = min(candidatos, key=lambda e: abs(e["start_ms"] - borrador["onset_ms"]))
            pares.append({"clip": clip, "condicion": borrador["condition"], "marca_ms": borrador["onset_ms"],
                          "gt_ms": mejor["start_ms"],
                          "delta_s": round(abs(mejor["start_ms"] - borrador["onset_ms"]) / 1000, 3)})
    con_gt = [p for p in pares if p["delta_s"] is not None]
    metricas = {"pares": len(con_gt), "sin_episodio_en_gt": len(pares) - len(con_gt)}
    for u in umbrales:
        metricas[f"dentro_de_{u}s"] = sum(1 for p in con_gt if p["delta_s"] <= u)
    carpeta.escribir("evals/concordancia.json", {"umbrales_s": umbrales, "pares": pares})
    resumen = [{"clave": f"dentro_de_{u}s", "nombre": f"Marcas del operador a ≤ {u} s del inicio en el GT",
                "valor": f"{metricas[f'dentro_de_{u}s']}/{metricas['pares']}", "unidad": None,
                "gen1": ((prueba.gen1.get("referencia") or {}).get("valores") or {}).get(f"dentro_de_{u}s")}
               for u in umbrales]
    return {"metricas": metricas, "resumen": resumen}


# --- GT-02 ----------------------------------------------------------------------------

COMPARE_POS = ["episodes_total", "episodes_censored", "episodes_evaluable", "matched",
               "missed", "false_positives", "re_alerts", "sub_threshold",
               "recall_micro", "precision_micro", "f1_micro"]


def _temporal():
    from eovrt_control.evaluation import temporal  # noqa: PLC0415 (lo instala la imagen / el venv)

    return temporal


def _clamp(s, e, d, dur):
    s2 = max(0.0, s + d[0])
    e2 = e + d[1]
    if dur is not None:
        e2 = min(float(dur), e2)
        s2 = min(s2, float(dur))
    return s2, max(s2, e2)


def _perturbar(gt, shifts_ep, shifts_sub):
    dur = gt.duration_ms
    eps = []
    for ep, d in zip(gt.episodes, shifts_ep):
        s, e = _clamp(ep.start_ms, ep.end_ms, d, dur)
        eps.append(ep.model_copy(update={"start_ms": s, "end_ms": e}))
    subs = []
    for ev, d in zip(gt.sub_threshold_events, shifts_sub):
        s, e = _clamp(ev.start_ms, ev.end_ms, d, dur)
        subs.append(ev.model_copy(update={"start_ms": s, "end_ms": e}))
    return gt.model_copy(update={"episodes": eps, "sub_threshold_events": subs})


def _evaluar_banco(ctx, clips, gts, alertas, rutas, shifts_de):
    T = _temporal()
    agg = importar_datasets(ctx.ent, "bench.aggregate_clip_campaign")
    filas = []
    for c in clips:
        gt = gts[c]
        se, ss = shifts_de(gt)
        pg = _perturbar(gt, se, ss)
        win = T._resolve_matching_windows(pg, None)
        ev = T._evaluate_v2(alertas[c], pg, rutas[c], ctx.ent.gt_banco / f"{c}.json", win)
        filas.append({"clip_id": c, "eval": ev.model_dump(mode="json"), "gt": pg.model_dump(mode="json")})
    original = agg._load
    agg._load = lambda *_a, **_k: filas
    try:
        return agg.aggregate_campaign("mem", "mem")
    finally:
        agg._load = original


def _pick(m):
    p, n = m["positives"], m["negatives"]
    return {**{k: p[k] for k in COMPARE_POS}, "neg_false_positives": n["false_positives"]}


def _pct(xs, q):
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, round(q * (len(xs) - 1))))
    return xs[k]


# Conclusión -> (campañas que compara, chequeo). Los nombres son los del piloto 134.
CHEQUEOS = {
    "C1_G1>T1": (("G1", "T1"), lambda r: r["G1"]["f1"] > r["T1"]["f1"]),
    "C2_T1>=T2": (("T1", "T2"), lambda r: r["T1"]["f1"] >= r["T2"]["f1"]),
    "C3_D1_prec<0.5": (("D1",), lambda r: (r["D1"]["p"] or 0.0) < 0.5),
    "C4_T1>H1": (("T1", "H1"), lambda r: r["T1"]["f1"] > r["H1"]["f1"]),
    "C5_T1>B1": (("T1", "B1"), lambda r: r["T1"]["f1"] > r["B1"]["f1"]),
    "C6_R2>R1": (("R2", "R1"), lambda r: r["R2"]["f1"] > r["R1"]["f1"]),
    "C6_R4>R3": (("R4", "R3"), lambda r: r["R4"]["f1"] > r["R3"]["f1"]),
    "C6_R6>R5": (("R6", "R5"), lambda r: r["R6"]["f1"] > r["R5"]["f1"]),
    "C7_T1>=R1": (("T1", "R1"), lambda r: r["T1"]["f1"] >= r["R1"]["f1"]),
    "C7_R1>R3": (("R1", "R3"), lambda r: r["R1"]["f1"] > r["R3"]["f1"]),
    "C7_R3>R5": (("R3", "R5"), lambda r: r["R3"]["f1"] > r["R5"]["f1"]),
    "C8_I1_FPneg<I2_FPneg": (("I1", "I2"), lambda r: r["I1"]["fpneg"] < r["I2"]["fpneg"]),
}


def chequeos_para(etiquetas) -> tuple[dict, list[str]]:
    """(chequeos que se pueden evaluar con estas campañas, los que quedan solo con la gen 1).

    Las pruebas de contraste no se regeneran (doc 134 §13.6): sus conclusiones (C2–C5)
    conservan la fracción del piloto de la generación 1.
    """
    hay = set(etiquetas)
    evaluables = {k: f for k, (req, f) in CHEQUEOS.items() if hay.issuperset(req)}
    return evaluables, [k for k in CHEQUEOS if k not in evaluables]


def _piloto_gen1(ctx: Contexto, receta: dict) -> dict | None:
    ruta = receta.get("piloto_gen1")
    if not ruta:
        return None
    archivo = ctx.ent.ws / ruta
    if not archivo.is_file():
        ctx.avisar(f"    aviso: no está el piloto de la generación 1 ({ruta}); la columna gen 1 queda vacía")
        return None
    return json.loads(archivo.read_text(encoding="utf-8"))


def _gt02(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    T = _temporal()
    # El evaluador avisa por logging en cada clip negativo; en 5.000 réplicas × 3 J × las
    # campañas eso son cientos de miles de líneas. El aviso no cambia ningún número.
    logging.getLogger(T.__name__).setLevel(logging.ERROR)
    r = prueba.receta
    chequeos, solo_gen1 = chequeos_para(r["campanas"])
    piloto = _piloto_gen1(ctx, r)
    n, semilla = int(r.get("n", 5000)), int(r.get("semilla", 20261025))
    js = [int(j) for j in r.get("J_ms", [500, 1000, 2000])]
    bancos = {}
    for nombre_banco, seleccion in (("a", "rodaje"), ("v", "internet")):
        clips = clips_de(ctx.ent, seleccion)
        bancos[nombre_banco] = (clips, {c: T._load_ground_truth(ctx.ent.gt_banco / f"{c}.json") for c in clips})
    campanas = {}
    for etiqueta, spec in r["campanas"].items():
        pid, banco = spec["prueba"], spec["banco"]
        variante = spec.get("variante")
        corridas = ctx.corridas_completas(pid)
        clips, gts = bancos[banco]
        alertas, rutas = {}, {}
        for c in clips:
            reg = corridas[c]
            if variante:
                reg = (reg.get("variantes") or {})[variante]
            ruta = ctx.ent.control_runs / reg["control_run_id"] / "alerts.jsonl"
            rutas[c] = ruta
            alertas[c] = T._load_alerts(ruta)
        base = _pick(_evaluar_banco(ctx, clips, gts, alertas, rutas, lambda gt: ([(0.0, 0.0)] * len(gt.episodes),
                                                                              [(0.0, 0.0)] * len(gt.sub_threshold_events))))
        publicado = json.loads((ctx.ent.resultados / pid / (f"variantes/{variante}/metrics.json" if variante else "metrics.json")).read_text())
        if base != _pick(publicado):
            raise RuntimeError(f"[{etiqueta}] V1 FALLA: el arnés no reproduce el metrics.json de {pid}")
        campanas[etiqueta] = {"prueba": pid, "variante": variante, "banco": banco, "alertas": alertas, "rutas": rutas,
                              "base": base, "alerts_sha256": {c: sha256_archivo(p) for c, p in rutas.items()}}
        ctx.avisar(f"    [{etiqueta}] V1 ok · F1 {base['f1_micro']} · FP neg {base['neg_false_positives']}")
    fila_base = {k: {"f1": c["base"]["f1_micro"], "p": c["base"]["precision_micro"],
                     "fpneg": c["base"]["neg_false_positives"]} for k, c in campanas.items()}
    res = {"schema": "gt02_todas.gen2.v1", "n": n, "seed": semilla,
           "campaigns": {k: {"prueba": c["prueba"], "variante": c["variante"], "base": c["base"],
                             "alerts_sha256": c["alerts_sha256"]} for k, c in campanas.items()},
           "conclusiones_base": {k: bool(f(fila_base)) for k, f in chequeos.items()}, "por_J": {}}
    if solo_gen1:
        res["solo_generacion_1"] = {
            "conclusiones": solo_gen1,
            "motivo": "sus campañas son pruebas de contraste que no se regeneran (doc 134 §13.6)",
            "fuente": r.get("piloto_gen1"),
            "frac_sostenida": ({J: {k: v["frac_sostenida"].get(k) for k in solo_gen1}
                                for J, v in piloto["por_J"].items()} if piloto else None),
        }
    for J in js:
        rng = random.Random(f"{semilla}-todas-{J}")
        t0 = time.time()
        f1s = {k: [] for k in campanas}
        sostenidas = {k: 0 for k in chequeos}
        for _ in range(n):
            shifts = {}
            for _banco, (clips, gts) in bancos.items():
                for c in clips:
                    gt = gts[c]
                    shifts[c] = ([(rng.uniform(-J, J), rng.uniform(-J, J)) for _ in gt.episodes],
                                 [(rng.uniform(-J, J), rng.uniform(-J, J)) for _ in gt.sub_threshold_events])
            fila = {}
            for k, c in campanas.items():
                clips, gts = bancos[c["banco"]]
                m = _evaluar_banco(ctx, clips, gts, c["alertas"], c["rutas"], lambda gt: shifts[gt.clip_id])
                fila[k] = {"f1": m["positives"]["f1_micro"], "p": m["positives"]["precision_micro"],
                           "fpneg": m["negatives"]["false_positives"]}
                f1s[k].append(fila[k]["f1"])
            for k, f in chequeos.items():
                sostenidas[k] += bool(f(fila))
        res["por_J"][f"J{J}"] = {
            "frac_sostenida": {k: round(v / n, 4) for k, v in sostenidas.items()},
            "f1_rango_central_95": {k: [_pct(v, .025), _pct(v, .975)] for k, v in f1s.items()},
            "f1_media": {k: round(mean(v), 6) for k, v in f1s.items()},
            "segundos": round(time.time() - t0, 1),
        }
        ctx.avisar(f"    J{J}: {res['por_J'][f'J{J}']['frac_sostenida']}")
    carpeta.escribir("evals/gt02.json", res)
    metricas = {f"J{J}.{k}": v for J in js for k, v in res["por_J"][f"J{J}"]["frac_sostenida"].items()}
    gen1_j500 = ((piloto or {}).get("por_J") or {}).get("J500", {}).get("frac_sostenida", {})
    resumen = [{"clave": k, "nombre": f"Fracción de referencias simuladas (±0,5 s) en que se sostiene {k}",
                "valor": res["por_J"]["J500"]["frac_sostenida"][k] if "J500" in res["por_J"] else None,
                "unidad": None, "gen1": gen1_j500.get(k)} for k in chequeos]
    return {"metricas": metricas, "resumen": resumen, "conclusiones_base": res["conclusiones_base"],
            **({"solo_generacion_1": res["solo_generacion_1"]} if solo_gen1 else {})}


_PRUEBAS = {"DEN-07": _den07, "GT-01": _gt01, "GT-02": _gt02,
            "ERR-01": errores.anatomia, "ERR-02": errores.anatomia, "SEG-01": errores.fragmentacion}


@familia("analisis")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    funcion = _PRUEBAS.get(prueba.id)
    if funcion is None:
        raise ValueError(f"{prueba.id}: no hay análisis definido para esta prueba")
    salida = funcion(ctx, prueba, carpeta)
    datos = {"familia": "analisis", "estado": "completo", **salida,
             "veredicto": proponer(salida["metricas"], prueba)}
    carpeta.resultado(datos)
    return {"estado": "completo", "veredicto": datos["veredicto"]["propuesto"]}
