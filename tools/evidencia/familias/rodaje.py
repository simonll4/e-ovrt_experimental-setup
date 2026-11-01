"""RT-04 — obra simulada en vivo: las tomas del rodaje repetidas en la plataforma.

No se graba ni se anota (decisión del equipo, 2026-10-26): cada toma es una sesión de la
demo (`/demo`) etiquetada con su escena, lanzada y guiada por voz con
`infra/platform/rodaje.ps1`. Este módulo IMPORTA esas sesiones desde `defensa/sesiones/` (no
dispara la toma: la toma necesita personas frente a la cámara) y, por cada una:

- compara lo que pasó con lo que su guion espera (`escenas.json`: alerta o silencio por
  condición) — es una evaluación funcional, no contra un GT cuadro a cuadro;
- mide los tramos de cada alerta en reloj de pared: acción (marca del director por voz) →
  captura de la primera evidencia → confirmación (`confirmed_wall_ms` del mensaje MQTT) →
  llegada al broker (testigo de la sesión). Entre la primera evidencia y la confirmación está
  la ventana de persistencia del patrón: NO es latencia;
- toma la latencia por cuadro de `metrics.jsonl` (G2A, captura → host, vidrio → resultado);
- relee las MISMAS detecciones por sujeto con el runner de la consola (reuso), lo que vuelve
  evaluable la atribución en las escenas de dos personas (P7);
- para las tomas DEMO, aplica el criterio de ensayo aprobado de la spec de la demo (§9).

Las sesiones contienen caras del equipo y quedan fuera de git; acá solo se escriben números.

RT-05 (compromiso en vivo) usa la misma importación sobre las sesiones de EXPLORACIÓN de la
demo (`rodaje.ps1 -Motor … -Camara …`: otro motor u otra cadencia de la lista cerrada de
`experiments/demo_defensa/exploracion.yaml`, marcadas en su session.json). Las agrupa por celda
(motor × cámara) con la misma escena guionada. RT-04 nunca las cuenta, y RT-05 no cuenta las
sesiones de la demo congelada.

RT-06 (✎ 2026-11-01, enmienda del doc 134 §13.13) es el subset de comparación del guion con la
SEGUNDA fuente, la cámara IP por RTSP (P1, P2 y P5, como en julio): la misma importación, pero solo
de las sesiones cuya cámara elegida es RTSP (`camara.plugin` en session.json) y con el stream que
fija el pre-registro. RT-04 cuenta solo las de la OAK-D. Con la RTSP no hay marca de captura del
dispositivo: se mide G2A, no «captura → host» ni «vidrio → resultado».

El chaleco (✎ 2026-11-01, doc 134 §13.14): CR-02 depende de él, así que cada pre-registro lo fija
(`receta.chaleco`) y cada toma lo declara (`rodaje.ps1 -Chaleco` → marcas.json). RT-04, RT-05 y RT-06
cuentan solo el de julio; RT-07 (OAK-D) y RT-08 (cámara IP), solo el amarillo no reflectivo. Una toma con otro, o sin declararlo,
queda como no evaluable con el motivo.
"""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

from ..catalogo import Prueba
from ..herramientas import escribir_yaml, resumen_control
from ..huellas import sha256_archivo
from ..registro import Carpeta, ahora
from . import Contexto, familia
from .clips import experiment_id_de, slug_de
from .vivo import _metricas_toma, _stats

TERMINADAS = ("done",)
INICIO_INFRACCION = ("sacar", "entrar_", "volver")  # acciones que abren una infracción
FIN_INFRACCION = ("poner",)
ESTADOS_RESUELTOS = ("resolved", "inactive", "idle")


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


def _iso_a_s(valor: str | None) -> float | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor).timestamp()
    except ValueError:
        return None


def cargar_escenas(prueba: Prueba) -> dict[str, dict]:
    datos = json.loads((prueba.ruta.parent / prueba.receta["escenas"]).read_text(encoding="utf-8"))
    return {e["id"]: e for e in datos["escenas"]}


def fuente_de(sesion: dict) -> str:
    """La cámara de la sesión: el plugin de la elegida en la pantalla, o la OAK-D de la plantilla."""
    return ((sesion.get("camara") or {}).get("plugin")) or "oak_d"


def sesiones_del_rodaje(directorio: Path, escenas: dict[str, dict], *,
                        exploracion: bool = False, fuente: str = "oak_d") -> list[dict]:
    """Las sesiones de la demo etiquetadas con una escena del catálogo, en orden: las de la
    demo congelada (RT-04) o, con `exploracion`, solo las de exploración (RT-05). Solo las de la
    `fuente` pedida: RT-04 y RT-05 son con la OAK-D; RT-06, con la cámara IP (`rtsp`)."""
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
        if (datos.get("escena") in escenas and bool(datos.get("exploracion")) == exploracion
                and fuente_de(datos) == fuente):
            filas.append({**datos, "_dir": carpeta})
    return filas


