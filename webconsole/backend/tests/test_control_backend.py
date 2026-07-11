import httpx
import pytest

from eovrt_webconsole.experiment.control_backend import (
    ControlPlaneBackend,
    RunBusy,
    ServiceRejected,
    ServiceUnavailable,
    UnknownRun,
)
from tests.fake_control_service import FakeControlState, make_fake_control_service


@pytest.fixture
def control_backend():
    state = FakeControlState()
    transport = httpx.ASGITransport(app=make_fake_control_service(state))
    http = httpx.AsyncClient(base_url="http://control", transport=transport)
    return ControlPlaneBackend(http), state


async def test_launch_live_returns_control_run_id_and_subscribed(control_backend):
    backend, state = control_backend
    run_id = await backend.launch({"input": {"type": "bus"}}, mode="live", experiment_id="exp-1")
    assert run_id
    current = await backend.current()
    assert current["subscribed"] is True   # el 201 de live implica suscripto


async def test_launch_conflict_raises_run_busy(control_backend):
    backend, state = control_backend
    state.active_run_id = "otro"
    with pytest.raises(RunBusy):
        await backend.launch({"input": {"type": "bus"}}, mode="live", experiment_id="x")


async def test_launch_replay_records_mode_and_experiment_id(control_backend):
    backend, state = control_backend
    run_id = await backend.launch({"input": {"type": "file"}}, mode="replay", experiment_id="exp-2")
    assert run_id
    assert state.received_mode == "replay"
    assert state.received_experiment_id == "exp-2"


async def test_launch_rejected_422(control_backend):
    backend, state = control_backend
    state.reject_launch = True
    with pytest.raises(ServiceRejected):
        await backend.launch({"input": {"type": "bus"}}, mode="live", experiment_id="x")


async def test_status_desconocido(control_backend):
    backend, _ = control_backend
    with pytest.raises(UnknownRun):
        await backend.status("nope")


async def test_status_ok(control_backend):
    backend, _ = control_backend
    run_id = await backend.launch({"input": {"type": "file"}}, mode="replay", experiment_id="exp-3")
    status = await backend.status(run_id)
    assert status["control_run_id"] == run_id


async def test_alerts_y_config(control_backend):
    backend, _ = control_backend
    run_id = await backend.launch({"input": {"type": "file"}}, mode="replay", experiment_id="exp-4")
    alerts = await backend.alerts(run_id)
    assert alerts == []
    config = await backend.config()
    assert "effective_config" in config


async def test_servicio_caido():
    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_down),
                                 base_url="http://control") as http:
        with pytest.raises(ServiceUnavailable):
            await ControlPlaneBackend(http).config()
