from pathlib import Path

from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings


def _settings(tmp_path: Path) -> ConsoleSettings:
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "experiments").mkdir(exist_ok=True)
    return ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(tmp_path)})


def test_health_ok(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_target_ready(client):
    r = client.get("/api/target")
    assert r.status_code == 200
    body = r.json()
    assert body["healthy"] is True
    assert body["ready"] is True
    assert body["model"]["ref"] == "mock"
    assert body["model"]["thresholds"]["box"] == 0.35  # read-only para la UI


def test_target_no_ready(client, fake_state):
    fake_state.ready = False
    body = client.get("/api/target").json()
    assert body["healthy"] is True
    assert body["ready"] is False
    assert body["model"] is None


def test_spa_estatica_montada(tmp_path):
    settings = _settings(tmp_path)
    dist = tmp_path / "webconsole" / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>console</body></html>")
    with TestClient(create_app(settings)) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "console" in r.text
        # /api sigue teniendo precedencia sobre el mount estático
        assert client.get("/api/health").json() == {"status": "ok"}


def test_sin_dist_no_rompe(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/api/health").status_code == 200
