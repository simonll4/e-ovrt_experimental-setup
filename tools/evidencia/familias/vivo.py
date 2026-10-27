"""Pruebas en vivo (Tabla 54, §17.5.5).

- RT-01: sobrecarga de la plataforma sin inferencia — `mp-mock`, n = 300 (como P3 del doc 133).
- RT-02: integridad del bus — una corrida en vivo con bus (control → medios) y su relectura
  offline sobre las MISMAS detecciones: los artefactos del control tienen que ser idénticos
  módulo los campos volátiles de `test_bus_parity.py`, con 0 pérdidas en el bus.
- RT-03: tomas con la OAK-D y personas en escena (`vivo RT-03 --toma ... --config ...`), en la
  config de la demo y a 1080p@30 (la del informe). Antes de cada toma se reinicia la instancia
  del modelo (F-101.5). Se mide G2A, captura → host y vidrio → resultado por cuadro. (Las
  escenas del rodaje con alertas y broker son RT-04: `familias/rodaje.py`.)
- DIST-01: alerta → PUBACK MQTT QoS 1 sobre el corpus de alertas de la generación 2, con el
  ledger en el disco del contenedor (doc 133 §3.4), dentro del contenedor `distribution`.
"""
from __future__ import annotations

import json
import math
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

from ..catalogo import Prueba
from ..comparar import proponer
from ..entorno import contenedor_de, docker_compose
from ..herramientas import escribir_yaml, resumen_control, resumen_media, ruta_video
from ..huellas import armar_prompts, sha256_archivo
from ..registro import Carpeta, ahora, escribir_json
from . import Contexto, familia, preparar_modelo
from .clips import experiment_id_de, slug_de
from .imagenes import _correr_medios

# Los de `test_bus_parity.py` del control-plane, más `experiment_id`: el runner de la consola
# lo inyecta en cada corrida, y vivo y relectura son dos experimentos distintos por construcción.
VOLATILES = ("control_run_id", "alert_id", "first_evidence_ms", "alert_registered_ms", "experiment_id")
# El publicador del media-plane espera a que el control se suscriba antes del primer evento
# (sin esto, con un video el primer evento se pierde: ensayo del 2026-10-26).
BUS_MEDIOS = {"wait_for_subscriber_ms": 10000}


def nearest_rank(xs: list[float], q: float):
    xs = sorted(xs)
    return xs[max(0, math.ceil(q / 100 * len(xs)) - 1)] if xs else None


def _stats(xs: list[float]) -> dict:
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "p50": round(nearest_rank(xs, 50), 3), "p95": round(nearest_rank(xs, 95), 3),
            "max": round(max(xs), 3)}


