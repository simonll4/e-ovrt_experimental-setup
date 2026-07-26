"""Passthrough del estado vivo del control-plane (riesgo activo, feature
'patrones activos en vivo'). Espeja el patron de get_experiment_alerts en
routers/experiments.py: 404 se propaga tal cual (no hay corrida activa),
502 si el control-plane no responde."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole.experiment.control_backend import ServiceUnavailable, UnknownRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control")


@router.get("/current")
async def get_control_current(request: Request) -> dict:
    control_backend = request.app.state.control_backend
    try:
        return await control_backend.current()
    except UnknownRun as exc:
        raise HTTPException(
            status_code=404, detail="No hay corrida activa en el control-plane"
        ) from exc
    except ServiceUnavailable as exc:
        logger.warning("get_control_current: control-plane inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
