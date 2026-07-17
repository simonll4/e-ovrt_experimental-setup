from __future__ import annotations

NEW_SET = {
    "id": "nuevo_set",
    "description": "creado por test",
    "status": "exploratory",
    "classes": [
        {"id": "person", "strategy": "canonical_positive",
         "phrasings": {"default": ["person"]}},
    ],
}


def test_list_and_get(client):
    sets = client.get("/api/prompt-sets").json()
    ids = {s["id"] for s in sets}
    assert {"demo_set", "frozen_set"} <= ids
    detail = client.get("/api/prompt-sets/demo_set")
    assert detail.status_code == 200
    assert detail.json()["classes"]
    assert client.get("/api/prompt-sets/inexistente").status_code == 404


def test_create_update_delete_cycle(client):
    assert client.post("/api/prompt-sets", json=NEW_SET).status_code == 201
    assert client.post("/api/prompt-sets", json=NEW_SET).status_code == 409
    updated = {**NEW_SET, "description": "v2"}
    assert client.put("/api/prompt-sets/nuevo_set", json=updated).status_code == 200
    assert client.get("/api/prompt-sets/nuevo_set").json()["description"] == "v2"
    assert client.delete("/api/prompt-sets/nuevo_set").status_code == 204
    assert client.get("/api/prompt-sets/nuevo_set").status_code == 404


def test_invalid_payload_is_422(client):
    bad = {**NEW_SET, "id": "malo",
           "classes": [{"id": "x", "strategy": "inventada",
                        "phrasings": {"default": ["x"]}}]}
    response = client.post("/api/prompt-sets", json=bad)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_freeze_flow_and_immutability(client):
    client.post("/api/prompt-sets", json=NEW_SET)
    assert client.post("/api/prompt-sets/nuevo_set/freeze-request").status_code == 200
    assert client.put("/api/prompt-sets/nuevo_set",
                      json={**NEW_SET, "description": "tarde"}).status_code == 409
    frozen = client.post("/api/prompt-sets/nuevo_set/freeze")
    assert frozen.status_code == 200
    assert frozen.json()["frozen_sha256"]
    assert client.put("/api/prompt-sets/nuevo_set", json=NEW_SET).status_code == 409
    assert client.delete("/api/prompt-sets/nuevo_set").status_code == 409
    assert client.post("/api/prompt-sets/nuevo_set/freeze").status_code == 409


def test_derive(client):
    body = {"new_id": "demo_set_v2", "changes": "prueba"}
    created = client.post("/api/prompt-sets/demo_set/derive", json=body)
    assert created.status_code == 201
    data = created.json()
    assert data["derives_from"] == "demo_set" and data["status"] == "exploratory"
    assert client.post("/api/prompt-sets/demo_set/derive", json=body).status_code == 409
    sin_changes = {"new_id": "otro", "changes": "  "}
    assert client.post("/api/prompt-sets/demo_set/derive", json=sin_changes).status_code == 422


def test_catalog_exposes_status_and_yaml_frozen(client):
    sets = {s["id"]: s for s in client.get("/api/catalog/prompt-sets").json()}
    # frozen_set viene del env de settings (legacy override) sin status en el YAML
    assert sets["frozen_set"]["frozen"] is True
    assert sets["demo_set"]["frozen"] is False
    assert sets["demo_set"]["status"] == "exploratory"
    # un set con status frozen en el YAML queda frozen aunque no esté en el env
    client.post("/api/prompt-sets", json=NEW_SET)
    client.post("/api/prompt-sets/nuevo_set/freeze-request")
    client.post("/api/prompt-sets/nuevo_set/freeze")
    sets = {s["id"]: s for s in client.get("/api/catalog/prompt-sets").json()}
    assert sets["nuevo_set"]["frozen"] is True and sets["nuevo_set"]["status"] == "frozen"
