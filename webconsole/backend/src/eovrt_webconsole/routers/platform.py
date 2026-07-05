"""Plataforma: ciclo de vida del fleet de instancias media-plane (spec §4)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.orchestrator import (
    ComposeError,
    PlatformBusy,
    SwitchFailed,
    TargetManager,
    UnknownInstance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platform")


def _manager(request: Request) -> TargetManager:
    manager = getattr(request.app.state, "target_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=501,
            detail="Orquestación no habilitada (definí EOVRT_CONSOLE_COMPOSE_DIR)",
        )
    return manager


@router.get("/instances")
async def instances(request: Request) -> list[dict]:
    try:
        return await _manager(request).instances()
    except ComposeError as exc:
        logger.warning("instances: docker compose falló: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/instances/{name}/activate")
async def activate(name: str, request: Request):
    manager = _manager(request)
    try:
        return await manager.switch(name)
    except UnknownInstance as exc:
        raise HTTPException(status_code=404, detail=f"Instancia fuera del fleet: {name}") from exc
    except PlatformBusy as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": "Hay un run activo en el target actual", "run_id": exc.run_id},
        )
    except SwitchFailed as exc:
        status = 504 if exc.step == "readyz" else 502
        logger.warning("activate(%s) falló en %s: %s", name, exc.step, exc.detail)
        return JSONResponse(status_code=status, content={"detail": exc.detail, "step": exc.step})
    except ComposeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stop")
async def stop(request: Request):
    manager = _manager(request)
    try:
        await manager.stop_active()
    except PlatformBusy as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": "Hay un run activo en el target actual", "run_id": exc.run_id},
        )
    except SwitchFailed as exc:
        return JSONResponse(status_code=502, content={"detail": exc.detail, "step": exc.step})
    return {"target": None}
