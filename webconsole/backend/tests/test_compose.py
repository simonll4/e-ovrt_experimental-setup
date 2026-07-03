def _body(**overrides) -> dict:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 1},
    }
    body.update(overrides)
    return body


def test_composicion_valida(client):
    r = client.post("/api/compose/validate", json=_body())
    assert r.status_code == 200
    assert r.json() == {"valid": True, "errors": []}


def test_plugin_fuera_del_mvp(client):
    r = client.post("/api/compose/validate", json=_body(ingest={"plugin": "rtsp", "config": {}}))
    errors = r.json()["errors"]
    assert any(e["field"] == "ingest.plugin" for e in errors)


def test_dataset_desconocido_o_no_disponible(client):
    for dataset in ("nope", "roto"):
        body = _body(ingest={"plugin": "image_folder", "config": {"dataset": dataset}})
        errors = client.post("/api/compose/validate", json=body).json()["errors"]
        assert any(e["field"] == "ingest.config.dataset" for e in errors)


def test_image_folder_sin_dataset_ni_path(client):
    body = _body(ingest={"plugin": "image_folder", "config": {}})
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert any(e["field"] == "ingest.config.path" for e in errors)


def test_prompt_set_inexistente_y_active_ids_invalidos(client):
    errors = client.post(
        "/api/compose/validate", json=_body(prompts={"set_id": "nope", "active_ids": None})
    ).json()["errors"]
    assert any(e["field"] == "prompts.set_id" for e in errors)
    errors = client.post(
        "/api/compose/validate",
        json=_body(prompts={"set_id": "demo_set", "active_ids": ["person", "alien"]}),
    ).json()["errors"]
    assert any(e["field"] == "prompts.active_ids" and "alien" in e["message"] for e in errors)


def test_params_invalidos(client):
    errors = client.post(
        "/api/compose/validate", json=_body(run={"stride": 0, "max_units": 0})
    ).json()["errors"]
    fields = {e["field"] for e in errors}
    assert "run.stride" in fields and "run.max_units" in fields


def test_policy_model_ref_distinto_bloquea(client):
    body = _body(manifest_model_ref="yoloe/yoloe-26l")  # el target tiene 'mock'
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert any(e["field"] == "model" and "mock" in e["message"] for e in errors)
    # con confirmación explícita, pasa
    body["confirm_target_model"] = True
    assert client.post("/api/compose/validate", json=body).json()["valid"] is True


def test_body_malformado_422(client):
    r = client.post("/api/compose/validate", json={"ingest": {"plugin": "x"}, "extra": 1})
    assert r.status_code == 422  # extra="forbid" de Composition


def test_servicio_caido_solo_target(settings):
    """Servicio media-plane caído: return-temprano de validate_composition en el
    except ServiceUnavailable — un único error de field '_target', el resto de
    las validaciones locales (que pasarían) ni se ejecutan."""
    import httpx
    from fastapi.testclient import TestClient

    from eovrt_webconsole.app import create_app

    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    app = create_app(settings, service_transport=httpx.MockTransport(_down))
    with TestClient(app) as c:
        r = c.post("/api/compose/validate", json=_body())
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert len(body["errors"]) == 1
    assert body["errors"][0]["field"] == "_target"
