import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import make_fake_service
from tests.test_orchestrator import make_fake_compose


@pytest.fixture
def state():
    return {"ps": {"mp-mock": "exited"}}


@pytest.fixture
def platform_client(state, fake_state, repo, tmp_path):
    settings = ConsoleSettings(
        service_url="http://ignored", repo_root=repo, frozen_set_ids=frozenset({"frozen_set"}),
        compose_dir=tmp_path, switch_timeout_seconds=1.0,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    app = create_app(settings, service_transport=transport, compose_runner=make_fake_compose(state))
    with TestClient(app) as client:
        yield client


def test_static_mode_501(client):
    # `client` es el fixture existente de conftest (sin compose_dir)
    assert client.get("/api/platform/instances").status_code == 501
    assert client.post("/api/platform/instances/mp-mock/activate").status_code == 501
    assert client.post("/api/platform/stop").status_code == 501


def test_instances_lista_fleet(platform_client):
    rows = {r["name"]: r for r in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["state"] == "exited"
    assert rows["mp-gdino-tiny"]["state"] == "absent"
    assert all(r["is_target"] is False for r in rows.values())


def test_activate_ok_y_target_operativo(platform_client, fake_state):
    r = platform_client.post("/api/platform/instances/mp-mock/activate")
    assert r.status_code == 200
    assert r.json() == {"target": "mp-mock", "model_ref": "mock"}
    rows = {x["name"]: x for x in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["is_target"] is True and rows["mp-mock"]["ready"] is True
    # el target dinámico responde por los endpoints existentes:
    assert platform_client.get("/api/target").json()["ready"] is True


def test_activate_desconocida_404(platform_client):
    assert platform_client.post("/api/platform/instances/nope/activate").status_code == 404


def test_activate_con_run_activo_409(platform_client, fake_state):
    platform_client.post("/api/platform/instances/mp-mock/activate")
    fake_state.active_run_id = "run_x"
    r = platform_client.post("/api/platform/instances/mp-gdino-tiny/activate")
    assert r.status_code == 409
    assert r.json()["run_id"] == "run_x"


def test_activate_readyz_timeout_504(platform_client, fake_state):
    fake_state.ready = False
    r = platform_client.post("/api/platform/instances/mp-mock/activate")
    assert r.status_code == 504
    assert r.json()["step"] == "readyz"


def test_stop_apaga_el_target(platform_client):
    platform_client.post("/api/platform/instances/mp-mock/activate")
    r = platform_client.post("/api/platform/stop")
    assert r.status_code == 200 and r.json() == {"target": None}
    rows = {x["name"]: x for x in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["state"] == "exited"
