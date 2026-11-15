"""«Correr un clip» (plan de la consola de evidencia, §7.2): un clip del rodaje por la cadena completa.

Tres clips fijos del rodaje propio —uno sin casco, uno sin chaleco y uno sin infracción—, nada que configurar.
Corre con el perfil operativo y la configuración congelada de la demo (la que se chequea contra el tag del
informe), a 5 cuadros por segundo (uno de cada 6 de un video a 30), por video → reglas en vivo → distribución en
vivo → broker. Lo lanza el mismo administrador de experimentos que usan el driver y la demo, sin modificarlo
(plan §11). El testigo MQTT de la demo registra el mensaje que llega al broker.

No es evidencia y lo dice: queda en `runs/demostracion/<corrida>/` (el consolidado del experimento, en `runs/`),
fuera de `results/gen2`, rotulado «demostración».
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from eovrt_webconsole.demo import config as demo_config
from eovrt_webconsole.demo.testigo import TestigoError, TestigoMqtt, ping_broker
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.plataforma import PERFIL_OPERATIVO

logger = logging.getLogger(__name__)

CLIPS: tuple[dict[str, str], ...] = (
    {"id": "a_p1_c04", "titulo": "Sin casco"},
    {"id": "a_p2_c03", "titulo": "Sin chaleco"},
    {"id": "a_p3_c01", "titulo": "Sin infracción"},
)
# Uno de cada 6 cuadros de un video a 30: los 5 cuadros por segundo del despliegue.
STRIDE = 6
SLUG = "demostracion_clip"
TIMEOUT_S = 300.0
_VENTANA_MS = 10_000.0  # si la evaluación no la trae: hasta cuánto después del fin del episodio cuenta una alerta
_FASES_DEMO = ("preparing", "live", "finishing", "rendering")
_BANCO = Path("e-ovrt_datasets") / "datasets"


class ClipDesconocido(KeyError):
    pass


class ClipOcupado(RuntimeError):
    pass


class ClipNoListo(RuntimeError):
    def __init__(self, preparacion: dict) -> None:
        super().__init__("la plataforma no está lista para correr el clip")
        self.preparacion = preparacion


def _leer_json(ruta: Path) -> Any:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _leer_jsonl(ruta: Path) -> list[dict]:
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    salida = []
    for linea in lineas:
        try:
            dato = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if isinstance(dato, dict):
            salida.append(dato)
    return salida


def armar_resultado(referencia: dict, alertas: list[dict], evaluacion: dict | None,
                    mensajes: list[dict]) -> dict[str, Any]:
    """Las alertas de la corrida al lado de los episodios de la referencia del clip.

    Las cifras de conteo son las del evaluador oficial (`temporal_evaluation.json`). El emparejamiento de cada
    alerta con su episodio es solo para mostrarlas juntas: la misma condición, confirmada entre el comienzo del
    episodio y su fin más la ventana que usó el evaluador. La demora es desde que empieza el episodio.
    """
    fps = float(referencia.get("fps_nominal") or 30)
    episodios = [e for e in referencia.get("episodes") or [] if isinstance(e, dict)]
    ventanas = (evaluacion or {}).get("effective_matching_windows") or {}
    usados: set[str] = set()
    por_alerta = {((m.get("payload") or {}).get("alert_id")): m for m in mensajes if isinstance(m, dict)}
    filas = []
    for a in sorted(alertas, key=lambda x: x.get("timestamp_ms") or 0):
        condicion = a.get("condition_id")
        confirmada = a.get("timestamp_ms")
        primera = a.get("first_evidence_frame_index")
        episodio = None
        for e in episodios:
            ventana = float((ventanas.get(condicion) or {}).get("t_alert_max_ms") or _VENTANA_MS)
            if (e.get("id") not in usados and e.get("condition_id") == condicion and confirmada is not None
                    and e.get("start_ms", 0) <= confirmada <= e.get("end_ms", 0) + ventana):
                episodio = e
                usados.add(e.get("id"))
                break
        mensaje = por_alerta.get(a.get("alert_id"))
        payload = (mensaje or {}).get("payload") or {}
        emitida = payload.get("confirmed_wall_ms")
        filas.append({
            "alert_id": a.get("alert_id"),
            "condicion": condicion,
            "confirmada_ms": confirmada,
            "primera_evidencia_ms": round(primera / fps * 1000, 1) if isinstance(primera, (int, float)) else None,
            "episodio": {"condicion": episodio["condition_id"], "desde_ms": episodio["start_ms"],
                         "hasta_ms": episodio.get("end_ms")} if episodio else None,
            "demora_ms": round(confirmada - episodio["start_ms"], 1) if episodio and confirmada is not None else None,
            "broker": {
                "topic": mensaje.get("topic"), "recibido_en": mensaje.get("recibido_en"), "payload": payload,
                "demora_ms": round(mensaje["recibido_ms"] - emitida, 1)
                if isinstance(mensaje.get("recibido_ms"), (int, float)) and isinstance(emitida, (int, float)) else None,
            } if mensaje else None,
        })
    sin_alerta = [{"condicion": e.get("condition_id"), "desde_ms": e.get("start_ms"), "hasta_ms": e.get("end_ms")}
                  for e in episodios if e.get("id") not in usados]
    oficial = None
    if isinstance(evaluacion, dict):
        oficial = {k: evaluacion.get(f"{k}_alerts_count") for k in ("expected", "observed", "matched", "missed", "unexpected")}
    return {"alertas": filas, "sin_alerta": sin_alerta, "evaluacion": oficial}


@dataclass
class _Corrida:
    id: str
    clip: dict
    experiment_id: str
    carpeta: Path
    iniciada: float
    cuadros_esperados: int | None
    testigo: Any
    fase: str = "corriendo"
    ids: dict[str, str] = field(default_factory=dict)
    pasos: dict[str, dict] = field(default_factory=lambda: {
        p: {"estado": "espera"} for p in ("deteccion", "reglas", "distribucion", "broker")})
    resultado: dict | None = None
    error: str | None = None
    terminada: float | None = None

    def publica(self) -> dict[str, Any]:
        return {
            "id": self.id, "clip": self.clip, "experiment_id": self.experiment_id, "fase": self.fase,
            "iniciada_en": datetime.fromtimestamp(self.iniciada, tz=UTC).isoformat(),
            "terminada_en": datetime.fromtimestamp(self.terminada, tz=UTC).isoformat() if self.terminada else None,
            "cuadros_esperados": self.cuadros_esperados, "pasos": self.pasos, "resultado": self.resultado,
            "error": self.error, "demostracion": True,
        }


class CorrerClip:
    def __init__(self, app: Any, salida: Path | None = None, *,
                 testigo_factory: Callable[[str, int], Any] | None = None,
                 ping: Callable[..., dict] | None = None,
                 reloj: Callable[[], float] = time.time, poll_s: float = 0.5,
                 extra_runner: dict | None = None, workspace: Path | None = None) -> None:
        self._app = app
        settings = app.state.settings
        self._repo = Path(settings.repo_root)
        self._ws = workspace
        self.salida = salida or (self._repo / "runs" / "demostracion")
        self._testigo_factory = testigo_factory or (lambda host, port: TestigoMqtt(host, port))
        self._ping = ping or ping_broker
        self._reloj = reloj
        self._poll_s = poll_s
        self._extra = extra_runner or {}
        self._corrida: _Corrida | None = None
        self._tareas: set[asyncio.Task] = set()
        self._arranque = asyncio.Lock()

    # --- los clips ---------------------------------------------------------------------------

    def _workspace(self) -> Path:
        return self._ws or self._repo.parent

    def _referencia(self, clip_id: str) -> dict | None:
        datos = _leer_json(self._workspace() / _BANCO / "processed" / "clip_bench" / "gt" / f"{clip_id}.json")
        return datos if isinstance(datos, dict) else None

    def _video(self, clip_id: str) -> Path:
        return self._workspace() / _BANCO / "raw" / "clip_bench" / "clips" / f"{clip_id}.mp4"

    def cadencia(self) -> dict[str, Any]:
        """Uno de cada `STRIDE` cuadros del video: los cuadros por segundo que procesa, calculados del clip."""
        fps = next((float(r["fps_nominal"]) for c in CLIPS if (r := self._referencia(c["id"])) and r.get("fps_nominal")), None)
        return {"uno_de_cada": STRIDE, "cuadros_por_segundo": round(fps / STRIDE, 2) if fps else None}

    def clips(self) -> list[dict[str, Any]]:
        salida = []
        for c in CLIPS:
            ref = self._referencia(c["id"]) or {}
            salida.append({
                **c,
                "disponible": self._video(c["id"]).is_file() and bool(ref),
                "duracion_ms": ref.get("duration_ms"),
                "referencia": [{"condicion": e.get("condition_id"), "desde_ms": e.get("start_ms"), "hasta_ms": e.get("end_ms")}
                               for e in ref.get("episodes") or [] if isinstance(e, dict)],
            })
        return salida

    # --- antes de correr ---------------------------------------------------------------------

    def _en_curso(self) -> str | None:
        demo = getattr(self._app.state, "demo_manager", None)
        if demo is not None and demo.estado().get("fase") in _FASES_DEMO:
            return "hay una sesión de demo en curso"
        if self._app.state.experiment_manager.current() is not None:
            return "hay una corrida en curso en la consola"
        return None

    async def _sano(self, cliente: httpx.AsyncClient, ruta: str = "/healthz") -> bool:
        try:
            return (await cliente.get(ruta)).status_code == 200
        except httpx.HTTPError:
            return False

    async def preparacion(self) -> dict[str, Any]:
        """Lo que tiene que estar para correr: el perfil operativo activo y los tres servicios que siguen."""
        settings = self._app.state.settings
        items = []

        def item(id_: str, nombre: str, ok: bool, detalle: str) -> None:
            items.append({"id": id_, "nombre": nombre, "ok": ok, "detalle": detalle})

        manager = getattr(self._app.state, "target_manager", None)
        if settings.compose_dir is None or manager is None:
            item("orquestacion", "Plataforma en contenedores", False, "«Correr un clip» necesita la consola en contenedor")
        else:
            activa = manager.active
            listo = activa == PERFIL_OPERATIVO and await self._sano(self._app.state.http, "/readyz")
            item("deteccion", "Motor de detección", listo,
                 f"{PERFIL_OPERATIVO} activo y listo" if listo else
                 f"tiene que estar activo {PERFIL_OPERATIVO} (ahora: {activa or 'ninguno'})")
        item("reglas", "Motor de reglas", await self._sano(self._app.state.control_http), "")
        item("distribucion", "Distribución de alertas", await self._sano(self._app.state.distribution_http), "")
        desp = demo_config.despliegue(settings, getattr(manager, "active", None))
        try:
            broker = await asyncio.to_thread(self._ping, desp.mqtt_host, desp.mqtt_port)
            item("broker", "Broker MQTT", bool(broker.get("ok")), broker.get("detalle") or "")
        except Exception as exc:  # noqa: BLE001
            item("broker", "Broker MQTT", False, str(exc)[:200])
        en_curso = self._en_curso()
        item("libre", "Nada en curso", en_curso is None, en_curso or "")
        return {"listo": all(i["ok"] for i in items), "items": items}

    # --- correr ------------------------------------------------------------------------------

    def armar_media(self, configs: dict, clip_id: str, desp: demo_config.Despliegue) -> dict:
        """La config del motor de detección de la demo, con el clip como entrada en vez de la cámara."""
        datasets = "/e-ovrt_datasets" if desp.modo == "compose" else str(desp.workspace / "e-ovrt_datasets")
        media = dict(configs["media"])
        media["ingest"] = {"plugin": "video_file", "config": {
            "path": f"{datasets}/datasets/raw/clip_bench/clips/{clip_id}.mp4", "source_id": clip_id}}
        media["run"] = {**(media.get("run") or {}), "name": f"demostracion_{clip_id}", "stride": STRIDE,
                        "save_previews": False}
        return media

    async def correr(self, clip_id: str) -> dict[str, Any]:
        clip = next((c for c in CLIPS if c["id"] == clip_id), None)
        if clip is None:
            raise ClipDesconocido(clip_id)
        async with self._arranque:
            if self._corrida is not None and self._corrida.fase == "corriendo":
                raise ClipOcupado(f"ya está corriendo {self._corrida.clip['id']}")
            referencia = self._referencia(clip_id)
            if referencia is None or not self._video(clip_id).is_file():
                raise ClipDesconocido(f"{clip_id} no está en este equipo")
            preparacion = await self.preparacion()
            if not preparacion["listo"]:
                raise ClipNoListo(preparacion)

            settings = self._app.state.settings
            desp = demo_config.despliegue(settings, self._app.state.target_manager.active)
            configs = demo_config.resolver_configs(self._repo, "oakd", desp)
            configs = {**configs, "media": self.armar_media(configs, clip_id, desp)}
            modelo = None
            try:
                modelo = (await self._app.state.http.get("/api/model")).json()
            except (httpx.HTTPError, ValueError):
                pass
            congelado = demo_config.verificar_congelado(self._repo, configs, modelo)
            if not congelado["ok"]:
                raise ClipNoListo({"listo": False, "items": [{
                    "id": "congelado", "nombre": "Configuración del informe", "ok": False,
                    "detalle": "difiere de la congelada en el tag del informe"}]})

            ahora = self._reloj()
            sello = datetime.fromtimestamp(ahora, tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            corrida_id = f"clip_{sello}_{clip_id}"
            carpeta = self.salida / corrida_id
            carpeta.mkdir(parents=True, exist_ok=False)
            rutas = demo_config.escribir_configs(carpeta / "config", configs)

            # El testigo se suscribe antes de lanzar: lo que se publique antes no lo vería.
            testigo = self._testigo_factory(desp.mqtt_host, desp.mqtt_port)
            try:
                await asyncio.to_thread(testigo.iniciar)
                await asyncio.to_thread(testigo.esperar_suscripcion, 5.0)
            except TestigoError as exc:
                await asyncio.to_thread(testigo.cerrar)
                raise ClipNoListo({"listo": False, "items": [
                    {"id": "broker", "nombre": "Broker MQTT", "ok": False, "detalle": str(exc)}]}) from exc

            experiment_id = f"exp_{sello}_{SLUG}_{clip_id}"
            gt = self._workspace() / _BANCO / "processed" / "clip_bench" / "gt" / f"{clip_id}.json"
            manifest = ExperimentManifest.model_validate({
                "schema_version": "experiment.manifest.v1",
                "slug": SLUG,
                "experiment_id": experiment_id,
                "runs": {
                    "media": {"service": "media-plane", "config": str(rutas["media"]), "mode": "run"},
                    "control": {"service": "control-plane", "config": str(rutas["control"]), "mode": "live"},
                    "distribution": {"service": "alert-distribution", "config": str(rutas["distribution"]),
                                     "mode": "live", "endpoint": desp.alert_bus_endpoint},
                },
                "sequencing": "control_first",
                "clip_id": clip_id,
                "ground_truth": str(gt),
                "changes": "demostración: no es evidencia",
                "frozen": {"tag": congelado["tag"], "ok": congelado["ok"],
                           "huellas": {i["id"]: i["actual"] for i in congelado["items"]}},
            })
            fps = float(referencia.get("fps_nominal") or 30)
            esperados = (math.ceil(float(referencia["duration_ms"]) / 1000 * fps / STRIDE)
                         if referencia.get("duration_ms") else None)
            c = _Corrida(id=corrida_id, clip=clip, experiment_id=experiment_id, carpeta=carpeta,
                         iniciada=ahora, cuadros_esperados=esperados, testigo=testigo)
            self._app.state.experiment_manager.start(
                manifest,
                media_backend=self._app.state.backend,
                control_backend=self._app.state.control_backend,
                now=datetime.now(UTC),
                poll_interval_s=settings.experiment_poll_interval_s,
                timeout_s=TIMEOUT_S,
                **self._extra,
            )
            self._corrida = c
            self._guardar(c)
            tarea = asyncio.create_task(self._vigilar(c))
            self._tareas.add(tarea)
            tarea.add_done_callback(self._tareas.discard)
            return {"id": corrida_id, "experiment_id": experiment_id}

    # --- mientras corre ----------------------------------------------------------------------

    async def _muestrear(self, c: _Corrida, estado_exp: dict) -> None:
        for clave in ("media_run_id", "control_run_id"):
            if estado_exp.get(clave):
                c.ids[clave] = estado_exp[clave]
        if c.ids.get("media_run_id"):
            try:
                st = await self._app.state.backend.status(c.ids["media_run_id"])
                # Los cuadros procesados: arriba, en el progreso mientras corre o en el resumen al terminar.
                cuadros = next((x.get("units_processed") for x in (st, st.get("progress") or {}, st.get("summary") or {})
                                if isinstance(x, dict) and x.get("units_processed") is not None), None)
                c.pasos["deteccion"] = {"estado": "ok" if st.get("status") == "succeeded" else "en_curso",
                                        "cuadros": cuadros}
            except Exception:  # noqa: BLE001 -- observar no puede tumbar la corrida
                pass
        if c.ids.get("control_run_id"):
            try:
                actual = await self._app.state.control_backend.current()
                if actual and actual.get("control_run_id") == c.ids["control_run_id"]:
                    progreso = actual.get("progress") or {}
                    c.pasos["reglas"] = {"estado": "en_curso", "cuadros": progreso.get("units_processed")}
            except Exception:  # noqa: BLE001
                pass
        if c.pasos["distribucion"]["estado"] == "espera":
            try:
                r = await self._app.state.distribution_http.get("/api/runs/current")
                if r.status_code == 200:
                    c.pasos["distribucion"] = {"estado": "en_curso"}
            except httpx.HTTPError:
                pass
        mensajes = len(c.testigo.mensajes())
        c.pasos["broker"] = {"estado": "en_curso" if mensajes else c.pasos["broker"]["estado"], "mensajes": mensajes}

    async def _vigilar(self, c: _Corrida) -> None:
        manager = self._app.state.experiment_manager
        try:
            while True:
                estado_exp = manager.get(c.experiment_id) or {}
                await self._muestrear(c, estado_exp)
                if estado_exp.get("status") in ("succeeded", "failed"):
                    break
                await asyncio.sleep(self._poll_s)
            await asyncio.sleep(self._poll_s)  # lo último que publique el broker
            await self._cerrar(c, manager.get(c.experiment_id) or {})
        except Exception as exc:  # noqa: BLE001
            logger.exception("correr un clip: falló la vigilancia de %s", c.id)
            c.fase, c.error = "fallida", str(exc)[:300]
            self._guardar(c)
        finally:
            await asyncio.to_thread(c.testigo.cerrar)

    async def _cerrar(self, c: _Corrida, estado_exp: dict) -> None:
        mensajes = c.testigo.mensajes()
        await asyncio.to_thread(c.testigo.escribir, c.carpeta / "testigo.jsonl")
        ok = estado_exp.get("status") == "succeeded"
        consolidado = Path(estado_exp["consolidated_dir"]) if estado_exp.get("consolidated_dir") else None
        alertas = _leer_jsonl(consolidado / "control" / "alerts.jsonl") if consolidado else []
        evaluacion = _leer_json(consolidado / "control" / "temporal_evaluation.json") if consolidado else None
        c.resultado = {**armar_resultado(self._referencia(c.clip["id"]) or {}, alertas, evaluacion, mensajes),
                       "consolidado": consolidado.relative_to(self._repo).as_posix() if consolidado and
                       consolidado.is_relative_to(self._repo) else None}
        for paso in ("deteccion", "reglas", "distribucion"):
            c.pasos[paso]["estado"] = "ok" if ok else ("error" if c.pasos[paso]["estado"] != "ok" else "ok")
        c.pasos["broker"] = {"estado": "ok" if mensajes or ok else "error", "mensajes": len(mensajes)}
        c.fase = "terminada" if ok else "fallida"
        c.error = None if ok else (estado_exp.get("error") or "la corrida no terminó bien")
        c.terminada = self._reloj()
        self._guardar(c)

    def _guardar(self, c: _Corrida) -> None:
        try:
            (c.carpeta / "corrida.json").write_text(
                json.dumps(c.publica(), indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("correr un clip: no se pudo guardar %s: %s", c.carpeta, exc)

    # --- lectura -----------------------------------------------------------------------------

    def actual(self) -> dict[str, Any] | None:
        """La corrida en curso o la última de esta consola."""
        return self._corrida.publica() if self._corrida else None

    def corrida(self, corrida_id: str) -> dict[str, Any] | None:
        if self._corrida is not None and self._corrida.id == corrida_id:
            return self._corrida.publica()
        if "/" in corrida_id or "\\" in corrida_id or corrida_id.startswith("."):
            return None
        datos = _leer_json(self.salida / corrida_id / "corrida.json")
        return datos if isinstance(datos, dict) else None

    async def aclose(self) -> None:
        for tarea in list(self._tareas):
            tarea.cancel()
