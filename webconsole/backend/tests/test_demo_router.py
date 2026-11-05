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
                   "congelado", "host", "encuadre"]
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


def test_camaras_lista_los_presets_aptos_sin_credenciales(two_plane_client, tmp_path):
    import yaml
    client = two_plane_client
    cameras = client.app.state.settings.cameras_dir
    cameras.mkdir(exist_ok=True)
    (cameras / "dvr.yaml").write_text(yaml.safe_dump({"camera": {
        "id": "dvr", "name": "DVR", "plugin": "rtsp", "config": {"url": "rtsp://admin:Clave1@10.0.0.5:554/s"}}}))
    async def sin_camino(host, puerto):  # sin red real: en WSL espejo un puerto cerrado cuelga
        raise TimeoutError

    client.app.state.demo_manager._conectar = sin_camino
    filas = client.get("/api/demo/camaras").json()
    assert [f["id"] for f in filas] == ["dvr"] and filas[0]["destino"] == "10.0.0.5:554"
    assert filas[0]["estado"] == "inactiva" and "no contesta" in filas[0]["detalle"]
    assert "Clave1" not in str(filas)


def test_comprobar_una_camara_inexistente_es_404(two_plane_client):
    r = two_plane_client.post("/api/demo/camaras/no_existe/comprobar")
    assert r.status_code == 404


def test_start_con_camara_que_no_es_texto_es_422(two_plane_client):
    _sin_red(two_plane_client)
    assert two_plane_client.post("/api/demo/start", json={"variante": "oakd", "camara": 5}).status_code == 422


def test_modos_sin_lista_es_503_y_un_modo_mal_pedido_es_422(client):
    """Sin `modos.yaml` la pantalla se queda con el campeón; un modo se pide por id, de la lista."""
    assert client.get("/api/demo/modos").status_code == 503
    assert client.get("/api/demo/preflight", params={"modo": "edir"}).status_code == 422
    assert client.post("/api/demo/start", json={"variante": "oakd", "modo": ["edir"]}).status_code == 422


def test_modos_lista_los_tres_con_frases_y_cifras(client):
    import shutil

    from tests.demo_fixtures import PROMPT_SETS, REPO_REAL

    repo = client.app.state.settings.repo_root
    destino = repo / "experiments" / "demo_defensa"
    destino.mkdir(parents=True)
    shutil.copy2(REPO_REAL / "experiments" / "demo_defensa" / "modos.yaml", destino)
    for archivo in PROMPT_SETS:
        shutil.copy2(REPO_REAL / "prompts" / archivo, repo / "prompts")
    body = client.get("/api/demo/modos").json()
    assert body["default"] == "campeon"
    assert [m["id"] for m in body["modos"]] == ["campeon", "edir", "clase_nueva", "reflective"]
    edir = body["modos"][1]
    assert edir["prompt_set"] == "edir_v1_pair_nivel_b" and edir["pattern_set"] == "cr01_cr02_edir_v1"
    assert edir["clases"][1]["frases"] == ["construction worker without safety helmet"]
    assert edir["cifras"][0]["prueba"] == "ALR-04"
    assert client.get("/api/demo/preflight", params={"modo": "nada"}).status_code == 422
