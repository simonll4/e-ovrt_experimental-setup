"""Salud del BFF y estado agregado del target (servicio media-plane)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/target")
async def target(request: Request) -> dict:
    """Estado agregado de la instancia del servicio: healthz + readyz + modelo."""
    http: httpx.AsyncClient = request.app.state.http
    settings = request.app.state.settings
    out: dict = {"service_url": settings.service_url, "healthy": False, "ready": False, "model": None}
    try:
        out["healthy"] = (await http.get("/healthz")).status_code == 200
        out["ready"] = (await http.get("/readyz")).status_code == 200
        if out["ready"]:
            out["model"] = (await http.get("/api/model")).json()
    except httpx.HTTPError:
        pass  # servicio caído: healthy/ready quedan en False
    return out
