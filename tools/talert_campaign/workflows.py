from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eovrt_distribution.channels.mqtt import MqttChannel
from eovrt_distribution.distributor import Distributor
from eovrt_distribution.policy import NotificationPolicy
from eovrt_distribution.sources import JsonlReplaySource

from .config import CampaignConfig
from .corpus import load_corpus, stage_alerts, validate_alerts
from .live_bus import publish_run
from .model import CorpusRun, GateViolation
from .mqtt_witness import ManagedBroker, MqttWitness

_ATTEMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


def create_attempt(root: Path, attempt_id: str) -> Path:
    if not _ATTEMPT_ID.fullmatch(attempt_id):
        raise GateViolation("attempt_id contains unsafe characters")
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    attempt = root / attempt_id
    try:
        attempt.mkdir()
    except FileExistsError as exc:
        raise GateViolation(f"attempt already exists: {attempt_id}") from exc
    _write_json(
        attempt / "attempt.json",
        {
            "schema_version": "talert_notification_attempt.v1",
            "attempt_id": attempt_id,
            "status": "prepared",
        },
    )
    return attempt


def prepare_attempt(config: CampaignConfig, attempt_id: str) -> dict[str, Any]:
    attempt = create_attempt(config.repo_root / "runs/t-alert-notification", attempt_id)
    workspace = config.repo_root.parent
    repo_names = (
        "e-ovrt_experimental-setup",
        "e-ovrt_media-plane",
        "e-ovrt_control-plane",
        "e-ovrt_alert-distribution",
        "e-ovrt_datasets",
    )
    repositories = {
        name: _git_fingerprint(workspace / name)
        for name in repo_names
    }
    hash_paths = {
        "campaign": config.path,
        "resolved_runs": config.corpus.resolved_runs,
        "distribution_live": config.repo_root
        / "experiments/t_alert_notification/distribution-live.yaml",
        "distribution_replay": config.repo_root
        / "experiments/t_alert_notification/distribution-replay.yaml",
        "design": config.repo_root
        / "docs/superpowers/specs/2026-08-13-campana-t-alert-notification-design.md",
        "plan": config.repo_root
        / "docs/superpowers/plans/2026-08-13-campana-t-alert-notification.md",
    }
    hashes = {name: _sha256(path) for name, path in hash_paths.items()}
    hashes["tooling_tree"] = _tree_sha256(
        config.repo_root,
        (
            config.repo_root / "tools/t_alert_notification_campaign.py",
            config.repo_root / "tools/talert_campaign",
            config.repo_root / "experiments/t_alert_notification",
        ),
    )
    versions = {}
    for distribution in (
        "amqtt",
        "paho-mqtt",
        "pyzmq",
        "eovrt-control-plane",
        "eovrt-alert-distribution",
        "eovrt-webconsole",
    ):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    state = {
        "schema_version": "talert_notification_attempt.v1",
        "attempt_id": attempt_id,
        "status": "prepared",
        "prepared_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "versions": versions,
        },
        "repositories": repositories,
        "hashes": hashes,
    }
    _write_json(attempt / "attempt.json", state)
    return state


