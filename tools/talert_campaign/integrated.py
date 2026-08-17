from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

import httpx
import yaml
from eovrt_webconsole.experiment.control_backend import ControlPlaneBackend
from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import run_experiment
from eovrt_webconsole.run_backend import RunBackend

from .config import CampaignConfig
from .model import GateViolation
from .mqtt_witness import ManagedBroker, MqttWitness


def run_integrated_video(
    config: CampaignConfig, attempt: Path, *, phase_id: str = "integrated-video"
) -> dict[str, Any]:
    if not re.fullmatch(r"integrated-video(?:-[0-9]{2})?", phase_id):
        raise GateViolation("invalid integrated video phase_id")
    phase = attempt / phase_id
    try:
        phase.mkdir()
    except FileExistsError as exc:
        raise GateViolation("integrated video phase already exists") from exc
    templates = config.repo_root / "experiments/t_alert_notification/video"
    broker_executable = Path(sys.executable).with_name("amqtt")
    broker_config = config.repo_root / "infra/platform/mosquitto/amqtt.yaml"
    witness = MqttWitness(config.broker.host, config.broker.port)
    expected_ids: set[str] = set()
    admissions: list[dict[str, Any]] = []
    repetitions: list[dict[str, Any]] = []
    previous_path = os.environ.get("PATH")
    previous_distribution = os.environ.get("EOVRT_DISTRIBUTION_EXECUTABLE")
    bin_dir = Path(sys.executable).parent
    os.environ["PATH"] = f"{bin_dir}:{previous_path or ''}"
    os.environ["EOVRT_DISTRIBUTION_EXECUTABLE"] = str(bin_dir / "eovrt-distribute")
    try:
        with ManagedBroker.start(broker_executable, broker_config):
            witness.start(f"{config.mqtt.topic_prefix}/#")
            witness.wait_subscribed()
            selected: str | None = None
            for index, clip_id in enumerate(("a_p1_c08", "a_p7_c02", "a_p6_c01"), 1):
                record = _execute_integrated(
                    config,
                    phase,
                    templates,
                    clip_id=clip_id,
                    label=f"admission-{index}",
                )
                admissions.append(record)
                expected_ids.update(record["delivered_ids"])
                witness.wait_for_ids(expected_ids, timeout_s=10)
                if record["delivered"] > 0:
                    selected = clip_id
                    break
            if selected is None:
                raise GateViolation("integrated admission produced no delivered alert")
            for repetition in range(1, 4):
                record = _execute_integrated(
                    config,
                    phase,
                    templates,
                    clip_id=selected,
                    label=f"repetition-{repetition}",
                )
                if record["delivered"] < 1:
                    raise GateViolation(
                        f"integrated repetition {repetition} produced no delivered alert"
                    )
                repetitions.append(record)
                expected_ids.update(record["delivered_ids"])
                witness.wait_for_ids(expected_ids, timeout_s=10)
            snapshot = witness.snapshot()
            observed = {message["notification_id"] for message in snapshot["messages"]}
            if observed != expected_ids:
                detail = min(observed.symmetric_difference(expected_ids))
                raise GateViolation(f"integrated witness ID mismatch: {detail}")
            _write_json(phase / "witness.json", snapshot)
    finally:
        witness.close()
        if previous_distribution is None:
            os.environ.pop("EOVRT_DISTRIBUTION_EXECUTABLE", None)
        else:
            os.environ["EOVRT_DISTRIBUTION_EXECUTABLE"] = previous_distribution
        if previous_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = previous_path
    result = {
        "schema_version": "talert_notification_integrated_video.v1",
        "selected_clip": selected,
        "admissions": admissions,
        "repetitions": repetitions,
        "status": "succeeded",
    }
    _write_json(phase / "integrated-runs.json", result)
    return result


