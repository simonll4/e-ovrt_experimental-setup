"""Calibración de encuadre (enmienda del 2026-11-05, doc 134 §13.19; la propuesta completa es el doc 143).

Antes de la primera toma de una jornada y antes de la demo, con la cámara ya ubicada por el
operador, una persona en regla se para en la marca cercana, camina a la lejana y vuelve
(`rodaje.ps1 -Calibrar`: una sesión de /demo con escena `CAL`). Este módulo la mide con las cajas
de `person` del detector y la compara con los criterios GEOMÉTRICOS pre-registrados en
`experiments/demo_defensa/calibracion.json`: cámara por encima de la cabeza y mirando hacia
abajo, persona con la cabeza en el quinto superior y no cortada en la cadera, una sola persona,
la lejana todavía detectable. Nunca mira cuánto `vest` falso hay: eso sería ajustar la cámara al
resultado.

Deja una constancia por calibración en `results/gen2/_calibraciones/<session_id>.json` (números,
sin cuadros) y la «vigente» por cámara en `vigente.json`, que `rodaje.ps1` lee antes de cada
toma y copia a `marcas.json` (`calibracion`), y que el chequeo previo de /demo muestra. Una
calibración que no pasa también queda vigente (con `ok: false`): hasta que una pase, o hasta que
se acepte con motivo y firma (`calibrar --aceptar`, p. ej. para el control del encuadre del 11-01
en RT-09), `rodaje.ps1` no lanza tomas con esa cámara.
"""
from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

from .entorno import Entorno
from .huellas import sha256_archivo
from .registro import ahora, escribir_json

ESCENA = "CAL"
SPEC = Path("experiments") / "demo_defensa" / "calibracion.json"
CARPETA = "_calibraciones"
VIGENTE = "vigente.json"
# La región del torso de CR-02 (cr01_cr02_v2): solo para el criterio informativo «chaleco puesto visto».
TORSO = {"y_min_ratio": 0.25, "y_max_ratio": 0.85, "x_margin_ratio": 0.08}
VEST_MIN = 0.25


class CalibracionInvalida(ValueError):
    pass


def cargar_spec(repo: Path) -> dict:
    ruta = Path(repo) / SPEC
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("schema") != "calibracion.encuadre.v1":
        raise CalibracionInvalida(f"{ruta}: schema desconocido {datos.get('schema')!r}")
    datos["_sha256"] = sha256_archivo(ruta)
    return datos


