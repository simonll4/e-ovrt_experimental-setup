"""Reintento único de GET ante una conexión keep-alive que el servidor ya cerró.

httpx y uvicorn expiran las conexiones ociosas a los mismos 5 s. Si la consola
reusa una que el servidor acaba de cerrar, el GET falla con "Server disconnected
without sending a response" y la pantalla muestra un 502 que no es real: pasaba
en el primer pedido después de unos segundos quieta (cambiar de pantalla en la
demo). Solo se reintentan GET/HEAD, que son idempotentes; un POST puede haber
llegado y reintentarlo podría lanzar dos corridas.
"""
from __future__ import annotations

import httpx

_IDEMPOTENTES = frozenset({"GET", "HEAD"})


class ReintentoKeepAlive(httpx.AsyncBaseTransport):
    def __init__(self, interno: httpx.AsyncBaseTransport | None = None) -> None:
        self._interno = interno or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return await self._interno.handle_async_request(request)
        except httpx.RemoteProtocolError:
            if request.method not in _IDEMPOTENTES:
                raise
            return await self._interno.handle_async_request(request)

    async def aclose(self) -> None:
        await self._interno.aclose()
