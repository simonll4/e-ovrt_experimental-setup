"""La evidencia consolidada sigue navegable con un manager recién iniciado."""

import json

import pytest


@pytest.fixture
def historical(repo):
    directory = repo / "runs" / "exp_historical"
    (directory / "report").mkdir(parents=True)
    (directory / "control").mkdir()
    (directory / "manifest.effective.yaml").write_text("slug: historical\n")
    (directory / "report/report.json").write_text(json.dumps({
        "identificacion": {
            "experiment_id": "exp_historical",
            "media_run_id": "media_historical",
            "control_run_id": "control_historical",
            "fecha_inicio": "2026-07-25T19:57:01Z",
        },
        "resultados": [{"name": "G2A", "value": 12.5, "unit": "ms"}],
    }))
    (directory / "control/alerts.jsonl").write_text(
        '{"alert_id": "alert_1", "condition_id": "CR-01", "severity": "high"}\n'
    )
    return directory


def test_history_detail_report_and_alerts_survive_empty_manager(client, historical):
    before = {p: p.read_bytes() for p in historical.rglob("*") if p.is_file()}
    assert client.app.state.experiment_manager.get("exp_historical") is None
    detail = client.get("/api/experiments/exp_historical")
    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"
    assert detail.json()["slug"] == "historical"
    assert detail.json()["media_run_id"] == "media_historical"
    assert detail.json()["control_run_id"] == "control_historical"
    report = client.get("/api/experiments/exp_historical/report")
    assert report.status_code == 200
    assert report.json()["resultados"][0]["value"] == 12.5
    alerts = client.get("/api/experiments/exp_historical/alerts")
    assert alerts.status_code == 200
    assert alerts.json()[0]["alert_id"] == "alert_1"
    assert client.get("/api/experiments/current").status_code == 404
    assert client.app.state.experiment_manager.get("exp_historical") is None
    assert before == {p: p.read_bytes() for p in historical.rglob("*") if p.is_file()}


def test_live_state_takes_priority_over_disk(client, historical):
    manager = client.app.state.experiment_manager
    manager._states["exp_historical"] = {"experiment_id": "exp_historical", "status": "running"}
    assert client.get("/api/experiments/exp_historical").json()["status"] == "running"


def test_no_report_does_not_invent_success(client, historical):
    (historical / "report/report.json").unlink()
    assert client.get("/api/experiments/exp_historical").status_code == 404


def test_empty_alert_file_is_valid_evidence(client, historical):
    (historical / "control/alerts.jsonl").write_text("")
    response = client.get("/api/experiments/exp_historical/alerts")
    assert response.status_code == 200
    assert response.json() == []


def test_missing_alert_file_is_not_zero_alerts(client, historical):
    (historical / "control/alerts.jsonl").unlink()
    assert client.get("/api/experiments/exp_historical/alerts").status_code == 404


@pytest.mark.parametrize("payload", ["{", "[]", '{"identificacion": {"experiment_id": "other"}}'])
def test_invalid_report_is_explicit_error(client, historical, payload):
    (historical / "report/report.json").write_text(payload)
    assert client.get("/api/experiments/exp_historical").status_code == 500


def test_corrupt_alerts_are_not_hidden(client, historical):
    (historical / "control/alerts.jsonl").write_text('{"alert_id": "valid"}\ninvalid\n')
    assert client.get("/api/experiments/exp_historical/alerts").status_code == 500


@pytest.mark.parametrize("relative,endpoint", [
    ("report/report.json", ""), ("control/alerts.jsonl", "/alerts"),
])
def test_artifact_symlink_cannot_escape_consolidated_directory(
    client, historical, tmp_path, relative, endpoint,
):
    target = tmp_path / "outside.json"
    artifact = historical / relative
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    artifact.symlink_to(target)
    assert client.get(f"/api/experiments/exp_historical{endpoint}").status_code == 404


def test_experiment_directory_symlink_cannot_escape_runs(client, repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "runs").mkdir(exist_ok=True)
    (repo / "runs/exp_escape").symlink_to(outside, target_is_directory=True)
    assert client.get("/api/experiments/exp_escape").status_code == 404