def stream_de(carpeta: Path) -> str | None:
    """La ruta del stream RTSP con el que corrió la sesión (de `config/media.yaml`; la clave queda
    redactada al cerrar, la ruta no). None si no es RTSP o no se puede leer."""
    try:
        media = yaml.safe_load((carpeta / "config" / "media.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    ingest = media.get("ingest") or {}
    if ingest.get("plugin") != "rtsp":
        return None
    return urlparse(str((ingest.get("config") or {}).get("url") or "")).path or None


def _marcas(carpeta: Path) -> dict | None:
    ruta = carpeta / "marcas.json"
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8-sig"))  # PowerShell puede dejar BOM


def motivo_de_otro_chaleco(receta: dict, carpeta: Path) -> str | None:
    """Enmienda del 2026-11-01 (doc 134 §13.14): CR-02 depende del chaleco, así que cada pre-registro
    fija uno (`receta.chaleco`) y cada toma lo declara (`rodaje.ps1 -Chaleco` → `marcas.json`). Una toma
    con otro chaleco, o sin declararlo, no se mezcla: queda como no evaluable con este motivo."""
    fijado = receta.get("chaleco")
    if not fijado:
        return None
    try:
        declarado = (_marcas(carpeta) or {}).get("chaleco")
    except (OSError, json.JSONDecodeError):
        declarado = None
    if declarado == fijado:
        return None
    if not declarado:
        return f"chaleco sin declarar (el pre-registro fija {fijado!r}; rodaje.ps1 -Chaleco)"
    return f"otro chaleco: {declarado!r} (el pre-registro fija {fijado!r})"


def evaluar_toma(ctx: Contexto, escena: dict, sesion: dict) -> dict:
    """Los números de una toma (todo en ms de reloj de pared del contenedor)."""
    carpeta: Path = sesion["_dir"]
    ids = sesion.get("ids") or {}
    media_id, control_id = ids.get("media_run_id"), ids.get("control_run_id")
    alertas = _leer_jsonl(ctx.ent.control_runs / control_id / "alerts.jsonl") if control_id else []
    eventos = _leer_jsonl(ctx.ent.control_runs / control_id / "pattern_events.jsonl") if control_id else []
    filas_metricas = _leer_jsonl(ctx.ent.media_runs / media_id / "metrics.jsonl") if media_id else []
    captura = {f["unit_id"]: f.get("capture_wallclock_ms") for f in filas_metricas if f.get("unit_id")}
    testigo = _leer_jsonl(carpeta / "witness.jsonl")
    marcas = _marcas(carpeta)
    desfase = (marcas or {}).get("desfase_contenedor_menos_host_ms") or 0.0
    acciones = [{**a, "t": a["pared_ms"] + desfase} for a in (marcas or {}).get("acciones") or []]

    def accion_previa(condicion: str, t: float, prefijos) -> dict | None:
        previas = [a for a in acciones if a.get("condicion") == condicion
                   and str(a.get("accion", "")).startswith(prefijos) and a["t"] <= t]
        return max(previas, key=lambda a: a["t"]) if previas else None

    filas_alertas = []
    for alerta in alertas:
        cond = alerta.get("condition_id")
        mensaje = next((m for m in testigo if (m.get("payload") or {}).get("alert_id") == alerta.get("alert_id")), None)
        confirmada = (mensaje or {}).get("payload", {}).get("confirmed_wall_ms") if mensaje else None
        fila: dict = {
            "condicion": cond,
            "alert_id": alerta.get("alert_id"),
            "subject_key": alerta.get("subject_key"),
            "captura_primera_evidencia_ms": captura.get(alerta.get("first_evidence_unit_id")),
            "captura_confirmacion_ms": captura.get(alerta.get("unit_id")) or alerta.get("timestamp_ms"),
            "confirmada_ms": confirmada,
            "broker_ms": (mensaje or {}).get("recibido_ms"),
        }
        if fila["confirmada_ms"] and fila["broker_ms"]:
            fila["confirmacion_a_broker_ms"] = round(fila["broker_ms"] - fila["confirmada_ms"], 1)
        if fila["captura_primera_evidencia_ms"] and fila["confirmada_ms"]:
            fila["primera_evidencia_a_confirmacion_ms"] = round(
                fila["confirmada_ms"] - fila["captura_primera_evidencia_ms"], 1)
        referencia = fila["confirmada_ms"] or fila["captura_confirmacion_ms"]
        accion = accion_previa(cond, referencia, INICIO_INFRACCION) if referencia else None
        if accion:
            fila["accion"] = accion.get("accion")
            if fila["confirmada_ms"]:
                fila["accion_a_confirmacion_ms"] = round(fila["confirmada_ms"] - accion["t"], 1)
            if fila["captura_primera_evidencia_ms"]:
                fila["accion_a_primera_evidencia_ms"] = round(fila["captura_primera_evidencia_ms"] - accion["t"], 1)
            if fila["broker_ms"]:
                fila["accion_a_broker_ms"] = round(fila["broker_ms"] - accion["t"], 1)
        elif acciones and referencia:
            fila["antes_de_la_accion"] = True  # alertó sin que el guion hubiera abierto la infracción
        # ¿Se resolvió después? Primer cambio a un estado de reposo de esa condición posterior.
        resueltos = [e for e in eventos if e.get("condition_id") == cond
                     and e.get("state") in ESTADOS_RESUELTOS
                     and (captura.get(e.get("unit_id")) or e.get("timestamp_ms") or 0) >= (fila["captura_confirmacion_ms"] or 0)]
        fila["resuelta"] = bool(resueltos)
        if resueltos:
            t_res = captura.get(resueltos[0].get("unit_id")) or resueltos[0].get("timestamp_ms")
            fin = accion_previa(cond, t_res, FIN_INFRACCION) if t_res else None
            if fin and t_res:
                fila["accion_fin_a_resolucion_ms"] = round(t_res - fin["t"], 1)
        filas_alertas.append(fila)

    por_condicion = {}
    for cond, esperado in (escena.get("espera") or {}).items():
        n = sum(1 for a in filas_alertas if a["condicion"] == cond)
        ok = n >= 1 if esperado == "alerta" else n == 0
        por_condicion[cond] = {"esperado": esperado, "alertas": n, "ok": ok}
    resumen_c = resumen_control(ctx.ent, control_id) if control_id else {}
    metricas = _metricas_toma(ctx, media_id) if media_id else {"_series": {}}
    series = metricas.pop("_series", {})
    termino = _iso_a_s(sesion.get("terminada_en"))
    pidio_fin = _iso_a_s(sesion.get("fin_pedido_en"))
    return {
        "escena": escena["id"],
        "session_id": sesion.get("session_id"),
        "experiment_id": sesion.get("experiment_id"),
        "ids": ids,
        "marcas": bool(marcas),
        "alertas": filas_alertas,
        "por_condicion": por_condicion,
        "como_se_esperaba": all(c["ok"] for c in por_condicion.values()),
        "alertas_antes_de_la_accion": sum(1 for a in filas_alertas if a.get("antes_de_la_accion")),
        "bus_dropped_events": resumen_c.get("bus_dropped_events"),
        "resultado_listo_s": round(termino - pidio_fin, 1) if termino and pidio_fin else None,
        "latencia": metricas,
        "_series": series,
    }


def ensayo_demo(toma: dict, criterio: dict) -> dict:
    """Ensayo aprobado (spec de la demo §9): CR-01 confirmada a ≤ 6 s de la acción, el testigo
    la recibió, se resolvió al ponerse el casco, 0 eventos perdidos y Resultado en < 60 s."""
    cr01 = [a for a in toma["alertas"] if a["condicion"] == "CR-01" and not a.get("antes_de_la_accion")]
    primera = cr01[0] if cr01 else {}
    motivos = []
    if not primera:
        motivos.append("CR-01 no confirmó")
    else:
        t = primera.get("accion_a_confirmacion_ms")
        if t is None:
            motivos.append("sin marca de la acción (¿se usó rodaje.ps1?)")
        elif t > criterio["cr01_max_s_desde_la_accion"] * 1000:
            motivos.append(f"CR-01 confirmó a {t / 1000:.1f} s de la acción")
        if not primera.get("broker_ms"):
            motivos.append("el testigo no recibió el mensaje")
        if not primera.get("resuelta"):
            motivos.append("CR-01 no se resolvió")
    if toma.get("bus_dropped_events"):
        motivos.append(f"{toma['bus_dropped_events']} eventos perdidos en el bus")
    listo = toma.get("resultado_listo_s")
    if listo is None or listo > criterio["resultado_max_s"]:
        motivos.append(f"Resultado listo a {listo} s del cierre")
    cr02 = toma["por_condicion"].get("CR-02", {})
    return {"aprobado": not motivos, "motivos": motivos, "cr02_en_vivo": bool(cr02.get("ok"))}


def _releer_por_sujeto(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, sesion: dict) -> dict:
    """Mismas detecciones, granularidad por sujeto: un replay por el runner de la consola."""
    ids = sesion.get("ids") or {}
    spec = prueba.receta["sujeto"]
    nombre = f"gen2_rt04_sujeto_{sesion['session_id']}"
    dir_gen = ctx.ent.generados / prueba.id / nombre
    patrones = ctx.ent.patrones / f"{spec['patrones']}.yaml"
    control = escribir_yaml(dir_gen / "control.yaml", {
        "run": {"id": None, "scenario": "DBE", "name": nombre,
                "description": f"Generación 2, RT-04: {sesion['session_id']} releída por sujeto"},
        "input": {"type": "media_jsonl", "path": "(la completa el runner de la consola)",
                  "track_persons": bool(spec.get("track_persons"))},
        "patterns": {"file": str(patrones), "active_ids": list(spec.get("activos") or ["CR-01", "CR-02"])},
        "outputs": {"base_dir": str(ctx.ent.control_runs), "save_pattern_events_jsonl": True,
                    "save_alerts_jsonl": True, "save_metrics_jsonl": True, "save_errors_jsonl": True,
                    "save_summary_json": True},
        "logging": {"level": "WARNING"},
    })
    media_config = sesion["_dir"] / "config" / "media.yaml"
    manifiesto = {
        "schema_version": "experiment.manifest.v1",
        "slug": slug_de(prueba),
        "experiment_id": experiment_id_de(nombre),
        "runs": {
            "media": {"service": "media-plane", "config": str(media_config), "mode": "run",
                      "reuse_run_id": ids["media_run_id"]},
            "control": {"service": "control-plane", "config": str(control), "mode": "replay"},
        },
        "sequencing": "media_first",
        "timeout_s": float(prueba.receta.get("timeout_s", 900)),
        "changes": f"generación 2 — {prueba.id}: relectura por sujeto de {sesion['session_id']}",
    }
    escribir_yaml(dir_gen / "manifest.yaml", manifiesto)
    carpeta.guardar_ejemplo(dir_gen)
    carpeta.comando(f"POST /api/experiments/run  manifiesto={dir_gen / 'manifest.yaml'}")
    t0 = time.monotonic()
    estado = ctx.consola.correr(manifiesto, timeout_s=manifiesto["timeout_s"])
    registro = {"estado": "ok" if estado.get("ok") else "fallo", "experiment_id": estado.get("experiment_id"),
                "control_run_id": estado.get("control_run_id"), "segundos": round(time.monotonic() - t0, 1),
                "sha256": {"control_config": sha256_archivo(control), "patrones": sha256_archivo(patrones)}}
    if not estado.get("ok"):
        registro["error"] = estado.get("error") or f"control={estado.get('control_status')}"
    return registro


def _sujeto(ctx: Contexto, escena: dict, registro: dict) -> dict:
    alertas = _leer_jsonl(ctx.ent.control_runs / registro["control_run_id"] / "alerts.jsonl")
    por_condicion = {}
    for cond, esperado in (escena.get("espera") or {}).items():
        de_cond = [a for a in alertas if a.get("condition_id") == cond]
        ok = len(de_cond) >= 1 if esperado == "alerta" else not de_cond
        por_condicion[cond] = {"esperado": esperado, "alertas": len(de_cond),
                               "sujetos": len({a.get("subject_key") for a in de_cond}), "ok": ok}
    sujetos = len({a.get("subject_key") for a in alertas})
    return {"por_condicion": por_condicion, "como_se_esperaba": all(c["ok"] for c in por_condicion.values()),
            "sujetos_con_alerta": sujetos}


def _mediana(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def _celda(sesion: dict) -> tuple[str, str]:
    x = sesion.get("exploracion") or {}
    return x.get("motor") or "?", x.get("camara") or "?"


def _exploracion(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, escenas: dict[str, dict],
                 descartes: dict) -> dict:
    """RT-05: las sesiones de exploración de una escena, agrupadas por motor × cámara."""
    r = prueba.receta
    escena = escenas[r["escena"]]
    matriz = r["matriz"]
    sesiones = [s for s in sesiones_del_rodaje(ctx.ent.repo / r["sesiones"], escenas, exploracion=True)
                if s.get("escena") == escena["id"]]
    carpeta.escribir("configuracion.json", {"escenas": sha256_archivo(prueba.ruta.parent / r["escenas"]),
                                            "matriz": matriz, "chaleco": r.get("chaleco"),
                                            "sesiones_encontradas": [s.get("session_id") for s in sesiones]})
    tomas, no_evaluables = [], []
    for sesion in sesiones:
        sid = sesion.get("session_id")
        motor, camara = _celda(sesion)
        if motivo := motivo_de_otro_chaleco(r, sesion["_dir"]):
            no_evaluables.append({"session_id": sid, "celda": f"{motor} @ {camara}", "motivo": motivo})
            continue
        if sid in descartes:
            no_evaluables.append({"session_id": sid, "celda": f"{motor} @ {camara}",
                                  "motivo": "descartada: " + str(descartes[sid].get("motivo"))})
            continue
        if sesion.get("fase") not in TERMINADAS:
            no_evaluables.append({"session_id": sid, "celda": f"{motor} @ {camara}",
                                  "motivo": f"la sesión terminó en {sesion.get('fase')!r}: {sesion.get('error')}"})
            continue
        toma = evaluar_toma(ctx, escena, sesion)
        series = toma.pop("_series")
        toma.update({"motor": motor, "camara": camara,
                     "modelo": (sesion.get("exploracion") or {}).get("modelo")})
        (carpeta.dir / "tomas" / sid).mkdir(parents=True, exist_ok=True)
        carpeta.escribir(f"tomas/{sid}/series.json", series)
        carpeta.escribir(f"tomas/{sid}/toma.json", toma)
        carpeta.guardar_corrida(sid, {"estado": "ok", "escena": escena["id"], "motor": motor, "camara": camara,
                                      "experiment_id": toma["experiment_id"], **dict(toma["ids"]),
                                      "importada": ahora()})
        tomas.append({**toma, "_series": series})

    celdas: dict[str, dict] = {}
    for motor in matriz["motores"]:
        for camara in matriz["camaras"]:
            de_celda = [t for t in tomas if t["motor"] == motor and t["camara"] == camara]
            alertas = [a for t in de_celda for a in t["alertas"] if not a.get("antes_de_la_accion")]
            pool = {k: [v for t in de_celda for v in t["_series"].get(k, [])]
                    for k in ("g2a", "captura_a_host", "vidrio_a_resultado")}
            fps = [t["latencia"].get("fps_efectivos") for t in de_celda if t["latencia"].get("fps_efectivos") is not None]
            celdas[f"{motor} @ {camara}"] = {
                "motor": motor, "camara": camara,
                "modelo": next((t["modelo"] for t in de_celda if t.get("modelo")), None),
                "tomas": len(de_celda),
                "faltan": max(0, int(matriz.get("tomas_por_celda", 0)) - len(de_celda)),
                "como_se_esperaba": sum(1 for t in de_celda if t["como_se_esperaba"]),
                "cr01_confirmo": sum(1 for t in de_celda if (t["por_condicion"].get("CR-01") or {}).get("ok")),
                "cr02_confirmo": sum(1 for t in de_celda if (t["por_condicion"].get("CR-02") or {}).get("ok")),
                "alertas_antes_de_la_accion": sum(t["alertas_antes_de_la_accion"] for t in de_celda),
                "accion_a_confirmacion_mediana_ms": {
                    cond: _mediana([a.get("accion_a_confirmacion_ms") for a in alertas if a["condicion"] == cond])
                    for cond in ("CR-01", "CR-02")},
                "latencia_por_cuadro": {k: _stats(v) for k, v in pool.items()},
                "fps_efectivos_media": round(statistics.mean(fps), 2) if fps else None,
                "cuadros_descartados": sum(t["latencia"].get("descartadas") or 0 for t in de_celda),
                "bus_dropped_events": sum(t.get("bus_dropped_events") or 0 for t in de_celda),
            }

    def segundos(ms):
        return f"{ms / 1000:.1f} s" if ms is not None else "—"

    resumen = []
    for clave, c in celdas.items():
        if not c["tomas"]:
            continue
        n = c["tomas"]
        t01, t02 = c["accion_a_confirmacion_mediana_ms"]["CR-01"], c["accion_a_confirmacion_mediana_ms"]["CR-02"]
        vidrio = c["latencia_por_cuadro"]["vidrio_a_resultado"].get("p95")
        resumen.append({
            "clave": clave, "nombre": clave,
            "valor": (f"CR-01 {c['cr01_confirmo']}/{n} ({segundos(t01)}) · CR-02 {c['cr02_confirmo']}/{n} "
                      f"({segundos(t02)}) · {c['fps_efectivos_media']} fps · vidrio → resultado p95 "
                      f"{vidrio if vidrio is not None else '—'} ms"),
            "unidad": None, "gen1": None})
    metricas = {"tomas": len(tomas), "celdas": celdas,
                "celdas_completas": sum(1 for c in celdas.values() if c["tomas"] and not c["faltan"]),
                "celdas_totales": len(celdas), "no_evaluables": no_evaluables}
    carpeta.escribir("evals/tomas.json", [{k: v for k, v in t.items() if k != "_series"} for t in tomas])
    completa = bool(tomas) and metricas["celdas_completas"] == metricas["celdas_totales"]
    datos = {
        "familia": "rodaje",
        "estado": "completo" if completa else "parcial",
        "metricas": metricas,
        "resumen": resumen,
        "veredicto": {"propuesto": "otra_combinacion", "motivo": prueba.gen1.get("motivo"),
                      "referencia": prueba.gen1.get("doc"), "diferencias": {}, "confirmado": None},
    }
    if not tomas:
        datos["nota"] = "todavía no hay sesiones de exploración (rodaje.ps1 -Escena DEMO -Motor … -Camara …)"
    carpeta.resultado(datos)
    return {"estado": datos["estado"], "tomas": len(tomas), "celdas_completas": metricas["celdas_completas"]}


def _agregar(tomas: list[dict], *, fuente: str, etiqueta: str, minimas: dict | None = None,
             sufijo: str = "", clave_sufijo: str = "") -> tuple[dict, list[dict]]:
    """Las métricas y el resumen de un conjunto de tomas (todas, o las de un stream en RT-06)."""
    por_escena: dict[str, dict] = {}
    for t in tomas:
        e = por_escena.setdefault(t["escena"], {"tomas": 0, "como_se_esperaba": 0, "sujeto_como_se_esperaba": 0,
                                                "alertas_antes_de_la_accion": 0})
        e["tomas"] += 1
        e["como_se_esperaba"] += bool(t["como_se_esperaba"])
        e["sujeto_como_se_esperaba"] += bool((t.get("sujeto") or {}).get("como_se_esperaba"))
        # Una alerta antes de la acción cuenta como «alertó» para la escena, pero es otro hecho (p. ej. el
        # casco puesto que no se ve de lejos, P1b): se cuenta aparte para que no quede tapada.
        e["alertas_antes_de_la_accion"] += t.get("alertas_antes_de_la_accion") or 0
    pool = {k: [v for t in tomas for v in t["_series"].get(k, [])] for k in ("g2a", "captura_a_host", "vidrio_a_resultado")}
    alertas = [a for t in tomas for a in t["alertas"]]
    tramo = {cond: _mediana([a.get("accion_a_confirmacion_ms") for a in alertas if a["condicion"] == cond])
             for cond in ("CR-01", "CR-02")}
    ensayos = [t["ensayo_demo"] for t in tomas if "ensayo_demo" in t]
    racha = mejor = 0
    for e in ensayos:
        racha = racha + 1 if e["aprobado"] else 0
        mejor = max(mejor, racha)
    broker = [a.get("confirmacion_a_broker_ms") for a in alertas if a.get("confirmacion_a_broker_ms") is not None]
    fps = [t["latencia"].get("fps_efectivos") for t in tomas if t["latencia"].get("fps_efectivos") is not None]
    metricas = {
        "tomas": len(tomas),
        "tomas_como_se_esperaba": sum(1 for t in tomas if t["como_se_esperaba"]),
        "tomas_sujeto_como_se_esperaba": sum(1 for t in tomas if (t.get("sujeto") or {}).get("como_se_esperaba")),
        "alertas_antes_de_la_accion": sum(t.get("alertas_antes_de_la_accion") or 0 for t in tomas),
        "por_escena": por_escena,
        "accion_a_confirmacion_mediana_ms": tramo,
        "confirmacion_a_broker": _stats(broker),
        "latencia_por_cuadro": {k: _stats(v) for k, v in pool.items()},
        "fps_efectivos_media": round(statistics.mean(fps), 2) if fps else None,
        "ensayos_demo": {"total": len(ensayos), "aprobados": sum(1 for e in ensayos if e["aprobado"]),
                         "mejor_racha": mejor, "cr02_en_vivo": sum(1 for e in ensayos if e["cr02_en_vivo"])},
    }
    if minimas:
        metricas["faltan_tomas"] = {e: max(0, n - por_escena.get(e, {}).get("tomas", 0)) for e, n in minimas.items()}
    resumen = [
        {"clave": "tomas_como_se_esperaba", "nombre": "Tomas que se comportaron como su guion (escena)",
         "valor": f"{metricas['tomas_como_se_esperaba']}/{len(tomas)}", "unidad": None, "gen1": None},
        {"clave": "tomas_sujeto_como_se_esperaba", "nombre": "Las mismas tomas releídas por sujeto",
         "valor": f"{metricas['tomas_sujeto_como_se_esperaba']}/{len(tomas)}", "unidad": None, "gen1": None},
        {"clave": "alertas_antes_de_la_accion", "nombre": "Alertas antes de la acción (el guion no había abierto la infracción)",
         "valor": metricas["alertas_antes_de_la_accion"], "unidad": None, "gen1": None},
        {"clave": "cr01_accion_a_alerta_s", "nombre": "CR-01: de la acción a la alerta confirmada (mediana)",
         "valor": round(tramo["CR-01"] / 1000, 2) if tramo["CR-01"] else None, "unidad": "s", "gen1": None},
        {"clave": "cr02_accion_a_alerta_s", "nombre": "CR-02: de la acción a la alerta confirmada (mediana)",
         "valor": round(tramo["CR-02"] / 1000, 2) if tramo["CR-02"] else None, "unidad": "s", "gen1": None},
        {"clave": "confirmacion_a_broker_p95_ms", "nombre": "De la confirmación al broker MQTT, p95",
         "valor": metricas["confirmacion_a_broker"].get("p95"), "unidad": "ms", "gen1": None},
        {"clave": "vidrio_a_resultado_p95_ms", "nombre": f"Vidrio → resultado por cuadro, p95 ({etiqueta})",
         "valor": metricas["latencia_por_cuadro"]["vidrio_a_resultado"].get("p95"), "unidad": "ms", "gen1": None},
        {"clave": "fps_efectivos", "nombre": "Cuadros por segundo procesados", "valor": metricas["fps_efectivos_media"],
         "unidad": "fps", "gen1": None},
        {"clave": "ensayos_demo_aprobados", "nombre": "Ensayos de la demo aprobados (mejor racha)",
         "valor": f"{metricas['ensayos_demo']['aprobados']}/{len(ensayos)} ({mejor})", "unidad": None, "gen1": None},
    ]
    if fuente != "oak_d":
        # Sin marca de captura del dispositivo (RTSP): «vidrio → resultado» no existe; el número
        # comparable es G2A (desde que el cuadro sale de la cola), y no hay ensayos de la demo.
        resumen = [x for x in resumen if x["clave"] not in ("vidrio_a_resultado_p95_ms", "ensayos_demo_aprobados")]
        resumen.append({"clave": "g2a_p95_ms", "nombre": f"G2A por cuadro, p95 ({etiqueta})",
                        "valor": metricas["latencia_por_cuadro"]["g2a"].get("p95"), "unidad": "ms", "gen1": None})
    if sufijo or clave_sufijo:
        resumen = [{**x, "clave": x["clave"] + clave_sufijo, "nombre": x["nombre"] + sufijo} for x in resumen]
    return metricas, resumen


@familia("rodaje")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    escenas = cargar_escenas(prueba)
    descartes = carpeta.leer("descartes.json") or {}
    if r.get("matriz"):
        return _exploracion(ctx, prueba, carpeta, escenas, descartes)
    fuente = r.get("fuente", "oak_d")
    incluidas = r.get("escenas_incluidas")
    escenas_de_la_prueba = {k: v for k, v in escenas.items() if not incluidas or k in incluidas}
    sesiones = sesiones_del_rodaje(ctx.ent.repo / r["sesiones"], escenas_de_la_prueba, fuente=fuente)
    carpeta.escribir("configuracion.json", {"escenas": sha256_archivo(prueba.ruta.parent / r["escenas"]),
                                            "fuente": fuente, "escenas_incluidas": incluidas, "chaleco": r.get("chaleco"),
                                            "stream": r.get("stream"),
                                            "sesiones_encontradas": [s.get("session_id") for s in sesiones]})
    # Las configuraciones de stream que fija el pre-registro (RT-06): ruta -> nombre.
    configs_stream = r.get("streams") or ({"unico": {"ruta": r["stream"]}} if r.get("stream") else {})
    streams = {c["ruta"]: nombre for nombre, c in configs_stream.items()}
    tomas, no_evaluables = [], []
    for sesion in sesiones:
        sid = sesion.get("session_id")
        if motivo := motivo_de_otro_chaleco(r, sesion["_dir"]):
            no_evaluables.append({"session_id": sid, "escena": sesion.get("escena"), "motivo": motivo})
            continue
        stream = None
        if streams:
            stream = stream_de(sesion["_dir"])
            if stream not in streams:
                # Lo fija el pre-registro: una toma con otro stream es otra configuración.
                no_evaluables.append({"session_id": sid, "escena": sesion.get("escena"),
                                      "motivo": f"otro stream: {stream!r} (el pre-registro fija {sorted(streams)})"})
                continue
        if sid in descartes:
            no_evaluables.append({"session_id": sid, "escena": sesion.get("escena"),
                                  "motivo": f"descartada: {descartes[sid].get('motivo')}"})
            continue
        if sesion.get("fase") not in TERMINADAS:
            no_evaluables.append({"session_id": sid, "escena": sesion.get("escena"),
                                  "motivo": f"la sesión terminó en {sesion.get('fase')!r}: {sesion.get('error')}"})
            continue
        escena = escenas[sesion["escena"]]
        toma = evaluar_toma(ctx, escena, sesion)
        series = toma.pop("_series")
        (carpeta.dir / "tomas" / sid).mkdir(parents=True, exist_ok=True)
        carpeta.escribir(f"tomas/{sid}/series.json", series)
        if r.get("ensayo_demo") and escena["id"] == r["ensayo_demo"]["escena"]:
            toma["ensayo_demo"] = ensayo_demo(toma, r["ensayo_demo"])
        previo = carpeta.corridas().get(sid) or {}
        sujeto = previo.get("sujeto")
        if (not sujeto or sujeto.get("estado") != "ok") and not ctx.reagregar and toma["ids"].get("media_run_id"):
            ctx.avisar(f"  {sid} ({escena['id']}): relectura por sujeto")
            sujeto = _releer_por_sujeto(ctx, prueba, carpeta, sesion)
        if sujeto and sujeto.get("estado") == "ok":
            toma["sujeto"] = _sujeto(ctx, escena, sujeto)
        carpeta.guardar_corrida(sid, {"estado": "ok", "escena": escena["id"], "experiment_id": toma["experiment_id"],
                                      **{k: v for k, v in toma["ids"].items()}, "sujeto": sujeto,
                                      "importada": ahora()})
        if stream is not None:
            toma["stream"] = streams[stream]
        carpeta.escribir(f"tomas/{sid}/toma.json", toma)
        tomas.append({**toma, "_series": series})

    # --- agregado ------------------------------------------------------------------
    if len(configs_stream) > 1:
        # RT-06: una configuración por stream; cada una con su agregado y sus tomas mínimas.
        por_stream, resumen, faltan_alguna = {}, [], False
        for nombre, cfg in configs_stream.items():
            m, res = _agregar([t for t in tomas if t.get("stream") == nombre], fuente=fuente,
                              etiqueta=cfg.get("etiqueta", nombre), minimas=cfg.get("tomas_minimas"),
                              sufijo=f" — stream {nombre}", clave_sufijo=f"_{nombre}")
            por_stream[nombre] = {"ruta": cfg["ruta"], **m}
            resumen += res
            faltan_alguna |= any((m.get("faltan_tomas") or {}).values())
        metricas = {"tomas": len(tomas),
                    "tomas_como_se_esperaba": sum(1 for t in tomas if t["como_se_esperaba"]),
                    "por_stream": por_stream, "no_evaluables": no_evaluables, "fuente": fuente}
        estado = "completo" if tomas and not faltan_alguna else "parcial"
    else:
        etiqueta = (next(iter(configs_stream.values()), {}).get("etiqueta")
                    or r.get("etiqueta_camara", "960×540 a 5 fps"))
        m, resumen = _agregar(tomas, fuente=fuente, etiqueta=etiqueta, minimas=r.get("tomas_minimas"))
        # Una escena del guion sin ninguna toma no desaparece en silencio: se nombra y la prueba
        # queda «parcial» (p. ej., las de dos personas si un día falta el segundo juego de EPP).
        sin_tomas = [e for e in escenas_de_la_prueba if e not in m["por_escena"]]
        metricas = {**m, "escenas_sin_tomas": sin_tomas, "no_evaluables": no_evaluables, "fuente": fuente}
        faltan = sin_tomas or any((m.get("faltan_tomas") or {}).values())
        estado = "completo" if tomas and not faltan else "parcial"
    carpeta.escribir("evals/tomas.json", [{k: v for k, v in t.items() if k != "_series"} for t in tomas])
    datos = {
        "familia": "rodaje",
        "estado": estado,
        "metricas": metricas,
        "resumen": resumen,
        "veredicto": {"propuesto": "otra_combinacion", "motivo": prueba.gen1.get("motivo"),
                      "referencia": prueba.gen1.get("doc"), "diferencias": {}, "confirmado": None},
    }
    if not tomas:
        datos["nota"] = "todavía no hay sesiones de la demo etiquetadas con una escena (rodaje.ps1)"
    carpeta.resultado(datos)
    return {"estado": datos["estado"], "tomas": len(tomas), "como_se_esperaba": metricas["tomas_como_se_esperaba"]}