def _leer_jsonl(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def _bus_endpoint(ctx: Contexto, receta: dict) -> str:
    if ctx.ent.modo == "docker":
        return f"tcp://{receta['instancia']}:5557"
    return receta.get("bus_nativo", "tcp://127.0.0.1:5557")


def _control_live(ctx: Contexto, receta: dict, nombre: str, *, alert_bus: bool) -> dict:
    spec = receta["control"]
    config = {
        "run": {"id": None, "scenario": "EBE", "name": nombre,
                "description": f"Generación 2 — {nombre}"},
        "input": {
            "type": "bus",
            "bus": {
                "endpoint": _bus_endpoint(ctx, receta),
                "topics": ["media.detection.v1.", "run.lifecycle.v1."],
                "hwm": 1000,
                "recv_timeout_ms": 1000,
                "idle_timeout_s": 300,
                "finish": {"signal": "run_lifecycle", "poll_url": None, "poll_interval_s": 5},
            },
        },
        "patterns": {"file": str(ctx.ent.patrones / f"{spec['patrones']}.yaml"),
                     "active_ids": list(spec.get("activos") or ["CR-01", "CR-02"])},
        "outputs": {"base_dir": str(ctx.ent.control_runs), "save_pattern_events_jsonl": True,
                    "save_alerts_jsonl": True, "save_metrics_jsonl": True, "save_errors_jsonl": True,
                    "save_summary_json": True},
        "logging": {"level": "INFO"},
    }
    if spec.get("track_persons"):
        config["input"]["track_persons"] = True
    if alert_bus:
        config["alert_bus"] = {"enabled": True, "endpoint": "tcp://0.0.0.0:5558", "hwm": 1000,
                               "wait_for_subscriber_ms": 10000}
    return config


def _lanzar(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, nombre: str, runs: dict, sequencing: str,
            timeout_s: float, **extra) -> dict:
    manifiesto = {"schema_version": "experiment.manifest.v1", "slug": slug_de(prueba),
                  "experiment_id": experiment_id_de(nombre), "runs": runs,
                  "sequencing": sequencing, "timeout_s": timeout_s,
                  "changes": f"generación 2 — prueba {prueba.id}", **extra}
    dir_gen = ctx.ent.generados / prueba.id / nombre
    escribir_yaml(dir_gen / "manifest.yaml", manifiesto)
    carpeta.comando(f"POST /api/experiments/run  manifiesto={dir_gen / 'manifest.yaml'}")
    t0, inicio = time.monotonic(), ahora()
    estado = ctx.consola.correr(manifiesto, timeout_s=timeout_s)
    return {"estado": "ok" if estado.get("ok") else "fallo", "inicio": inicio, "fin": ahora(),
            "segundos": round(time.monotonic() - t0, 1), **{k: estado.get(k) for k in (
                "experiment_id", "media_run_id", "control_run_id", "media_status", "control_status",
                "distribution_status", "consolidated_dir", "error")}}


# --- RT-01 ----------------------------------------------------------------------------


def _rt01(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    objetivo = preparar_modelo(ctx, r, carpeta)
    prompts, constancia = armar_prompts(r["prompts"], ctx.ent.repo)
    clave = "mock_n300"
    if not carpeta.corrida_ok(clave):
        media_cfg = {
            "ingest": {"plugin": "video_file", "config": {
                "path": ctx.ent.ruta_medios(ruta_video(ctx.ent, r["clip"])), "source_id": r["clip"]}},
            "prompts": prompts,
            "run": {"name": f"gen2_rt01_{clave}", "max_units": int(r.get("unidades", 300)), "save_previews": False},
        }
        carpeta.guardar_corrida(clave, _correr_medios(ctx, prueba, carpeta, clave, media_cfg, 900))
    registro = carpeta.corrida_ok(clave)
    if not registro:
        raise RuntimeError(f"RT-01: la corrida falló: {carpeta.corridas()[clave].get('error')}")
    resumen_m = resumen_media(ctx.ent, registro["media_run_id"])
    g2a = resumen_m.get("g2a") or {}
    metricas = {"g2a_p50_ms": g2a.get("p50_ms"), "g2a_p95_ms": g2a.get("p95_ms"), "n": g2a.get("count"),
                "unidades": resumen_m.get("units_processed"), "descartadas": resumen_m.get("units_dropped")}
    carpeta.escribir("configuracion.json", {"prompts": constancia, "modelo_cargado": objetivo})
    resumen = [
        {"clave": "g2a_p50_ms", "nombre": "G2A p50 sin inferencia (detector simulado)", "valor": metricas["g2a_p50_ms"], "unidad": "ms", "gen1": None},
        {"clave": "g2a_p95_ms", "nombre": "G2A p95 sin inferencia (detector simulado)", "valor": metricas["g2a_p95_ms"], "unidad": "ms", "gen1": None},
    ]
    return {"metricas": metricas, "resumen": resumen}


# --- RT-02 ----------------------------------------------------------------------------


def _normalizar(ruta: Path) -> list[dict]:
    filas = []
    for fila in _leer_jsonl(ruta):
        for campo in VOLATILES:
            fila.pop(campo, None)
        filas.append(fila)
    return filas


def _rt02(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    objetivo = preparar_modelo(ctx, r, carpeta)
    prompts, constancia = armar_prompts(r["prompts"], ctx.ent.repo)
    clip = r["clip"]
    if not carpeta.corrida_ok("vivo"):
        nombre = f"gen2_rt02_vivo_{clip}"
        dir_gen = ctx.ent.generados / prueba.id / nombre
        media_path = escribir_yaml(dir_gen / "media.yaml", {
            "ingest": {"plugin": "video_file", "config": {
                "path": ctx.ent.ruta_medios(ruta_video(ctx.ent, clip)), "source_id": clip}},
            "prompts": prompts,
            "run": {"name": nombre, "save_previews": False},
            "bus": dict(BUS_MEDIOS),
        })
        control_path = escribir_yaml(dir_gen / "control.yaml", _control_live(ctx, r, nombre, alert_bus=False))
        reg = _lanzar(ctx, prueba, carpeta, nombre, {
            "media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
            "control": {"service": "control-plane", "config": str(control_path), "mode": "live"},
        }, "control_first", 1800, clip_id=clip)
        reg["media_config"] = str(media_path)
        carpeta.guardar_corrida("vivo", reg)
    vivo = carpeta.corrida_ok("vivo")
    if not vivo:
        raise RuntimeError(f"RT-02: la corrida en vivo falló: {carpeta.corridas()['vivo'].get('error')}")
    if not carpeta.corrida_ok("relectura"):
        nombre = f"gen2_rt02_relectura_{clip}"
        dir_gen = ctx.ent.generados / prueba.id / nombre
        spec = r["control"]
        control_cfg = _control_live(ctx, r, nombre, alert_bus=False)
        control_cfg["run"]["scenario"] = "DBE"
        control_cfg["input"] = {"type": "media_jsonl", "path": "(la completa el runner de la consola)"}
        if spec.get("track_persons"):
            control_cfg["input"]["track_persons"] = True
        control_path = escribir_yaml(dir_gen / "control.yaml", control_cfg)
        reg = _lanzar(ctx, prueba, carpeta, nombre, {
            "media": {"service": "media-plane", "config": vivo["media_config"], "mode": "run",
                      "reuse_run_id": vivo["media_run_id"]},
            "control": {"service": "control-plane", "config": str(control_path), "mode": "replay"},
        }, "media_first", 600, clip_id=clip)
        carpeta.guardar_corrida("relectura", reg)
    relectura = carpeta.corrida_ok("relectura")
    if not relectura:
        raise RuntimeError(f"RT-02: la relectura falló: {carpeta.corridas()['relectura'].get('error')}")
    a = ctx.ent.control_runs / vivo["control_run_id"]
    b = ctx.ent.control_runs / relectura["control_run_id"]
    comparacion = {}
    for archivo in ("pattern_events.jsonl", "alerts.jsonl"):
        na, nb = _normalizar(a / archivo), _normalizar(b / archivo)
        comparacion[archivo] = {"vivo": len(na), "relectura": len(nb), "identicos": na == nb}
    resumen_c = resumen_control(ctx.ent, vivo["control_run_id"])
    caidos = resumen_c.get("bus_dropped_events")
    metricas = {"paridad": all(c["identicos"] for c in comparacion.values()),
                "bus_dropped_events": caidos,
                "eventos_de_patron": comparacion["pattern_events.jsonl"]["vivo"],
                "alertas": comparacion["alerts.jsonl"]["vivo"]}
    carpeta.escribir("evals/paridad.json", {"volatiles": VOLATILES, "comparacion": comparacion,
                                            "resumen_control_vivo": resumen_c})
    carpeta.escribir("configuracion.json", {"prompts": constancia, "modelo_cargado": objetivo})
    resumen = [
        {"clave": "paridad", "nombre": "Vivo y relectura producen los mismos eventos y alertas",
         "valor": "sí" if metricas["paridad"] else "NO", "unidad": None, "gen1": "sí"},
        {"clave": "bus_dropped_events", "nombre": "Eventos perdidos en el bus", "valor": caidos, "unidad": None, "gen1": 0},
        {"clave": "alertas", "nombre": "Alertas de la corrida", "valor": metricas["alertas"], "unidad": None, "gen1": None},
    ]
    return {"metricas": metricas, "resumen": resumen}


# --- RT-03: tomas con la OAK-D -------------------------------------------------


def _reiniciar_instancia(ctx: Contexto, r: dict, carpeta: Carpeta) -> None:
    """F-101.5: una corrida con la OAK-D por vida del motor. En Docker, `docker compose restart`
    (no recrea el contenedor: la regla del doc 133) y espera de `readyz`."""
    if ctx.ent.modo != "docker":
        if not ctx.opciones.get("sin_reinicio"):
            raise RuntimeError("en nativo reiniciá el media-plane a mano antes de cada toma "
                               "(F-101.5) y repetí con --sin-reinicio")
        return
    carpeta.comando(f"docker compose restart {r['instancia']}")
    if docker_compose(ctx.ent, "restart", r["instancia"], timeout=180) is None:
        raise RuntimeError(f"no se pudo reiniciar {r['instancia']}")
    limite = time.monotonic() + 300
    while time.monotonic() < limite:
        time.sleep(3)
        try:
            objetivo = ctx.consola.objetivo()
        except Exception:  # noqa: BLE001 - el servicio todavía no responde
            continue
        if objetivo.get("ready") and (objetivo.get("model") or {}).get("ref") == r["modelo"]:
            return
    raise RuntimeError(f"{r['instancia']} no quedó listo 300 s después de reiniciarlo")


def _metricas_toma(ctx: Contexto, media_run_id: str) -> dict:
    filas = _leer_jsonl(ctx.ent.media_runs / media_run_id / "metrics.jsonl")
    g2a = [f["g2a_ms"] for f in filas if f.get("g2a_ms") is not None]
    c2h = [f["capture_to_host_ms"] for f in filas if f.get("capture_to_host_ms") is not None]
    vidrio = [f["g2a_ms"] + f["capture_to_host_ms"] for f in filas
              if f.get("g2a_ms") is not None and f.get("capture_to_host_ms") is not None]
    capturas = sorted(f["capture_wallclock_ms"] for f in filas if f.get("capture_wallclock_ms") is not None)
    huecos = [b - a for a, b in zip(capturas, capturas[1:])]
    resumen_m = resumen_media(ctx.ent, media_run_id)
    mediana = statistics.median(huecos) if huecos else None
    hueco_max = max(huecos) if huecos else None
    c2h_p95 = nearest_rank(c2h, 95) if c2h else None
    contaminada = bool(
        (hueco_max is not None and mediana is not None and hueco_max > max(5 * mediana, 3000))
        or (c2h_p95 is not None and c2h_p95 > 2000)
    )
    desfase = [f["capture_wallclock_ms"] - f["capture_monotonic_ns"] / 1e6 for f in filas
               if f.get("capture_wallclock_ms") is not None and f.get("capture_monotonic_ns") is not None]
    return {
        "unidades": resumen_m.get("units_processed"),
        "descartadas": resumen_m.get("units_dropped"),
        "fps_efectivos": resumen_m.get("fps_effective"),
        "inferencia_p50_ms": resumen_m.get("p50_latency_ms"),
        "inferencia_p95_ms": resumen_m.get("p95_latency_ms"),
        "g2a": _stats(g2a),
        "captura_a_host": _stats(c2h),
        "vidrio_a_resultado": _stats(vidrio),
        "hueco_max_ms": hueco_max,
        "hueco_mediana_ms": mediana,
        "contaminada": contaminada,
        "reloj_pared_menos_monotonico_ms": statistics.median(desfase) if desfase else None,
        "_series": {"g2a": g2a, "captura_a_host": c2h, "vidrio_a_resultado": vidrio},
    }


def _toma(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    toma, config = ctx.opciones.get("toma"), ctx.opciones.get("config")
    if toma and config:
        _correr_toma(ctx, prueba, carpeta, toma, config)
    elif not ctx.reagregar:
        raise ValueError(f"{prueba.id} corre por tomas: `vivo {prueba.id} --toma <nombre> --config "
                         f"{'|'.join(r['configs'])}` (o `correr {prueba.id} --reagregar`)")
    # Agregado por configuración, juntando los cuadros de las tomas válidas.
    por_config: dict[str, dict] = {}
    for clave, reg in carpeta.corridas().items():
        if reg.get("estado") != "ok" or reg.get("metricas", {}).get("contaminada"):
            continue
        series = json.loads((carpeta.dir / "tomas" / clave / "series.json").read_text())
        agg = por_config.setdefault(reg["config"], {"tomas": [], "g2a": [], "captura_a_host": [],
                                                    "vidrio_a_resultado": [], "fps": []})
        agg["tomas"].append(clave)
        for k in ("g2a", "captura_a_host", "vidrio_a_resultado"):
            agg[k].extend(series[k])
        if reg["metricas"].get("fps_efectivos") is not None:
            agg["fps"].append(reg["metricas"]["fps_efectivos"])
    metricas, resumen = {}, []
    for cfg, agg in sorted(por_config.items()):
        datos = {k: _stats(agg[k]) for k in ("g2a", "captura_a_host", "vidrio_a_resultado")}
        datos["fps_efectivos"] = round(statistics.mean(agg["fps"]), 2) if agg["fps"] else None
        datos["tomas"] = agg["tomas"]
        metricas[cfg] = datos
    demo = r.get("config_demo")
    if demo in metricas:
        d = metricas[demo]
        resumen = [
            {"clave": "fps_efectivos", "nombre": f"Cuadros por segundo procesados ({demo})", "valor": d["fps_efectivos"], "unidad": "fps", "gen1": None},
            {"clave": "g2a_p95_ms", "nombre": f"G2A p95 ({demo})", "valor": d["g2a"].get("p95"), "unidad": "ms", "gen1": None},
            {"clave": "capture_to_host_p50_ms", "nombre": f"Captura → host p50 ({demo})", "valor": d["captura_a_host"].get("p50"), "unidad": "ms", "gen1": None},
            {"clave": "vidrio_a_resultado_p95_ms", "nombre": f"Vidrio → resultado p95 ({demo})", "valor": d["vidrio_a_resultado"].get("p95"), "unidad": "ms", "gen1": None},
        ]
    return {"metricas": metricas, "resumen": resumen, "tomas_validas": sum(len(a["tomas"]) for a in por_config.values())}


def _correr_toma(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, toma: str, config: str) -> None:
    r = prueba.receta
    if config not in r["configs"]:
        raise ValueError(f"config {config!r} no está en la receta ({list(r['configs'])})")
    if carpeta.corrida_ok(toma) and not ctx.forzar:
        ctx.avisar(f"  la toma {toma} ya está registrada (usá otro nombre)")
        return
    _reiniciar_instancia(ctx, r, carpeta)
    preparar_modelo(ctx, r, carpeta)
    prompts, constancia = armar_prompts(r["prompts"], ctx.ent.repo)
    perfil = r["configs"][config]
    camara = {**r["camara"], **perfil["camara"]}
    # `max_units` cuenta cuadros RECIBIDOS: a 5 fps, 300 ≈ 60 s (nota del manifiesto validado en la Victus).
    unidades = int(ctx.opciones.get("unidades") or perfil.get("unidades") or r.get("unidades", 250))
    nombre = f"gen2_{prueba.id.lower().replace('-', '')}_{toma}"
    dir_gen = ctx.ent.generados / prueba.id / nombre
    media_path = escribir_yaml(dir_gen / "media.yaml", {
        "ingest": {"plugin": "oak_d", "config": camara},
        "prompts": prompts,
        "run": {"name": nombre, "max_units": unidades, "save_previews": True},
        "bus": dict(BUS_MEDIOS),
    })
    control_path = escribir_yaml(dir_gen / "control.yaml", _control_live(ctx, r, nombre, alert_bus=False))
    runs = {"media": {"service": "media-plane", "config": str(media_path), "mode": "run"},
            "control": {"service": "control-plane", "config": str(control_path), "mode": "live"}}
    toma_dir = carpeta.dir / "tomas" / toma
    toma_dir.mkdir(parents=True, exist_ok=True)
    ctx.avisar(f"  toma {toma} ({config}): lanzando; la persona entra a cuadro cuando la consola "
               "muestre cuadros procesados (~11 s)")
    reg = _lanzar(ctx, prueba, carpeta, nombre, runs, "control_first", float(r.get("timeout_s", 1800)))
    reg.update({"config": config, "media_config": str(media_path), "control_config": str(control_path),
                "sha256": {"media_config": sha256_archivo(media_path), "control_config": sha256_archivo(control_path)}})
    if reg["estado"] == "ok" or reg.get("media_run_id"):
        metricas = _metricas_toma(ctx, reg["media_run_id"])
        escribir_json(toma_dir / "series.json", metricas.pop("_series"))
        reg["metricas"] = metricas
        if metricas["contaminada"]:
            ctx.avisar("      ⚠ toma contaminada (huecos de la cámara o captura → host > 2 s, doc 101 §5.3): "
                       "no entra al agregado; apagá y prendé la OAK-D y repetí")
    carpeta.escribir("configuracion.json", {"prompts": constancia})
    carpeta.guardar_corrida(toma, reg)
    if reg["estado"] != "ok":
        ctx.avisar(f"      la toma terminó con estado {reg['estado']}: {reg.get('error')}")


# --- DIST-01 ------------------------------------------------------------------------------

_SCRIPT_DIST = Path(__file__).resolve().parent.parent / "dist01_contenedor.py"


def _dist01(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    base = ctx.ent.trabajo / prueba.id
    corpus_dir = base / "corpus"
    if corpus_dir.exists():
        shutil.rmtree(corpus_dir)
    corpus_dir.mkdir(parents=True)
    corridas_corpus = []
    for pid in r["corpus"]:
        for clave, reg in sorted(ctx.corridas_completas(pid).items()):
            registros = [reg, *((reg.get("variantes") or {}).values())]
            for x in registros:
                cid = x.get("control_run_id")
                if not cid:
                    continue
                origen = ctx.ent.control_runs / cid / "alerts.jsonl"
                destino = corpus_dir / f"{cid}.jsonl"
                shutil.copyfile(origen, destino) if origen.is_file() else destino.write_text("")
                corridas_corpus.append(cid)
    (base / "corpus_runs.json").write_text(json.dumps(corridas_corpus), encoding="utf-8")
    ledgers = base / "ledgers"
    if ledgers.exists():
        shutil.rmtree(ledgers)
    broker_host = r["broker"].get("host_nativo", "127.0.0.1") if ctx.ent.modo == "nativo" else r["broker"]["host"]
    params = {"corpus": str(corpus_dir), "runs": str(base / "corpus_runs.json"), "salida": str(ledgers),
              "broker_host": broker_host, "broker_port": int(r["broker"]["port"]),
              "endpoint": r.get("endpoint", "tcp://127.0.0.1:15558"),
              "ledger_tmp": r.get("ledger_tmp", "/tmp/eovrt-dist01")}
    carpeta.escribir("evals/parametros.json", params)
    if ctx.ent.modo == "docker":
        contenedor = contenedor_de(ctx.ent, r.get("servicio", "distribution"))
        if not contenedor:
            raise RuntimeError("no se encontró el contenedor del servicio de distribución")
        cmd = ["docker", "exec", "-i", contenedor, "python3", "-", json.dumps(params)]
    else:
        cmd = [sys.executable, "-", json.dumps(params)]
    carpeta.comando(" ".join(cmd[:-1]) + " '<parametros>' < tools/evidencia/dist01_contenedor.py")
    ctx.avisar(f"  DIST-01: {len(corridas_corpus)} corridas del corpus por el canal (esto tarda)")
    proc = subprocess.run(cmd, input=_SCRIPT_DIST.read_text(encoding="utf-8"), capture_output=True,
                          text=True, check=False)
    (carpeta.dir / "logs").mkdir(parents=True, exist_ok=True)
    (carpeta.dir / "logs" / "dist01.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"DIST-01 rc={proc.returncode}: {proc.stderr[-400:]}")
    agregado = _agregar_talert(ledgers)
    carpeta.escribir("evals/talert_notification.json", agregado)
    metricas = {"corridas": agregado["runs"], "entregadas": agregado["outcomes"].get("delivered", 0),
                "suprimidas": agregado["outcomes"].get("suppressed_cooldown", agregado["outcomes"].get("suppressed", 0)),
                "p50_ms": agregado["all"].get("p50"), "p95_ms": agregado["all"].get("p95"),
                "primeras_p95_ms": agregado["first_per_run"].get("p95")}
    resumen = [
        {"clave": "p95_ms", "nombre": "Alerta → PUBACK MQTT QoS 1, p95 (todas las entregas)", "valor": metricas["p95_ms"], "unidad": "ms", "gen1": 64.534},
        {"clave": "primeras_p95_ms", "nombre": "Primera entrega de cada corrida, p95", "valor": metricas["primeras_p95_ms"], "unidad": "ms", "gen1": 49.9},
        {"clave": "entregadas", "nombre": "Notificaciones entregadas", "valor": metricas["entregadas"], "unidad": None, "gen1": 460},
    ]
    return {"metricas": metricas, "resumen": resumen}


def _agregar_talert(raiz: Path) -> dict:
    """Reglas de la campaña original (talert_aggregate.py del doc 133): solo `delivered` en
    vivo, nearest-rank, primeras entregas de cada corrida vs 2.ª en adelante."""
    todas, primeras, resto, resultados = [], [], [], {}
    corridas = 0
    for d in sorted(p for p in raiz.iterdir() if p.is_dir()):
        corridas += 1
        k = 0
        for fila in _leer_jsonl(d / "notifications.jsonl"):
            resultados[fila.get("outcome")] = resultados.get(fila.get("outcome"), 0) + 1
            if fila.get("outcome") == "delivered" and fila.get("mode") == "live" and fila.get("latency_mode") == "live":
                v = fila["talert_notification_ms"]
                todas.append(v)
                (primeras if k == 0 else resto).append(v)
                k += 1

    def st(xs):
        return ({"n": len(xs), "min": round(min(xs), 3), "mean": round(sum(xs) / len(xs), 3),
                 "p50": round(nearest_rank(xs, 50), 3), "p95": round(nearest_rank(xs, 95), 3),
                 "p99": round(nearest_rank(xs, 99), 3), "max": round(max(xs), 3)} if xs else {"n": 0})

    return {"runs": corridas, "outcomes": resultados, "all": st(todas), "first_per_run": st(primeras),
            "second_plus": st(resto)}


_PRUEBAS = {"RT-01": _rt01, "RT-02": _rt02, "RT-03": _toma, "DIST-01": _dist01}


@familia("vivo")
def correr(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    funcion = _PRUEBAS.get(prueba.id)
    if funcion is None:
        raise ValueError(f"{prueba.id}: no hay prueba en vivo definida")
    salida = funcion(ctx, prueba, carpeta)
    datos = {"familia": "vivo", "estado": "completo", **salida,
             "veredicto": proponer(salida["metricas"], prueba)}
    if prueba.id == "RT-03" and not salida.get("tomas_validas"):
        datos["estado"] = "parcial"
    carpeta.resultado(datos)
    return {"estado": datos["estado"], "veredicto": datos["veredicto"]["propuesto"]}
