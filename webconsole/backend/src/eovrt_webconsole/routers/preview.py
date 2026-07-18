"""Proxy REST + WS de la sesión de preview del media-plane."""
from __future__ import annotations

import asyncio
import logging

import websockets
import websockets.exceptions
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response

from eovrt_webconsole.routers.stream import _safe_close_code
from eovrt_webconsole.run_backend import PreviewConflict, ServiceRejected, ServiceUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preview")


def _preview_ws_url(service_url: str) -> str:
    base = service_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    return f"{base}/api/preview/stream"


@router.post("", status_code=201)
async def start_preview(payload: dict, request: Request) -> dict:
    try:
        return await request.app.state.backend.preview_start(payload)
    except PreviewConflict as exc:
        return JSONResponse(status_code=409, content=exc.body)
    except ServiceRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc.detail)) from exc
    except ServiceUnavailable as exc:
        logger.warning("preview_start: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("")
async def preview_status(request: Request) -> dict:
    try:
        return await request.app.state.backend.preview_status()
    except ServiceUnavailable as exc:
        logger.warning("preview_status: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("", status_code=204)
async def stop_preview(request: Request):
    try:
        await request.app.state.backend.preview_stop()
    except ServiceUnavailable as exc:
        logger.warning("stop_preview: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(status_code=204)


@router.websocket("/stream")
async def preview_stream_ws(websocket: WebSocket) -> None:
    """Passthrough binario/texto del WS de preview: sin coalescing (el
    media-plane ya pacea enviando solo el último frame)."""
    settings = websocket.app.state.settings
    await websocket.accept()
    close_code = 1000
    try:
        async with websockets.connect(_preview_ws_url(settings.service_url)) as upstream:

            async def _pump() -> None:
                async for raw in upstream:
                    if isinstance(raw, bytes):
                        await websocket.send_bytes(raw)
                    else:
                        await websocket.send_text(raw)

            async def _watch_client() -> None:
                try:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                except (WebSocketDisconnect, RuntimeError):
                    return

            pump = asyncio.create_task(_pump())
            watch = asyncio.create_task(_watch_client())
            active = {pump, watch}
            try:
                done, pending = await asyncio.wait(
                    active, return_when=asyncio.FIRST_COMPLETED
                )
            finally:
                for task in pending:
                    task.cancel()
                # Consumir excepciones de TODAS las tasks (done y pending), no
                # solo las canceladas: si pump terminó con excepción (upstream
                # cayó abrupto) y nadie la lee, queda "Task exception was never
                # retrieved".
                await asyncio.gather(*active, return_exceptions=True)
            if pump in done:
                close_code = _safe_close_code(upstream.close_code)
    except (OSError, websockets.exceptions.WebSocketException):
        close_code = 4503
    except WebSocketDisconnect:
        return
    try:
        await websocket.close(code=close_code)
    except RuntimeError:
        pass
