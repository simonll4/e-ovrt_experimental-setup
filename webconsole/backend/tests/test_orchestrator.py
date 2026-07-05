import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from eovrt_webconsole.orchestrator import (
    ComposeError,
    ComposeOrchestrator,
    PlatformBusy,
    SwitchFailed,
    TargetManager,
    UnknownInstance,
)
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

CONFIG_JSON = json.dumps({
    "services": {
        "console": {"labels": {}},
        "mp-mock": {"labels": {"eovrt.instance": "true", "eovrt.model_ref": "mock"}},
        # compose puede normalizar labels a lista "k=v": el parser debe tolerar ambas formas
        "mp-gdino-tiny": {"labels": ["eovrt.instance=true", "eovrt.model_ref=grounding-dino/gdino-tiny"]},
    }
})


def make_fake_compose(state: dict):
    """run_cmd fake: sirve config/ps desde `state` y registra up/stop."""
    async def run_cmd(*args: str, cwd: Path):
        verb = args[4]  # docker compose --project-name eovrt <verb> ...
        state.setdefault("calls", []).append(list(args))
        if verb == "config":
            return 0, CONFIG_JSON, ""
        if verb == "ps":
            lines = "\n".join(
                json.dumps({"Service": n, "State": s}) for n, s in state.get("ps", {}).items()
            )
            return 0, lines, ""
        if verb == "up":
            if state.get("fail_up"):
                return 1, "", "boom del daemon"
            state["ps"][args[-1]] = "running"
            return 0, "", ""
        if verb == "stop":
            state["ps"][args[-1]] = "exited"
            return 0, "", ""
        return 1, "", f"verb inesperado: {verb}"
    return run_cmd


@pytest.fixture
def state():
    return {"ps": {"mp-mock": "exited"}}


@pytest.fixture
def orch(state, tmp_path):
    return ComposeOrchestrator(tmp_path, run_cmd=make_fake_compose(state))


async def test_fleet_filtra_por_label_y_tolera_lista(orch):
    fleet = await orch.fleet()
    assert fleet == {"mp-mock": "mock", "mp-gdino-tiny": "grounding-dino/gdino-tiny"}
    assert "console" not in fleet


async def test_ps_solo_instancias_del_fleet(orch, state):
    state["ps"]["console"] = "running"  # no debe aparecer
    assert await orch.ps() == {"mp-mock": "exited"}


async def test_up_y_stop_pasan_por_compose(orch, state):
    await orch.up("mp-mock")
    assert state["ps"]["mp-mock"] == "running"
    up_call = next(c for c in state["calls"] if "up" in c)
    assert "--no-build" in up_call and "--project-name" in up_call and "eovrt" in up_call
    await orch.stop("mp-mock")
    assert state["ps"]["mp-mock"] == "exited"


async def test_nombre_fuera_del_fleet_es_unknown(orch):
    with pytest.raises(UnknownInstance):
        await orch.up("console")
    with pytest.raises(UnknownInstance):
        await orch.stop("rm -rf")


async def test_error_de_compose_levanta_con_stderr(orch, state):
    state["fail_up"] = True
    with pytest.raises(ComposeError, match="boom del daemon"):
        await orch.up("mp-mock")


@pytest.fixture
def fake_state():
    return FakeState()


@pytest.fixture
def manager(state, fake_state, tmp_path, repo):
    settings = ConsoleSettings(
        service_url="http://ignored", repo_root=repo, frozen_set_ids=frozenset(),
        compose_dir=tmp_path, switch_timeout_seconds=1.0,
    )
    app = FastAPI()
    orch = ComposeOrchestrator(tmp_path, run_cmd=make_fake_compose(state))
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    return TargetManager(app, orch, settings, service_transport=transport, poll_interval=0.01)


async def test_bootstrap_sin_running_deja_target_none(manager):
    await manager.bootstrap()
    assert manager.active is None


async def test_bootstrap_con_una_running_la_adopta(manager, state):
    state["ps"]["mp-mock"] = "running"
    await manager.bootstrap()
    assert manager.active == "mp-mock"


async def test_bootstrap_con_varias_running_deja_target_none(manager, state):
    state["ps"] = {"mp-mock": "running", "mp-gdino-tiny": "running"}
    await manager.bootstrap()
    assert manager.active is None


async def test_switch_apaga_running_levanta_y_espera_ready(manager, state):
    state["ps"] = {"mp-mock": "running", "mp-gdino-tiny": "exited"}
    await manager.bootstrap()
    result = await manager.switch("mp-gdino-tiny")
    assert result == {"target": "mp-gdino-tiny", "model_ref": "grounding-dino/gdino-tiny"}
    assert state["ps"]["mp-mock"] == "exited"
    assert state["ps"]["mp-gdino-tiny"] == "running"
    assert manager.active == "mp-gdino-tiny"


async def test_switch_con_run_activo_es_platform_busy(manager, state, fake_state):
    state["ps"] = {"mp-mock": "running"}
    fake_state.active_run_id = "run_x"
    await manager.bootstrap()
    with pytest.raises(PlatformBusy) as exc:
        await manager.switch("mp-gdino-tiny")
    assert exc.value.run_id == "run_x"


async def test_switch_readyz_timeout_es_switch_failed_sin_target(manager, state, fake_state):
    fake_state.ready = False  # /readyz responde 503 → nunca ready
    await manager.bootstrap()
    with pytest.raises(SwitchFailed) as exc:
        await manager.switch("mp-mock")
    assert exc.value.step == "readyz"
    assert manager.active is None  # sin rollback: estado honesto


async def test_switch_a_target_actual_ready_es_noop(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    calls_before = len(state.get("calls", []))
    await manager.switch("mp-mock")
    verbs = [c[4] for c in state["calls"][calls_before:]]
    assert "up" not in verbs and "stop" not in verbs


async def test_stop_active_apaga_y_deja_none(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    await manager.stop_active()
    assert manager.active is None
    assert state["ps"]["mp-mock"] == "exited"


async def test_instances_shape(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    rows = {r["name"]: r for r in await manager.instances()}
    assert rows["mp-mock"] == {"name": "mp-mock", "model_ref": "mock",
                               "state": "running", "ready": True, "is_target": True}
    assert rows["mp-gdino-tiny"]["state"] == "absent"
    assert rows["mp-gdino-tiny"]["ready"] is False
