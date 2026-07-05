"""Factory de la app FastAPI del BFF de la consola."""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from eovrt_webconsole.orchestrator import ComposeOrchestrator, RunCmd, TargetManager
from eovrt_webconsole.routers import (
    catalog,
    compare,
    compose,
    manifests,
    meta,
    platform,
    runs,
    stream,
)
from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings


def create_app(
    settings: ConsoleSettings | None = None,
    service_transport: httpx.AsyncBaseTransport | None = None,
    compose_runner: RunCmd | None = None,
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
        yield
        await app.state.http.aclose()

    app = FastAPI(title="eovrt-webconsole", lifespan=_lifespan)
    app.state.settings = settings
    app.include_router(meta.router)
    app.include_router(catalog.router)
    app.include_router(compare.router)
    app.include_router(compose.router)
    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(manifests.router)
    app.include_router(platform.router)

    frontend_dist = settings.spa_dist or (settings.repo_root / "webconsole" / "frontend" / "dist")
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
    return app