def _leer_jsonl(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    filas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip():
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
    return filas


def _marcas(carpeta: Path) -> dict | None:
    ruta = carpeta / "marcas.json"
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8-sig"))  # PowerShell puede dejar BOM


def sesiones_cal(directorio: Path) -> list[dict]:
    """Las sesiones de /demo con escena `CAL`, en orden (la última es la más nueva)."""
    filas = []
    if not directorio.is_dir():
        return filas
    for carpeta in sorted(p for p in directorio.iterdir() if p.is_dir()):
        sesion_json = carpeta / "session.json"
        if not sesion_json.is_file():
            continue
        try:
            datos = json.loads(sesion_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if datos.get("escena") == ESCENA:
            filas.append({**datos, "_dir": carpeta})
    return filas


def plugin_de(sesion: dict) -> str:
    return ((sesion.get("camara") or {}).get("plugin")) or "oak_d"


def _segmentos(marcas: dict | None, spec: dict) -> dict[str, tuple[float, float | None] | None]:
    """Las ventanas de cada segmento en reloj de pared del contenedor: desde la acción + margen
    hasta la acción siguiente (o el fin de la toma)."""
    desfase = (marcas or {}).get("desfase_contenedor_menos_host_ms") or 0.0
    acciones = {a.get("accion"): a["pared_ms"] + desfase for a in (marcas or {}).get("acciones") or []}
    salida = {}
    for nombre, s in spec["segmentos"].items():
        if s["desde"] not in acciones:
            salida[nombre] = None
            continue
        desde = acciones[s["desde"]] + 1000 * float(s.get("margen_s", 0))
        hasta = acciones.get(s["hasta"]) if s.get("hasta") else None
        salida[nombre] = (desde, hasta)
    return salida


def _en_torso(caja, persona) -> bool:
    x1, y1, x2, y2 = persona
    ancho, alto = x2 - x1, y2 - y1
    margen = ancho * TORSO["x_margin_ratio"]
    cx, cy = (caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2
    return x1 + margen <= cx <= x2 - margen and y1 + alto * TORSO["y_min_ratio"] <= cy <= y1 + alto * TORSO["y_max_ratio"]


def _area(caja) -> float:
    return max(0.0, caja[2] - caja[0]) * max(0.0, caja[3] - caja[1])


def _p50(xs: list[float]) -> float | None:
    return round(statistics.median(xs), 3) if xs else None


def geometria(cuadros: list[tuple[float, list[dict]]], ancho: int, alto: int, spec: dict) -> dict:
    """La geometría de la persona (la caja más grande que pasa los umbrales de sujeto) en un
    segmento: tamaño, ancho/alto, posición de la cabeza y de los pies, bordes, y si con el
    chaleco puesto el detector lo ve en el torso."""
    borde = float(spec.get("borde", 0.02))
    conf_min, area_min = float(spec["persona"]["confianza_min"]), float(spec["persona"]["area_min_px"])
    n = len(cuadros)
    con_persona = con_dos = cabeza = pies = chaleco = 0
    altos, anchos_altos, tops, bots = [], [], [], []
    for _t, dets in cuadros:
        personas = [d for d in dets if d.get("label") == "person" and d.get("confidence", 0) >= conf_min
                    and _area(d.get("bbox_xyxy") or [0, 0, 0, 0]) >= area_min]
        if not personas:
            continue
        con_persona += 1
        con_dos += len(personas) >= 2
        p = max(personas, key=lambda d: _area(d["bbox_xyxy"]))
        x1, y1, x2, y2 = p["bbox_xyxy"]
        altos.append((y2 - y1) / alto)
        anchos_altos.append((x2 - x1) / max(1e-6, y2 - y1))
        tops.append(y1 / alto)
        bots.append(y2 / alto)
        cabeza += y1 / alto > borde
        pies += y2 / alto < 1 - borde
        chaleco += any(d.get("label") == "vest" and d.get("confidence", 0) >= VEST_MIN
                       and _en_torso(d["bbox_xyxy"], p["bbox_xyxy"]) for d in dets)
    def f(k: int) -> float | None:
        return round(k / con_persona, 3) if con_persona else None

    return {
        "cuadros": n,
        "con_persona": con_persona,
        "persona_detectada": round(con_persona / n, 3) if n else None,
        "dos_personas": f(con_dos),
        "alto_p50": _p50(altos),
        "ancho_alto_p50": _p50(anchos_altos),
        "cabeza_top_p50": _p50(tops),
        "pies_bot_p50": _p50(bots),
        "cabeza_visible": f(cabeza),
        "pies_visibles": f(pies),
        "chaleco_puesto_visto": f(chaleco),
    }


def _criterios(seg: dict, fisica: dict, spec: dict) -> list[dict]:
    u = spec["umbrales"]
    textos = {**spec["criterios"]["bloqueantes"], **spec["criterios"]["recomendados"]}
    sug = spec.get("sugerencias") or {}
    cerca, lejos, cerca2 = seg.get("cerca") or {}, seg.get("lejos") or {}, seg.get("cerca_2") or {}
    altura = fisica.get("altura_m")

    def ge(v, m):
        return v is not None and v >= m

    def le(v, m):
        return v is not None and v <= m

    def fila(id_, tipo, ok, valor):
        return {"id": id_, "tipo": tipo, "ok": bool(ok), "valor": valor, "que": textos.get(id_),
                "sugerencia": None if ok else sug.get(id_)}

    desnivel = (None if cerca.get("cabeza_top_p50") is None or lejos.get("cabeza_top_p50") is None
                else round(lejos["cabeza_top_p50"] - cerca["cabeza_top_p50"], 3))
    bloqueantes = [
        fila("una_persona", "bloqueante",
             ge(cerca.get("persona_detectada"), u["persona_detectada_min"]) and le(cerca.get("dos_personas"), u["dos_personas_max"])
             and ge(lejos.get("persona_detectada"), u["lejos_persona_detectada_min"]) and le(lejos.get("dos_personas"), u["dos_personas_max"]),
             {"cerca": {"persona_detectada": cerca.get("persona_detectada"), "dos_personas": cerca.get("dos_personas")},
              "lejos": {"persona_detectada": lejos.get("persona_detectada"), "dos_personas": lejos.get("dos_personas")}}),
        fila("altura_declarada", "bloqueante", ge(altura, u["altura_camara_min_m"]), {"altura_m": altura}),
        fila("cabeza_visible", "bloqueante",
             ge(cerca.get("cabeza_visible"), u["cabeza_visible_min"]) and ge(lejos.get("cabeza_visible"), u["cabeza_visible_min"]),
             {"cerca": cerca.get("cabeza_visible"), "lejos": lejos.get("cabeza_visible")}),
        fila("cerca_no_cortada", "bloqueante", le(cerca.get("ancho_alto_p50"), u["cerca_ancho_alto_max"]),
             {"ancho_alto_p50": cerca.get("ancho_alto_p50")}),
        fila("cerca_tamano", "bloqueante",
             ge(cerca.get("alto_p50"), u["cerca_alto_min"]) and le(cerca.get("alto_p50"), u["cerca_alto_max"]),
             {"alto_p50": cerca.get("alto_p50")}),
        fila("camara_alta", "bloqueante",
             le(cerca.get("cabeza_top_p50"), u["cerca_cabeza_top_max"]) and le(desnivel, u["desnivel_cabeza_max"]),
             {"cabeza_top_p50_cerca": cerca.get("cabeza_top_p50"), "cabeza_top_p50_lejos": lejos.get("cabeza_top_p50"),
              "desnivel": desnivel}),
        fila("lejos_tamano", "bloqueante", ge(lejos.get("alto_p50"), u["lejos_alto_min"]), {"alto_p50": lejos.get("alto_p50")}),
    ]
    repetible = (cerca2.get("ancho_alto_p50") is not None and cerca.get("ancho_alto_p50") is not None
                 and (le(cerca2["ancho_alto_p50"], u["cerca_ancho_alto_max"]) == le(cerca["ancho_alto_p50"], u["cerca_ancho_alto_max"]))
                 and (le(cerca2.get("cabeza_top_p50"), u["cerca_cabeza_top_max"]) == le(cerca.get("cabeza_top_p50"), u["cerca_cabeza_top_max"])))
    recomendados = [
        fila("pies_visibles", "recomendado",
             ge(cerca.get("pies_visibles"), u["pies_visibles_min"]) and ge(lejos.get("pies_visibles"), u["pies_visibles_min"]),
             {"cerca": cerca.get("pies_visibles"), "lejos": lejos.get("pies_visibles")}),
        fila("altura_recomendada", "recomendado", ge(altura, u["altura_camara_recomendada_m"]), {"altura_m": altura}),
        fila("chaleco_puesto_visto", "recomendado",
             ge(cerca.get("chaleco_puesto_visto"), u["chaleco_puesto_visto_min"]) and ge(lejos.get("chaleco_puesto_visto"), u["chaleco_puesto_visto_min"]),
             {"cerca": cerca.get("chaleco_puesto_visto"), "lejos": lejos.get("chaleco_puesto_visto")}),
        fila("repetible", "recomendado", repetible,
             {"cerca_2": {"ancho_alto_p50": cerca2.get("ancho_alto_p50"), "cabeza_top_p50": cerca2.get("cabeza_top_p50")}}),
    ]
    return bloqueantes + recomendados


def evaluar(ent: Entorno, sesion: dict, spec: dict) -> dict:
    """La evaluación completa de una sesión `CAL`: geometría por segmento, criterios y veredicto."""
    carpeta: Path = sesion["_dir"]
    ids = sesion.get("ids") or {}
    media_id = ids.get("media_run_id")
    marcas = _marcas(carpeta)
    if not marcas:
        raise CalibracionInvalida(f"{sesion.get('session_id')}: sin marcas.json (¿se lanzó con rodaje.ps1 -Calibrar?)")
    if not media_id:
        raise CalibracionInvalida(f"{sesion.get('session_id')}: la sesión no tiene media_run_id")
    captura = {f["unit_id"]: f.get("capture_wallclock_ms")
               for f in _leer_jsonl(ent.media_runs / media_id / "metrics.jsonl") if f.get("unit_id")}
    filas = _leer_jsonl(ent.media_runs / media_id / "detections.jsonl")
    if not filas:
        raise CalibracionInvalida(f"{sesion.get('session_id')}: sin detecciones en {ent.media_runs / media_id}")
    fuente = filas[0].get("source") or {}
    ancho, alto = int(fuente.get("width") or 0), int(fuente.get("height") or 0)
    if not ancho or not alto:
        raise CalibracionInvalida(f"{sesion.get('session_id')}: las detecciones no traen el tamaño del cuadro")
    cuadros = []
    for fila in filas:
        t = captura.get(fila.get("unit_id")) or (fila.get("source") or {}).get("timestamp_ms")
        if t is not None:
            cuadros.append((t, fila.get("detections") or []))
    segmentos = {}
    for nombre, ventana in _segmentos(marcas, spec).items():
        if ventana is None:
            segmentos[nombre] = None
            continue
        desde, hasta = ventana
        en_ventana = [c for c in cuadros if c[0] >= desde and (hasta is None or c[0] <= hasta)]
        segmentos[nombre] = {"desde_ms": desde, "hasta_ms": hasta, **geometria(en_ventana, ancho, alto, spec)}
    fisica = marcas.get("fisica") or {}
    criterios = _criterios(segmentos, fisica, spec)
    fallan = [c["id"] for c in criterios if c["tipo"] == "bloqueante" and not c["ok"]]
    observaciones = [c["id"] for c in criterios if c["tipo"] == "recomendado" and not c["ok"]]
    camara = sesion.get("camara") or {}
    return {
        "schema": "calibracion.gen2.v1",
        "session_id": sesion.get("session_id"),
        "fecha": ahora(),
        "terminada_en": sesion.get("terminada_en"),
        "fase": sesion.get("fase"),
        "escena": ESCENA,
        "camara": {"plugin": plugin_de(sesion), "id": camara.get("id"), "nombre": camara.get("nombre"),
                   "resolucion": [ancho, alto]},
        "fisica": fisica,
        "spec": {"version": spec.get("version"), "sha256": spec.get("_sha256")},
        "ids": ids,
        "cuadros": len(cuadros),
        "segmentos": segmentos,
        "criterios": criterios,
        "ok": not fallan,
        "fallan": fallan,
        "observaciones": observaciones,
        "sugerencias": [c["sugerencia"] for c in criterios if not c["ok"] and c.get("sugerencia")],
        "aceptada": None,
    }


def carpeta_de(ent: Entorno) -> Path:
    return ent.resultados / CARPETA


def leer_vigente(ent: Entorno) -> dict:
    ruta = carpeta_de(ent) / VIGENTE
    if not ruta.is_file():
        return {"schema": "calibraciones.vigentes.v1", "por_camara": {}}
    return json.loads(ruta.read_text(encoding="utf-8"))


def resumen_vigente(evaluacion: dict) -> dict:
    f = evaluacion.get("fisica") or {}
    return {
        "session_id": evaluacion["session_id"],
        "fecha": evaluacion["fecha"],
        "ok": evaluacion["ok"],
        "aceptada": bool(evaluacion.get("aceptada")),
        "motivo": (evaluacion.get("aceptada") or {}).get("motivo"),
        "altura_m": f.get("altura_m"),
        "distancia_cerca_m": f.get("distancia_cerca_m"),
        "distancia_lejos_m": f.get("distancia_lejos_m"),
        "fallan": evaluacion["fallan"],
        "observaciones": evaluacion["observaciones"],
        "archivo": f"{evaluacion['session_id']}.json",
    }


def guardar(ent: Entorno, evaluacion: dict) -> Path:
    """La constancia de la calibración y la vigente de su cámara (la última calibración de esa
    cámara, pase o no: hasta que una pase o se acepte, `rodaje.ps1` no lanza tomas con ella)."""
    base = carpeta_de(ent)
    ruta = base / f"{evaluacion['session_id']}.json"
    escribir_json(ruta, evaluacion)
    vigente = leer_vigente(ent)
    vigente["por_camara"][evaluacion["camara"]["plugin"]] = resumen_vigente(evaluacion)
    vigente["actualizado"] = ahora()
    escribir_json(base / VIGENTE, vigente)
    return ruta


def leer_constancia(ent: Entorno, session_id: str) -> dict | None:
    ruta = carpeta_de(ent) / f"{session_id}.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else None


def vigencia(resumen: dict | None, spec: dict, ahora_utc: datetime | None = None) -> tuple[bool, str]:
    """¿La vigente sirve para lanzar una toma? (ok o aceptada, y más nueva que `vigencia_max_h`)."""
    if not resumen:
        return False, "sin calibración de encuadre para esta cámara (rodaje.ps1 -Calibrar; evidencia calibrar)"
    try:
        fecha = datetime.fromisoformat(resumen["fecha"])
    except (KeyError, ValueError):
        return False, "la calibración vigente no tiene fecha legible"
    edad_h = ((ahora_utc or datetime.now(UTC)) - fecha).total_seconds() / 3600
    if edad_h > float(spec["umbrales"].get("vigencia_max_h", 12)):
        return False, f"la calibración vigente tiene {edad_h:.1f} h (máximo {spec['umbrales'].get('vigencia_max_h', 12)}): repetirla"
    if resumen.get("ok"):
        return True, f"encuadre calibrado hace {edad_h * 60:.0f} min ({resumen['session_id']})"
    if resumen.get("aceptada"):
        return True, (f"la calibración vigente NO pasó ({', '.join(resumen.get('fallan') or [])}) y fue aceptada con motivo: "
                      f"{resumen.get('motivo')}")
    return False, (f"la calibración vigente NO pasó ({', '.join(resumen.get('fallan') or [])}): mover la cámara y repetirla, "
                   "o aceptarla con motivo (evidencia calibrar --aceptar)")


def informe(evaluacion: dict) -> str:
    """El reporte legible que imprime `calibrar` (y que Claude lee para dar el OK)."""
    cam = evaluacion["camara"]
    cabecera = (f"Calibración de encuadre — {evaluacion['session_id']} — cámara {cam['plugin']}"
                + (f" {cam['id']}" if cam.get("id") else "")
                + f" {cam['resolucion'][0]}×{cam['resolucion'][1]} — altura declarada "
                + f"{(evaluacion.get('fisica') or {}).get('altura_m')} m")
    lineas = [cabecera]
    for nombre, s in evaluacion["segmentos"].items():
        if not s:
            lineas.append(f"  {nombre:8} sin marca (¿se cortó el guion?)")
            continue
        lineas.append(f"  {nombre:8} cuadros {s['cuadros']:3} persona {s['persona_detectada']} dos {s['dos_personas']} · "
                      f"alto {s['alto_p50']} ancho/alto {s['ancho_alto_p50']} cabeza {s['cabeza_top_p50']} pies {s['pies_bot_p50']} · "
                      f"cabeza visible {s['cabeza_visible']} pies visibles {s['pies_visibles']} chaleco visto {s['chaleco_puesto_visto']}")
    for c in evaluacion["criterios"]:
        marca = "OK " if c["ok"] else ("NO " if c["tipo"] == "bloqueante" else "obs")
        lineas.append(f"  [{marca}] {c['id']:22} {json.dumps(c['valor'], ensure_ascii=False)}"
                      + (f"  → {c['sugerencia']}" if not c["ok"] and c.get("sugerencia") else ""))
    if evaluacion["ok"]:
        lineas.append("VEREDICTO: encuadre OK" + (f" (observaciones: {', '.join(evaluacion['observaciones'])})"
                                                   if evaluacion["observaciones"] else ""))
    else:
        lineas.append(f"VEREDICTO: NO pasa ({', '.join(evaluacion['fallan'])}). Mover la cámara y repetir "
                      "(rodaje.ps1 -Calibrar), o aceptar con motivo (calibrar --aceptar --motivo … --quien …).")
    if evaluacion.get("aceptada"):
        lineas.append(f"ACEPTADA por {evaluacion['aceptada'].get('quien')}: {evaluacion['aceptada'].get('motivo')}")
    return "\n".join(lineas)
