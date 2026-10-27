"""Rutas `/api/demo/*` sobre la app real (con los fakes de siempre)."""
from __future__ import annotations

import httpx


def _sin_red(client) -> None:
    """Sin red real: en WSL espejo un puerto cerrado de localhost cuelga en vez de
    rechazar, así que el broker y la distribución se simulan."""
    client.app.state.demo_manager._ping = lambda host, port: {
        "ok": False, "rtt_ms": None, "detalle": "sin broker en el test"}

    def distribucion(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404, json={"detail": "No hay run activo"})

    client.app.state.distribution_http = httpx.AsyncClient(
        base_url="http://dist", transport=httpx.MockTransport(distribucion)
    )


def test_state_sin_sesion_es_idle(client):
    body = client.get("/api/demo/state").json()
    assert body["fase"] == "idle" and body["session_id"] is None
    assert body["motor"]["estado"] == "desconocido"


def test_preflight_lista_los_chequeos_y_no_revienta_sin_plantillas(two_plane_client):
    client = two_plane_client
    _sin_red(client)
    body = client.get("/api/demo/preflight").json()
    ids = [i["id"] for i in body["items"]]
    assert ids == ["sesion", "deteccion", "motor", "reglas", "distribucion", "broker",
                   "congelado", "host"]
    assert body["listo"] is False  # sin broker y sin plantillas: rojo
    congelado = next(i for i in body["items"] if i["id"] == "congelado")
    assert congelado["estado"] == "error"


def test_start_con_chequeo_en_rojo_es_503_con_el_detalle(two_plane_client):
    client = two_plane_client
    _sin_red(client)
    r = client.post("/api/demo/start", json={"variante": "oakd"})
    assert r.status_code == 503
    assert "preflight" in r.json()


def test_exploracion_mal_pedida_es_422(client):
    """RT-05: el motor y la cámara salen de una lista cerrada (exploracion.yaml)."""
    assert client.get("/api/demo/preflight", params={"motor": "mp-nada"}).status_code == 422
    r = client.post("/api/demo/start", json={"escena": "DEMO", "exploracion": "mp-yoloe-26s"})
    assert r.status_code == 422


def test_finish_sin_sesion_es_409(client):
    assert client.post("/api/demo/finish").status_code == 409


def test_sesiones_vacias_y_desconocidas(client):
    assert client.get("/api/demo/sessions").json() == []
    assert client.get("/api/demo/sessions/demo_20261026T000000Z").status_code == 404
    assert client.get("/api/demo/sessions/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/demo/respaldo").status_code == 404
    r = client.get("/api/demo/sessions/demo_20261026T000000Z/archivo/session.json")
    assert r.status_code == 404


def test_reiniciar_motor_en_nativo_es_501(client):
    assert client.post("/api/demo/motor/reiniciar").status_code == 501


def test_cifras_pendientes(client):
    cifras = client.get("/api/demo/cifras").json()
    assert {c["prueba"] for c in cifras} == {"ALR-01", "ALR-07", "ALR-08", "RT-03"}
    assert all(c["pendiente"] for c in cifras)


def test_stack_nativo(client):
    body = client.get("/api/demo/stack").json()
    assert body["modo"] == "nativo" and body["contenedores"] is None
    assert len(body["repos"]) == 5


def test_hora_del_servidor_para_el_director_del_rodaje(client):
    """`rodaje.ps1` mide con esto el desfase host ↔ contenedor (RT-04, doc 134)."""
    import time

    antes = time.time() * 1000
    body = client.get("/api/demo/hora").json()
    assert antes - 5 <= body["ms"] <= time.time() * 1000 + 5


def test_start_con_escena_invalida_es_422(client):
    r = client.post("/api/demo/start", json={"escena": "../fuera"})
    assert r.status_code in (422, 503)
