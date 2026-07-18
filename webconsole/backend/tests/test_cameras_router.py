from __future__ import annotations

PRESET = {
    "id": "oak_d_lab",
    "name": "OAK-D laboratorio",
    "plugin": "oak_d",
    "config": {"url": "192.168.1.50"},
}


def test_crud_por_http(client):
    r = client.post("/api/cameras", json=PRESET)
    assert r.status_code == 201
    r = client.get("/api/cameras")
    assert [c["id"] for c in r.json()] == ["oak_d_lab"]
    r = client.put("/api/cameras/oak_d_lab", json={**PRESET, "name": "otro"})
    assert r.json()["name"] == "otro"
    assert client.delete("/api/cameras/oak_d_lab").status_code == 204
    assert client.get("/api/cameras/oak_d_lab").status_code == 404


def test_duplicado_409(client):
    assert client.post("/api/cameras", json=PRESET).status_code == 201
    assert client.post("/api/cameras", json=PRESET).status_code == 409


def test_invalido_422(client):
    r = client.post("/api/cameras", json={**PRESET, "id": "Oak D!"})
    assert r.status_code == 422
