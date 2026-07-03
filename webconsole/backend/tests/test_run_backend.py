import httpx
import pytest

from eovrt_webconsole.run_backend import (
    RunBackend,
    RunBusy,
    ServiceRejected,
    ServiceUnavailable,
    UnknownRun,
)
from tests.fake_service import FakeState, make_fake_service

RUN_REQUEST = {
    "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
    "prompts": {"set_inline": {"id": "demo_set", "classes": []}, "active_ids": None},
    "run": {"save_annotated_video": False, "save_previews": True},
}


@pytest.fixture
def state() -> FakeState:
    return FakeState()


@pytest.fixture
async def backend(state: FakeState):
    transport = httpx.ASGITransport(app=make_fake_service(state))
    async with httpx.AsyncClient(transport=transport, base_url="http://service.fake") as http:
        yield RunBackend(http)


async def test_launch_ok(backend, state):
    run_id = await backend.launch(RUN_REQUEST)
    assert run_id == "run_active_1"
    assert state.launched == [RUN_REQUEST]


async def test_launch_busy(backend, state):
    state.active_run_id = "run_activo_previo"
    with pytest.raises(RunBusy) as exc:
        await backend.launch(RUN_REQUEST)
    assert exc.value.active_run_id == "run_activo_previo"


async def test_launch_rechazado_422(backend):
    with pytest.raises(ServiceRejected):
        await backend.launch({**RUN_REQUEST, "model": {"ref": "x"}})


async def test_status_activo_y_terminado(backend, state):
    state.active_run_id = "run_active_1"
    active = await backend.status("run_active_1")
    assert active == {"run_id": "run_active_1", "status": "running",
                      "started_at": "2026-07-03T12:00:00+00:00", "model": "mock"}
    done = await backend.status("run_done_1")
    assert done["summary"]["fps_effective"] == 12.5


async def test_status_desconocido(backend):
    with pytest.raises(UnknownRun):
        await backend.status("nope")


async def test_stop_y_list(backend, state):
    state.active_run_id = "run_active_1"
    await backend.stop("run_active_1")
    assert state.stopped == ["run_active_1"]
    runs = await backend.list_runs()
    assert {r["run_id"] for r in runs} == {"run_active_1", "run_done_1"}


async def test_detections_paginadas(backend):
    page = await backend.detections("run_done_1", page=1, page_size=2)
    assert page["total"] == 5 and len(page["items"]) == 2


async def test_stop_servicio_no_listo_503(backend, state):
    state.active_run_id = "run_active_1"
    state.ready = False
    with pytest.raises(ServiceUnavailable):
        await backend.stop("run_active_1")


async def test_status_servicio_no_listo_503(backend, state):
    state.active_run_id = "run_active_1"
    state.ready = False
    with pytest.raises(ServiceUnavailable):
        await backend.status("run_active_1")


async def test_launch_servicio_no_listo_503(backend, state):
    state.ready = False
    with pytest.raises(ServiceUnavailable):
        await backend.launch(RUN_REQUEST)


async def test_servicio_caido():
    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_down),
                                 base_url="http://service.fake") as http:
        with pytest.raises(ServiceUnavailable):
            await RunBackend(http).model()
