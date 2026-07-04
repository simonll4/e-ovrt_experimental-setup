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
    client_gone = False
    try:
        async with websockets.connect(_ws_url(settings.service_url, run_id)) as upstream:

            async def _pump() -> None:
                """Lee del upstream y coalesce en el buffer (termina al cerrar upstream)."""
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

            async def _flush() -> None:
                """Drena el buffer al SPA cada FLUSH_INTERVAL (termina si el send falla)."""
                while True:
                    await asyncio.sleep(FLUSH_INTERVAL)
                    pending = buffer.drain()
                    for index, event in enumerate(pending):
                        try:
                            await websocket.send_json(event)
                        except asyncio.CancelledError:
                            # Nos cancelan (p.ej. el upstream cerró) a mitad del
                            # batch ya drenado: devolver la cola no enviada al
                            # buffer para que el drain final no la pierda (incluye
                            # el evento terminal `state`).
                            for leftover in pending[index:]:
                                buffer.push(leftover)
                            raise

            async def _watch_client() -> None:
                """Detecta la desconexión del SPA aunque el upstream esté en
                silencio. Sin esto, un stream quieto tras irse el cliente dejaba
                colgados el WS al servicio y las tasks (fuga de recursos)."""
                try:
                    while True:
                        message = await websocket.receive()
                        if message["type"] == "websocket.disconnect":
                            return
                except (WebSocketDisconnect, RuntimeError):
                    return

            pump = asyncio.create_task(_pump())
            flush = asyncio.create_task(_flush())
            watch = asyncio.create_task(_watch_client())
            active = {pump, flush, watch}
            try:
                done, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in active:
                    task.cancel()
                await asyncio.gather(*active, return_exceptions=True)

            if watch in done or flush in done:
                # El SPA se fue (watch) o un send falló porque se fue (flush): no
                # hay a quién enviarle ni a quién cerrarle el WS.
                client_gone = True
            else:
                # El upstream terminó con el SPA aún conectado: drain final para
                # no perder la cola y propagar el close code real del servicio.
                for event in buffer.drain():
                    try:
                        await websocket.send_json(event)
                    except (
                        RuntimeError,
                        WebSocketDisconnect,
                        websockets.exceptions.WebSocketException,
                    ):
                        client_gone = True
                        break
                close_code = upstream.close_code
    except (OSError, websockets.exceptions.WebSocketException):
        close_code = 4503  # servicio inaccesible: el SPA reintenta la conexión
    except WebSocketDisconnect:
        return  # el SPA se fue: nada que cerrar
    if client_gone:
        return
    try:
        await websocket.close(code=_safe_close_code(close_code))
    except (RuntimeError, websockets.exceptions.WebSocketException):
        pass  # ya cerrado por el cliente, o código no enviable por el transporte
