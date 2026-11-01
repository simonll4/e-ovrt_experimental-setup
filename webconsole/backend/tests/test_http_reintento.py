import httpx
import pytest

from eovrt_webconsole.http_reintento import ReintentoKeepAlive


def _servidor_que_corta_una_vez():
    llamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request.method)
        if len(llamadas) == 1:
            # Lo que ve httpx cuando reusa una conexión keep-alive que el servidor ya cerró.
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler), llamadas


async def test_get_se_reintenta_una_vez_si_el_servidor_corto_la_conexion():
    transporte, llamadas = _servidor_que_corta_una_vez()
    async with httpx.AsyncClient(transport=ReintentoKeepAlive(transporte),
                                 base_url="http://svc.fake") as http:
        r = await http.get("/api/runs")
    assert r.json() == {"ok": True}
    assert llamadas == ["GET", "GET"]


async def test_post_no_se_reintenta():
    # Un POST puede haber llegado al servidor: reintentarlo podría lanzar dos corridas.
    transporte, llamadas = _servidor_que_corta_una_vez()
    async with httpx.AsyncClient(transport=ReintentoKeepAlive(transporte),
                                 base_url="http://svc.fake") as http:
        with pytest.raises(httpx.RemoteProtocolError):
            await http.post("/api/runs", json={})
    assert llamadas == ["POST"]


async def test_un_servicio_caido_no_se_reintenta():
    llamadas = []

    def handler(request: httpx.Request) -> httpx.Response:
        llamadas.append(request.method)
        raise httpx.ConnectError("down", request=request)

    async with httpx.AsyncClient(transport=ReintentoKeepAlive(httpx.MockTransport(handler)),
                                 base_url="http://svc.fake") as http:
        with pytest.raises(httpx.ConnectError):
            await http.get("/api/runs")
    assert llamadas == ["GET"]