def run_camera_smoke(
    config: CampaignConfig,
    attempt: Path,
    *,
    preset_path: Path,
    phase_id: str = "camera-smoke",
) -> dict[str, Any]:
    if not re.fullmatch(r"camera-smoke(?:-[0-9]{2})?", phase_id):
        raise GateViolation("invalid camera smoke phase_id")
    phase = attempt / phase_id
    try:
        phase.mkdir()
    except FileExistsError as exc:
        raise GateViolation("camera smoke phase already exists") from exc
    camera = _load_camera_preset(preset_path)
    broker_executable = Path(sys.executable).with_name("amqtt")
    broker_config = config.repo_root / "infra/platform/mosquitto/amqtt.yaml"
    witness = MqttWitness(config.broker.host, config.broker.port)
    previous_path = os.environ.get("PATH")
    previous_distribution = os.environ.get("EOVRT_DISTRIBUTION_EXECUTABLE")
    bin_dir = Path(sys.executable).parent
    os.environ["PATH"] = f"{bin_dir}:{previous_path or ''}"
    os.environ["EOVRT_DISTRIBUTION_EXECUTABLE"] = str(bin_dir / "eovrt-distribute")
    try:
        with tempfile.TemporaryDirectory(prefix="eovrt-camera-smoke-") as temporary:
            manifest = _materialize_camera_manifest(
                config, Path(temporary), camera["plugin"], camera["config"]
            )
            with ManagedBroker.start(broker_executable, broker_config):
                witness.start(f"{config.mqtt.topic_prefix}/#")
                witness.wait_subscribed()
                execution = asyncio.run(_run_manifest(manifest, phase / "consolidated"))
                record = _camera_result(execution)
                expected_ids = set(record["delivered_ids"])
                if expected_ids:
                    witness.wait_for_ids(expected_ids, timeout_s=10)
                snapshot = witness.snapshot()
                observed = {message["notification_id"] for message in snapshot["messages"]}
                if observed != expected_ids:
                    detail = min(observed.symmetric_difference(expected_ids))
                    raise GateViolation(f"camera witness ID mismatch: {detail}")
                _write_json(phase / "witness.json", snapshot)
    finally:
        witness.close()
        if previous_distribution is None:
            os.environ.pop("EOVRT_DISTRIBUTION_EXECUTABLE", None)
        else:
            os.environ["EOVRT_DISTRIBUTION_EXECUTABLE"] = previous_distribution
        if previous_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = previous_path
    result = {
        "schema_version": "talert_notification_camera_smoke.v1",
        "plugin": camera["plugin"],
        "source_id": "camera_smoke",
        "protocol": {
            "max_units": 120,
            "person_visible_without_helmet_or_vest": True,
            "unsafe_activity": False,
        },
        "execution": record,
        "status": "succeeded" if record["delivered"] > 0 else "negative",
        "negative_cause": None if record["delivered"] > 0 else record.get("cause"),
    }
    serialized = json.dumps(result, ensure_ascii=True)
    for forbidden in ("rtsp://", "userinfo", "credential", "password", "preset_path"):
        if forbidden in serialized.lower():
            raise GateViolation(f"camera evidence contains sensitive token: {forbidden}")
    _write_json(phase / "camera-smoke.json", result)
    return result


def materialize_video_manifest(
    config: CampaignConfig,
    phase: Path,
    templates: Path,
    *,
    clip_id: str,
    label: str,
) -> Path:
    materialized = phase / label / "config"
    materialized.mkdir(parents=True)
    experiment_id = f"exp_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}_talert_{label}"
    workspace = config.repo_root.parent
    replacements = {
        "EOVRT_WORKSPACE": str(workspace),
        "EOVRT_CLIP_ID": clip_id,
        "EOVRT_EXPERIMENT_ID": experiment_id,
    }
    for source_name, target_name in (
        ("media.template.yaml", "media.yaml"),
        ("control.template.yaml", "control.yaml"),
    ):
        rendered = Template((templates / source_name).read_text(encoding="utf-8")).substitute(
            replacements
        )
        (materialized / target_name).write_text(rendered, encoding="utf-8")
    replacements.update(
        {
            "EOVRT_MEDIA_CONFIG": str(materialized / "media.yaml"),
            "EOVRT_CONTROL_CONFIG": str(materialized / "control.yaml"),
            "EOVRT_DISTRIBUTION_CONFIG": str(
                config.repo_root / "experiments/t_alert_notification/distribution-live.yaml"
            ),
        }
    )
    manifest_path = materialized / "manifest.yaml"
    manifest_path.write_text(
        Template((templates / "manifest.template.yaml").read_text(encoding="utf-8")).substitute(
            replacements
        ),
        encoding="utf-8",
    )
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    ExperimentManifest.model_validate(payload)
    return manifest_path


