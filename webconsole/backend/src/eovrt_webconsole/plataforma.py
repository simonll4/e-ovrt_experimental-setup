"""La plataforma (plan de la consola de evidencia, §7.1): el estado de los trece servicios y su orquestación.

No modifica el orquestador (`orchestrator.py`, plan §11). Para las instancias de detección usa su
`TargetManager` tal como está (activar una detiene la anterior; con una corrida en curso se niega). Para el
núcleo —motor de reglas, distribución y broker— tiene su propia lista cerrada y llama a `docker compose` con
el mismo proyecto y los mismos verbos (`up -d --no-build`, `stop`, `restart`): nunca un nombre libre hacia el
socket de Docker. La consola no se detiene a sí misma: devuelve el comando. Detener o reiniciar con una
corrida o una demo en curso pide confirmación. Cada pedido queda en el registro de acciones.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from eovrt_webconsole.demo.config import MOTOR_DEMO
from eovrt_webconsole.orchestrator import (
    _SERVICE_PORT,
    INSTANCE_LABEL,
    MODEL_REF_LABEL,
    PROJECT_NAME,
    ComposeError,
    RunCmd,
    _normalize_labels,
    _run_subprocess,
)

logger = logging.getLogger(__name__)

# El núcleo, en el orden en que se muestra. La consola está pero no se orquesta desde sí misma.
NUCLEO: dict[str, str] = {
    "console": "Consola",
    # El nombre del informe y, entre paréntesis, qué hace (revisión del 2026-11-19: vocabulario del informe con
    # una aclaración llana).
    "control-plane": "Plano de control (reglas)",
    "distribution": "Módulo de distribución (alertas)",
    "mosquitto": "Broker MQTT",
}
ORQUESTABLES = ("control-plane", "distribution", "mosquitto")
CONSOLA = "console"
# El perfil operativo: la instancia que corrió la campaña en vivo y la demo.
PERFIL_OPERATIVO = MOTOR_DEMO
VERBOS_NUCLEO = {"levantar": ("up", "-d", "--no-build"), "detener": ("stop",), "reiniciar": ("restart",)}
DETIENEN = {"detener", "reiniciar", "activar"}
_GPU_TTL_S = 3.0


class AccionInvalida(ValueError):
    """Un servicio o un verbo fuera de la lista cerrada."""


class ConsolaPropia(RuntimeError):
    """La consola no se detiene a sí misma: se devuelve el comando para hacerlo a mano."""

    def __init__(self, comando: str) -> None:
        super().__init__(comando)
        self.comando = comando


class EnCurso(RuntimeError):
    """Hay una corrida o una demo en curso y el pedido la cortaría: hace falta confirmarlo."""


def _filas_ps(texto: str) -> list[dict]:
    texto = texto.strip()
    if not texto:
        return []
    try:  # compose emite un arreglo JSON o NDJSON según la versión
        datos = json.loads(texto)
        return datos if isinstance(datos, list) else [datos]
    except json.JSONDecodeError:
        return [json.loads(linea) for linea in texto.splitlines() if linea.strip()]


def _puerto(fila: dict | None, declarado: list, interno: int | None = None) -> str | None:
    """El puerto publicado en el equipo; si no publica ninguno, el de adentro de la red (en las instancias de
    detección, aunque estén detenidas: es el mismo para todas)."""
    publicados = [p for p in (fila or {}).get("Publishers") or [] if isinstance(p, dict)]
    afuera = sorted({int(p["PublishedPort"]) for p in publicados if p.get("PublishedPort")})
    if afuera:
        return ", ".join(str(p) for p in afuera)
    adentro = sorted({int(p["TargetPort"]) for p in publicados if p.get("TargetPort")})
    if not adentro:
        for p in declarado or []:
            if isinstance(p, dict) and p.get("target"):
                adentro.append(int(p["target"]))
    if not adentro and interno:
        adentro.append(interno)
    return ", ".join(f"{p} (red interna)" for p in sorted(set(adentro))) or None


class Plataforma:
    def __init__(
        self,
        app: Any,
        compose_dir: Path | None,
        registro: Path,
        run_cmd: RunCmd | None = None,
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self._app = app
        self._dir = compose_dir
        self._run_cmd = run_cmd or _run_subprocess
        self._registro = registro
        self._reloj = reloj
        self._config: dict[str, dict] | None = None
        self._gpu: tuple[float, dict | None] | None = None
        self._lock = asyncio.Lock()

    @property
    def orquestada(self) -> bool:
        return self._dir is not None and getattr(self._app.state, "target_manager", None) is not None

    # --- docker compose, de solo lectura ------------------------------------------------------

    async def _docker(self, *args: str) -> str:
        code, out, err = await self._run_cmd(*args, cwd=self._dir)
        if code != 0:
            raise ComposeError(err.strip() or out.strip() or f"exit {code}: {' '.join(args)}")
        return out

    async def _compose(self, *args: str) -> str:
        return await self._docker("docker", "compose", "--project-name", PROJECT_NAME, *args)

    async def _servicios(self) -> dict[str, dict]:
        """Los servicios declarados en el compose de la plataforma (cacheado)."""
        if self._config is None:
            try:
                datos = json.loads(await self._compose("config", "--format", "json"))
            except json.JSONDecodeError as exc:
                raise ComposeError(f"config --format json imparseable: {exc}") from exc
            self._config = {nombre: svc for nombre, svc in (datos.get("services") or {}).items()
                            if isinstance(svc, dict)}
        return self._config

    async def _desde(self, contenedores: list[str]) -> dict[str, str]:
        """Desde cuándo corre cada contenedor (StartedAt de `docker inspect`)."""
        if not contenedores:
            return {}
        try:
            salida = await self._docker("docker", "inspect", "--format", "{{.Name}} {{.State.StartedAt}}", *contenedores)
        except ComposeError:
            return {}
        desde = {}
        for linea in salida.splitlines():
            partes = linea.strip().split(" ", 1)
            if len(partes) == 2 and not partes[1].startswith("0001-"):
                desde[partes[0].lstrip("/")] = partes[1]
        return desde

    async def gpu(self, activa: str | None) -> dict[str, Any]:
        """La memoria de GPU en uso, leída con `nvidia-smi` adentro de la instancia activa: el motor de
        detección no la expone por HTTP y su repositorio no se toca."""
        if not activa:
            return {"disponible": False, "motivo": "no hay una instancia del plano de medios activa"}
        ahora = self._reloj()
        if self._gpu and ahora - self._gpu[0] < _GPU_TTL_S and (self._gpu[1] or {}).get("instancia") == activa:
            return self._gpu[1] or {}
        try:
            salida = await self._compose("exec", "-T", activa, "nvidia-smi",
                                         "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits")
            nombre, usada, total = [x.strip() for x in salida.strip().splitlines()[0].split(",")]
            gpu = {"disponible": True, "instancia": activa, "nombre": nombre,
                   "usada_mb": int(float(usada)), "total_mb": int(float(total))}
        except (ComposeError, ValueError, IndexError) as exc:
            gpu = {"disponible": False, "instancia": activa, "motivo": f"nvidia-smi no respondió: {str(exc)[:160]}"}
        self._gpu = (ahora, gpu)
        return gpu

    async def estado(self) -> dict[str, Any]:
        """Los servicios del compose en dos grupos —núcleo y detección— con su estado, su salud, su
        imagen, desde cuándo corre y su puerto; la instancia activa y la memoria de GPU que usa."""
        if not self.orquestada:
            return {"orquestada": False, "nucleo": [], "deteccion": [], "gpu": None, "en_curso": self.en_curso()}
        servicios = await self._servicios()
        filas = {f.get("Service"): f for f in _filas_ps(await self._compose("ps", "-a", "--format", "json"))}
        corriendo = [f.get("Name") for f in filas.values() if f.get("State") == "running" and f.get("Name")]
        desde = await self._desde(corriendo)
        activa = getattr(self._app.state.target_manager, "active", None)

        def fila(nombre: str, grupo: str) -> dict[str, Any]:
            svc = servicios.get(nombre) or {}
            ps = filas.get(nombre)
            etiquetas = _normalize_labels(svc.get("labels"))
            estado = str(ps.get("State")) if ps else "ausente"
            # Si la etiqueta se movió a otra construcción después de crear el contenedor, compose muestra el digest
            # de la imagen con que se creó: se muestra el nombre declarado y se avisa que la etiqueta ya no es esa.
            imagen = (ps or {}).get("Image") or svc.get("image")
            movida = bool(imagen and str(imagen).startswith("sha256:"))
            return {
                "servicio": nombre,
                "nombre": NUCLEO.get(nombre),
                "grupo": grupo,
                "modelo": etiquetas.get(MODEL_REF_LABEL),
                "estado": estado,
                "salud": (ps or {}).get("Health") or None,
                "imagen": svc.get("image") if movida else imagen,
                "etiqueta_movida": movida,
                "desde": desde.get((ps or {}).get("Name") or "") if estado == "running" else None,
                "puerto": _puerto(ps, svc.get("ports") or [], _SERVICE_PORT if grupo == "deteccion" else None),
                "activa": nombre == activa,
                "orquestable": grupo == "deteccion" or nombre in ORQUESTABLES,
            }

        nucleo = [fila(n, "nucleo") for n in NUCLEO if n in servicios]
        deteccion = sorted(
            (fila(n, "deteccion") for n, svc in servicios.items()
             if _normalize_labels(svc.get("labels")).get(INSTANCE_LABEL) == "true"),
            key=lambda f: (not f["activa"], f["servicio"]),
        )
        return {
            "orquestada": True,
            "nucleo": nucleo,
            "deteccion": deteccion,
            "activa": activa,
            "perfil_operativo": PERFIL_OPERATIVO,
            "gpu": await self.gpu(activa if activa and filas.get(activa, {}).get("State") == "running" else None),
            "en_curso": self.en_curso(),
        }

    # --- guardas y registro ------------------------------------------------------------------

    def en_curso(self) -> str | None:
        """Qué se cortaría si se detiene algo: un experimento (o un clip) o una sesión de demo."""
        demo = getattr(self._app.state, "demo_manager", None)
        if demo is not None:
            try:
                estado = demo.estado()
            except Exception:  # noqa: BLE001 -- leer el estado no puede tumbar la pantalla
                estado = {}
            if estado.get("fase") in ("preparing", "live", "finishing", "rendering"):
                return f"la sesión de demo {estado.get('session_id')}"
        manager = getattr(self._app.state, "experiment_manager", None)
        actual = manager.current() if manager is not None else None
        if actual:
            return f"la corrida {actual.get('experiment_id')}"
        return None

    def _anotar(self, accion: str, servicio: str | None, resultado: str, detalle: str | None, t0: float) -> dict:
        entrada = {
            "t": datetime.fromtimestamp(t0, tz=UTC).isoformat(),
            "accion": accion,
            "servicio": servicio,
            "resultado": resultado,
            "detalle": detalle,
            "duracion_s": round(self._reloj() - t0, 1),
        }
        try:
            self._registro.parent.mkdir(parents=True, exist_ok=True)
            with self._registro.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("plataforma: no se pudo anotar en %s: %s", self._registro, exc)
        return entrada

    def acciones(self, limite: int = 30) -> list[dict]:
        """Las últimas acciones, la más nueva primero."""
        try:
            lineas = self._registro.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        salida = []
        for linea in reversed(lineas[-limite:]):
            try:
                salida.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
        return salida

    # --- acciones ---------------------------------------------------------------------------

    async def accion(self, servicio: str, verbo: str, confirmar: bool = False) -> dict[str, Any]:
        """Un verbo sobre un servicio. Núcleo: levantar, detener o reiniciar. Detección: activar o detener."""
        if not self.orquestada:
            raise AccionInvalida("la orquestación necesita la consola en contenedor")
        servicios = await self._servicios()
        if servicio not in servicios:
            raise AccionInvalida(f"servicio fuera de la plataforma: {servicio}")
        if servicio == CONSOLA:
            raise ConsolaPropia(f"docker compose --project-name {PROJECT_NAME} {'stop' if verbo == 'detener' else 'restart'} {CONSOLA}")
        es_deteccion = _normalize_labels(servicios[servicio].get("labels")).get(INSTANCE_LABEL) == "true"
        permitidos = {"activar", "detener"} if es_deteccion else set(VERBOS_NUCLEO)
        if verbo not in permitidos:
            raise AccionInvalida(f"«{verbo}» no se puede hacer con {servicio}")
        en_curso = self.en_curso()
        if verbo in DETIENEN and en_curso and not confirmar:
            raise EnCurso(f"está en curso {en_curso}: confirmalo para seguir")
        t0 = self._reloj()
        async with self._lock:
            try:
                if es_deteccion:
                    manager = self._app.state.target_manager
                    if verbo == "activar":
                        await manager.switch(servicio)
                    elif manager.active == servicio:
                        await manager.stop_active()
                    else:
                        raise AccionInvalida(f"{servicio} no es la instancia activa")
                else:
                    await self._compose(*VERBOS_NUCLEO[verbo], servicio)
            except AccionInvalida:
                raise
            except Exception as exc:  # noqa: BLE001 -- se registra y se devuelve el motivo
                self._anotar(verbo, servicio, "error", str(exc)[:300], t0)
                raise
        return self._anotar(verbo, servicio, "ok", None, t0)

    async def dejar_lista(self, confirmar: bool = False) -> dict[str, Any]:
        """Levanta lo que falte del núcleo y activa el perfil operativo, sin recrear lo que ya corre.

        Si para eso hay que cambiar el motor y hay una demo o una corrida en curso, pide confirmación, como
        `accion()`: cambiar el motor la cortaría (revisión del 2026-11-19).
        """
        if not self.orquestada:
            raise AccionInvalida("la orquestación necesita la consola en contenedor")
        en_curso = self.en_curso()
        activa = getattr(getattr(self._app.state, "target_manager", None), "active", None)
        if en_curso and not confirmar and activa != PERFIL_OPERATIVO:
            raise EnCurso(f"está en curso {en_curso} y dejarla lista cambia el motor: confirmalo para seguir")
        t0 = self._reloj()
        hecho: list[str] = []
        async with self._lock:
            try:
                filas = {f.get("Service"): f for f in _filas_ps(await self._compose("ps", "-a", "--format", "json"))}
                for servicio in ORQUESTABLES:
                    if (filas.get(servicio) or {}).get("State") != "running":
                        await self._compose(*VERBOS_NUCLEO["levantar"], servicio)
                        hecho.append(f"levantó {NUCLEO[servicio].lower()}")
                manager = self._app.state.target_manager
                if manager.active != PERFIL_OPERATIVO or (filas.get(PERFIL_OPERATIVO) or {}).get("State") != "running":
                    await manager.switch(PERFIL_OPERATIVO)
                    hecho.append(f"activó {PERFIL_OPERATIVO}")
            except Exception as exc:  # noqa: BLE001
                self._anotar("dejar lista", None, "error", "; ".join([*hecho, str(exc)[:300]]), t0)
                raise
        return self._anotar("dejar lista", None, "ok", "; ".join(hecho) or "ya estaba lista", t0)
