"""Factory de la app FastAPI del BFF de la consola."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.run_manager import ExperimentRunManager
from eovrt_webconsole.orchestrator import ComposeOrchestrator, RunCmd, TargetManager
from eovrt_webconsole.recording.manager import RecordingManager
from eovrt_webconsole.recording.oakd_recorder import InterpreterUnavailable, check_interpreter
from eovrt_webconsole.routers import (
    cameras,
    catalog,
    compare,
    compose,
    experiments,
    manifests,
    meta,
    platform,
    preview,
    prompts,
    recordings,
    runs,
    stream,
)
from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings


def create_app(
    settings: ConsoleSettings | None = None,
    service_transport: httpx.AsyncBaseTransport | None = None,
    compose_runner: RunCmd | None = None,
    control_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or ConsoleSettings.from_env()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        if settings.compose_dir is not None:
            # Modo orquestado: el target es dinámico (la instancia activa del fleet);
            # TargetManager es dueño de app.state.http/backend y los swapea al switchear.
            orchestrator = ComposeOrchestrator(settings.compose_dir, run_cmd=compose_runner)
            manager = TargetManager(
                app, orchestrator, settings, service_transport=service_transport
            )
            app.state.target_manager = manager
            await manager.bootstrap()
        else:
            # Modo static: target fijo, comportamiento histórico intacto.
            app.state.target_manager = None
            app.state.http = httpx.AsyncClient(
                base_url=settings.service_url, transport=service_transport, timeout=30.0
            )
            app.state.backend = RunBackend(app.state.http)
        # Segundo backend (control-plane :8081): target fijo siempre, independiente
        # del swap de fleet del modo orquestado (ese swap es solo media-plane).
        app.state.control_http = httpx.AsyncClient(
            base_url=settings.control_service_url, transport=control_transport, timeout=30.0
        )
        app.state.control_backend = ControlPlaneBackend(app.state.control_http)
        # Manager del disparo orquestado (Tarea 3): un experimento activo por vez,
        # corrido como asyncio.Task en este mismo loop (ver run_manager.py).
        app.state.experiment_manager = ExperimentRunManager()
        # Grabación de rodaje: vive en la consola, no depende del media-plane
        # (spec 2026-07-21). El chequeo del intérprete se hace acá y no al
        # apretar grabar: el fallo se descubre ahora, no en medio del rodaje.
        oakd_script = settings.repo_root / "webconsole" / "tools" / "record_oakd.py"
        app.state.recording_manager = RecordingManager(
            raw_dir=settings.raw_dir,
            oakd_interpreter=settings.oakd_interpreter,
            oakd_script=oakd_script,
        )
        try:
            check_interpreter(settings.oakd_interpreter)
        except InterpreterUnavailable as exc:
            logging.getLogger(__name__).warning("Rama OAK-D no disponible: %s", exc)
        for basename in app.state.recording_manager.recover_orphans():
            logging.getLogger(__name__).warning("Grabación huérfana cerrada: %s", basename)
        yield
        # Cancela/awaitea cualquier experimento en curso antes de cerrar los
        # clientes HTTP que usa -- evita un task pendiente huerfano al apagar.
        await app.state.experiment_manager.aclose()
        await app.state.http.aclose()
        await app.state.control_http.aclose()

    app = FastAPI(title="eovrt-webconsole", lifespan=_lifespan)
    app.state.settings = settings
    app.include_router(meta.router)
    app.include_router(catalog.router)
    app.include_router(compare.router)
    app.include_router(compose.router)
    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(manifests.router)
    app.include_router(experiments.router)
    app.include_router(platform.router)
    app.include_router(prompts.router)
    app.include_router(cameras.router)
    app.include_router(preview.router)
    app.include_router(recordings.router)

    frontend_dist = settings.spa_dist or (settings.repo_root / "webconsole" / "frontend" / "dist")
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
    return app