def _execute_integrated(
    config: CampaignConfig,
    phase: Path,
    templates: Path,
    *,
    clip_id: str,
    label: str,
) -> dict[str, Any]:
    manifest_path = materialize_video_manifest(
        config, phase, templates, clip_id=clip_id, label=label
    )
    manifest = ExperimentManifest.model_validate(
        yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    )
    result = asyncio.run(_run_manifest(manifest, phase / label / "consolidated"))
    if not result.ok or result.distribution_status != "succeeded":
        raise GateViolation(f"integrated {label} failed: {result.model_dump(mode='json')}")
    if not result.consolidated_dir or not result.report_path:
        raise GateViolation(f"integrated {label} did not produce report artifacts")
    consolidated = Path(result.consolidated_dir)
    summary = _load_json(consolidated / "distribution/distribution_summary.json")
    source_stats = summary.get("source_stats", {})
    if source_stats.get("termination_reason") != "run_finished":
        raise GateViolation(f"integrated {label} did not terminate by run_finished")
    for key in ("bus_dropped_events", "skipped_malformed"):
        if source_stats.get(key) != 0:
            raise GateViolation(f"integrated {label} {key}={source_stats.get(key)}")
    if summary.get("skipped_invalid_alerts") != 0:
        raise GateViolation(f"integrated {label} contains invalid alerts")
    counts = summary.get("counts", {})
    if counts.get("dead_letter", 0):
        raise GateViolation(f"integrated {label} contains dead letters")
    records = _load_jsonl(
        consolidated / "distribution/notifications.jsonl",
        missing_ok=not counts,
    )
    delivered = [row for row in records if row.get("outcome") == "delivered"]
    for row in delivered:
        if row.get("mode") != "live" or row.get("latency_mode") != "live":
            raise GateViolation(f"integrated {label} produced non-live latency")
    report = _load_json(Path(result.report_path))
    metric = next(
        (row for row in report.get("resultados", []) if row.get("name") == "t_alert-notification"),
        None,
    )
    expected_status = "computed" if delivered else "applicable_not_computed"
    if not isinstance(metric, dict) or metric.get("status") != expected_status:
        raise GateViolation(f"integrated {label} report metric status mismatch")
    return {
        "label": label,
        "clip_id": clip_id,
        "experiment_id": result.experiment_id,
        "media_run_id": result.media_run_id,
        "control_run_id": result.control_run_id,
        "consolidated_dir": str(consolidated),
        "report_path": result.report_path,
        "delivered": len(delivered),
        "delivered_ids": sorted(row["notification_id"] for row in delivered),
        "latency_p95_ms": ((summary.get("talert_notification_ms") or {}).get("live") or {}).get(
            "p95"
        ),
        "report_metric": metric,
        "status": "succeeded",
    }


async def _run_manifest(manifest: ExperimentManifest, dest_root: Path):
    async with (
        httpx.AsyncClient(base_url="http://127.0.0.1:8080", timeout=30) as media_http,
        httpx.AsyncClient(base_url="http://127.0.0.1:8081", timeout=30) as control_http,
    ):
        return await run_experiment(
            manifest,
            media_backend=RunBackend(media_http),
            control_backend=ControlPlaneBackend(control_http),
            now=datetime.now(UTC),
            poll_interval_s=0.2,
            timeout_s=600,
            dest_root=dest_root,
        )


