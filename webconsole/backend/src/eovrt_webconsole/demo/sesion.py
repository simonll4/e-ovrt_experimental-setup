"""La sesión de la demo en vivo: una a la vez (spec 2026-10-23 §6.4).

Fases: `idle → preparing → live → finishing → rendering → done | failed`.

- **start** corre el chequeo previo, resuelve las configs de la variante (OAK-D o
  cámara de ensayo) y las guarda en la carpeta de la sesión, prende el testigo MQTT
  (suscripto ANTES de lanzar) y dispara el experimento con el ejecutor de siempre
  (control → distribución → medios), sin límite práctico de tiempo y con ganchos
  (`RunHooks`) que publican los ids apenas se conocen y permiten el cierre por el
  operador.
- Mientras corre, una tarea consulta `GET :8081/api/runs/current` cada ≤ 500 ms,
  deriva lo que muestra cada tarjeta (`estado.Derivador`) y lo deja en
  `state_log.jsonl`, así la pantalla es reproducible. «Listo» es el primer cuadro
  procesado que llega al control.
- **finish** (F F) marca el cierre por el operador y detiene el media-plane: el media
  publica `run_finished`, el control cierra y lo republica en el bus de alertas, la
  distribución cierra, se escribe el reporte. Cada espera tiene su tiempo máximo; si se
  vence, la sesión queda `failed` pero el Resultado se arma igual con lo que haya.
- Al terminar: el render (`render.render_sesion`) y, en compose, el reinicio del
  motor (F-101.5: una corrida con la OAK-D por vida del proceso).

Todo lo de acá es observación: no cambia ningún umbral ni transición.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from eovrt_webconsole.demo import config as demo_config
from eovrt_webconsole.demo.cifras import leer_cifras
from eovrt_webconsole.demo.estado import Derivador
from eovrt_webconsole.demo.render import render_sesion
from eovrt_webconsole.demo.testigo import TestigoError, TestigoMqtt, ping_broker
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import RunHooks, _default_dest_root, _default_resolve_run_dir

logger = logging.getLogger(__name__)

FASES_ACTIVAS = frozenset({"preparing", "live", "finishing", "rendering"})
# Sin límite PRÁCTICO de tiempo (D-5: el inicio y el fin los comanda el operador).
# Se usa un tope finito y holgado, no infinito: el mismo valor viaja hasta el cliente
# HTTP de la distribución, que no admite un timeout infinito.
DEMO_TIMEOUT_S = 6 * 3600.0
CIERRE_TIMEOUT_S = 30.0  # cada espera del cierre en cascada (control, distribución)
ESPERA_FIN_S = 120.0  # tope total desde F F hasta que el experimento termina
SIN_SENAL_S = 5.0
BROKER_ESPERA_S = 5.0
HOST_PREFLIGHT_MAX_S = 15 * 60
RESPALDO = "RESPALDO"
# Etiqueta opcional de la toma: la escena del rodaje en vivo de la generación 2 (P1…P9,
# P7c, DEMO; RT-04 del doc 134). No cambia nada de lo que corre: solo nombra la sesión
# para que el driver de evidencia la encuentre y la compare con su guion.
_ESCENA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,23}$")
# Sufijos: la variante (`_ensayo`), la escena del rodaje (`_P1`, `_P7a`, `_DEMO`) y `_exp`.
# Sin puntos ni barras: el id es un nombre de carpeta y no puede salir de `sesiones/`.
_ID_RE = re.compile(r"^demo_\d{8}T\d{6}Z(_[A-Za-z0-9-]+)*$")
_PREFLIGHT_HOST = "preflight_host.json"

REPOS = (
    ("e-ovrt_media-plane", "simonll4"),
    ("e-ovrt_control-plane", "Pandulc"),
    ("e-ovrt_alert-distribution", "simonll4"),
    ("e-ovrt_experimental-setup", "simonll4"),
    ("e-ovrt_datasets", "Pandulc"),
)
TAG_EVALUADO = "informe-2026"


class DemoOcupada(Exception):
    """Ya hay una sesión, un experimento o una corrida en curso."""


class DemoNoLista(Exception):
    """El chequeo previo tiene algo en rojo."""

    def __init__(self, preflight: dict) -> None:
        bloqueos = [i["nombre"] for i in preflight.get("items", []) if i.get("estado") == "error"]
        super().__init__("chequeo previo con errores: " + ", ".join(bloqueos))
        self.preflight = preflight


class DemoSinSesion(Exception):
    """No hay una sesión que finalizar."""


class SesionDesconocida(KeyError):
    pass


def _ahora_iso(t: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if t is None else t, tz=UTC).isoformat()


def _git_head(repo: Path) -> str | None:
    """Commit de HEAD leyendo `.git` a mano: la imagen de la consola no trae git."""
    git = repo / ".git"
    try:
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head or None
    ref = head[5:].strip()
    try:
        return (git / ref).read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:
        for linea in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            if linea.endswith(" " + ref):
                return linea.split(" ", 1)[0]
    except OSError:
        return None
    return None


@dataclass
class _Sesion:
    id: str
    dir: Path
    variante: str
    despliegue: demo_config.Despliegue
    experiment_id: str
    hooks: RunHooks
    testigo: TestigoMqtt
    congelado: dict
    iniciada: float
    escena: str | None = None
    # RT-05: otro motor u otra cámara (exploracion.yaml). None = la demo congelada.
    exploracion: dict | None = None
    fase: str = "preparing"
    ids: dict[str, str] = field(default_factory=dict)
    derivador: Derivador = field(default_factory=Derivador)
    cuadros: int = 0
    ultimo_cuadro: float | None = None
    bus_perdidos: int = 0
    en_vivo_desde: float | None = None
    fin_pedido: float | None = None
    terminada: float | None = None
    ended_by: str | None = None
    error: str | None = None
    metricas: dict[str, Any] = field(default_factory=dict)
    pasos: dict[str, str] = field(
        default_factory=lambda: {"reglas": "en_curso", "distribucion": "pendiente",
                                 "deteccion": "pendiente", "camara": "pendiente"}
    )
    eventos: deque = field(default_factory=lambda: deque(maxlen=60))
    resultado: dict | None = None
    experimento: dict | None = None


class DemoManager:
    def __init__(
        self,
        app: Any,
        *,
        sesiones_dir: Path | None = None,
        poll_s: float = 0.5,
        testigo_factory: Callable[[str, int], TestigoMqtt] | None = None,
        ping: Callable[..., dict] | None = None,
        render: Callable[..., dict] = render_sesion,
        reloj: Callable[[], float] = time.time,
        cierre_timeout_s: float = CIERRE_TIMEOUT_S,
        espera_fin_s: float = ESPERA_FIN_S,
        telemetria: bool = True,
        run_distribution: Callable[..., Any] | None = None,
        resolve_run_dir: Callable[[str, str], Path] = _default_resolve_run_dir,
        dest_root: Path | None = None,
    ) -> None:
        self._app = app
        settings = app.state.settings
        self._repo_root = Path(settings.repo_root)
        self.sesiones_dir = sesiones_dir or (self._repo_root / "defensa" / "sesiones")
        self._poll_s = poll_s
        self._testigo_factory = testigo_factory or (lambda host, port: TestigoMqtt(host, port))
        self._ping = ping or ping_broker
        self._render = render
        self._reloj = reloj
        self._cierre_timeout_s = cierre_timeout_s
        self._espera_fin_s = espera_fin_s
        self._telemetria = telemetria
        # Inyectables para tests; en producción, los del runner (convención de
        # workspace hermano y `<repo>/runs`).
        self._run_distribution = run_distribution
        self._resolve_run_dir = resolve_run_dir
        self._dest_root = dest_root
        self._sesion: _Sesion | None = None
        self._tareas: set[asyncio.Task] = set()
        self._arranque = asyncio.Lock()
        # Frescura del motor (F-101.5): "fresco" solo si lo reinició esta consola y el
        # media-plane no corrió nada desde entonces. Sin reinicio registrado, no se sabe.
        self._motor: dict[str, Any] = {"estado": "desconocido", "desde": None, "runs": None}

    # --- utilidades -------------------------------------------------------------

    @property
    def _settings(self) -> Any:
        return self._app.state.settings

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    def _despliegue(self) -> demo_config.Despliegue:
        tm = getattr(self._app.state, "target_manager", None)
        return demo_config.despliegue(self._settings, tm.active if tm is not None else None)

    def _tarea(self, coro) -> asyncio.Task:
        tarea = asyncio.create_task(coro)
        self._tareas.add(tarea)
        tarea.add_done_callback(self._tareas.discard)
        return tarea

    def _evento(self, s: _Sesion, texto: str, **datos: Any) -> None:
        fila = {"t": _ahora_iso(self._reloj()), "evento": texto, **datos}
        s.eventos.append(fila)
        logger.info("demo %s: %s %s", s.id, texto, datos or "")

    def _guardar(self, s: _Sesion) -> None:
        data = {
            "session_id": s.id,
            "variante": s.variante,
            "escena": s.escena,
            "exploracion": s.exploracion,
            "fase": s.fase,
            "stack": s.despliegue.modo,
            "experiment_id": s.experiment_id,
            "ids": s.ids,
            "iniciada_en": _ahora_iso(s.iniciada),
            "en_vivo_desde": _ahora_iso(s.en_vivo_desde) if s.en_vivo_desde else None,
            "en_vivo_desde_ms": round(s.en_vivo_desde * 1000.0, 3) if s.en_vivo_desde else None,
            "fin_pedido_en": _ahora_iso(s.fin_pedido) if s.fin_pedido else None,
            "terminada_en": _ahora_iso(s.terminada) if s.terminada else None,
            "ended_by": s.ended_by,
            "error": s.error,
            "congelado": s.congelado,
            "experimento": s.experimento,
            "alertas": [c for c in s.derivador.foto()],
        }
        (s.dir / "session.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    # --- motor (F-101.5) --------------------------------------------------------

    async def _run_ids_media(self) -> tuple[set[str], bool] | None:
        """Los ids de corrida del media-plane. Primero por el filesystem compartido
        (listar `runs/` es barato); `GET /api/runs` lee el summary de CADA corrida y,
        sobre el bind mount de Windows, con cientos de corridas tarda."""
        runs_dir = self._resolve_run_dir("media", "_").parent
        if runs_dir.is_dir():
            try:
                return {p.name for p in runs_dir.iterdir() if p.is_dir()}, False
            except OSError:
                pass
        try:
            filas = await self._app.state.backend.list_runs()
        except Exception:  # noqa: BLE001 -- motor caído: no se sabe
            return None
        ids = {str(f.get("run_id")) for f in filas if f.get("run_id")}
        corriendo = any(f.get("status") == "running" for f in filas)
        return ids, corriendo

    async def estado_motor(self) -> dict[str, Any]:
        estado = self._motor["estado"]
        if estado in {"reiniciando", "error"}:
            return dict(self._motor)
        if self._motor.get("runs") is None:
            return {**self._motor, "estado": "desconocido"}
        vistos = await self._run_ids_media()
        if vistos is None:
            return {**self._motor, "estado": "desconocido", "detalle": "el motor no responde"}
        ids, corriendo = vistos
        nuevos = sorted(ids - self._motor["runs"])
        if corriendo or nuevos:
            return {**self._motor, "estado": "usado", "corridas_desde_reinicio": nuevos}
        return {**self._motor, "estado": "fresco"}

    async def reiniciar_motor(self) -> dict[str, Any]:
        """Reinicia la instancia activa (compose) y registra el motor como fresco."""
        tm = getattr(self._app.state, "target_manager", None)
        if tm is None:
            raise RuntimeError(
                "despliegue nativo: la consola no puede reiniciar el media-plane; "
                "reinicialo a mano (doc 133 §5.4)"
            )
        self._motor = {"estado": "reiniciando", "desde": None, "runs": None}
        try:
            resultado = await tm.restart_active()
        except Exception as exc:
            self._motor = {"estado": "error", "desde": None, "runs": None, "detalle": str(exc)}
            raise
        vistos = await self._run_ids_media()
        self._motor = {
            "estado": "fresco",
            "desde": _ahora_iso(self._reloj()),
            "runs": vistos[0] if vistos is not None else set(),
            "instancia": resultado.get("target"),
        }
        return {"estado": "fresco", "instancia": resultado.get("target")}

    def reiniciar_motor_en_segundo_plano(self) -> None:
        async def _correr() -> None:
            try:
                await self.reiniciar_motor()
            except Exception:  # noqa: BLE001 -- queda en self._motor["estado"] = "error"
                logger.warning("demo: el reinicio del motor falló", exc_info=True)

        self._tarea(_correr())

    # --- chequeo previo ---------------------------------------------------------

    async def _salud(self, http: httpx.AsyncClient, *, ready: bool = True) -> tuple[bool, bool]:
        healthy = listo = False
        try:
            healthy = (await http.get("/healthz")).status_code == 200
            if ready:
                listo = (await http.get("/readyz")).status_code == 200
        except httpx.HTTPError:
            pass
        return healthy, listo

    async def _corrida_activa(self, http: httpx.AsyncClient) -> str | None:
        try:
            r = await http.get("/api/runs/current")
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None
        try:
            body = r.json()
        except ValueError:
            return None
        return body.get("control_run_id") or body.get("distribution_run_id") or "?"

    def _host(self) -> dict[str, Any]:
        path = self.sesiones_dir / _PREFLIGHT_HOST
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            edad = self._reloj() - path.stat().st_mtime
        except (OSError, json.JSONDecodeError):
            return {"presente": False}
        return {"presente": True, "edad_s": round(edad, 1), "datos": data}

    async def preflight(self, exploracion: dict | None = None) -> dict[str, Any]:
        """Chequeo previo. Con `exploracion` (RT-05, `demo_config.resolver_exploracion`) el
        motor esperado es el de la exploración y lo congelado no bloquea: se muestra en
        amarillo, porque la sesión no es la demo congelada y queda marcada como tal."""
        app = self._app
        items: list[dict[str, Any]] = []

        def item(id_: str, nombre: str, estado: str, detalle: str, accion: str | None = None) -> None:
            items.append({"id": id_, "nombre": nombre, "estado": estado, "detalle": detalle,
                          "accion": accion})

        s = self._sesion
        if s is not None and s.fase in FASES_ACTIVAS:
            item("sesion", "sesión", "error", f"hay una sesión en curso ({s.id}, {s.fase})",
                 "esperar a que termine o finalizarla (F F)")
        elif app.state.experiment_manager.current() is not None:
            item("sesion", "sesión", "error", "hay un experimento en curso en la consola",
                 "esperar a que termine")
        else:
            item("sesion", "sesión", "ok", "sin sesiones ni experimentos en curso")

        healthy, listo = await self._salud(app.state.http)
        modelo: dict | None = None
        if listo:
            try:
                modelo = (await app.state.http.get("/api/model")).json()
            except (httpx.HTTPError, ValueError):
                modelo = None
        try:
            congelado_esperado = demo_config.cargar_congelado(self._repo_root)
            ref_esperada = congelado_esperado["modelo"]["ref"]
        except (demo_config.ConfigDemoError, KeyError, TypeError):
            congelado_esperado, ref_esperada = {}, demo_config.MOTOR_DEMO
        motor_pedido = demo_config.MOTOR_DEMO
        if exploracion:
            ref_esperada, motor_pedido = exploracion["modelo"], exploracion["motor"]
        if not healthy:
            item("deteccion", "detección", "error", "el motor de detección no responde",
                 f"activar {motor_pedido} (Plataforma, o infra/demo/demo.ps1 up)")
        elif not listo:
            item("deteccion", "detección", "error", "el motor todavía está cargando el modelo",
                 "esperar unos segundos")
        elif (congelado_esperado or exploracion) and (modelo or {}).get("ref") != ref_esperada:
            item("deteccion", "detección", "error",
                 f"el motor tiene cargado {(modelo or {}).get('ref')!r}, no {ref_esperada}",
                 f"activar {motor_pedido} en Plataforma")
        else:
            item("deteccion", "detección", "ok", f"{ref_esperada} listo")

        motor = await self.estado_motor()
        compose = getattr(app.state, "target_manager", None) is not None
        if motor["estado"] == "fresco":
            item("motor", "motor fresco", "ok", "reiniciado por la consola y sin corridas desde entonces")
        elif motor["estado"] == "reiniciando":
            item("motor", "motor fresco", "error", "reiniciando el motor…", "esperar ~30 s")
        elif motor["estado"] == "usado":
            item("motor", "motor fresco", "error",
                 "el motor ya hizo una corrida en esta vida (F-101.5: la segunda puede tirarlo)",
                 "reiniciar el motor: infra/demo/demo.ps1 restart-motor")
        elif compose:
            item("motor", "motor fresco", "error",
                 "no se sabe si el motor está fresco (la consola no lo reinició)",
                 "reiniciar el motor: infra/demo/demo.ps1 restart-motor")
        else:
            item("motor", "motor fresco", "aviso",
                 "despliegue nativo: la consola no puede verificarlo",
                 "reiniciar el media-plane a mano antes de empezar")

        for id_, nombre, http in (
            ("reglas", "reglas", app.state.control_http),
            ("distribucion", "distribución", app.state.distribution_http),
        ):
            sano, _ = await self._salud(http, ready=False)
            activa = await self._corrida_activa(http) if sano else None
            if not sano:
                item(id_, nombre, "error", f"el servicio de {nombre} no responde",
                     "infra/demo/demo.ps1 reset")
            elif activa:
                item(id_, nombre, "error", f"quedó una corrida activa ({activa})",
                     "infra/demo/demo.ps1 reset (reinicia control, distribución y motor)")
            else:
                item(id_, nombre, "ok", "listo")

        desp = self._despliegue()
        ping = await asyncio.to_thread(self._ping, desp.mqtt_host, desp.mqtt_port)
        item("broker", "broker", "ok" if ping.get("ok") else "error",
             f"{desp.mqtt_host}:{desp.mqtt_port} — {ping.get('detalle')}",
             None if ping.get("ok") else "revisar el contenedor mosquitto (docker ps)")

        try:
            configs = demo_config.resolver_configs(self._repo_root, "oakd", desp, exploracion)
            congelado = demo_config.verificar_congelado(self._repo_root, configs, modelo)
        except (demo_config.ConfigDemoError, KeyError, TypeError) as exc:
            congelado = {"ok": False, "tag": congelado_esperado.get("tag"), "items": [],
                         "error": f"no se pudo verificar lo congelado: {exc}"}
        if exploracion:
            item("congelado", "configuración congelada", "aviso",
                 f"exploración: {exploracion['motor']} con la cámara a {exploracion['camara']}. "
                 "No es la configuración congelada: la sesión queda marcada y no cuenta como ensayo",
                 None)
        else:
            item("congelado", "configuración congelada", "ok" if congelado["ok"] else "error",
                 f"igual al tag {congelado.get('tag')}" if congelado["ok"]
                 else (congelado.get("error") or "difiere del tag: ver la capa de evidencia (E)"),
                 None if congelado["ok"] else "no correr la demo: algo de lo medido cambió")

        host = self._host()
        if not host["presente"]:
            item("host", "chequeo del host", "aviso", "no hay chequeo del host",
                 "correr infra/demo/demo.ps1 check")
        elif host["edad_s"] > HOST_PREFLIGHT_MAX_S:
            item("host", "chequeo del host", "aviso",
                 f"el chequeo del host tiene {host['edad_s'] / 60:.0f} min",
                 "volver a correr infra/demo/demo.ps1 check")
        else:
            fallas = [k for k, v in ((host.get("datos") or {}).get("chequeos") or {}).items()
                      if isinstance(v, dict) and v.get("ok") is False]
            item("host", "chequeo del host", "aviso" if fallas else "ok",
                 "con observaciones: " + ", ".join(fallas) if fallas
                 else f"hace {host['edad_s'] / 60:.0f} min",
                 "ver la capa de evidencia (E)" if fallas else None)

        return {
            # Solo los rojos frenan la tecla I. Los amarillos (p.ej. un chequeo del host
            # de hace más de 15 min, que en plena defensa es lo normal) se muestran pero
            # no bloquean: decisión de implementación, ver infra/demo/README.md.
            "listo": not any(i["estado"] == "error" for i in items),
            "items": items,
            "congelado": congelado,
            "exploracion": exploracion,
            "motor": {k: v for k, v in motor.items() if k != "runs"},
            "stack": desp.modo,
            "comprobado_en": _ahora_iso(self._reloj()),
        }

    # --- arranque ---------------------------------------------------------------

    async def start(self, variante: str = "oakd", escena: str | None = None,
                    exploracion: dict | None = None) -> dict[str, Any]:
        """Arranca una sesión. `exploracion` ({"motor", "camara"}, RT-05) corre la misma
        escena con otro motor u otra cámara de la lista cerrada de `exploracion.yaml`: solo
        con la OAK-D, y la sesión queda marcada (id con `_exp`, `exploracion` en session.json)."""
        async with self._arranque:
            if self._sesion is not None and self._sesion.fase in FASES_ACTIVAS:
                raise DemoOcupada(f"hay una sesión en curso: {self._sesion.id}")
            if variante not in demo_config.VARIANTES:
                raise ValueError(f"variante desconocida: {variante!r}")
            if escena is not None and not _ESCENA.match(escena):
                raise ValueError(f"escena inválida: {escena!r} (letras, números, '-' y '_', hasta 24)")
            if exploracion is not None:
                if variante != "oakd":
                    raise ValueError("la exploración es con la OAK-D (variante oakd)")
                exploracion = demo_config.resolver_exploracion(
                    self._repo_root, exploracion.get("motor"), exploracion.get("camara"))
            manager = self._app.state.experiment_manager
            if manager.current() is not None:
                raise DemoOcupada("hay un experimento en curso en la consola")
            preflight = await self.preflight(exploracion)
            if not preflight["listo"]:
                raise DemoNoLista(preflight)

            ahora = self._reloj()
            sello = datetime.fromtimestamp(ahora, tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            session_id = (f"demo_{sello}" + ("" if variante == "oakd" else f"_{variante}")
                          + (f"_{escena}" if escena else "") + ("_exp" if exploracion else ""))
            carpeta = self.sesiones_dir / session_id
            carpeta.mkdir(parents=True, exist_ok=False)
            desp = self._despliegue()
            configs = demo_config.resolver_configs(self._repo_root, variante, desp, exploracion)
            modelo = None
            try:
                modelo = (await self._app.state.http.get("/api/model")).json()
            except (httpx.HTTPError, ValueError):
                pass
            congelado = demo_config.verificar_congelado(self._repo_root, configs, modelo)
            if exploracion:
                # Se registra el modelo que el motor dice tener (umbrales incluidos): es lo
                # que distingue una celda de la otra en RT-05.
                exploracion = {**exploracion, "modelo_cargado": modelo}
            elif not congelado["ok"]:
                raise DemoNoLista({**preflight, "items": [
                    {"id": "congelado", "nombre": "configuración congelada", "estado": "error",
                     "detalle": "difiere del tag", "accion": None}]})
            rutas = demo_config.escribir_configs(carpeta / "config", configs)
            (carpeta / "preflight.json").write_text(
                json.dumps({"consola": preflight, "host": self._host()}, indent=2,
                           ensure_ascii=False, default=str) + "\n",
                encoding="utf-8",
            )

            # El testigo se suscribe ANTES de lanzar: lo que se publique antes de la
            # suscripción no lo vería (mismo principio que el bus PUB/SUB).
            testigo = self._testigo_factory(desp.mqtt_host, desp.mqtt_port)
            try:
                await asyncio.to_thread(testigo.iniciar)
                await asyncio.to_thread(testigo.esperar_suscripcion, 5.0)
            except TestigoError as exc:
                await asyncio.to_thread(testigo.cerrar)
                raise DemoNoLista({**preflight, "items": [
                    {"id": "broker", "nombre": "broker", "estado": "error", "detalle": str(exc),
                     "accion": None}]}) from exc

            slug = demo_config.VARIANTES[variante]
            experiment_id = f"exp_{sello}_{slug}"
            hooks = RunHooks(close_timeout_s=self._cierre_timeout_s)
            s = _Sesion(
                id=session_id, dir=carpeta, variante=variante, despliegue=desp,
                experiment_id=experiment_id, hooks=hooks, testigo=testigo,
                congelado=congelado, iniciada=ahora, escena=escena, exploracion=exploracion,
            )
            hooks.on_ids = lambda ids: self._ids(s, ids)
            manifest = ExperimentManifest.model_validate({
                "schema_version": "experiment.manifest.v1",
                "slug": slug,
                "experiment_id": experiment_id,
                "runs": {
                    "media": {"service": "media-plane", "config": str(rutas["media"]), "mode": "run"},
                    "control": {"service": "control-plane", "config": str(rutas["control"]),
                                "mode": "live"},
                    "distribution": {
                        "service": "alert-distribution", "config": str(rutas["distribution"]),
                        "mode": "live", "endpoint": desp.alert_bus_endpoint,
                    },
                },
                "sequencing": "control_first",
                "report": {},
                "frozen": {"tag": congelado["tag"], "ok": congelado["ok"],
                           "huellas": {i["id"]: i["actual"] for i in congelado["items"]},
                           **({"exploracion": {k: exploracion[k] for k in ("motor", "modelo", "camara")}}
                              if exploracion else {})},
            })
            self._motor = {**self._motor, "estado": "usado"}
            extra: dict[str, Any] = {"resolve_run_dir": self._resolve_run_dir}
            if self._run_distribution is not None:
                extra["run_distribution"] = self._run_distribution
            if self._dest_root is not None:
                extra["dest_root"] = self._dest_root
            manager.start(
                manifest,
                media_backend=self._app.state.backend,
                control_backend=self._app.state.control_backend,
                now=datetime.now(UTC),
                poll_interval_s=self._settings.experiment_poll_interval_s,
                timeout_s=DEMO_TIMEOUT_S,
                hooks=hooks,
                **extra,
            )
            self._sesion = s
            self._evento(s, "inicio", variante=variante, escena=escena, experiment_id=experiment_id,
                         **({"exploracion": f"{exploracion['motor']} @ {exploracion['camara']}"}
                            if exploracion else {}))
            self._guardar(s)
            self._tarea(self._vigilar(s))
            if self._telemetria:
                self._tarea(self._metricas(s))
            return {"session_id": session_id, "experiment_id": experiment_id}

    def _ids(self, s: _Sesion, ids: dict[str, str]) -> None:
        s.ids.update(ids)
        if "control_run_id" in ids:
            s.pasos["reglas"] = "ok"
            s.pasos["distribucion"] = "en_curso"
        if "media_run_id" in ids:
            s.pasos["deteccion"] = "ok"
            s.pasos["camara"] = "en_curso"
        self._evento(s, "ids", **ids)

    # --- durante la corrida -------------------------------------------------------

    async def _muestrear(self, s: _Sesion) -> None:
        ahora = self._reloj()
        episodios: list[dict] = []
        control_id = s.ids.get("control_run_id")
        if control_id:
            try:
                actual = await self._app.state.control_backend.current()
            except Exception:  # noqa: BLE001 -- 404 (ya cerró) o caído: sin foto nueva
                actual = None
            if actual and actual.get("control_run_id") == control_id:
                episodios = actual.get("episodes") or []
                progreso = actual.get("progress") or {}
                unidades = int(progreso.get("units_processed") or 0)
                s.bus_perdidos = int(progreso.get("bus_dropped_events") or 0)
                if unidades > s.cuadros:
                    s.cuadros = unidades
                    s.ultimo_cuadro = ahora
                if s.fase == "preparing" and unidades >= 1:
                    s.fase = "live"
                    s.en_vivo_desde = ahora
                    s.pasos["camara"] = "ok"
                    self._evento(s, "listo: primer cuadro procesado")
                    self._guardar(s)
        if s.pasos["distribucion"] == "en_curso" and "distribution_run_id" not in s.ids:
            try:
                r = await self._app.state.distribution_http.get("/api/runs/current")
                if r.status_code == 200:
                    s.ids["distribution_run_id"] = r.json().get("distribution_run_id")
                    s.pasos["distribucion"] = "ok"
                    self._evento(s, "distribución suscripta",
                                 distribution_run_id=s.ids["distribution_run_id"])
            except (httpx.HTTPError, ValueError):
                pass
        if s.fase in {"preparing", "live"}:
            for t in s.derivador.actualizar(episodios, ahora):
                self._evento(s, f"{t['condicion']}: {t['de']} → {t['a']}")
        with (s.dir / "state_log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "t": _ahora_iso(ahora), "fase": s.fase, "cuadros": s.cuadros,
                "condiciones": [
                    {k: c[k] for k in ("condicion", "estado", "transcurrido_ms", "umbral_ms", "alertas")}
                    for c in s.derivador.foto()
                ],
                "broker_mensajes": len(s.testigo.mensajes()),
            }, ensure_ascii=False) + "\n")

    async def _metricas(self, s: _Sesion) -> None:
        """Telemetría del motor (fps, latencia, memoria de GPU) por su WS, a título
        informativo para la capa de evidencia. Si no conecta, la capa lo dice."""
        import websockets

        while s.fase in {"preparing", "live"}:
            run_id = s.ids.get("media_run_id")
            if not run_id:
                await asyncio.sleep(0.5)
                continue
            base = str(self._app.state.http.base_url).rstrip("/")
            url = base.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
            try:
                async with websockets.connect(f"{url}/api/runs/{run_id}/stream") as ws:
                    async for raw in ws:
                        try:
                            ev = json.loads(raw)
                        except (json.JSONDecodeError, ValueError):
                            continue
                        if ev.get("type") == "metric":
                            s.metricas = {
                                "fps": ev.get("fps"),
                                "latencia_ms": ev.get("latency_total_ms"),
                                "gpu_mb": ev.get("gpu_memory_mb"),
                                "unit_id": ev.get("unit_id"),
                                "t": _ahora_iso(self._reloj()),
                            }
                        if s.fase not in {"preparing", "live"}:
                            return
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 -- telemetría opcional: reintento suave
                await asyncio.sleep(2.0)

    async def _vigilar(self, s: _Sesion) -> None:
        manager = self._app.state.experiment_manager
        estado_exp: dict = {}
        try:
            while True:
                await self._muestrear(s)
                estado_exp = manager.get(s.experiment_id) or {}
                if estado_exp.get("status") in {"succeeded", "failed"}:
                    break
                if s.fase == "finishing" and s.fin_pedido is not None and (
                    self._reloj() - s.fin_pedido > self._espera_fin_s
                ):
                    s.error = f"el cierre en cascada no terminó en {self._espera_fin_s:.0f} s"
                    self._evento(s, "cierre vencido: se cancela el experimento")
                    manager.cancel(s.experiment_id)
                    await asyncio.sleep(0.5)
                    estado_exp = manager.get(s.experiment_id) or {"status": "failed"}
                    break
                await asyncio.sleep(self._poll_s)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- la sesión no puede quedar colgada
            logger.exception("demo %s: el vigilante falló", s.id)
            s.error = f"falla interna del vigilante: {exc}"
        await self._cerrar(s, estado_exp)

    async def _cerrar(self, s: _Sesion, estado_exp: dict) -> None:
        if s.fase != "finishing" and s.ended_by is None:
            self._evento(s, "la corrida terminó sola", estado=estado_exp.get("status"),
                         error=estado_exp.get("error"))
        s.fase = "rendering"
        s.experimento = estado_exp
        self._guardar(s)
        if getattr(self._app.state, "target_manager", None) is not None:
            # Motor fresco para la próxima (F-101.5), en paralelo con el render: el
            # render lee del disco, no le pide nada al motor.
            self.reiniciar_motor_en_segundo_plano()
        await asyncio.sleep(0.5)  # últimos mensajes del broker en vuelo
        await asyncio.to_thread(s.testigo.cerrar)
        s.testigo.escribir(s.dir / "witness.jsonl")
        media_id = estado_exp.get("media_run_id") or s.ids.get("media_run_id")
        control_id = estado_exp.get("control_run_id") or s.ids.get("control_run_id")
        experimento_dir = (
            Path(estado_exp["consolidated_dir"]) if estado_exp.get("consolidated_dir")
            else (self._dest_root or _default_dest_root()) / s.experiment_id
        )
        try:
            s.resultado = await asyncio.to_thread(
                self._render,
                s.dir / "resultado",
                media_dir=self._resolve_run_dir("media", media_id) if media_id else None,
                control_dir=self._resolve_run_dir("control", control_id) if control_id else None,
                experimento_dir=experimento_dir,
                testigo=s.testigo.mensajes(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("demo %s: el render falló", s.id)
            s.error = (s.error + "; " if s.error else "") + f"el render falló: {exc}"
        ok = estado_exp.get("status") == "succeeded" and s.error is None
        if not ok and s.error is None:
            s.error = estado_exp.get("error") or "el experimento terminó con fallas"
        s.fase = "done" if ok else "failed"
        s.terminada = self._reloj()
        self._evento(s, f"sesión {s.fase}", resultado_en=str(s.dir / "resultado"))
        self._guardar(s)

    # --- fin por el operador ----------------------------------------------------

    async def finish(self) -> dict[str, Any]:
        s = self._sesion
        if s is None or s.fase not in {"preparing", "live"}:
            raise DemoSinSesion("no hay una sesión en curso para finalizar")
        s.fase = "finishing"
        s.fin_pedido = self._reloj()
        s.ended_by = "operator"
        s.hooks.ended_by = "operator"
        self._evento(s, "F F: cierre pedido por el operador")
        self._guardar(s)
        self._tarea(self._detener_medios(s))
        return {"session_id": s.id, "fase": s.fase}

    async def _detener_medios(self, s: _Sesion) -> None:
        limite = self._reloj() + self._cierre_timeout_s
        while not s.ids.get("media_run_id") and self._reloj() < limite:
            await asyncio.sleep(0.2)
        run_id = s.ids.get("media_run_id")
        if not run_id:
            self._evento(s, "el motor nunca arrancó la corrida: no hay nada que detener")
            return
        try:
            await self._app.state.backend.stop(run_id)
            self._evento(s, "media-plane detenido", media_run_id=run_id)
        except Exception as exc:  # noqa: BLE001 -- lo registra; el vigilante vence el cierre
            self._evento(s, f"no se pudo detener el media-plane: {exc}")

    # --- lo que consulta la pantalla -----------------------------------------------

    def _broker_por_condicion(self, s: _Sesion) -> dict[str, str | None]:
        """Para cada condición con una alerta: ¿llegó al broker?"""
        mensajes = s.testigo.mensajes()
        control_id = s.ids.get("control_run_id")
        ahora = self._reloj()
        salida: dict[str, str | None] = {}
        for c in s.derivador.foto():
            desde = c["alerta_desde"]
            if desde is None:
                salida[c["condicion"]] = None
                continue
            propios = [
                m for m in mensajes
                if (m.get("payload") or {}).get("condition_id") == c["condicion"]
                and (control_id is None or (m.get("payload") or {}).get("control_run_id") == control_id)
            ]
            if any(m["recibido_ms"] / 1000.0 >= desde - 2.0 for m in propios):
                salida[c["condicion"]] = "recibido"
            elif any(desde - 30.0 <= m["recibido_ms"] / 1000.0 < desde - 2.0 for m in propios):
                salida[c["condicion"]] = "suprimido_enfriamiento"
            elif ahora - desde > BROKER_ESPERA_S:
                salida[c["condicion"]] = "no_llego"
            else:
                salida[c["condicion"]] = "esperando"
        return salida

    def estado(self) -> dict[str, Any]:
        s = self._sesion
        if s is None:
            return {"fase": "idle", "session_id": None, "motor": self._motor_publico()}
        ahora = self._reloj()
        mensajes = s.testigo.mensajes()
        ultimo = mensajes[-1] if mensajes else None
        broker = self._broker_por_condicion(s)
        condiciones = []
        for c in s.derivador.foto():
            condiciones.append({**c, "broker": broker.get(c["condicion"])})
        hace = (ahora - s.ultimo_cuadro) if s.ultimo_cuadro is not None else None
        return {
            "fase": s.fase,
            "session_id": s.id,
            "variante": s.variante,
            "escena": s.escena,
            "exploracion": s.exploracion,
            "stack": s.despliegue.modo,
            "experiment_id": s.experiment_id,
            "ids": s.ids,
            "iniciada_en": _ahora_iso(s.iniciada),
            "en_vivo_desde_ms": round(s.en_vivo_desde * 1000.0, 3) if s.en_vivo_desde else None,
            "transcurrido_s": round((s.terminada or ahora) - (s.en_vivo_desde or s.iniciada), 1),
            "en_vivo_desde": _ahora_iso(s.en_vivo_desde) if s.en_vivo_desde else None,
            "pasos": [{"id": k, "estado": v} for k, v in s.pasos.items()],
            "condiciones": condiciones,
            "broker": {
                "mensajes": len(mensajes),
                "ultimo": None if ultimo is None else {
                    "topic": ultimo["topic"],
                    "recibido_en": ultimo["recibido_en"],
                    "hace_s": round(ahora - ultimo["recibido_ms"] / 1000.0, 1),
                    "condition_id": (ultimo.get("payload") or {}).get("condition_id"),
                    "crudo": ultimo.get("crudo"),
                },
            },
            "camara": {
                "cuadros": s.cuadros,
                "ultimo_cuadro_hace_s": round(hace, 1) if hace is not None else None,
                "sin_senal": s.fase == "live" and hace is not None and hace > SIN_SENAL_S,
                "bus_perdidos": s.bus_perdidos,
            },
            "metricas": s.metricas,
            "ended_by": s.ended_by,
            "error": s.error,
            "eventos": list(s.eventos)[-30:],
            "motor": self._motor_publico(),
        }

    def _motor_publico(self) -> dict[str, Any]:
        return {k: v for k, v in self._motor.items() if k != "runs"}

    # --- sesiones guardadas ---------------------------------------------------------

    def _dir_sesion(self, session_id: str) -> Path:
        if not _ID_RE.match(session_id):
            raise SesionDesconocida(session_id)
        carpeta = self.sesiones_dir / session_id
        if not (carpeta / "session.json").is_file():
            raise SesionDesconocida(session_id)
        return carpeta

    def respaldo(self) -> str | None:
        try:
            valor = (self.sesiones_dir / RESPALDO).read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return valor if valor and _ID_RE.match(valor) else None

    def marcar_respaldo(self, session_id: str) -> None:
        self._dir_sesion(session_id)
        self.sesiones_dir.mkdir(parents=True, exist_ok=True)
        (self.sesiones_dir / RESPALDO).write_text(session_id + "\n", encoding="utf-8")

    def sesiones(self) -> list[dict[str, Any]]:
        if not self.sesiones_dir.is_dir():
            return []
        respaldo = self.respaldo()
        filas = []
        for carpeta in sorted(self.sesiones_dir.iterdir(), reverse=True):
            path = carpeta / "session.json"
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            filas.append({
                "session_id": data.get("session_id"), "variante": data.get("variante"),
                "fase": data.get("fase"), "iniciada_en": data.get("iniciada_en"),
                "ended_by": data.get("ended_by"), "respaldo": data.get("session_id") == respaldo,
                "escena": data.get("escena"), "exploracion": data.get("exploracion"),
            })
        return filas

    def sesion(self, session_id: str) -> dict[str, Any]:
        carpeta = self._dir_sesion(session_id)

        def leer(rel: str) -> Any:
            try:
                return json.loads((carpeta / rel).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None

        testigo = []
        try:
            for linea in (carpeta / "witness.jsonl").read_text(encoding="utf-8").splitlines():
                if linea.strip():
                    testigo.append(json.loads(linea))
        except (OSError, json.JSONDecodeError):
            pass
        eventos = []
        try:
            lineas = (carpeta / "state_log.jsonl").read_text(encoding="utf-8").splitlines()
            eventos = [json.loads(x) for x in lineas[-200:] if x.strip()]
        except (OSError, json.JSONDecodeError):
            pass
        return {
            "session": leer("session.json"),
            "resumen": leer("resultado/resumen.json"),
            "linea_de_tiempo": leer("resultado/linea_de_tiempo.json") or [],
            "testigo": testigo,
            "state_log": eventos,
            "respaldo": self.respaldo() == session_id,
        }

    def archivo(self, session_id: str, rel: str) -> Path:
        carpeta = self._dir_sesion(session_id).resolve()
        destino = (carpeta / rel).resolve()
        if carpeta not in destino.parents or not destino.is_file():
            raise SesionDesconocida(rel)
        return destino

    # --- capa de evidencia ----------------------------------------------------------

    async def stack(self) -> dict[str, Any]:
        app = self._app
        tm = getattr(app.state, "target_manager", None)
        contenedores: list[dict] | None = None
        error = None
        if tm is not None:
            try:
                contenedores = await tm.contenedores()
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
        workspace = self._repo_root.parent
        repos = [
            {
                "repo": nombre,
                "commit": _git_head(workspace / nombre),
                "tag_evaluado": TAG_EVALUADO,
                "url_tag": f"https://github.com/{duenio}/{nombre}/tree/{TAG_EVALUADO}",
            }
            for nombre, duenio in REPOS
        ]
        return {
            "modo": "compose" if tm is not None else "nativo",
            "contenedores": contenedores,
            "error": error,
            "host": self._host(),
            "repos": repos,
            "servicios": {
                "media": str(app.state.http.base_url),
                "control": self._settings.control_service_url,
                "distribucion": self._settings.distribution_service_url,
            },
        }

    def cifras(self) -> list[dict[str, Any]]:
        return leer_cifras(self._repo_root / "results")

    async def aclose(self) -> None:
        for tarea in list(self._tareas):
            tarea.cancel()
        for tarea in list(self._tareas):
            try:
                await tarea
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 -- drenar el teardown
                pass
        s = self._sesion
        if s is not None:
            await asyncio.to_thread(s.testigo.cerrar)
