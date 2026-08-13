"""Runner: rama DBE-replay (media primero -> control replay), spec 44 SS3."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment
from eovrt_webconsole.run_backend import RunBackend
from tests.fake_control_service import FakeControlState, make_fake_control_service
from tests.fake_service import FakeState, make_fake_service

NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC)

MEDIA_CONFIG = {"ingest": {"type": "image_folder", "path": "demo"}, "prompts": {"ref": "demo_set"}}
CONTROL_CONFIG = {"pattern_set": "cr01_cr02_v2"}


def _load_config(path: str) -> dict:
    if path == "media.yaml":
        return dict(MEDIA_CONFIG)
    if path == "control.yaml":
        return dict(CONTROL_CONFIG)
    raise AssertionError(f"config no esperada: {path}")


def _build_manifest(*, with_distribution: bool = False) -> ExperimentManifest:
    runs = {
        "media": {"service": "http://media", "config": "media.yaml", "mode": "run"},
        "control": {
            "service": "http://control",
            "config": "control.yaml",
            "mode": "replay",
        },
    }
    if with_distribution:
        runs["distribution"] = {
            "service": "http://distribution",
            "config": "distribution.yaml",
            "mode": "replay",
        }
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": runs,
            "sequencing": "media_first",
            "report": {},
            "frozen": {},
        }
    )


def _write_media_artifacts(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"run_id": run_dir.name}), encoding="utf-8"
    )


def _write_control_artifacts(run_dir: Path, *, alerts: list[dict] | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps({"control_run_id": run_dir.name}), encoding="utf-8"
    )
    rows = alerts or []
    (run_dir / "alerts.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


class RecordingMediaBackend:
    """Envuelve RunBackend (media-plane): status() es terminal de inmediato.

    El fake real (tests/fake_service.py) no transiciona un run recien lanzado
    a un estado terminal por si solo (siempre 'running' hasta 'run_done_1'
    hardcodeado); no editamos ese archivo preexistente (regla del proyecto).
    Este wrapper vive solo en este test y ademas registra el orden de
    eventos para el assert de secuencia media-primero.
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
    """Envuelve ControlPlaneBackend solo para registrar el orden de eventos."""

    def __init__(self, backend: ControlPlaneBackend, events: list) -> None:
        self._backend = backend
        self._events = events

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        self._events.append(("control_launch", mode))
        return await self._backend.launch(config, mode=mode, experiment_id=experiment_id)

    async def status(self, control_run_id: str) -> dict:
        return await self._backend.status(control_run_id)


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


async def test_dbe_replay_happy_path(media_backend, control_backend):
    real_media, media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    events: list = []
    media = RecordingMediaBackend(real_media, events)
    control = RecordingControlBackend(real_control, events)

    result = await run_experiment(
        _build_manifest(),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_load_config,
    )

    assert result.ok
    assert result.experiment_id.startswith("exp_")
    assert result.media_run_id and result.control_run_id
    assert result.media_status == "succeeded"
    assert result.control_status == "succeeded"

    # orden: el media debe terminar antes de que se dispare el control
    media_status_idx = events.index(("media_status", result.media_run_id))
    control_launch_idx = events.index(("control_launch", "replay"))
    assert media_status_idx < control_launch_idx

    # experiment_id propagado a ambos payloads
    assert media_state.launched[0]["experiment_id"] == result.experiment_id
    assert control_state.received_experiment_id == result.experiment_id
    assert control_state.received_mode == "replay"


async def test_dbe_replay_media_failure_skips_control(media_backend, control_backend):
    real_media, _media_state = media_backend
    real_control, control_state = control_backend

    events: list = []
    media = RecordingMediaBackend(real_media, events, terminal_status="failed")
    control = RecordingControlBackend(real_control, events)

    result = await run_experiment(
        _build_manifest(),
        media_backend=media,
        control_backend=control,
        now=NOW,
        load_config=_load_config,
    )

    assert result.ok is False
    assert result.media_status == "failed"
    assert result.control_run_id is None
    assert result.control_status is None
    assert control_state.active_run_id is None
    assert control_state.launched == []


async def test_dbe_replay_runs_distribution_after_consolidation(media_backend, control_backend, tmp_path):
    """DBE-replay: orden explícito y contrato de salida de distribución.

    Después de media y control, `run_distribution` corre con:
    - alerts_path apuntando a control/alerts del consolidado
    - out_dir dentro de runs/{experiment_id}/distribution
    - mode 'replay'
    """
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    run_dir = tmp_path / "runs"
    media_dir = run_dir / "media"
    control_dir = run_dir / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir, alerts=[{"alert_id": "al-1"}])

    calls: list[tuple[str, Path | None, str | None, float | None]] = []

    async def fake_distribution(
        *,
        mode: str,
        alerts_path: Path | None,
        out_dir: Path,
        config_path: str | None,
        endpoint: str | None,
        control_run_id: str | None,
        backfill_path: Path | None,
        idle_timeout_ms: float | None,
        timeout_s: float,
    ) -> dict:
        calls.append((mode, alerts_path, endpoint, idle_timeout_ms))
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "schema_version": "control.distribution_summary.v1",
            "counts": {"delivered": 1},
            "source_stats": {"read": 1, "skipped_malformed": 0},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": None,
        }
        (out_dir / "distribution_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
        return summary

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        return media_dir if plane == "media" else control_dir

    result = await run_experiment(
        _build_manifest(with_distribution=True),
        media_backend=RecordingMediaBackend(real_media, []),
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        run_distribution=fake_distribution,
        resolve_run_dir=resolve_run_dir,
        dest_root=run_dir,
    )

    assert result.ok
    assert result.distribution_status == "succeeded"
    assert result.consolidated_dir == str(run_dir / result.experiment_id)
    assert result.report_path is not None

    assert calls
    mode, alerts_path, endpoint, idle_timeout_ms = calls[0]
    assert mode == "replay"
    assert alerts_path is not None
    assert alerts_path.name == "alerts.jsonl"
    assert alerts_path.parent == run_dir / result.experiment_id / "control"
    assert endpoint is None
    assert idle_timeout_ms is None


async def test_dbe_replay_distribution_failure_cancela_chain(media_backend, control_backend, tmp_path):
    """Si `run_distribution` falla, el experimento entra como no exitoso y no
    genera `report`, pero conserva el consolidado.

    Esto cierra el borde B4: distribución no es opcional para el path de éxito,
    y su error no debe presentarse como corrida exitosa.
    """
    real_media, _media_state = media_backend
    real_control, control_state = control_backend
    control_state.finish_status = "succeeded"

    run_dir = tmp_path / "runs"
    media_dir = run_dir / "media"
    control_dir = run_dir / "control"
    _write_media_artifacts(media_dir)
    _write_control_artifacts(control_dir, alerts=[{"alert_id": "al-1"}])

    async def fake_distribution(**_: object) -> dict:  # type: ignore[type-arg]
        raise RuntimeError("eovrt-distribute no pudo ejecutar")

    def resolve_run_dir(plane: str, run_id: str) -> Path:
        return media_dir if plane == "media" else control_dir

    result = await run_experiment(
        _build_manifest(with_distribution=True),
        media_backend=RecordingMediaBackend(real_media, []),
        control_backend=real_control,
        now=NOW,
        load_config=_load_config,
        run_distribution=fake_distribution,
        resolve_run_dir=resolve_run_dir,
        dest_root=run_dir,
    )

    assert result.ok is False
    assert result.distribution_status == "failed"
    assert result.report_path is None