def load_attempt(root: Path, attempt_id: str, *, allow_completed: bool = False) -> Path:
    """Carga un intento de campaña.

    Por defecto exige `prepared`: la campaña avanza en un sentido y operar sobre un
    intento cerrado escondería una corrida. `allow_completed=True` admite además un
    intento ya publicado (`succeeded`) y existe sólo para los caminos de regeneración
    declarados (`verify --allow-completed`, `rebuild-curated`), que re-derivan artefactos
    a partir de fases inmutables y no producen mediciones nuevas.
    """
    if not _ATTEMPT_ID.fullmatch(attempt_id):
        raise GateViolation("attempt_id contains unsafe characters")
    attempt = root.resolve() / attempt_id
    state_path = attempt / "attempt.json"
    if not state_path.is_file():
        raise GateViolation(f"attempt does not exist: {attempt_id}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"invalid attempt state: {attempt_id}") from exc
    allowed = {"prepared", "succeeded"} if allow_completed else {"prepared"}
    if state.get("attempt_id") != attempt_id or state.get("status") not in allowed:
        raise GateViolation(
            f"attempt is not prepared nor published: {attempt_id}"
            if allow_completed
            else f"attempt is not prepared: {attempt_id}"
        )
    return attempt


def invalidate_attempt(attempt: Path, reason: str) -> dict[str, Any]:
    state = _load_json(attempt / "attempt.json")
    if state.get("status") != "prepared":
        raise GateViolation("only a prepared attempt can be invalidated")
    state["status"] = "invalid"
    state["invalid_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    state["invalid_reason"] = reason
    _write_json(attempt / "attempt.json", state)
    return state


def select_runs(config: CampaignConfig, sample: tuple[str, ...]) -> tuple[CorpusRun, ...]:
    corpus = load_corpus(config)
    if not sample:
        return corpus
    by_id = {run.run_id: run for run in corpus}
    missing = sorted(set(sample) - by_id.keys())
    if missing:
        raise GateViolation(f"sample run is not in the campaign corpus: {missing[0]}")
    if len(sample) != len(set(sample)):
        raise GateViolation("sample contains duplicate run IDs")
    return tuple(by_id[run_id] for run_id in sample)


def run_preflight_dbe(
    config: CampaignConfig,
    attempt: Path,
    *,
    sample: tuple[str, ...] = (),
) -> dict[str, Any]:
    runs = select_runs(config, sample)
    phase_root = attempt / "preflight-dbe"
    phase_root.mkdir()
    totals: Counter[str] = Counter()
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="staging-", dir=attempt) as temporary:
        staging = Path(temporary)
        for run in runs:
            staged = stage_alerts(run, staging)
            alert_stats = validate_alerts(staged)
            run_root = phase_root / run.run_id
            working = run_root / "working"
            pass_1 = run_root / "pass-1"
            pass_2 = run_root / "pass-2"
            working.mkdir(parents=True)
            pass_1.mkdir()
            pass_2.mkdir()

            # La política se conserva entre pasadas: forma parte del estado del run.
            policy = NotificationPolicy(
                cooldown_ms=config.policy.cooldown_ms,
                key_fields=config.policy.key,
            )
            first = _run_replay(staged, working, policy)
            _snapshot_distribution(working, pass_1)
            second = _run_replay(staged, working, policy)
            _snapshot_distribution(working, pass_2)
            _gate_replay(run, alert_stats.valid, first, second)

            first_counts = first.get("counts", {})
            totals["runs"] += 1
            totals["nonempty_runs"] += int(alert_stats.valid > 0)
            totals["events"] += alert_stats.valid
            totals["delivered"] += int(first_counts.get("delivered", 0))
            totals["suppressed_cooldown"] += int(
                first_counts.get("suppressed_cooldown", 0)
            )
            results.append(
                {
                    "run_id": run.run_id,
                    "series": run.series,
                    "events": alert_stats.valid,
                    "first_counts": first_counts,
                    "second_counts": second.get("counts", {}),
                    "status": "succeeded",
                }
            )
    summary = {
        "schema_version": "talert_notification_preflight_dbe.v1",
        "sample": bool(sample),
        "runs": results,
        "totals": dict(sorted(totals.items())),
        "status": "succeeded",
    }
    if not sample:
        expected = config.corpus.expected
        observed = (
            totals["runs"],
            totals["nonempty_runs"],
            totals["events"],
        )
        if observed != (expected.runs, expected.nonempty_runs, expected.events):
            raise GateViolation("full DBE preflight totals drift")
    _write_json(attempt / "preflight-dbe-summary.json", summary)
    return summary


def run_live_series(
    config: CampaignConfig,
    attempt: Path,
    *,
    series: str,
    sample: tuple[str, ...] = (),
) -> dict[str, Any]:
    if series not in {"primary", "supplemental"}:
        raise GateViolation("live series must be primary or supplemental")
    runs = select_runs(config, sample)
    allowed = {"primary_dbe", "primary_ebe"} if series == "primary" else {"supplemental"}
    if sample:
        wrong = [run.run_id for run in runs if run.series not in allowed]
        if wrong:
            raise GateViolation(f"run does not belong to live {series} series: {wrong[0]}")
    else:
        runs = tuple(run for run in runs if run.series in allowed)
        expected_runs = config.corpus.primary.runs if series == "primary" else config.corpus.supplemental.runs
        if len(runs) != expected_runs:
            raise GateViolation(f"live {series} corpus size drift")

    phase_root = attempt / f"live-{series}"
    try:
        phase_root.mkdir()
    except FileExistsError as exc:
        raise GateViolation(f"live {series} phase already exists") from exc
    preflight_counts = _load_preflight_counts(attempt)
    broker_executable = Path(sys.executable).with_name("amqtt")
    distribute_executable = Path(sys.executable).with_name("eovrt-distribute")
    broker_config = config.repo_root / "infra/platform/mosquitto/amqtt.yaml"
    distribution_config = config.repo_root / "experiments/t_alert_notification/distribution-live.yaml"
    totals: Counter[str] = Counter()
    executions: list[dict[str, Any]] = []
    cumulative_expected: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="staging-live-", dir=attempt) as temporary:
        staging = Path(temporary)
        with ManagedBroker.start(
            broker_executable,
            broker_config,
            host=config.broker.host,
            port=config.broker.port,
        ):
            witness = MqttWitness(config.broker.host, config.broker.port)
            try:
                witness.start(f"{config.mqtt.topic_prefix}/#")
                witness.wait_subscribed()
                for run in runs:
                    staged = stage_alerts(run, staging)
                    alerts = _read_alerts(staged)
                    run_root = phase_root / run.run_id
                    distribution_dir = run_root / "distribution"
                    run_root.mkdir(parents=True)
                    stdout_path = run_root / "distributor.stdout.log"
                    stderr_path = run_root / "distributor.stderr.log"
                    process = subprocess.Popen(
                        [
                            str(distribute_executable),
                            "live",
                            "--endpoint",
                            config.bus.endpoint,
                            "--control-run-id",
                            run.run_id,
                            "--config",
                            str(distribution_config),
                            "--out-dir",
                            str(distribution_dir),
                            "--idle-timeout-ms",
                            "10000",
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    try:
                        publish_stats = publish_run(
                            alerts,
                            run.run_id,
                            config.bus.endpoint,
                            subscriptions_expected=config.bus.subscriptions_expected,
                        )
                        stdout, stderr = process.communicate(timeout=20)
                    except Exception:
                        if process.poll() is None:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait(timeout=5)
                        raise
                    stdout_path.write_bytes(stdout)
                    stderr_path.write_bytes(stderr)
                    if process.returncode != 0:
                        raise GateViolation(
                            f"{run.run_id}: distributor exited {process.returncode}"
                        )
                    summary = _load_json(distribution_dir / "distribution_summary.json")
                    records = _load_jsonl(
                        distribution_dir / "notifications.jsonl", missing_ok=not alerts
                    )
                    delivered_ids = {
                        row["notification_id"]
                        for row in records
                        if row.get("outcome") == "delivered"
                    }
                    cumulative_expected.update(delivered_ids)
                    witness.wait_for_ids(cumulative_expected, timeout_s=10)
                    snapshot = witness.snapshot()
                    observed = {
                        message["notification_id"] for message in snapshot["messages"]
                    }
                    unexpected = observed - cumulative_expected
                    if unexpected:
                        raise GateViolation(
                            f"{run.run_id}: witness observed unexpected ID {min(unexpected)}"
                        )
                    _gate_live_run(
                        run,
                        len(alerts),
                        summary,
                        records,
                        delivered_ids,
                        observed,
                        preflight_counts.get(run.run_id),
                    )
                    counts = summary.get("counts", {})
                    totals["runs"] += 1
                    totals["nonempty_runs"] += int(bool(alerts))
                    totals["events"] += len(alerts)
                    for outcome, count in counts.items():
                        totals[outcome] += int(count)
                    executions.append(
                        {
                            "run_id": run.run_id,
                            "origin": run.origin,
                            "events": len(alerts),
                            "counts": counts,
                            "delivered_ids": sorted(delivered_ids),
                            "publish": publish_stats.__dict__,
                            "status": "succeeded",
                        }
                    )
                _write_json(phase_root / "witness.json", witness.snapshot())
            finally:
                witness.close()
    result = {
        "schema_version": "talert_notification_live_series.v1",
        "series": series,
        "sample": bool(sample),
        "runs": executions,
        "totals": dict(sorted(totals.items())),
        "status": "succeeded",
    }
    if not sample:
        expected = config.corpus.primary if series == "primary" else config.corpus.supplemental
        observed = (
            totals["runs"],
            totals["nonempty_runs"],
            totals["events"],
        )
        if observed != (expected.runs, expected.nonempty_runs, expected.events):
            raise GateViolation(f"full live {series} totals drift")
    _write_json(phase_root / "series-summary.json", result)
    return result


def _run_replay(path: Path, out_dir: Path, policy: NotificationPolicy) -> dict[str, Any]:
    distributor = Distributor(
        source=JsonlReplaySource(path),
        channel=MqttChannel(mode="dry_run", qos=1),
        policy=policy,
        out_dir=out_dir,
        max_attempts=3,
        retry_wait_ms=500,
    )
    return distributor.run()


def _gate_live_run(
    run: CorpusRun,
    expected_events: int,
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    delivered_ids: set[str],
    observed_ids: set[str],
    preflight_counts: dict[str, int] | None,
) -> None:
    source = summary.get("source_stats", {})
    if source.get("read") != expected_events:
        raise GateViolation(f"{run.run_id}: live source read mismatch")
    if source.get("termination_reason") != "run_finished":
        raise GateViolation(f"{run.run_id}: live did not terminate by run_finished")
    for key in ("skipped_malformed", "bus_dropped_events"):
        if source.get(key) != 0:
            raise GateViolation(f"{run.run_id}: live {key}={source.get(key)}")
    if summary.get("skipped_invalid_alerts") != 0:
        raise GateViolation(f"{run.run_id}: live invalid alerts")
    counts = summary.get("counts", {})
    if counts.get("dead_letter", 0):
        raise GateViolation(f"{run.run_id}: live dead letters")
    if sum(counts.values()) != expected_events:
        raise GateViolation(f"{run.run_id}: live outcome count mismatch")
    if preflight_counts is not None:
        for outcome in ("delivered", "suppressed_cooldown"):
            if counts.get(outcome, 0) != preflight_counts.get(outcome, 0):
                raise GateViolation(f"{run.run_id}: live/preflight {outcome} mismatch")
    delivered = [record for record in records if record.get("outcome") == "delivered"]
    if len(delivered) != counts.get("delivered", 0):
        raise GateViolation(f"{run.run_id}: delivered ledger mismatch")
    for record in delivered:
        latency = record.get("talert_notification_ms")
        if record.get("mode") != "live" or record.get("latency_mode") != "live":
            raise GateViolation(f"{run.run_id}: non-live delivered record")
        if not isinstance(latency, (int, float)) or latency < 0:
            raise GateViolation(f"{run.run_id}: invalid live latency")
    if not delivered_ids.issubset(observed_ids):
        raise GateViolation(f"{run.run_id}: witness mismatch")


def _load_preflight_counts(attempt: Path) -> dict[str, dict[str, int]]:
    path = attempt / "preflight-dbe-summary.json"
    if not path.is_file():
        return {}
    summary = _load_json(path)
    return {
        row["run_id"]: row["first_counts"]
        for row in summary.get("runs", [])
        if isinstance(row, dict)
        and isinstance(row.get("run_id"), str)
        and isinstance(row.get("first_counts"), dict)
    }


def _read_alerts(path: Path) -> list[dict[str, Any]]:
    return _load_jsonl(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot read JSON artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise GateViolation(f"JSON artifact is not an object: {path.name}")
    return value


def _load_jsonl(path: Path, *, missing_ok: bool = False) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if missing_ok and not path.exists():
        return values
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise GateViolation(f"{path.name}: line {line_number} is not an object")
            values.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot read JSONL artifact: {path.name}") from exc
    return values


def _gate_replay(
    run: CorpusRun,
    expected_events: int,
    first: dict[str, Any],
    second: dict[str, Any],
) -> None:
    for label, summary in (("pass-1", first), ("pass-2", second)):
        stats = summary.get("source_stats", {})
        if stats.get("read") != expected_events:
            raise GateViolation(f"{run.run_id} {label}: source read mismatch")
        if stats.get("skipped_malformed") != 0:
            raise GateViolation(f"{run.run_id} {label}: malformed alerts")
        if summary.get("skipped_invalid_alerts") != 0:
            raise GateViolation(f"{run.run_id} {label}: invalid alerts")
        latency = summary.get("talert_notification_ms") or {}
        if "live" in latency:
            raise GateViolation(f"{run.run_id} {label}: live latency in DBE preflight")
    first_counts = first.get("counts", {})
    if sum(first_counts.values()) != expected_events:
        raise GateViolation(f"{run.run_id} pass-1: outcome count mismatch")
    second_counts = second.get("counts", {})
    if second_counts.get("delivered", 0):
        raise GateViolation(f"{run.run_id} pass-2: notification was redelivered")
    if sum(second_counts.values()) != expected_events:
        raise GateViolation(f"{run.run_id} pass-2: outcome count mismatch")
    if second_counts.get("skipped_duplicate", 0) != first_counts.get("delivered", 0):
        raise GateViolation(f"{run.run_id} pass-2: delivered ledger mismatch")


def _snapshot_distribution(source: Path, target: Path) -> None:
    for name in ("distribution_summary.json", "notifications.jsonl", "dead_letter.jsonl"):
        path = source / name
        if path.exists():
            shutil.copy2(path, target / name)


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _git_fingerprint(repo: Path) -> dict[str, Any]:
    if not (repo / ".git").exists():
        # Worktrees can expose .git as a file; git itself remains authoritative.
        probe = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            raise GateViolation(f"repository unavailable during prepare: {repo.name}")
    values: dict[str, str] = {}
    for key, argv in {
        "commit": ["git", "-C", str(repo), "rev-parse", "HEAD"],
        "branch": ["git", "-C", str(repo), "branch", "--show-current"],
        "status": ["git", "-C", str(repo), "status", "--short"],
    }.items():
        completed = subprocess.run(argv, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise GateViolation(f"cannot fingerprint repository: {repo.name}")
        values[key] = completed.stdout.rstrip("\n")
    return {**values, "dirty": bool(values["status"])}


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise GateViolation(f"cannot hash missing campaign input: {path.name}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(root: Path, entries: tuple[Path, ...]) -> str:
    files: list[Path] = []
    for entry in entries:
        if entry.is_file():
            files.append(entry)
        elif entry.is_dir():
            files.extend(
                path
                for path in entry.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            )
        else:
            raise GateViolation(f"cannot hash missing campaign input: {entry.name}")
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()
