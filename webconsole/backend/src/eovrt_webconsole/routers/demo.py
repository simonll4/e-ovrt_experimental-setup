"""Rutas de la demo en vivo de la defensa (spec 2026-10-23 §6.4.4). Todo `/api/demo/*`.

La pantalla `/demo` consulta `GET /api/demo/state` cada 500 ms mientras corre y el
chequeo previo mientras espera. Ninguna ruta de acá toca lo medido: arrancan y cierran
una sesión con el ejecutor de experimentos de siempre y leen sus artefactos.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from eovrt_webconsole.demo import config as demo_config
from eovrt_webconsole.demo.config import ConfigDemoError
from eovrt_webconsole.demo.sesion import (
    DemoManager,
    DemoNoLista,
    DemoOcupada,
    DemoSinSesion,
    SesionDesconocida,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo")


def _demo(request: Request) -> DemoManager:
    manager = getattr(request.app.state, "demo_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="La demo no está inicializada")
    return manager


@router.get("/hora")
def hora() -> dict:
    """Reloj de pared del servidor en ms. El director de tomas del rodaje en vivo
    (`infra/platform/rodaje.ps1`) mide con esto el desfase host ↔ contenedor para poner sus
    marcas de tiempo en el mismo reloj que las corridas."""
    return {"ms": round(time.time() * 1000.0, 3)}


@router.get("/preflight")
async def preflight(request: Request, motor: str | None = None, camara: str | None = None) -> dict:
    """Con `motor`/`camara` (query), el chequeo de una sesión de exploración (RT-05)."""
    demo = _demo(request)
    try:
        exploracion = demo_config.resolver_exploracion(demo.repo_root, motor, camara)
    except ConfigDemoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await demo.preflight(exploracion)


@router.post("/start", status_code=202)
async def start(request: Request, body: dict | None = None):
    variante = (body or {}).get("variante", "oakd")
    escena = (body or {}).get("escena")
    exploracion = (body or {}).get("exploracion")
    if exploracion is not None and not isinstance(exploracion, dict):
        raise HTTPException(status_code=422, detail="exploracion: {\"motor\": ..., \"camara\": ...}")
    try:
        return await _demo(request).start(variante, escena, exploracion)
    except DemoOcupada as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except DemoNoLista as exc:
        return JSONResponse(status_code=503, content={"detail": str(exc), "preflight": exc.preflight})
    except (ConfigDemoError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/finish", status_code=202)
async def finish(request: Request):
    try:
        return await _demo(request).finish()
    except DemoSinSesion as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})


@router.get("/state")
async def state(request: Request) -> dict:
    return _demo(request).estado()


@router.get("/stack")
async def stack(request: Request) -> dict:
    return await _demo(request).stack()


@router.get("/cifras")
async def cifras(request: Request) -> list[dict]:
    return _demo(request).cifras()


@router.post("/motor/reiniciar", status_code=202)
async def reiniciar_motor(request: Request):
    """Reinicio del motor en segundo plano (la pantalla ve `motor.estado`). En nativo
    la consola no puede reiniciar el media-plane: 501 con la indicación."""
    demo = _demo(request)
    if getattr(request.app.state, "target_manager", None) is None:
        return JSONResponse(
            status_code=501,
            content={"detail": "despliegue nativo: reiniciar el media-plane a mano"},
        )
    if demo.estado().get("fase") in {"preparing", "live", "finishing"}:
        return JSONResponse(status_code=409, content={"detail": "hay una sesión en curso"})
    demo.reiniciar_motor_en_segundo_plano()
    return {"motor": "reiniciando"}


@router.get("/respaldo")
async def respaldo(request: Request) -> dict:
    session_id = _demo(request).respaldo()
    if session_id is None:
        raise HTTPException(status_code=404, detail="No hay ninguna sesión marcada como respaldo")
    return {"session_id": session_id}


@router.get("/sessions")
async def sessions(request: Request) -> list[dict]:
    return _demo(request).sesiones()


@router.get("/sessions/{session_id}")
async def session(session_id: str, request: Request) -> dict:
    try:
        return _demo(request).sesion(session_id)
    except SesionDesconocida as exc:
        raise HTTPException(status_code=404, detail=f"Sesión desconocida: {session_id}") from exc


@router.post("/sessions/{session_id}/respaldo")
async def marcar_respaldo(session_id: str, request: Request) -> dict:
    try:
        _demo(request).marcar_respaldo(session_id)
    except SesionDesconocida as exc:
        raise HTTPException(status_code=404, detail=f"Sesión desconocida: {session_id}") from exc
    return {"session_id": session_id, "respaldo": True}


@router.get("/sessions/{session_id}/archivo/{rel:path}")
async def archivo(session_id: str, rel: str, request: Request):
    try:
        path = _demo(request).archivo(session_id, rel)
    except SesionDesconocida as exc:
        raise HTTPException(status_code=404, detail="Archivo desconocido") from exc
    return FileResponse(path)
