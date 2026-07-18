import httpx
import pytest

from eovrt_webconsole.run_backend import (
    PreviewConflict,
    RunActive,
    RunBackend,
    RunBusy,
    RunNotFinished,
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
    assert exc.value.reason is None


async def test_launch_busy_reason_preview_active(backend, state):
    # F1: RunBusy debe transportar el "reason" que manda el media-plane
    # (p.ej. "preview_active") en vez de descartarlo.
    state.active_run_id = "run_activo_previo"
    state.launch_busy_reason = "preview_active"
    with pytest.raises(RunBusy) as exc:
        await backend.launch(RUN_REQUEST)
    assert exc.value.active_run_id == "run_activo_previo"
    assert exc.value.reason == "preview_active"


async def test_launch_rechazado_422(backend):
    with pytest.raises(ServiceRejected):
        await backend.launch({**RUN_REQUEST, "model": {"ref": "x"}})


async def test_status_activo_y_terminado(backend, state):
    state.active_run_id = "run_active_1"
    active = await backend.status("run_active_1")
    assert active == {"run_id": "run_active_1", "status": "running", "live": True,
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


async def test_evaluate_ok(backend, state):
    result = await backend.evaluate("run_done_1")
    assert result["mAP50"] == 0.47
    assert result["bench_split"] == "bench_v2_test"
    assert "run_done_1" in state.eval_results


async def test_evaluate_run_en_curso_es_run_not_finished(backend, state):
    state.active_run_id = "run_x"
    with pytest.raises(RunNotFinished):
        await backend.evaluate("run_x")


async def test_evaluate_no_bench_es_service_rejected(backend, state):
    state.evaluate_not_bench = True
    with pytest.raises(ServiceRejected):
        await backend.evaluate("run_done_1")


async def test_evaluate_desconocido_es_unknown_run(backend):
    with pytest.raises(UnknownRun):
        await backend.evaluate("nope")


async def test_evaluate_servicio_no_listo_503(backend, state):
    state.ready = False
    with pytest.raises(ServiceUnavailable):
        await backend.evaluate("run_done_1")


async def test_get_evaluation_404_y_ok(backend, state):
    with pytest.raises(UnknownRun):
        await backend.get_evaluation("run_done_1")
    await backend.evaluate("run_done_1")
    result = await backend.get_evaluation("run_done_1")
    assert result["cr01_detection_recall"] == 0.64


async def test_dropped_passthrough(backend, state):
    state.dropped["run-1"] = [
        {"reason": "queue_full", "unit_id": "u0", "frame_index": 0},
        {"reason": "queue_full", "unit_id": "u1", "frame_index": 1},
        {"reason": "backpressure", "unit_id": "u2", "frame_index": 2},
    ]
    result = await backend.dropped("run-1", page=1, page_size=2)
    assert result["total"] == 3 and len(result["items"]) == 2


async def test_dropped_desconocido(backend):
    with pytest.raises(UnknownRun):
        await backend.dropped("nope")


async def test_delete_ok(backend, state):
    await backend.delete("run_done_1")
    assert state.deleted == ["run_done_1"]


async def test_delete_404_desconocido(backend):
    with pytest.raises(UnknownRun):
        await backend.delete("nope")


async def test_delete_409_run_activo(backend, state):
    state.active_run_id = "run_x"
    with pytest.raises(RunActive) as exc:
        await backend.delete("run_x")
    assert "activo" in exc.value.detail


async def test_preview_start_ok(backend, state):
    result = await backend.preview_start({"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert result["preview_id"] == "pv_1"
    assert state.preview_started[0]["mode"] == "raw"


async def test_preview_start_409_run_activo(backend, state):
    state.preview_conflict = {"detail": "ocupado", "reason": "run_active", "active_run_id": "run_9"}
    with pytest.raises(PreviewConflict) as exc:
        await backend.preview_start({"mode": "raw", "ingest": {"plugin": "rtsp", "config": {}}})
    assert exc.value.body["reason"] == "run_active"


async def test_preview_status_y_stop(backend, state):
    state.preview_status = "streaming"
    assert (await backend.preview_status())["status"] == "streaming"
    await backend.preview_stop()
    assert state.preview_stopped == 1
