"""Runner: evaluacion temporal post-replay contra ground truth (spec 43 SS6).

Cuando el manifiesto trae `ground_truth`, el runner debe invocar el callable
`evaluate_temporal` inyectado (produccion: `eovrt-control evaluate-alerts` por
subproceso, ver `_default_evaluate_temporal`) DESPUES de que consolidate_experiment
arme el consolidado, con los paths correctos, y el resultado debe quedar
disponible para el reporte via `control/temporal_evaluation.json`. Si no hay
`ground_truth`, el paso se saltea entero (comportamiento actual intacto).
"""
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

MEDIA_CONFIG = {"ingest": {"plugin": "video_file", "config": {"path": "clip.mp4"}},
                 "prompts": {"set_inline": {}, "active_ids": None}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _load_config(path: str) -> dict:
    if path == "media.yaml":
        return dict(MEDIA_CONFIG)
    if path == "control.yaml":
        return dict(CONTROL_CONFIG)
    raise AssertionError(f"config no esperada: {path}")


def _build_manifest(*, clip_id: str | None = None, ground_truth: str | None = None) -> ExperimentManifest:
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
    if ground_truth is not None:
        data["ground_truth"] = ground_truth
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


def _write_media_artifacts(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": "media.summary.v2", "run_id": run_dir.name,
               "status": "succeeded", "source_clock": "none"}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "metrics.jsonl").write_text("", encoding="utf-8")
    (run_dir / "detections.jsonl").write_text("", encoding="utf-8")


def _write_control_artifacts(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": "control.summary.v1", "control_run_id": run_dir.name}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "alerts.jsonl").write_text('{"alert_id": "a1"}\n', encoding="utf-8")
    (run_dir / "pattern_events.jsonl").write_text('{"event": "cr01"}\n', encoding="utf-8")


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


async def test_ground_truth_triggers_evaluation_with_expected_paths(
    tmp_path, media_backend, control_backend
):
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_dir = tmp_path / "artifacts" / "media"
    control_dir = tmp_path / "artifacts" / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir)

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        return media_dir if plane == "media" else control_dir

    gt_path = tmp_path / "gt" / "clip_0007.gt.json"
    gt_path.parent.mkdir(parents=True, exist_ok=True)
    gt_path.write_text("{}", encoding="utf-8")

    calls: list[tuple] = []

    def fake_evaluate_temporal(alerts_path, ground_truth_path, output_path,
                                detections_path, patterns_path):
        calls.append((alerts_path, ground_truth_path, output_path,
                       detections_path, patterns_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = {"schema_version": "control.eval.temporal.v1", "scenario_id": "clip_0007",
                   "recall": 0.8, "precision": 0.9, "f1": 0.85,
                   "avg_latency_ms_from_episode_start": 1500.0}
        output_path.write_text(json.dumps(result), encoding="utf-8")
        return result

    dest_root = tmp_path / "runs"

    result = await run_experiment(
        _build_manifest(clip_id="clip_0007", ground_truth=str(gt_path)),
        media_backend=RecordingMediaBackend(real_media),
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        resolve_run_dir=resolve_run_dir,
        dest_root=dest_root,
        evaluate_temporal=fake_evaluate_temporal,
    )

    assert result.ok
    assert len(calls) == 1
    alerts_path, ground_truth_path, output_path, detections_path, patterns_path = calls[0]

    consolidated_dir = Path(result.consolidated_dir)
    assert alerts_path == consolidated_dir / "control" / "alerts.jsonl"
    assert ground_truth_path == gt_path
    assert output_path == consolidated_dir / "control" / "temporal_evaluation.json"
    assert detections_path == media_dir / "detections.jsonl"
    assert patterns_path == consolidated_dir / "control" / "pattern_events.jsonl"

    # el resultado quedo persistido y disponible para el reporte
    assert output_path.is_file()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["recall"] == 0.8

    # el reporte liga clip_id / ground_truth (trazabilidad spec 43 SS6)
    report = json.loads((consolidated_dir / "report" / "report.json").read_text(encoding="utf-8"))
    assert report["identificacion"]["clip_id"] == "clip_0007"
    assert report["identificacion"]["ground_truth_path"] == str(gt_path)


async def test_no_ground_truth_skips_evaluation(tmp_path, media_backend, control_backend):
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_dir = tmp_path / "artifacts" / "media"
    control_dir = tmp_path / "artifacts" / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir)

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        return media_dir if plane == "media" else control_dir

    calls: list = []

    def fake_evaluate_temporal(*args):
        calls.append(args)
        return None

    dest_root = tmp_path / "runs"

    result = await run_experiment(
        _build_manifest(),
        media_backend=RecordingMediaBackend(real_media),
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        resolve_run_dir=resolve_run_dir,
        dest_root=dest_root,
        evaluate_temporal=fake_evaluate_temporal,
    )

    assert result.ok
    assert calls == []
    consolidated_dir = Path(result.consolidated_dir)
    assert not (consolidated_dir / "control" / "temporal_evaluation.json").is_file()

    report = json.loads((consolidated_dir / "report" / "report.json").read_text(encoding="utf-8"))
    assert report["identificacion"]["clip_id"] is None
    assert report["identificacion"]["ground_truth_path"] is None


async def test_evaluation_failure_is_protected(tmp_path, media_backend, control_backend, caplog):
    """Si evaluate_temporal explota, el paso post-run sigue protegido (misma
    garantia que la consolidacion/reporte -- ver test_runner_report_wiring.py)."""
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    media_dir = tmp_path / "artifacts" / "media"
    control_dir = tmp_path / "artifacts" / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir)

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        return media_dir if plane == "media" else control_dir

    def boom_evaluate_temporal(*args):
        raise RuntimeError("boom: evaluate-alerts crasheo")

    dest_root = tmp_path / "runs"

    with caplog.at_level(logging.WARNING, logger="eovrt_webconsole.experiment.runner"):
        result = await run_experiment(
            _build_manifest(ground_truth="gt/clip.gt.json"),
            media_backend=RecordingMediaBackend(real_media),
            control_backend=real_control,
            now=NOW,
            load_config=_load_config,
            resolve_run_dir=resolve_run_dir,
            dest_root=dest_root,
            evaluate_temporal=boom_evaluate_temporal,
        )

    assert result.ok
    # todo el paso post-run (consolidacion + evaluacion + reporte) es una
    # unidad protegida: si la evaluacion explota, se pierde el reporte
    # tambien (no hay commit parcial), igual que el resto de los fallos
    # de este bloque (ver test_post_run_failure_is_protected).
    assert result.consolidated_dir is None
    assert result.report_path is None
    assert any("post-run" in record.message for record in caplog.records)
