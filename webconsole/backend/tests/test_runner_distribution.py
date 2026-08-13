from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import (
    _default_run_distribution,
    _distribution_summary_is_valid,
    run_experiment,
)

NOW = datetime(2026, 8, 12, 12, 0, 0, tzinfo=UTC)


def _manifest() -> ExperimentManifest:
    return ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "distribution-live",
            "runs": {
                "media": {"service": "media", "config": "media.yaml", "mode": "run"},
                "control": {
                    "service": "control",
                    "config": "control.yaml",
                    "mode": "live",
                },
                "distribution": {
                    "service": "distribution",
                    "config": "distribution.yaml",
                    "mode": "live",
                },
            },
            "sequencing": "control_first",
        }
    )


def _replay_manifest() -> ExperimentManifest:
    payload = _manifest().model_dump(mode="json")
    payload["runs"]["control"]["mode"] = "replay"
    payload["runs"]["distribution"]["mode"] = "replay"
    payload["sequencing"] = "media_first"
    return ExperimentManifest.model_validate(payload)


def _load_config(path: str) -> dict:
    if path == "media.yaml":
        return {"ingest": {"type": "rtsp"}, "prompts": {"ref": "demo"}}
    if path == "control.yaml":
        return {
            "input": {"bus": {"endpoint": "tcp://127.0.0.1:5557"}},
            "alert_bus": {
                "endpoint": "tcp://0.0.0.0:5558",
                "hwm": 250,
                "wait_for_subscriber_ms": 250,
            },
        }
    raise AssertionError(f"config inesperada: {path}")


class _MediaSucceeded:
    async def launch(self, run_request: dict) -> str:
        return "media-1"

    async def status(self, run_id: str) -> dict:
        return {"run_id": run_id, "status": "succeeded", "summary": {}}


class _ControlSucceeded:
    def __init__(self) -> None:
        self.launched_config: dict | None = None

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        self.launched_config = config
        return "control-1"

    async def current(self) -> dict:
        return {"control_run_id": "control-1", "subscribed": True}

    async def status(self, control_run_id: str) -> dict:
        return {"control_run_id": control_run_id, "status": "succeeded"}


class _ControlFailed(_ControlSucceeded):
    async def status(self, control_run_id: str) -> dict:
        return {"control_run_id": control_run_id, "status": "failed"}


def _valid_summary() -> dict:
    return {
        "schema_version": "control.distribution_summary.v1",
        "counts": {"delivered": 1},
        "source_stats": {"read": 1, "skipped_malformed": 0},
        "talert_notification_ms": {
            "live": {"count": 1, "min": 1.0, "mean": 1.0, "p95": 1.0}
        },
    }