def _load_camera_preset(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GateViolation("cannot load local camera preset") from exc
    camera = payload.get("camera") if isinstance(payload, dict) else None
    if not isinstance(camera, dict):
        raise GateViolation("camera preset has invalid shape")
    plugin = camera.get("plugin")
    plugin_config = camera.get("config")
    if plugin not in {"oak_d", "rtsp"} or not isinstance(plugin_config, dict):
        raise GateViolation("camera preset plugin/config is invalid")
    return {"plugin": plugin, "config": dict(plugin_config)}


def _materialize_camera_manifest(
    config: CampaignConfig,
    temporary: Path,
    plugin: str,
    plugin_config: dict[str, Any],
) -> ExperimentManifest:
    experiment_id = f"exp_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')}_talert_camera"
    media_path = temporary / "media.yaml"
    control_path = temporary / "control.yaml"
    manifest_path = temporary / "manifest.yaml"
    media_payload = {
        "ingest": {"plugin": plugin, "config": plugin_config},
        "prompts": {
            "set_inline": {
                "id": "cr01_cr02_v2_short",
                "classes": [
                    {"id": "person", "phrasings": {"default": ["person"]}},
                    {"id": "helmet", "phrasings": {"default": ["helmet"]}},
                    {"id": "vest", "phrasings": {"default": ["vest"]}},
                ],
            },
            "active_ids": ["person", "helmet", "vest"],
        },
        "run": {
            "name": "talert_camera_smoke",
            "max_units": 120,
            "save_previews": False,
        },
    }
    media_path.write_text(yaml.safe_dump(media_payload, sort_keys=False), encoding="utf-8")
    replacements = {
        "EOVRT_WORKSPACE": str(config.repo_root.parent),
        "EOVRT_EXPERIMENT_ID": experiment_id,
        "EOVRT_MEDIA_CONFIG": str(media_path),
        "EOVRT_CONTROL_CONFIG": str(control_path),
        "EOVRT_DISTRIBUTION_CONFIG": str(
            config.repo_root / "experiments/t_alert_notification/distribution-live.yaml"
        ),
    }
    templates = config.repo_root / "experiments/t_alert_notification/camera"
    control_path.write_text(
        Template((templates / "control.template.yaml").read_text(encoding="utf-8")).substitute(
            replacements
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        Template((templates / "manifest.template.yaml").read_text(encoding="utf-8")).substitute(
            replacements
        ),
        encoding="utf-8",
    )
    return ExperimentManifest.model_validate(
        yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    )


def _camera_result(execution: Any) -> dict[str, Any]:
    base = {
        "experiment_id": execution.experiment_id,
        "media_run_id": execution.media_run_id,
        "control_run_id": execution.control_run_id,
        "media_status": execution.media_status,
        "control_status": execution.control_status,
        "distribution_status": execution.distribution_status,
    }
    if not execution.ok or execution.distribution_status != "succeeded":
        raise GateViolation("camera integrated run failed")
    if not execution.consolidated_dir or not execution.report_path:
        raise GateViolation("camera integrated run did not produce report artifacts")
    consolidated = Path(execution.consolidated_dir)
    summary = _load_json(consolidated / "distribution/distribution_summary.json")
    source_stats = summary.get("source_stats", {})
    if source_stats.get("termination_reason") != "run_finished":
        raise GateViolation("camera distribution did not terminate by run_finished")
    for key in ("bus_dropped_events", "skipped_malformed"):
        if source_stats.get(key) != 0:
            raise GateViolation(f"camera distribution {key}={source_stats.get(key)}")
    if summary.get("skipped_invalid_alerts") != 0:
        raise GateViolation("camera distribution contains invalid alerts")
    counts = summary.get("counts", {})
    if counts.get("dead_letter", 0):
        raise GateViolation("camera distribution contains dead letters")
    records = _load_jsonl(
        consolidated / "distribution/notifications.jsonl",
        missing_ok=not counts,
    )
    delivered = [row for row in records if row.get("outcome") == "delivered"]
    for row in delivered:
        if row.get("mode") != "live" or row.get("latency_mode") != "live":
            raise GateViolation("camera distribution produced non-live latency")
    report = _load_json(Path(execution.report_path))
    metric = next(
        (row for row in report.get("resultados", []) if row.get("name") == "t_alert-notification"),
        None,
    )
    expected_status = "computed" if delivered else "applicable_not_computed"
    if not isinstance(metric, dict) or metric.get("status") != expected_status:
        raise GateViolation("camera report metric status mismatch")
    return {
        **base,
        "delivered": len(delivered),
        "delivered_ids": sorted(row["notification_id"] for row in delivered),
        "latency_p95_ms": ((summary.get("talert_notification_ms") or {}).get("live") or {}).get(
            "p95"
        ),
        "report_metric": metric,
        "cause": None if delivered else "no_confirmed_alert",
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot load integrated artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise GateViolation(f"integrated artifact is not an object: {path.name}")
    return value


def _load_jsonl(path: Path, *, missing_ok: bool) -> list[dict[str, Any]]:
    if missing_ok and not path.exists():
        return []
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot load integrated ledger: {path.name}") from exc
    if not all(isinstance(row, dict) for row in rows):
        raise GateViolation("integrated ledger contains non-object row")
    return rows


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
