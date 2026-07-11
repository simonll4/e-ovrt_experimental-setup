"""Runner: paso final post-run (consolidar + reportar), spec 44 SS4 Tarea 4."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment
from eovrt_webconsole.run_backend import RunBackend
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service

NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)

MEDIA_CONFIG = {"ingest": {"type": "image_folder", "path": "demo"}, "prompts": {"ref": "demo_set"}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _load_config(path: str) -> dict:
    if path == "media.yaml":
        return dict(MEDIA_CONFIG)
    if path == "control.yaml":
        return dict(CONTROL_CONFIG)
    raise AssertionError(f"config no esperada: {path}")


def _build_manifest() -> ExperimentManifest:
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
                "control": {
                    "service": "http://control",
                    "config": "control.yaml",
                    "mode": "replay",
                },
            },
            "sequencing": "media_first",
            "report": {},
            "frozen": {},
        }
    )


class RecordingMediaBackend:
    """Envuelve RunBackend (media-plane): status() es terminal de inmediato.

    Misma justificacion que en test_runner_dbe_replay.py: el fake real
    (tests/fake_service.py, preexistente, no se edita) no transiciona un run
    recien lanzado a un estado terminal por si solo.
    """

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


def _write_media_artifacts(run_dir: Path) -> None:
    """Artefactos sinteticos minimos del media-plane (livianos, ADR-014)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "media.summary.v2",
        "run_id": run_dir.name,
        "status": "succeeded",
        "source_clock": "none",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "metrics.jsonl").write_text("", encoding="utf-8")


def _write_control_artifacts(run_dir: Path) -> None:
    """Artefactos sinteticos minimos del control-plane (livianos, ADR-014)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": "control.summary.v1", "control_run_id": run_dir.name}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "alerts.jsonl").write_text("", encoding="utf-8")


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


async def test_post_run_consolidates_and_reports_on_success(tmp_path, media_backend, control_backend):
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media = RecordingMediaBackend(real_media)

    media_dir = tmp_path / "artifacts" / "media"
    control_dir = tmp_path / "artifacts" / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir)

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        assert run_id  # el runner debe pasar el run_id real de cada plano
        return media_dir if plane == "media" else control_dir

    dest_root = tmp_path / "runs"

    result = await run_experiment(
        _build_manifest(),
        media_backend=media,
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        resolve_run_dir=resolve_run_dir,
        dest_root=dest_root,
    )

    assert result.ok
    assert result.consolidated_dir is not None
    consolidated_dir = Path(result.consolidated_dir)
    assert consolidated_dir == dest_root / result.experiment_id
    assert result.report_path is not None
    report_json_path = Path(result.report_path)
    assert report_json_path == consolidated_dir / "report" / "report.json"
    assert report_json_path.is_file()
    assert (consolidated_dir / "report" / "report.md").is_file()

    report = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report["identificacion"]["experiment_id"] == result.experiment_id


async def test_post_run_skipped_on_media_failure(tmp_path, media_backend, control_backend):
    real_media, _media_state = media_backend
    real_control, _control_state = control_backend

    media = RecordingMediaBackend(real_media, terminal_status="failed")

    dest_root = tmp_path / "runs"

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        raise AssertionError("no deberia resolverse ningun run dir si el media fallo")

    result = await run_experiment(
        _build_manifest(),
        media_backend=media,
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        resolve_run_dir=resolve_run_dir,
        dest_root=dest_root,
    )

    assert result.ok is False
    assert result.consolidated_dir is None
    assert result.report_path is None
    assert not dest_root.exists()


async def test_post_run_failure_is_protected(tmp_path, media_backend, control_backend, caplog):
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media = RecordingMediaBackend(real_media)

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        raise RuntimeError("boom: resolucion de run dir rota")

    dest_root = tmp_path / "runs"

    with caplog.at_level(logging.WARNING, logger="eovrt_webconsole.experiment.runner"):
        result = await run_experiment(
            _build_manifest(),
            media_backend=media,
            control_backend=real_control,
            now=NOW,
            load_config=_load_config,
            resolve_run_dir=resolve_run_dir,
            dest_root=dest_root,
        )

    # el run en si tuvo exito (media + control succeeded); el paso post-run
    # protegido no debe tumbarlo aunque el injectable explote.
    assert result.ok
    assert result.consolidated_dir is None
    assert result.report_path is None
    assert any("post-run" in record.message for record in caplog.records)
