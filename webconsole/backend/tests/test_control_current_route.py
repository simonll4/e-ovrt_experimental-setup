"""GET /api/control/current: passthrough del estado vivo del control-plane
(riesgo activo en vivo). Ver control_backend.current() -> GET /api/runs/current
del control-plane; 404 si no hay corrida activa, 502 si el control-plane esta
caido (mismo patron que get_experiment_alerts en routers/experiments.py)."""
from __future__ import annotations

from eovrt_webconsole.experiment.control_backend import ServiceUnavailable


def test_control_current_200_proxya_los_patrones_del_fake(two_plane_client, control_state):
    control_state.active_run_id = "control_run_live_1"
    control_state.subscribed = True
    control_state.patterns = [
        {
            "pattern_id": "CR-01",
            "condition_id": "CR-01",
            "severity": "high",
            "subject_key": "CR-01:169.254.31.137",
            "state": "sustained",
            "since_timestamp_ms": 1785004249492.94,
            "subjects_in_evidence": 1,
        }
    ]

    r = two_plane_client.get("/api/control/current")

    assert r.status_code == 200
    body = r.json()
    assert body["control_run_id"] == "control_run_live_1"
    assert body["patterns"] == control_state.patterns


def test_control_current_200_lista_vacia_cuando_no_hay_riesgo_activo(
    two_plane_client, control_state
):
    control_state.active_run_id = "control_run_live_2"
    control_state.patterns = []

    r = two_plane_client.get("/api/control/current")

    assert r.status_code == 200
    assert r.json()["patterns"] == []


def test_control_current_404_sin_corrida_activa(two_plane_client, control_state):
    control_state.active_run_id = None

    r = two_plane_client.get("/api/control/current")

    assert r.status_code == 404


def test_control_current_502_service_unavailable(two_plane_client):
    async def boom():
        raise ServiceUnavailable("control-plane caido")

    two_plane_client.app.state.control_backend.current = boom

    r = two_plane_client.get("/api/control/current")

    assert r.status_code == 502
