"""Proxy WS de telemetría: servicio → BFF → SPA, con coalescing (Spec B §5.6).

Espejo de la política del servicio: métricas coalescidas (última gana), eventos
discretos en cola acotada drop-oldest. Un SPA lento nunca acumula memoria acá.
El fallback ante caída es RECONECTAR el WS (responsabilidad del SPA); este proxy
reenvía el close code del servicio (1000 fin normal, 4404 run desconocido,
4503 servicio no listo) para que el cliente decida.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

_COALESCE_TYPES = {"metric"}
FLUSH_INTERVAL = 0.1
_MAX_DISCRETE = 200


class _CoalescingBuffer:
    def __init__(self, max_discrete: int = _MAX_DISCRETE) -> None:
        self._latest: dict[str, dict[str, Any]] = {}
        self._discrete: deque[dict[str, Any]] = deque(maxlen=max_discrete)

    def push(self, event: dict[str, Any]) -> None:
        if event.get("type") in _COALESCE_TYPES:
            self._latest[event["type"]] = event
        else:
            self._discrete.append(event)

    def drain(self) -> list[dict[str, Any]]:
        out = list(self._discrete)
        self._discrete.clear()
        out.extend(self._latest.values())
        self._latest.clear()
        return out


def _ws_url(service_url: str, run_id: str) -> str:
    base = service_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    return f"{base}/api/runs/{run_id}/stream"


def _safe_close_code(raw: int | None) -> int:
    """Mapea el close code del upstream a uno enviable por el WS del SPA.

    Códigos de aplicación válidos: 1000 y 3000-4999 (incluye 4404, 4503).
    None y reservados (1005/1006/1015, etc.) → 4503 (el SPA reconecta).
    """
    if raw is not None and (raw == 1000 or 3000 <= raw <= 4999):
        return raw
    return 4503


@router.websocket("/api/runs/{run_id}/stream")
async def stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    settings = websocket.app.state.settings
    buffer = _CoalescingBuffer()
    close_code = 1000
    try:
        async with websockets.connect(_ws_url(settings.service_url, run_id)) as upstream:

            async def _pump() -> None:
                discarded = 0
                async for raw in upstream:
                    try:
                        event = json.loads(raw)
                    except (json.JSONDecodeError, ValueError):
                        discarded += 1
                        logger.warning(
                            "stream(%s): frame malformado descartado (total=%d)",
                            run_id,
                            discarded,
                        )
                        continue
                    buffer.push(event)

            pump = asyncio.create_task(_pump())
            try:
                while not pump.done():
                    await asyncio.sleep(FLUSH_INTERVAL)
                    for event in buffer.drain():
                        await websocket.send_json(event)
                for event in buffer.drain():  # drain final: no perder la cola
                    await websocket.send_json(event)
            finally:
                pump.cancel()
                await asyncio.gather(pump, return_exceptions=True)
            close_code = upstream.close_code
    except (OSError, websockets.exceptions.WebSocketException):
        close_code = 4503  # servicio inaccesible: el SPA reintenta la conexión
    except WebSocketDisconnect:
        return  # el SPA se fue: nada que cerrar
    try:
        await websocket.close(code=_safe_close_code(close_code))
    except (RuntimeError, websockets.exceptions.WebSocketException):
        pass  # ya cerrado por el cliente, o código no enviable por el transporte
