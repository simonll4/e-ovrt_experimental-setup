"""ExperimentRunManager: dispara `run_experiment` en background, un activo por vez
(spec 44 B, Tarea 3).

Usa `asyncio.Task` (mismo event loop que FastAPI), no threads: evitar la clase de
bug SIGABRT de cerrar un socket ZeroMQ desde un hilo distinto del que lo creo
mientras otro hilo esta en recv_multipart (ver CLAUDE.md raiz, "Trampa de
concurrencia, no negociable"). Como todo el disparo corre en el mismo loop que
maneja las requests HTTP del BFF, no hay ese cruce de hilos.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from eovrt_webconsole.experiment.manifest import ExperimentManifest, generate_experiment_id
from eovrt_webconsole.experiment.runner import (
    ControlBackendProtocol,
    MediaBackendProtocol,
    run_experiment,
)

logger = logging.getLogger(__name__)


class ExperimentBusy(Exception):
    """Ya hay un experimento activo: no se puede arrancar otro hasta que libere el slot."""

    def __init__(self, active_experiment_id: str) -> None:
        super().__init__(f"experimento activo: {active_experiment_id}")
        self.active_experiment_id = active_experiment_id


class ExperimentRunManager:
    """Coordina el disparo orquestado del experimento paraguas.

    Un solo experimento activo a la vez. `start()` es sincronico: crea el
    `asyncio.Task` y devuelve de inmediato (el caller -- la ruta HTTP -- no
    awaitea `run_experiment`, responde 202 y el task sigue corriendo en el
    loop). El estado de cada experimento (activo o terminado) queda
    direccionable por `experiment_id` en `_states` hasta que el proceso
    termine (no hay poda: alcance de esta tarea).
    """

    def __init__(self) -> None:
        self._active_id: str | None = None
        self._active_task: asyncio.Task | None = None
        self._states: dict[str, dict[str, Any]] = {}

    def start(
        self,
        manifest: ExperimentManifest,
        *,
        media_backend: MediaBackendProtocol,
        control_backend: ControlBackendProtocol,
        now: datetime,
        **run_kwargs: Any,
    ) -> str:
        """Arranca el experimento en background y devuelve su experiment_id.

        Guard de concurrencia: el slot (`_active_id`) se marca ANTES de crear
        el task (y por lo tanto antes de cualquier `await`), en el mismo tramo
        sincronico que el chequeo -- dos llamadas `start()` casi simultaneas
        en el mismo hilo/loop no pueden pisarse: la segunda ve `_active_id`
        ya seteado por la primera y levanta `ExperimentBusy` sin haber cedido
        el control del loop entre el chequeo y el seteo.
        """
        if self._active_id is not None:
            raise ExperimentBusy(self._active_id)

        experiment_id = manifest.experiment_id or generate_experiment_id(manifest.slug, now)
        self._active_id = experiment_id
        self._states[experiment_id] = {"experiment_id": experiment_id, "status": "running"}

        task = asyncio.create_task(
            run_experiment(
                manifest,
                media_backend=media_backend,
                control_backend=control_backend,
                now=now,
                **run_kwargs,
            )
        )
        self._active_task = task
        task.add_done_callback(lambda t: self._on_done(experiment_id, t))
        return experiment_id

    def _on_done(self, experiment_id: str, task: asyncio.Task) -> None:
        """Libera el slot activo pase lo que pase (exito, fallo de la corrida,
        excepcion o cancelacion del task) -- para que una corrida rota nunca
        deje el manager wedeado."""
        if self._active_id == experiment_id:
            self._active_id = None
            self._active_task = None

        if task.cancelled():
            self._states[experiment_id] = {
                "experiment_id": experiment_id,
                "status": "failed",
                "error": "cancelado",
            }
            return
        exc = task.exception()
        if exc is not None:
            logger.warning("experimento %s termino con excepcion", experiment_id, exc_info=exc)
            self._states[experiment_id] = {
                "experiment_id": experiment_id,
                "status": "failed",
                "error": str(exc),
            }
            return

        result = task.result()
        state = result.model_dump(mode="json")
        state["status"] = "succeeded" if result.ok else "failed"
        self._states[experiment_id] = state

    def current(self) -> dict[str, Any] | None:
        """Estado del experimento activo, o None si no hay ninguno corriendo."""
        if self._active_id is None:
            return None
        return self._states.get(self._active_id)

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        """Estado/resultado de un experimento por id (activo o ya terminado)."""
        return self._states.get(experiment_id)

    async def aclose(self) -> None:
        """Cancela y espera el task activo (teardown de la app: evita el warning
        de 'Task was destroyed but it is pending')."""
        task = self._active_task
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 -- solo drenar el teardown
            pass
