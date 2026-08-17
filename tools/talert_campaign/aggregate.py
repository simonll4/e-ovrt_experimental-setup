from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .model import GateViolation


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise GateViolation("cannot compute percentile over an empty sample")
    if not 0 < percentile <= 1:
        raise GateViolation("percentile must be in (0, 1]")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def aggregate_attempt(
    attempt: Path, *, allow_completed: bool = False
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Agrega un intento a partir de sus artefactos de fase.

    Por defecto sólo agrega un intento `prepared`: la campaña avanza en un sentido y
    re-agregar sobre un intento vivo escondería una corrida. `allow_completed=True`
    habilita la re-agregación de un intento ya publicado (`succeeded`) para un caso
    concreto y declarado: **regenerar el candidato cuando el propio agregador cambió**
    (p. ej. al incorporar bloques nuevos como `steady_state` o `payload_bytes`). Las
    fases de origen son inmutables, así que la re-agregación es determinista y no puede
    inventar muestras; lo que hace es devolverle procedencia a un artefacto publicado.
    """
    attempt = attempt.resolve()
    attempt_state = _load_json(attempt / "attempt.json")
    status = attempt_state.get("status")
    allowed = {"prepared", "succeeded"} if allow_completed else {"prepared"}
    if status not in allowed:
        raise GateViolation(
            "only a prepared or already published attempt can be re-aggregated"
            if allow_completed
            else "only a prepared attempt can be aggregated"
        )
    primary, primary_rows = _aggregate_series(attempt, "primary")
    supplemental, supplemental_rows = _aggregate_series(attempt, "supplemental")
    if (primary["runs"], primary["nonempty_runs"], primary["events"]) != (413, 356, 836):
        raise GateViolation("primary aggregate corpus drift")
    if (supplemental["runs"], supplemental["nonempty_runs"], supplemental["events"]) != (
        544,
        440,
        574,
    ):
        raise GateViolation("supplemental aggregate corpus drift")
    latencies = [
        row["talert_notification_ms"]
        for row in primary_rows
        if row["eligible_primary"]
    ]
    if len(latencies) != primary["outcomes"].get("delivered", 0):
        raise GateViolation("primary delivered/eligible sample mismatch")
    by_origin: dict[str, list[float]] = defaultdict(list)
    for row in primary_rows:
        if row["eligible_primary"]:
            by_origin[row["origin"]].append(row["talert_notification_ms"])
    payload_bytes = [
        int(row["payload_bytes"]) for row in primary_rows if isinstance(row.get("payload_bytes"), (int, float))
    ]
    metrics = {
        "schema_version": "talert_notification_metrics.v1",
        "attempt_id": attempt_state["attempt_id"],
        "definition": "puback_wall_ms - ts_publish_ms",
        "scope": "control alert bus to MQTT QoS 1 PUBACK",
        "latency_mode": "live",
        "steady_state": _steady_state_metrics(primary_rows),
        "primary": {
            **primary,
            "latency_ms": _stats(latencies),
            "by_origin": {
                origin: _stats(values) for origin, values in sorted(by_origin.items())
            },
        },
        "supplemental": supplemental,
        "payload_bytes": _stats(payload_bytes),
        "measurement_tooling_sha256": attempt_state.get("hashes", {}).get("tooling_tree"),
        "status": "candidate",
    }
    return metrics, primary_rows + supplemental_rows


def _steady_state_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    first_delivery: list[float] = []
    subsequent: list[float] = []
    for row in rows:
        if row.get("series") != "primary":
            continue
        if not row.get("eligible_primary") or row.get("outcome") != "delivered":
            continue
        latency = row.get("talert_notification_ms")
        if not isinstance(latency, (int, float)) or not math.isfinite(latency):
            continue
        if bool(row.get("first_delivery")):
            first_delivery.append(float(latency))
        else:
            subsequent.append(float(latency))
    return {
        "first_delivery_per_run": _stats(first_delivery),
        "subsequent_deliveries": _stats(subsequent),
    }


def write_candidate(attempt: Path, metrics: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    metrics_path = attempt / "candidate-metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "series",
        "origin",
        "run_id",
        "alert_id",
        "notification_id",
        "record_index",
        "attempt",
        "outcome",
        "mode",
        "latency_mode",
        "talert_notification_ms",
        "witness_multiplicity",
        "payload_bytes",
        "first_delivery",
        "eligible_primary",
    ]
    with (attempt / "candidate-outcomes.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _aggregate_series(attempt: Path, series: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    phase = attempt / f"live-{series}"
    summary = _load_json(phase / "series-summary.json")
    witness = _load_json(phase / "witness.json")
    if summary.get("status") != "succeeded" or summary.get("sample") is not False:
        raise GateViolation(f"{series} series is not a successful full run")
    if witness.get("errors"):
        raise GateViolation(f"{series} witness contains errors")
    witness_messages = witness.get("messages")
    if not isinstance(witness_messages, list):
        raise GateViolation(f"{series} witness messages are invalid")
    multiplicity = Counter()
    payload_bytes: dict[str, int] = {}
    for message in witness_messages:
        if not isinstance(message, dict) or not isinstance(message.get("notification_id"), str):
            raise GateViolation(f"{series} witness message is invalid")
        notification_id = message["notification_id"]
        multiplicity[notification_id] += 1
        payload_bytes.setdefault(notification_id, int(message.get("payload_bytes", 0)))

    run_rows = summary.get("runs")
    if not isinstance(run_rows, list):
        raise GateViolation(f"{series} summary runs are invalid")
    rows: list[dict[str, Any]] = []
    outcomes: Counter[str] = Counter()
    expected_ids: set[str] = set()
    nonempty = 0
    events = 0
    origins: Counter[str] = Counter()
    for run in run_rows:
        if not isinstance(run, dict):
            raise GateViolation(f"{series} run summary is invalid")
        run_id = run.get("run_id")
        origin = run.get("origin")
        if not isinstance(run_id, str) or not isinstance(origin, str):
            raise GateViolation(f"{series} run identity is invalid")
        run_events = int(run.get("events", -1))
        if run_events < 0:
            raise GateViolation(f"{series} run event count is invalid")
        events += run_events
        nonempty += int(run_events > 0)
        origins[origin] += 1
        ledger_path = phase / run_id / "distribution/notifications.jsonl"
        records = _load_jsonl(ledger_path, missing_ok=run_events == 0)
        if len(records) != run_events:
            raise GateViolation(f"{run_id}: aggregate ledger/event mismatch")
        first_delivery_seen = False
        for index, record in enumerate(records):
            outcome = record.get("outcome")
            if not isinstance(outcome, str):
                raise GateViolation(f"{run_id}: invalid outcome")
            outcomes[outcome] += 1
            notification_id = record.get("notification_id")
            if not isinstance(notification_id, str):
                raise GateViolation(f"{run_id}: invalid notification_id")
            delivered = outcome == "delivered"
            if delivered:
                expected_ids.add(notification_id)
                if multiplicity[notification_id] < 1:
                    raise GateViolation(f"{run_id}: delivered ID absent from witness")
                latency = record.get("talert_notification_ms")
                if (
                    record.get("mode") != "live"
                    or record.get("latency_mode") != "live"
                    or not isinstance(latency, (int, float))
                    or not math.isfinite(latency)
                    or latency < 0
                ):
                    raise GateViolation(f"{run_id}: ineligible delivered record")
            else:
                latency = record.get("talert_notification_ms")
            first_delivery = delivered and not first_delivery_seen
            first_delivery_seen = first_delivery_seen or delivered
            rows.append(
                {
                    "series": series,
                    "origin": origin,
                    "run_id": run_id,
                    "alert_id": record.get("alert_id"),
                    "notification_id": notification_id,
                    "record_index": index,
                    "attempt": record.get("attempt"),
                    "outcome": outcome,
                    "mode": record.get("mode"),
                    "latency_mode": record.get("latency_mode"),
                    "talert_notification_ms": latency,
                    "witness_multiplicity": multiplicity[notification_id],
                    "payload_bytes": payload_bytes.get(notification_id),
                    "first_delivery": first_delivery,
                    "eligible_primary": series == "primary" and delivered,
                }
            )
    observed_ids = set(multiplicity)
    if observed_ids != expected_ids:
        unexpected = observed_ids - expected_ids
        missing = expected_ids - observed_ids
        detail = min(unexpected or missing)
        raise GateViolation(f"{series} witness ID set mismatch: {detail}")
    totals = summary.get("totals", {})
    if dict(outcomes) != {
        key: value for key, value in totals.items() if key not in {"runs", "nonempty_runs", "events"}
    }:
        raise GateViolation(f"{series} outcome totals mismatch")
    result = {
        "runs": len(run_rows),
        "nonempty_runs": nonempty,
        "events": events,
        "outcomes": dict(sorted(outcomes.items())),
        "witness_messages": len(witness_messages),
        "witness_unique_ids": len(observed_ids),
        "mqtt_duplicates": sum(count - 1 for count in multiplicity.values()),
        "origins": dict(sorted(origins.items())),
    }
    return result, rows


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise GateViolation("cannot summarize an empty latency sample")
    return {
        "count": len(values),
        "min": min(values),
        "mean": statistics.fmean(values),
        "p50": nearest_rank(values, 0.50),
        "p95": nearest_rank(values, 0.95),
        "p99": nearest_rank(values, 0.99),
        "max": max(values),
    }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot load aggregate artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise GateViolation(f"aggregate artifact is not an object: {path.name}")
    return value


def _load_jsonl(path: Path, *, missing_ok: bool) -> list[dict[str, Any]]:
    if missing_ok and not path.exists():
        return []
    try:
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot load aggregate ledger: {path.parent.parent.name}") from exc
    if not all(isinstance(value, dict) for value in values):
        raise GateViolation(f"aggregate ledger contains a non-object: {path.parent.parent.name}")
    return values
