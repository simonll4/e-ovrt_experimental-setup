"""Anatomía de las falsas alarmas (ERR-01, ERR-02) y fragmentación de identidad (SEG-01).

Análisis sin GPU sobre lo que dejaron las pruebas de clips: las detecciones de la corrida de
medios, las alertas y la traza del motor de la corrida por sujeto, y la referencia de CVAT
(`clip_bench/annotations/<clip>.xml`: cajas cuadro a cuadro, atributos por tramo y
trayectorias ya corregidas por la revisión dirigida; su huella es la `xml_sha256` del GT).

La identidad por cuadro no se persiste en la generación 2: la pone la plataforma con
`input.track_persons` (doc 134 §13.2). Acá se reconstruye con
`eovrt_control.tools.track_detections`, que es el mismo `SimpleIoUTracker` sobre el mismo
stream en orden (equivalencia verificada en doc 134 §13.4). Cada alerta se coteja con la
reconstrucción: si la caja del sujeto en la alerta no es la del track reconstruido en ese
cuadro, se cuenta como discrepancia y se informa.

Taxonomía de una falsa alarma por sujeto (doc 137 §3.1). Se decide por mayoría sobre los
cuadros de su ventana, que va desde la última entrada del sujeto en `candidate` hasta la
alerta (traza del motor; si falta, la ventana de confirmación del pattern set):

  F-sin-persona   el track no coincide con ninguna persona de la referencia (IoU ≤ 0,1)
  F-parcial       se solapa con una persona de la referencia sin cubrirla (0,1 < IoU < 0,3)
  U               la referencia marca el atributo como no observable
  V               la referencia marca la falta (una falta real, breve o fuera de episodio)
  P-no-detectado  la referencia dice que el EPP estaba y el detector no lo vio sobre la persona
  P-fuera-region  el EPP se detectó sobre la persona, pero fuera de la región que evalúa la regla
  P-disputado     el EPP estaba en la región y también en la de otra persona (asignación)
  P-intermitente  el EPP estaba en la región, sin disputa, pero no lo bastante seguido para
                  resolver la ausencia (`resolve_after_ms` del pattern set)

Las alertas que caen sobre la MISMA persona de la referencia y la misma condición con tracks
distintos miden la fragmentación de identidad (el «ID switch» que multiplica alertas).
"""
from __future__ import annotations

import csv
import json
import random
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

import yaml

from ..catalogo import Prueba
from ..herramientas import clips_de
from ..huellas import sha256_archivo
from ..registro import Carpeta
from . import Contexto

IOU_PERSONA = 0.3  # alerta ↔ persona de la referencia (mismo umbral que el sondeo)
IOU_PARCIAL = 0.1
IOU_SEGUIMIENTO = 0.5  # cuadro a cuadro, para la fragmentación (umbral habitual en MOT)
BANDAS_PX = ((0, 80), (80, 120), (120, 220), (220, 320), (320, 10_000))
CAUSAS = ("F-sin-persona", "F-parcial", "U", "V", "P-no-detectado", "P-fuera-region",
          "P-disputado", "P-intermitente")
GRUESA = {"F-sin-persona": "sin_persona", "F-parcial": "sin_persona", "U": "no_juzgable",
          "V": "falta_real", "P-no-detectado": "tiene_epp", "P-fuera-region": "tiene_epp",
          "P-disputado": "tiene_epp", "P-intermitente": "tiene_epp"}

# --- geometría ------------------------------------------------------------------------


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def centro(b) -> tuple[float, float]:
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def dentro(p, r) -> bool:
    return r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]


def region(caja, spec: dict) -> list[float]:
    """La región del motor (`spatial_absence._region_bbox`), con su regla de sujeto agachado."""
    x1, y1, x2, y2 = caja
    ancho, alto = max(0.0, x2 - x1), max(0.0, y2 - y1)
    y0, y1r = float(spec.get("y_min_ratio", 0.0)), float(spec.get("y_max_ratio", 1.0))
    limite = spec.get("full_height_aspect_ratio")
    if limite is not None and alto > 0 and ancho / alto >= float(limite):
        y0, y1r = 0.0, 1.0
    mx = ancho * float(spec.get("x_margin_ratio", 0.0))
    return [x1 + mx, y1 + alto * y0, x2 - mx, y1 + alto * y1r]


