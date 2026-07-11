"""Runner: inyeccion de source_id=clip_id en ingest.config (spec 43 SS6).

Cuando el manifiesto trae `clip_id`, el runner debe inyectarlo como
`ingest.config.source_id` en la config que le manda al media-plane, sin pisar
un `source_id` explicito si ya viene en la config (el explicito gana). Cubre
las dos ramas del runner (DBE-replay y live) porque la inyeccion pasa por
`loader(media_run.config)` en ambas.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment
from eovrt_webconsole.run_backend import RunBackend
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service

NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)

CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _build_manifest(*, clip_id: str | None) -> ExperimentManifest:
    data = {
        "schema_version": "experiment.manifest.v1",
        "slug": "d1",
        "runs": {
            "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
            "control": {"service": "http://control", "config": "control.yaml", "mode": "replay"},
        },
        "sequencing": "media_first",
        "report": {},
        "frozen": {},
    }
    if clip_id is not None:
        data["clip_id"] = clip_id
    return ExperimentManifest.model_validate(data)


class RecordingMediaBackend:
    def __init__(self, backend: RunBackend, terminal_status: str = "succeeded") -> None:
        self._backend = backend
        self._terminal_status = terminal_status

    async def launch(self, run_request: dict) -> str:
        return await self._backend.launch(run_request)

    async def status(self, run_id: str) -> dict:
        return {
            "run_id": run_id,
            "status": self._terminal_status,
            "summary": {"detections_path": f"runs/{run_id}/detections.jsonl"},
        }


@pytest.fixture
def media_backend():
    state = FakeState()
    transport = httpx.ASGITransport(app=make_fake_service(state))
    http = httpx.AsyncClient(base_url="http://media", transport=transport)
    return RunBackend(http), state


@pytest.fixture
def control_backend():
    state = FakeControlState()
    transport = httpx.ASGITransport(app=make_fake_control_service(state))
    http = httpx.AsyncClient(base_url="http://control", transport=transport)
    return ControlPlaneBackend(http), state


async def test_clip_id_injects_source_id_into_ingest_config(media_backend, control_backend):
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_config = {"ingest": {"plugin": "video_file", "config": {"path": "clip.mp4"}},
                     "prompts": {"set_inline": {}, "active_ids": None}}

    def load_config(path: str) -> dict:
        if path == "media.yaml":
            return dict(media_config)
        if path == "control.yaml":
            return dict(CONTROL_CONFIG)
        raise AssertionError(path)

    result = await run_experiment(
        _build_manifest(clip_id="clip_0007"),
        media_backend=RecordingMediaBackend(real_media),
        control_backend=real_control,
        now=NOW,
        load_config=load_config,
    )

    assert result.ok
    assert media_state.launched[0]["ingest"]["config"]["source_id"] == "clip_0007"
    # la config original devuelta por el loader no debe mutarse in-place
    assert "source_id" not in media_config["ingest"]["config"]


async def test_explicit_source_id_wins_over_clip_id(media_backend, control_backend):
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_config = {
        "ingest": {"plugin": "video_file", "config": {"path": "clip.mp4", "source_id": "explicit"}},
        "prompts": {"set_inline": {}, "active_ids": None},
    }

    def load_config(path: str) -> dict:
        if path == "media.yaml":
            return dict(media_config)
        if path == "control.yaml":
            return dict(CONTROL_CONFIG)
        raise AssertionError(path)

    result = await run_experiment(
        _build_manifest(clip_id="clip_0007"),
        media_backend=RecordingMediaBackend(real_media),
        control_backend=real_control,
        now=NOW,
        load_config=load_config,
    )

    assert result.ok
    assert media_state.launched[0]["ingest"]["config"]["source_id"] == "explicit"


async def test_no_clip_id_leaves_ingest_config_untouched(media_backend, control_backend):
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_config = {"ingest": {"plugin": "video_file", "config": {"path": "clip.mp4"}},
                     "prompts": {"set_inline": {}, "active_ids": None}}

    def load_config(path: str) -> dict:
        if path == "media.yaml":
            return dict(media_config)
        if path == "control.yaml":
            return dict(CONTROL_CONFIG)
        raise AssertionError(path)

    result = await run_experiment(
        _build_manifest(clip_id=None),
        media_backend=RecordingMediaBackend(real_media),
        control_backend=real_control,
        now=NOW,
        load_config=load_config,
    )

    assert result.ok
    assert "source_id" not in media_state.launched[0]["ingest"]["config"]