def test_distribution_summary_validation_reads_the_requested_out_dir(tmp_path: Path) -> None:
    """Catch: validar accidentalmente ``out_dir/distribution/distribution_summary.json``."""
    out_dir = tmp_path / "distribution"
    out_dir.mkdir()
    summary = _valid_summary()
    (out_dir / "distribution_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    assert _distribution_summary_is_valid(summary, out_dir)


def test_distribution_summary_validation_rejects_stdout_file_mismatch(tmp_path: Path) -> None:
    out_dir = tmp_path / "distribution"
    out_dir.mkdir()
    returned = _valid_summary()
    persisted = {**returned, "counts": {"delivered": 99}}
    (out_dir / "distribution_summary.json").write_text(
        json.dumps(persisted), encoding="utf-8"
    )

    assert _distribution_summary_is_valid(returned, out_dir) is False


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("counts", []),
        ("counts", {"delivered": -1}),
        ("source_stats", []),
        ("source_stats", {"read": "one", "skipped_malformed": 0}),
        ("talert_notification_ms", []),
        ("talert_notification_ms", {"live": {"count": 1, "p95": "fast"}}),
    ],
)
def test_distribution_summary_validation_rejects_invalid_shape(
    tmp_path: Path, field: str, invalid_value: object
) -> None:
    out_dir = tmp_path / "distribution"
    out_dir.mkdir()
    summary = {**_valid_summary(), field: invalid_value}
    (out_dir / "distribution_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )

    assert _distribution_summary_is_valid(summary, out_dir) is False


async def test_live_uses_control_alert_bus_for_distribution(tmp_path: Path) -> None:
    """Catch: conectar el distribuidor al bus media->control (:5557)."""
    control = _ControlSucceeded()
    received_endpoint: str | None = None
    received_control_run_id: str | None = None

    async def run_distribution(
        *, out_dir: Path, endpoint: str | None, control_run_id: str | None, **_: object
    ) -> dict:
        nonlocal received_endpoint, received_control_run_id
        received_endpoint = endpoint
        received_control_run_id = control_run_id
        summary = _valid_summary()
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "distribution_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
        return summary

    result = await run_experiment(
        _manifest(),
        media_backend=_MediaSucceeded(),
        control_backend=control,
        now=NOW,
        load_config=_load_config,
        run_distribution=run_distribution,
        resolve_run_dir=lambda plane, run_id: tmp_path / plane / run_id,
        dest_root=tmp_path / "runs",
    )

    assert result.ok is True
    assert received_endpoint == "tcp://127.0.0.1:5558"
    assert received_control_run_id == "control-1"
    assert control.launched_config is not None
    assert control.launched_config["alert_bus"] == {
        "endpoint": "tcp://0.0.0.0:5558",
        "hwm": 250,
        "enabled": True,
        "wait_for_subscriber_ms": 10000,
    }
    assert "wait_for_subscriber_ms" not in control.launched_config["input"]["bus"]


async def test_live_cancels_distribution_if_media_launch_raises(tmp_path: Path) -> None:
    """Catch: dejar vivo el subprocesso de distribución al fallar el launch de media."""
    started = asyncio.Event()
    cleaned = asyncio.Event()

    class MediaLaunchFails:
        async def launch(self, run_request: dict) -> str:
            await started.wait()
            raise RuntimeError("media launch failed")

        async def status(self, run_id: str) -> dict:
            raise AssertionError("status no debe consultarse")

    async def run_distribution(**_: object) -> dict:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    with pytest.raises(RuntimeError, match="media launch failed"):
        await run_experiment(
            _manifest(),
            media_backend=MediaLaunchFails(),
            control_backend=_ControlSucceeded(),
            now=NOW,
            load_config=_load_config,
            run_distribution=run_distribution,
            dest_root=tmp_path / "runs",
        )

    assert cleaned.is_set()


async def test_live_cancels_distribution_immediately_if_control_fails(tmp_path: Path) -> None:
    started = asyncio.Event()
    cleaned = asyncio.Event()

    async def run_distribution(**_: object) -> dict:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    result = await asyncio.wait_for(
        run_experiment(
            _manifest(),
            media_backend=_MediaSucceeded(),
            control_backend=_ControlFailed(),
            now=NOW,
            load_config=_load_config,
            run_distribution=run_distribution,
            dest_root=tmp_path / "runs",
        ),
        timeout=0.5,
    )

    assert started.is_set()
    assert cleaned.is_set()
    assert result.ok is False
    assert result.distribution_status == "failed"


async def test_dbe_consolidation_failure_marks_required_distribution_failed(tmp_path: Path) -> None:
    called = False

    async def run_distribution(**_: object) -> dict:
        nonlocal called
        called = True
        return _valid_summary()

    def broken_resolver(plane: str, run_id: str) -> Path:
        raise OSError(f"no se puede resolver {plane}/{run_id}")

    result = await run_experiment(
        _replay_manifest(),
        media_backend=_MediaSucceeded(),
        control_backend=_ControlSucceeded(),
        now=NOW,
        load_config=_load_config,
        run_distribution=run_distribution,
        resolve_run_dir=broken_resolver,
        dest_root=tmp_path / "runs",
    )

    assert called is False
    assert result.ok is False
    assert result.distribution_status == "failed"
    assert result.report_path is None


async def test_subprocess_failure_does_not_expose_child_output(monkeypatch, tmp_path: Path) -> None:
    received_kwargs: dict[str, object] = {}

    class FailedProcess:
        returncode = 2

        async def communicate(self):
            return b"token=secret-stdout", b"password=secret-stderr"

    async def create_subprocess_exec(*args, **kwargs):
        received_kwargs.update(kwargs)
        return FailedProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_subprocess_exec)

    with pytest.raises(RuntimeError) as exc_info:
        await _default_run_distribution(
            mode="replay",
            alerts_path=tmp_path / "alerts.jsonl",
            out_dir=tmp_path / "distribution",
            config_path="distribution.yaml",
            endpoint=None,
        )

    message = str(exc_info.value)
    assert "secret-stdout" not in message
    assert "secret-stderr" not in message
    assert "salida omitida" in message
    assert received_kwargs["stderr"] is asyncio.subprocess.DEVNULL