def banda(alto: float) -> str:
    for lo, hi in BANDAS_PX:
        if lo <= alto < hi:
            return f"{lo}-{hi}" if hi < 10_000 else f">={lo}"
    return "?"


# --- insumos --------------------------------------------------------------------------


def patrones_por_condicion(ruta: Path) -> dict[str, dict]:
    """condición → {clase ausente, región, umbral del EPP, ventana de confirmación}."""
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    encontrados: list[dict] = []

    def recorrer(nodo):
        if isinstance(nodo, dict):
            if "condition_id" in nodo and "required_absent_class" in nodo:
                encontrados.append(nodo)
            for v in nodo.values():
                recorrer(v)
        elif isinstance(nodo, list):
            for v in nodo:
                recorrer(v)

    recorrer(datos)
    return {
        p["condition_id"]: {
            "clase": p["required_absent_class"],
            "region": p.get("region") or {},
            "min_epp": float((p.get("evidence") or {}).get("min_absent_class_confidence", 0.0)),
            "confirmar_ms": float((p.get("timing") or {}).get("confirm_after_ms", 0.0)),
            "resolver_ms": float((p.get("timing") or {}).get("resolve_after_ms", 0.0)),
        }
        for p in encontrados
    }


def cargar_referencia(xml: Path) -> dict[int, list[tuple]]:
    """cuadro → [(id de la persona, caja, atributos, occluded)] de las cajas visibles."""
    raiz = ET.parse(xml).getroot()
    por_cuadro: dict[int, list[tuple]] = defaultdict(list)
    for t in raiz.findall("track"):
        if t.get("label") != "person":
            continue
        for b in t.findall("box"):
            if b.get("outside") == "1":
                continue
            attrs = {a.get("name"): a.text for a in b.findall("attribute")}
            caja = [float(b.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")]
            por_cuadro[int(b.get("frame"))].append((t.get("id"), caja, attrs, b.get("occluded") == "1"))
    return por_cuadro


def rastrear(detecciones: Path, salida: Path) -> Path:
    """Identidad por cuadro reconstruida (cacheada: el stream de entrada no cambia)."""
    if salida.is_file() and salida.stat().st_mtime >= Path(detecciones).stat().st_mtime:
        return salida
    from eovrt_control.tools.track_detections import track_event_stream

    salida.parent.mkdir(parents=True, exist_ok=True)
    track_event_stream(Path(detecciones), salida)
    return salida


def leer_cuadros(rastreado: Path) -> dict[int, dict]:
    """cuadro → {ts, ancho, alto, personas: {track_id: (caja, conf)}, epp: [(label, caja, conf)]}."""
    cuadros = {}
    with Path(rastreado).open(encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            ev = json.loads(linea)
            src = ev.get("source") or {}
            personas, epp = {}, []
            for d in ev.get("detections") or []:
                if d.get("label") == "person" and d.get("track_id"):
                    personas[d["track_id"]] = (d["bbox_xyxy"], d.get("confidence"))
                elif d.get("label") != "person":
                    epp.append((d.get("label"), d["bbox_xyxy"], d.get("confidence")))
            cuadros[int(src.get("frame_index", 0))] = {
                "ts": float(src.get("timestamp_ms", 0.0)), "ancho": src.get("width"), "alto": src.get("height"),
                "personas": personas, "epp": epp,
            }
    return cuadros


def leer_jsonl(ruta: Path) -> list[dict]:
    if not Path(ruta).is_file():
        return []
    with Path(ruta).open(encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def inicios_candidato(eventos: list[dict]) -> dict[str, list[int]]:
    """subject_key → cuadros en que el sujeto entró en `candidate` (traza del motor)."""
    out: dict[str, list[int]] = defaultdict(list)
    for e in eventos:
        if e.get("event_type") == "pattern_state_changed" and e.get("state") == "candidate":
            out[e.get("subject_key")].append(int(e.get("frame_index", 0)))
    return out


# --- anatomía de un clip --------------------------------------------------------------


def _mayoria(votos: Counter):
    return votos.most_common(1)[0][0] if votos else None


def anatomia_clip(
    *, clip: str, gt_json: dict, referencia: dict[int, list[tuple]], cuadros: dict[int, dict],
    alertas: list[dict], eventos: list[dict], patrones: dict[str, dict], tamano_entrada: int,
    ids_contados: set[str] | None = None,
) -> list[dict]:
    """Una fila por alerta de un clip negativo. `ids_contados`, si se da, restringe a las
    alertas que el evaluador contó como falsas alarmas (`unexpected_alerts`)."""
    inicios = inicios_candidato(eventos)
    ordenados = sorted(cuadros)
    filas = []
    for a in alertas:
        if a.get("event_type") != "alert_event":
            continue
        if ids_contados is not None and a.get("alert_id") not in ids_contados:
            continue
        cond = a["condition_id"]
        pat = patrones[cond]
        clase = pat["clase"]
        atributo = f"has_{clase}"
        track = a["subject_key"].split(":")[-1]
        f_alerta = int(a["frame_index"])
        previos = [f for f in inicios.get(a["subject_key"], []) if f <= f_alerta]
        if previos:
            f_ini, origen_ventana = max(previos), "traza"
        else:
            t0 = float(a.get("timestamp_ms", 0.0)) - pat["confirmar_ms"]
            f_ini = next((f for f in ordenados if cuadros[f]["ts"] >= t0), f_alerta)
            origen_ventana = "confirmacion"
        caja_alerta = ((a.get("evidence") or {}).get("subject") or {}).get("bbox_xyxy")
        en_alerta = cuadros.get(f_alerta, {}).get("personas", {}).get(track)
        coincide = bool(en_alerta and caja_alerta and iou(en_alerta[0], caja_alerta) > 0.99)

        votos_persona, votos_attr, votos_epp = Counter(), Counter(), Counter()
        mejores_iou, alturas, solapadas, disputas, n = [], [], 0, Counter(), 0
        ventana = [f for f in ordenados if f_ini <= f <= f_alerta]
        for f in ventana:
            fila = cuadros[f]
            if track not in fila["personas"]:
                continue
            n += 1
            caja = fila["personas"][track][0]
            mejor, mejor_iou = None, 0.0
            for g in referencia.get(f, []):
                v = iou(caja, g[1])
                if v > mejor_iou:
                    mejor, mejor_iou = g, v
            mejores_iou.append(mejor_iou)
            reg = region(caja, pat["region"])
            items = [e for e in fila["epp"] if e[0] == clase and (e[2] or 0) >= pat["min_epp"]]
            en_reg = [e for e in items if dentro(centro(e[1]), reg)]
            if en_reg:
                votos_epp["en_region"] += 1
                otras = [region(p[0], pat["region"]) for t, p in fila["personas"].items() if t != track]
                disputas[any(dentro(centro(e[1]), r) for e in en_reg for r in otras)] += 1
            elif any(dentro(centro(e[1]), caja) for e in items):
                votos_epp["fuera_region"] += 1
            else:
                votos_epp["nada"] += 1
            if mejor is None or mejor_iou < IOU_PERSONA:
                votos_persona["__ninguna__"] += 1
                continue
            votos_persona[mejor[0]] += 1
            votos_attr[mejor[2].get(atributo, "?")] += 1
            alturas.append(mejor[1][3] - mejor[1][1])
            otras_ref = [g for g in referencia.get(f, []) if g[0] != mejor[0]]
            if mejor[3] or any(iou(mejor[1], o[1]) > 0.1 for o in otras_ref):
                solapadas += 1

        con_persona = sum(v for k, v in votos_persona.items() if k != "__ninguna__")
        if n == 0 or con_persona < n / 2:
            iou_med = statistics.median(mejores_iou) if mejores_iou else 0.0
            causa, persona = ("F-parcial" if iou_med > IOU_PARCIAL else "F-sin-persona"), None
        else:
            persona = _mayoria(Counter({k: v for k, v in votos_persona.items() if k != "__ninguna__"}))
            valor = _mayoria(votos_attr)
            if valor == "unknown":
                causa = "U"
            elif valor == "false":
                causa = "V"
            else:
                epp = _mayoria(votos_epp)
                if epp == "nada":
                    causa = "P-no-detectado"
                elif epp == "fuera_region":
                    causa = "P-fuera-region"
                else:
                    causa = "P-disputado" if disputas[True] > disputas[False] else "P-intermitente"
        # El adaptador de GDINO lleva el cuadro a un cuadrado de `tamano_entrada` con letterbox
        # (`input_spec`): un 1920×1080 entra como 560×315, así que la escala es sobre el lado mayor.
        dims = cuadros.get(f_alerta, {})
        lado_mayor = max(float(dims.get("ancho") or 0), float(dims.get("alto") or 0))
        alto_med = statistics.median(alturas) if alturas else None
        filas.append({
            "clip": clip,
            "alert_id": a.get("alert_id"),
            "condicion": cond,
            "track": track,
            "cuadro_alerta": f_alerta,
            "cuadro_inicio": f_ini,
            "ventana": origen_ventana,
            "cuadros_con_track": n,
            "persona_referencia": persona,
            "causa": causa,
            "alto_px": round(alto_med, 1) if alto_med is not None else None,
            "alto_px_entrada": (round(alto_med * tamano_entrada / lado_mayor, 1)
                                if alto_med is not None and lado_mayor else None),
            "banda": banda(alto_med) if alto_med is not None else None,
            "solapada": bool(con_persona and solapadas / con_persona >= 0.5),
            "iluminacion": (gt_json.get("recording") or {}).get("lighting"),
            "coincide_con_reconstruccion": coincide,
            "caja_sujeto": caja_alerta,
        })
    return filas


def exposicion_horas(referencia: dict[int, list[tuple]], fps: float) -> float:
    """Persona-horas visibles en la referencia (para comparar escena y sujeto con la misma vara)."""
    cajas = sum(len(v) for v in referencia.values())
    return cajas / fps / 3600 if fps else 0.0


def resumir(filas: list[dict], *, horas_persona: float, horas_clip: float, fa_escena: int | None) -> dict:
    causas = Counter(f["causa"] for f in filas)
    reales = [f for f in filas if f["persona_referencia"]]
    claves = Counter((f["clip"], f["persona_referencia"], f["condicion"]) for f in reales)
    extra = sum(v - 1 for v in claves.values())
    por_banda = defaultdict(Counter)
    por_luz = defaultdict(Counter)
    por_clip = defaultdict(Counter)
    for f in filas:
        por_banda[f["banda"] or "sin_persona"][f["causa"]] += 1
        por_luz[f["iluminacion"]][f["causa"]] += 1
        por_clip[f["clip"]][f["causa"]] += 1
    total = len(filas)
    return {
        "falsas_alarmas": total,
        "por_causa": {c: causas.get(c, 0) for c in CAUSAS},
        "por_causa_gruesa": dict(Counter(GRUESA[f["causa"]] for f in filas)),
        "fragmentacion": {
            "alertas_sobre_personas_reales": len(reales),
            "pares_persona_condicion": len(claves),
            "factor": round(len(reales) / len(claves), 4) if claves else None,
            "alertas_extra": extra,
            "pares_con_mas_de_una_alerta": sum(1 for v in claves.values() if v > 1),
        },
        "solapadas": sum(1 for f in reales if f["solapada"]),
        "por_banda": {k: dict(v) for k, v in sorted(por_banda.items())},
        "por_iluminacion": {str(k): dict(v) for k, v in por_luz.items()},
        "por_clip": {k: dict(v) for k, v in sorted(por_clip.items())},
        "exposicion": {"persona_horas": round(horas_persona, 4), "clip_horas": round(horas_clip, 4)},
        "tasas": {
            "sujeto_por_persona_hora": round(total / horas_persona, 3) if horas_persona else None,
            "escena_por_clip_hora": (round(fa_escena / horas_clip, 3)
                                     if fa_escena is not None and horas_clip else None),
            "sujeto_por_clip_hora": round(total / horas_clip, 3) if horas_clip else None,
        },
        "falsas_alarmas_escena": fa_escena,
        "discrepancias_reconstruccion": sum(1 for f in filas if not f["coincide_con_reconstruccion"]),
    }


# --- revisión humana de una muestra (ciega por procedimiento) -------------------------


def muestra(filas: list[dict], por_causa: int, semilla: int) -> list[dict]:
    rng = random.Random(semilla)
    elegidas = []
    for causa in CAUSAS:
        grupo = sorted((f for f in filas if f["causa"] == causa), key=lambda f: (f["clip"], f["cuadro_alerta"], f["alert_id"]))
        elegidas.extend(rng.sample(grupo, min(por_causa, len(grupo))))
    rng.shuffle(elegidas)
    return [{"n": i + 1, **{k: f[k] for k in ("clip", "alert_id", "condicion", "track", "cuadro_alerta",
                                                "caja_sujeto", "causa")}}
            for i, f in enumerate(elegidas)]


def gruesa_humana(es_persona: str, epp_visible: str) -> str | None:
    es_persona, epp_visible = (es_persona or "").strip().lower(), (epp_visible or "").strip().lower()
    if es_persona == "no":
        return "sin_persona"
    if es_persona != "si":
        return None
    return {"si": "tiene_epp", "no": "falta_real", "no_se_puede": "no_juzgable"}.get(epp_visible)


def concordancia(muestra_: list[dict], csv_path: Path) -> dict:
    """Concordancia entre la causa automática (gruesa) y la revisión humana de la muestra.
    Columnas del CSV: n, es_persona (si/no), epp_visible (si/no/no_se_puede), nota."""
    with Path(csv_path).open(encoding="utf-8") as fh:
        filas = {int(r["n"]): r for r in csv.DictReader(fh) if r.get("n")}
    pares = []
    for m in muestra_:
        r = filas.get(m["n"])
        humana = gruesa_humana(r.get("es_persona", ""), r.get("epp_visible", "")) if r else None
        if humana is not None:
            pares.append((GRUESA[m["causa"]], humana, m["causa"]))
    if not pares:
        return {"estado": "pendiente", "revisadas": 0, "de": len(muestra_)}
    acuerdo = sum(1 for a, h, _ in pares if a == h) / len(pares)
    etiquetas = sorted({x for a, h, _ in pares for x in (a, h)})
    pa = Counter(a for a, _, _ in pares)
    ph = Counter(h for _, h, _ in pares)
    azar = sum(pa[e] * ph[e] for e in etiquetas) / len(pares) ** 2
    kappa = (acuerdo - azar) / (1 - azar) if azar < 1 else None
    f_auto = [(h, c) for a, h, c in pares if a == "sin_persona"]
    return {
        "estado": "completa" if len(pares) == len(muestra_) else "parcial",
        "revisadas": len(pares),
        "de": len(muestra_),
        "acuerdo": round(acuerdo, 4),
        "kappa": round(kappa, 4) if kappa is not None else None,
        "matriz": {f"{a}|{h}": v for (a, h), v in sorted(Counter((a, h) for a, h, _ in pares).items())},
        # una F que la persona ve como persona no es desacuerdo sobre la falsa alarma: es una
        # persona que la referencia no anotó (incompletitud del GT), y se informa aparte
        "f_que_son_persona": sum(1 for h, _ in f_auto if h != "sin_persona"),
        "f_revisadas": len(f_auto),
    }


# --- prueba ERR-01 / ERR-02 -----------------------------------------------------------


def _corridas_de(ctx: Contexto, spec: dict) -> dict[str, dict]:
    """clip → registro de la corrida (o de su variante) de una prueba completa."""
    corridas = ctx.corridas_completas(spec["prueba"])
    variante = spec.get("variante")
    if not variante:
        return corridas
    return {c: (r.get("variantes") or {}).get(variante) for c, r in corridas.items()
            if ((r.get("variantes") or {}).get(variante) or {}).get("estado") == "ok"}


def _fa_escena(ctx: Contexto, spec: dict | None) -> int | None:
    if not spec:
        return None
    ctx.corridas_completas(spec["prueba"])
    nombre = "metrics.json" if not spec.get("variante") else f"variantes/{spec['variante']}/metrics.json"
    m = ctx.carpeta(spec["prueba"]).leer(nombre) or {}
    return (m.get("negatives") or {}).get("false_positives")


def campana(ctx: Contexto, prueba: Prueba, nombre: str, spec: dict) -> tuple[list[dict], dict]:
    ent = ctx.ent
    detecciones = _corridas_de(ctx, {"prueba": spec["detecciones"], "variante": None})
    sujeto = _corridas_de(ctx, spec["alertas"])
    patrones = patrones_por_condicion(ent.patrones / f"{spec['patrones']}.yaml")
    filas, horas_persona, horas_clip, faltan = [], 0.0, 0.0, []
    for clip in clips_de(ent, spec.get("clips", "internet")):
        gt_json = json.loads((ent.gt_banco / f"{clip}.json").read_text(encoding="utf-8"))
        if not gt_json.get("negative"):
            continue
        reg_det, reg_suj = detecciones.get(clip), sujeto.get(clip)
        if not reg_det or not reg_suj:
            faltan.append(clip)
            continue
        referencia = cargar_referencia(ent.banco / "annotations" / f"{clip}.xml")
        rastreado = rastrear(Path(reg_det["detecciones"]),
                             ent.trabajo / prueba.id / nombre / "rastreado" / f"{clip}.jsonl")
        run = ent.control_runs / reg_suj["control_run_id"]
        evaluacion = json.loads((ctx.carpeta(spec["alertas"]["prueba"]).dir / reg_suj["eval"]).read_text())
        contadas = {u["alert_id"] for u in evaluacion.get("unexpected_alerts") or []}
        filas += anatomia_clip(
            clip=clip, gt_json=gt_json, referencia=referencia, cuadros=leer_cuadros(rastreado),
            alertas=leer_jsonl(run / "alerts.jsonl"), eventos=leer_jsonl(run / "pattern_events.jsonl"),
            patrones=patrones, tamano_entrada=int(spec["tamano_entrada"]), ids_contados=contadas,
        )
        fps = float(gt_json.get("fps_nominal") or 30)
        horas_persona += exposicion_horas(referencia, fps)
        horas_clip += float(gt_json.get("duration_ms") or 0) / 3_600_000
    if faltan:
        raise RuntimeError(f"{prueba.id}/{nombre}: faltan corridas de {faltan}")
    resumen_ = resumir(filas, horas_persona=horas_persona, horas_clip=horas_clip,
                       fa_escena=_fa_escena(ctx, spec.get("escena")))
    return filas, resumen_


def anatomia(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    resultados, metricas, resumen_filas = {}, {}, []
    gen1 = (prueba.gen1.get("referencia") or {}).get("valores") or {}
    for nombre, spec in r["campanas"].items():
        filas, res = campana(ctx, prueba, nombre, spec)
        carpeta.escribir(f"evals/{nombre}_alertas.json", filas)
        carpeta.escribir(f"evals/{nombre}_resumen.json", res)
        resultados[nombre] = res
        metricas[f"{nombre}.falsas_alarmas"] = res["falsas_alarmas"]
        for c, v in res["por_causa"].items():
            metricas[f"{nombre}.{c}"] = v
        metricas[f"{nombre}.alertas_extra_por_fragmentacion"] = res["fragmentacion"]["alertas_extra"]
        metricas[f"{nombre}.discrepancias_reconstruccion"] = res["discrepancias_reconstruccion"]
        resumen_filas += [
            {"clave": f"{nombre}.falsas_alarmas", "nombre": f"Falsas alarmas por sujeto en negativos ({nombre})",
             "valor": res["falsas_alarmas"], "unidad": None, "gen1": gen1.get(f"{nombre}.falsas_alarmas")},
            *[{"clave": f"{nombre}.{c}", "nombre": f"… causa {c} ({nombre})", "valor": v, "unidad": None,
               "gen1": gen1.get(f"{nombre}.{c}")} for c, v in res["por_causa"].items()],
            {"clave": f"{nombre}.alertas_extra_por_fragmentacion",
             "nombre": f"Alertas de más por fragmentación de identidad ({nombre})",
             "valor": res["fragmentacion"]["alertas_extra"], "unidad": None,
             "gen1": gen1.get(f"{nombre}.alertas_extra_por_fragmentacion")},
        ]
        if r.get("muestra") and nombre == r["muestra"].get("campana"):
            m = muestra(filas, int(r["muestra"]["por_causa"]), int(r["muestra"]["semilla"]))
            carpeta.escribir("muestra.json", m)
            revision = carpeta.dir / "revision_humana.csv"
            resultados["revision_humana"] = (concordancia(m, revision) if revision.is_file()
                                             else {"estado": "pendiente", "revisadas": 0, "de": len(m)})
    contraste = r.get("contraste")
    if contraste:
        a, b = resultados[contraste["base"]], resultados[contraste["comparada"]]
        resultados["contraste"] = {
            "base": contraste["base"], "comparada": contraste["comparada"],
            "delta_falsas_alarmas": b["falsas_alarmas"] - a["falsas_alarmas"],
            "delta_por_causa": {c: b["por_causa"][c] - a["por_causa"][c] for c in CAUSAS},
            "p_no_detectado_por_banda": {
                k: [a["por_banda"].get(k, {}).get("P-no-detectado", 0), b["por_banda"].get(k, {}).get("P-no-detectado", 0)]
                for k in sorted(set(a["por_banda"]) | set(b["por_banda"]))},
        }
        metricas["contraste.delta_falsas_alarmas"] = resultados["contraste"]["delta_falsas_alarmas"]
    carpeta.escribir("evals/anatomia.json", resultados)
    return {"metricas": metricas, "resumen": resumen_filas, "anatomia": resultados}


# --- SEG-01: fragmentación de identidad -----------------------------------------------


def emparejar(gts: list[tuple], sistema: dict[str, tuple], umbral: float) -> dict[str, str]:
    """Emparejamiento voraz por IoU descendente (persona de la referencia → track)."""
    pares = sorted(((iou(g[1], s[0]), g[0], t) for g in gts for t, s in sistema.items()), reverse=True)
    usados_g, usados_t, out = set(), set(), {}
    for v, g, t in pares:
        if v < umbral:
            break
        if g in usados_g or t in usados_t:
            continue
        usados_g.add(g)
        usados_t.add(t)
        out[g] = t
    return out


def fragmentacion_clip(referencia: dict[int, list[tuple]], cuadros: dict[int, dict], fps: float,
                       umbral: float = IOU_SEGUIMIENTO) -> dict:
    secuencias: dict[str, list[str]] = defaultdict(list)
    cajas_ref: Counter = Counter()
    for f in sorted(referencia):
        gts = referencia[f]
        for g in gts:
            cajas_ref[g[0]] += 1
        sistema = (cuadros.get(f) or {}).get("personas") or {}
        for g, t in emparejar(gts, sistema, umbral).items():
            secuencias[g].append(t)
    cambios = sum(sum(1 for x, y in pairwise(s) if x != y) for s in secuencias.values())
    distintos = [len(set(s)) for s in secuencias.values()]
    cubiertas = sum(len(s) for s in secuencias.values())
    total = sum(cajas_ref.values())
    minutos = total / fps / 60 if fps else 0.0
    return {
        "personas_referencia": len(cajas_ref),
        "personas_seguidas": len(secuencias),
        "cajas_referencia": total,
        "cajas_cubiertas": cubiertas,
        "cobertura": round(cubiertas / total, 4) if total else None,
        "cambios_de_identidad": cambios,
        "cambios_por_persona_minuto": round(cambios / minutos, 4) if minutos else None,
        "tracks_por_persona": distintos,
        "persona_minutos": round(minutos, 4),
    }


def _agregar_fragmentacion(por_clip: dict[str, dict]) -> dict:
    tracks = [x for v in por_clip.values() for x in v["tracks_por_persona"]]
    cambios = sum(v["cambios_de_identidad"] for v in por_clip.values())
    minutos = sum(v["persona_minutos"] for v in por_clip.values())
    total = sum(v["cajas_referencia"] for v in por_clip.values())
    cubiertas = sum(v["cajas_cubiertas"] for v in por_clip.values())
    return {
        "clips": len(por_clip),
        "personas_referencia": sum(v["personas_referencia"] for v in por_clip.values()),
        "cobertura": round(cubiertas / total, 4) if total else None,
        "cambios_de_identidad": cambios,
        "cambios_por_persona_minuto": round(cambios / minutos, 4) if minutos else None,
        "tracks_por_persona_media": round(statistics.mean(tracks), 4) if tracks else None,
        "tracks_por_persona_mediana": statistics.median(tracks) if tracks else None,
        "personas_con_un_solo_track": sum(1 for x in tracks if x == 1),
    }


def fragmentacion(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    ent = ctx.ent
    resultados, metricas, resumen_filas = {}, {}, []
    gen1 = (prueba.gen1.get("referencia") or {}).get("valores") or {}
    for banco, pid in r["bancos"].items():
        corridas = ctx.corridas_completas(pid)
        por_clip, por_escenario = {}, defaultdict(dict)
        for clip in clips_de(ent, "rodaje" if banco == "rodaje" else "internet"):
            reg = corridas.get(clip)
            if not reg:
                raise RuntimeError(f"{prueba.id}: {pid} no tiene la corrida de {clip}")
            gt_json = json.loads((ent.gt_banco / f"{clip}.json").read_text(encoding="utf-8"))
            xml = ent.banco / "annotations" / f"{clip}.xml"
            rastreado = rastrear(Path(reg["detecciones"]), ent.trabajo / prueba.id / banco / f"{clip}.jsonl")
            res = fragmentacion_clip(cargar_referencia(xml), leer_cuadros(rastreado),
                                     float(gt_json.get("fps_nominal") or 30), float(r.get("iou", IOU_SEGUIMIENTO)))
            res["escenario"] = gt_json.get("scenario")
            res["sha256_referencia"] = sha256_archivo(xml)
            por_clip[clip] = res
            por_escenario[res["escenario"]][clip] = res
        agregado = _agregar_fragmentacion(por_clip)
        agregado["por_escenario"] = {k: _agregar_fragmentacion(v) for k, v in sorted(por_escenario.items(), key=lambda x: str(x[0]))}
        resultados[banco] = {"agregado": agregado, "por_clip": por_clip}
        for k in ("cobertura", "cambios_de_identidad", "cambios_por_persona_minuto", "tracks_por_persona_media"):
            metricas[f"{banco}.{k}"] = agregado[k]
            resumen_filas.append({"clave": f"{banco}.{k}", "nombre": f"{k.replace('_', ' ').capitalize()} ({banco})",
                                  "valor": agregado[k], "unidad": None, "gen1": gen1.get(f"{banco}.{k}")})
    carpeta.escribir("evals/fragmentacion.json", resultados)
    return {"metricas": metricas, "resumen": resumen_filas}
