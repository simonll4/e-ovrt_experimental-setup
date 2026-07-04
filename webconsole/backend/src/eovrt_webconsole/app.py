"""Factory de la app FastAPI del BFF de la consola."""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from eovrt_webconsole.routers import catalog, compare, compose, manifests, meta, runs, stream
from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings


def create_app(
    settings: ConsoleSettings | None = None,
    service_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or ConsoleSettings.from_env()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
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

    frontend_dist = settings.repo_root / "webconsole" / "frontend" / "dist"
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
    return app
