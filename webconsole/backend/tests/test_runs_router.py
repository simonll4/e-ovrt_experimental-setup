from eovrt_webconsole.routers.runs import _row
from eovrt_webconsole.run_backend import ServiceUnavailable


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


def test_evaluate_ok(client):
    r = client.post("/api/runs/run_done_1/evaluate")
    assert r.status_code == 200
    body = r.json()
    assert body["mAP50"] == 0.47
    assert body["bench_split"] == "bench_v2_test"


def test_evaluate_409_run_en_curso(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = client.post("/api/runs/run_active_1/evaluate")
    assert r.status_code == 409
    assert "detail" in r.json()


def test_evaluate_422_no_bench_va_como_service(client, fake_state):
    fake_state.evaluate_not_bench = True
    r = client.post("/api/runs/run_done_1/evaluate")
    assert r.status_code == 422
    assert any(e["field"] == "_service" for e in r.json()["errors"])


def test_evaluate_404_desconocido(client):
    assert client.post("/api/runs/nope/evaluate").status_code == 404


def test_evaluate_502_servicio_caido(client, monkeypatch):
    async def down(_run_id):
        raise ServiceUnavailable("down")

    monkeypatch.setattr(client.app.state.backend, "evaluate", down)
    assert client.post("/api/runs/run_done_1/evaluate").status_code == 502


def test_get_evaluation_404_y_luego_200(client):
    assert client.get("/api/runs/run_done_1/evaluate").status_code == 404
    client.post("/api/runs/run_done_1/evaluate")
    r = client.get("/api/runs/run_done_1/evaluate")
    assert r.status_code == 200
    assert r.json()["mAP50"] == 0.47


def test_listado_trae_flags_de_evaluacion(client):
    rows = {r["run_id"]: r for r in client.get("/api/runs").json()}
    assert rows["run_done_1"]["bench_split"] == "bench_v2_test"
    assert rows["run_done_1"]["evaluated"] is False


def test_get_run_passthrough_trae_bench_split(client):
    body = client.get("/api/runs/run_done_1").json()
    assert body["bench_split"] == "bench_v2_test"
    assert body["evaluated"] is False


def test_listado_incluye_live_y_topology(client):
    rows = client.get("/api/runs").json()
    by_id = {r["run_id"]: r for r in rows}
    # el fake declara un run terminado con run_descriptor two_node
    assert by_id["run_done_1"]["live"] is False
    assert by_id["run_done_1"]["topology"] == "two_node"


def test_delete_run_ok_ambos_planos(two_plane_client, fake_state, control_state):
    control_state.runs_index = [
        {"control_run_id": "ctrl-1", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-1"] = []

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 204
    assert fake_state.deleted == ["run_done_1"]
    assert control_state.deleted == ["ctrl-1"]


def test_delete_run_sin_control_correlacionado(two_plane_client, fake_state):
    r = two_plane_client.delete("/api/runs/run_done_1")
    assert r.status_code == 204
    assert fake_state.deleted == ["run_done_1"]


def test_delete_404_desconocido_en_ambos_planos(two_plane_client):
    assert two_plane_client.delete("/api/runs/nope").status_code == 404


def test_delete_409_run_activo_en_media(two_plane_client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = two_plane_client.delete("/api/runs/run_active_1")
    assert r.status_code == 409


def test_delete_409_run_activo_en_control(two_plane_client, control_state):
    control_state.runs_index = [
        {"control_run_id": "ctrl-2", "status": "running", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.active_run_id = "ctrl-2"

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 409


def test_delete_reintento_idempotente_tras_fallo_parcial(two_plane_client, fake_state, control_state, monkeypatch):
    from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable

    control_state.runs_index = [
        {"control_run_id": "ctrl-3", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-3"] = []

    original_delete = two_plane_client.app.state.control_backend.delete
    call_count = {"n": 0}

    async def flaky_delete(control_run_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ControlServiceUnavailable("caído")
        return await original_delete(control_run_id)

    monkeypatch.setattr(two_plane_client.app.state.control_backend, "delete", flaky_delete)

    r1 = two_plane_client.delete("/api/runs/run_done_1")
    assert r1.status_code == 207
    assert "control" in r1.json()["errors"]
    assert fake_state.deleted == ["run_done_1"]  # el lado media sí se borró

    monkeypatch.setattr(two_plane_client.app.state.control_backend, "delete", original_delete)
    r2 = two_plane_client.delete("/api/runs/run_done_1")
    assert r2.status_code == 204
    assert control_state.deleted == ["ctrl-3"]


def test_delete_falla_media_control_ok(two_plane_client, fake_state, control_state, monkeypatch):
    control_state.runs_index = [
        {"control_run_id": "ctrl-4", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-4"] = []

    async def media_down(_run_id):
        raise ServiceUnavailable("caído")

    monkeypatch.setattr(two_plane_client.app.state.backend, "delete", media_down)

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 207
    assert "media" in r.json()["errors"]
    assert control_state.deleted == ["ctrl-4"]  # el lado control sí se borró


def test_delete_falla_ambos_lados(two_plane_client, fake_state, control_state, monkeypatch):
    from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable

    control_state.runs_index = [
        {"control_run_id": "ctrl-5", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-5"] = []

    async def media_down(_run_id):
        raise ServiceUnavailable("caído media")

    async def control_down(_control_run_id):
        raise ControlServiceUnavailable("caído control")

    monkeypatch.setattr(two_plane_client.app.state.backend, "delete", media_down)
    monkeypatch.setattr(two_plane_client.app.state.control_backend, "delete", control_down)

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 207
    errors = r.json()["errors"]
    assert "media" in errors
    assert "control" in errors
