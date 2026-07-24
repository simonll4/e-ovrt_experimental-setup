"""Preflight de plataforma: estado agregado de media-plane + control-plane.

Compartido por GET /api/preflight (meta.py) y el gate de lanzamiento de
experimentos (experiments.py): una corrida en tiempo real no debe dispararse
si algún plano está caído o no listo — el fallo tiene que ser sincrónico y
explicable, no quedar enterrado en el task 202 del runner.

Los `blockers` son frases cortas en el idioma del operador: el frontend las
muestra tal cual, sin traducir códigos.
"""
from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI


async def _probe(http: httpx.AsyncClient) -> tuple[bool, bool]:
    """(healthy, ready) de un plano; servicio caído -> (False, False)."""
    healthy = ready = False
    try:
        healthy = (await http.get("/healthz")).status_code == 200
        ready = (await http.get("/readyz")).status_code == 200
    except httpx.HTTPError:
        pass
    return healthy, ready


async def platform_preflight(app: FastAPI) -> dict:
    settings = app.state.settings
    (media_healthy, media_ready), (control_healthy, control_ready) = await asyncio.gather(
        _probe(app.state.http), _probe(app.state.control_http)
    )

    media: dict = {
        "service_url": settings.service_url,
        "healthy": media_healthy,
        "ready": media_ready,
        "model": None,
    }
    if media_ready:
        try:
            media["model"] = (await app.state.http.get("/api/model")).json()
        except (httpx.HTTPError, ValueError):
            # ValueError cubre un body no-JSON de /api/model: el modelo es dato
            # decorativo del preflight, nunca debe convertir el gate en un 500.
            pass

    control: dict = {
        "service_url": settings.control_service_url,
        "healthy": control_healthy,
        "ready": control_ready,
    }

    blockers: list[str] = []
    if not media_healthy:
        blockers.append("el media-plane no responde")
    elif not media_ready:
        blockers.append("el media-plane no terminó de cargar el modelo")
    if not control_healthy:
        blockers.append("el control-plane no responde")
    elif not control_ready:
        blockers.append("el control-plane no está listo")

    return {"ready": not blockers, "blockers": blockers, "media": media, "control": control}
