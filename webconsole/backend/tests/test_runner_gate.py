"""Gate de la Tarea 5: runner end-to-end sobre los dos fakes, en los dos modos.

Este archivo es el gate (spec 44 SS3): corre run_experiment(...) completo
contra los fakes de ambos planos (tests/fake_service.py y
tests/fake_control_service.py), una vez en DBE-replay y otra en live, y
asserta la orquestacion completa (orden, run_ids, ok) y la propagacion del
experiment_id a los dos payloads. Una mutacion en runner.py que rompa el
orden de la rama live o deje de inyectar el experiment_id en el payload del
media debe hacer fallar este archivo (verificado por mutacion, ver
task-5-report.md).

No editamos fake_service.py ni run_backend.py (archivos preexistentes): las
clases Recording* de abajo son el mismo patron de wiring que ya usan
test_runner_dbe_replay.py y test_runner_live.py, duplicado aca para que este
gate sea autocontenido.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment
from eovrt_webconsole.run_backend import RunBackend
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service

NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)

REPLAY_MEDIA_CONFIG = {
    "ingest": {"type": "image_folder", "path": "demo"},
    "prompts": {"ref": "demo_set"},
}
LIVE_MEDIA_CONFIG = {
    "ingest": {"type": "rtsp", "path": "camera1"},
    "prompts": {"ref": "eind_v1"},
}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _load_config_for(media_config: dict):
    """Fabrica un load_config que devuelve media_config para media.yaml."""

    def _load(path: str) -> dict:
        if path == "media.yaml":
            return dict(media_config)
        if path == "control.yaml":
            return dict(CONTROL_CONFIG)
        raise AssertionError(f"config no esperada: {path}")

    return _load


def _build_manifest(*, mode: str, sequencing: str) -> ExperimentManifest:
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "gate",
            "runs": {
                "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
                "control": {"service": "http://control", "config": "control.yaml", "mode": mode},
            },
            "sequencing": sequencing,
            "report": {},
            "frozen": {},
        }
    )


def _media_backend():
    state = FakeState()
    transport = httpx.ASGITransport(app=make_fake_service(state))
    http = httpx.AsyncClient(base_url="http://media", transport=transport)
    return RunBackend(http), state


def _control_backend():
    state = FakeControlState()
    transport = httpx.ASGITransport(app=make_fake_control_service(state))
    http = httpx.AsyncClient(base_url="http://control", transport=transport)
    return ControlPlaneBackend(http), state


class RecordingMediaBackend:
    """Envuelve RunBackend y registra el orden de eventos (launch/status).

    El fake real no transiciona un run recien lanzado a un estado terminal
    por si solo (siempre 'running'), asi que status() devuelve directamente
    un resumen terminal; lo que importa para el gate es el orden en que se
    llaman launch/status/control_launch, no el polling en si (eso ya lo
    cubren test_runner_dbe_replay.py / test_runner_live.py).
    """

    def __init__(self, backend: RunBackend, events: list, terminal_status: str = "succeeded") -> None:
        self._backend = backend
        self._events = events
        self._terminal_status = terminal_status

    async def launch(self, run_request: dict) -> str:
        run_id = await self._backend.launch(run_request)
        self._events.append(("media_launch", run_id))
        return run_id

    async def status(self, run_id: str) -> dict:
        self._events.append(("media_status", run_id))
        return {
            "run_id": run_id,
            "status": self._terminal_status,
            "summary": {"detections_path": f"runs/{run_id}/detections.jsonl"},
        }


class RecordingControlBackend:
    """Envuelve ControlPlaneBackend y registra el orden de eventos.

    'control_subscribed' se agrega cuando el runner llama current() para
    confirmar la suscripcion del BusSource -- la base del assert de orden
    discriminante de la rama live.
    """

    def __init__(self, backend: ControlPlaneBackend, events: list) -> None:
        self._backend = backend
        self._events = events

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        run_id = await self._backend.launch(config, mode=mode, experiment_id=experiment_id)
        self._events.append(("control_launch", mode))
        return run_id

    async def current(self) -> dict:
        result = await self._backend.current()
        self._events.append(("control_subscribed", result.get("subscribed")))
        return result

    async def status(self, control_run_id: str) -> dict:
        return await self._backend.status(control_run_id)


async def test_runner_gate_dbe_replay_end_to_end():
    """Gate DBE-replay: media lanzado -> terminado -> control lanzado (replay), ok, ids propagados."""
    real_media, media_state = _media_backend()
    real_control, control_state = _control_backend()
    control_state.finish_status = "succeeded"

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    result = await run_experiment(
        _build_manifest(mode="replay", sequencing="media_first"),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_load_config_for(REPLAY_MEDIA_CONFIG),
    )

    assert result.ok
    assert result.experiment_id.startswith("exp_")
    assert result.media_run_id and result.control_run_id
    assert result.media_status == "succeeded"
    assert result.control_status == "succeeded"

    # orden: el media debe terminar (status terminal) antes de que se dispare el control
    media_status_idx = events.index(("media_status", result.media_run_id))
    control_launch_idx = events.index(("control_launch", "replay"))
    assert media_status_idx < control_launch_idx, (
        "DBE-replay: el control debe dispararse recien despues de que el media termine"
    )

    # experiment_id: generado y propagado al MISMO valor en los payloads de ambos planos
    media_experiment_id = media_state.launched[0]["experiment_id"]
    control_experiment_id = control_state.received_experiment_id
    assert media_experiment_id == control_experiment_id == result.experiment_id
    assert control_state.received_mode == "replay"


async def test_runner_gate_live_end_to_end():
    """Gate live: control lanzado + suscripto ANTES del media, bus habilitado, ok, ids propagados."""
    real_media, media_state = _media_backend()
    real_control, control_state = _control_backend()
    control_state.finish_status = "succeeded"

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    result = await run_experiment(
        _build_manifest(mode="live", sequencing="control_first"),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_load_config_for(LIVE_MEDIA_CONFIG),
    )

    assert result.ok
    assert result.experiment_id.startswith("exp_")
    assert result.media_run_id and result.control_run_id
    assert result.media_status == "succeeded"
    assert result.control_status == "succeeded"

    # orden: la confirmacion de suscripcion del control debe preceder al disparo del media
    # (invariante no negociable: PUB/SUB pierde lo publicado antes de la suscripcion)
    subscribed_idx = events.index(("control_subscribed", True))
    media_launch_idx = next(i for i, e in enumerate(events) if e[0] == "media_launch")
    assert subscribed_idx < media_launch_idx, (
        "live: la suscripcion del control debe confirmarse antes de disparar el media"
    )
    assert events[0] == ("control_launch", "live"), "live: el control-plane se dispara primero"

    # bus habilitado en el payload del media (spec 44 SS3 / doc 50 SS5.1)
    assert media_state.launched[0]["bus"]["enabled"] is True

    # experiment_id: generado y propagado al MISMO valor en los payloads de ambos planos
    media_experiment_id = media_state.launched[0]["experiment_id"]
    control_experiment_id = control_state.received_experiment_id
    assert media_experiment_id == control_experiment_id == result.experiment_id
    assert control_state.received_mode == "live"
