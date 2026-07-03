from eovrt_webconsole.routers.runs import _row


def _body(**overrides) -> dict:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 1, "max_units": 5},
    }
    body.update(overrides)
    return body


def test_lanzar_ok_y_request_sin_model(client, fake_state):
    r = client.post("/api/runs", json=_body())
    assert r.status_code == 201
    assert r.json() == {"run_id": "run_active_1"}
    sent = fake_state.launched[0]
    assert "model" not in sent
    assert sent["prompts"]["set_inline"]["id"] == "demo_set"
    assert sent["ingest"]["config"] == {"dataset": "demo_v2"}
    assert sent["run"]["stride"] == 1


def test_lanzar_invalido_422_con_errores_de_campo(client):
    r = client.post("/api/runs", json=_body(prompts={"set_id": "nope", "active_ids": None}))
    assert r.status_code == 422
    assert any(e["field"] == "prompts.set_id" for e in r.json()["errors"])


def test_lanzar_busy_409(client, fake_state):
    fake_state.active_run_id = "run_previo"
    r = client.post("/api/runs", json=_body())
    assert r.status_code == 409
    assert r.json()["active_run_id"] == "run_previo"


def test_lanzar_rechazo_servicio_422_service(client, fake_state):
    fake_state.reject_launch = True
    r = client.post("/api/runs", json=_body())
    assert r.status_code == 422
    assert any(e["field"] == "_service" for e in r.json()["errors"])


def test_listado_hidratado(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    rows = {r["run_id"]: r for r in client.get("/api/runs").json()}
    assert rows["run_active_1"]["status"] == "running"
    assert rows["run_active_1"]["model"] == "mock"
    done = rows["run_done_1"]
    assert done["fps_effective"] == 12.5
    assert done["total_detections"] == 7
    assert done["source_type"] == "image_folder"
    assert done["prompt_set_id"] == "demo_set"


def test_get_run_pass_through_y_404(client):
    assert client.get("/api/runs/run_done_1").json()["summary"]["total_detections"] == 7
    assert client.get("/api/runs/nope").status_code == 404


def test_stop_202(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = client.post("/api/runs/run_active_1/stop")
    assert r.status_code == 202
    assert fake_state.stopped == ["run_active_1"]


def test_row_sin_claves_degrada():
    # Un item del servicio sin run_id/status (payload degradado) no debe tirar KeyError.
    row = _row({})
    assert row["run_id"] is None
    assert row["status"] == "unknown"


def test_listado_hidratado_degrada_sin_500(client, fake_state, monkeypatch):
    fake_state.active_run_id = "run_active_1"

    async def fake_status(run_id):
        return {}  # simula un status hidratado sin run_id/status

    monkeypatch.setattr(client.app.state.backend, "status", fake_status)
    r = client.get("/api/runs")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert all(row["status"] == "unknown" for row in rows)
    assert all(row["run_id"] is None for row in rows)