async def test_default_distribution_replay_runs_the_sibling_service(tmp_path: Path) -> None:
    """Smoke real de la costura BFF -> CLI, no un doble que inventa el summary."""
    executable = (
        Path(__file__).resolve().parents[4]
        / "e-ovrt_alert-distribution"
        / ".venv"
        / "bin"
        / "eovrt-distribute"
    )
    if not executable.is_file():
        pytest.skip("el repositorio hermano del distribuidor no está instalado")

    alerts_path = tmp_path / "alerts.jsonl"
    alerts_path.write_text(
        json.dumps(
            {
                "schema_version": "control.alert.v1",
                "event_type": "alert_event",
                "control_run_id": "cr-smoke",
                "media_run_id": "mr-smoke",
                "unit_id": "unit-1",
                "source_id": "cam-1",
                "alert_id": "alert-smoke-1",
                "pattern_id": "PR-01",
                "condition_id": "CR-01",
                "subject_key": "driver",
                "severity": "high",
                "state": "open",
                "evidence": {},
                "timestamp_ms": 1000.0,
                "experiment_id": "exp-smoke",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "distribution"

    summary = await _default_run_distribution(
        mode="replay",
        alerts_path=alerts_path,
        out_dir=out_dir,
        config_path=None,
        endpoint=None,
        executable=str(executable),
        timeout_s=10.0,
    )

    assert summary["counts"] == {"delivered": 1}
    assert summary["control_run_id"] == "cr-smoke"
    assert _distribution_summary_is_valid(summary, out_dir)


async def test_replay_runner_generates_report_with_real_distribution_outcomes(
    tmp_path: Path, monkeypatch
) -> None:
    """Smoke DBE completo: runner -> CLI real -> consolidado -> report.json."""
    projects_root = Path(__file__).resolve().parents[4]
    executable = (
        projects_root
        / "e-ovrt_alert-distribution"
        / ".venv"
        / "bin"
        / "eovrt-distribute"
    )
    if not executable.is_file():
        pytest.skip("el repositorio hermano del distribuidor no está instalado")
    monkeypatch.setenv("EOVRT_DISTRIBUTION_EXECUTABLE", str(executable))

    manifest_payload = _replay_manifest().model_dump(mode="json")
    manifest_payload["runs"]["distribution"]["config"] = str(
        projects_root / "e-ovrt_alert-distribution" / "configs" / "example.yaml"
    )
    manifest = ExperimentManifest.model_validate(manifest_payload)

    media_dir = tmp_path / "plane-runs" / "media-1"
    media_dir.mkdir(parents=True)
    (media_dir / "summary.json").write_text(
        json.dumps({"run_id": "media-1"}), encoding="utf-8"
    )
    control_dir = tmp_path / "plane-runs" / "control-1"
    control_dir.mkdir(parents=True)
    (control_dir / "summary.json").write_text(
        json.dumps({"control_run_id": "control-1"}), encoding="utf-8"
    )
    alert = {
        "schema_version": "control.alert.v1",
        "event_type": "alert_event",
        "control_run_id": "control-1",
        "media_run_id": "media-1",
        "unit_id": "unit-1",
        "source_id": "cam-1",
        "alert_id": "alert-smoke-1",
        "pattern_id": "PR-01",
        "condition_id": "CR-01",
        "subject_key": "driver",
        "severity": "high",
        "state": "open",
        "evidence": {},
        "timestamp_ms": 1000.0,
        "experiment_id": "exp-smoke",
    }
    (control_dir / "alerts.jsonl").write_text(
        json.dumps(alert) + "\n", encoding="utf-8"
    )

    result = await run_experiment(
        manifest,
        media_backend=_MediaSucceeded(),
        control_backend=_ControlSucceeded(),
        now=NOW,
        load_config=_load_config,
        resolve_run_dir=lambda plane, _run_id: media_dir if plane == "media" else control_dir,
        dest_root=tmp_path / "runs",
    )

    assert result.ok is True
    assert result.distribution_status == "succeeded"
    assert result.report_path is not None
    report = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
    assert report["distribucion"]["counts"] == {"delivered": 1}
    assert report["distribucion_por_alerta"]["alert-smoke-1"]["outcome"] == "delivered"
