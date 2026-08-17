from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from eovrt_distribution.contracts.notification import NotificationEnvelope

from .config import CampaignConfig
from .model import AlertFileStats, CorpusRun, GateViolation, Series

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_PRIMARY_EBE_ROLES = {
    "claqueta_y_guards_negativos",
    "ensayo_ebe_1a1",
    "rodaje_ebe_final",
    "smoke_ebe_post_cambios",
}


def classify_run(resolved: dict[str, Any]) -> Series:
    """Clasifica un control copiado; cualquier grupo nuevo requiere decisión explícita."""
    if resolved.get("plane") != "control-plane" or resolved.get("status") != "copied":
        raise GateViolation("only copied control-plane runs can be classified")
    relations = resolved.get("relations")
    if not isinstance(relations, list):
        raise GateViolation("copied control-plane run has invalid relations")

    candidates: set[Series] = set()
    for relation in relations:
        if not isinstance(relation, dict):
            raise GateViolation("copied control-plane run has invalid relation")
        role = relation.get("role")
        collection = relation.get("collection")
        if role == "campaign_control" and collection == "dbe_video":
            candidates.add("primary_dbe")
        elif role == "control_replay_empirico" and collection == "ebe_realtime":
            candidates.add("supplemental")
        elif role in _PRIMARY_EBE_ROLES and collection == "ebe_realtime":
            candidates.add("primary_ebe")

    run_id = resolved.get("run_id", "<unknown>")
    if not candidates:
        raise GateViolation(f"unclassified copied control-plane run: {run_id}")
    if len(candidates) != 1:
        raise GateViolation(f"ambiguous campaign series for run: {run_id}")
    return next(iter(candidates))


def load_corpus(config: CampaignConfig) -> tuple[CorpusRun, ...]:
    try:
        payload = json.loads(config.corpus.resolved_runs.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot read resolved-runs.json: {exc}") from exc
    rows = payload.get("runs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise GateViolation("resolved-runs.json must contain a runs list")

    archive_root = config.corpus.resolved_runs.parent.resolve()
    result: list[CorpusRun] = []
    seen_runs: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise GateViolation("resolved-runs.json contains a non-object run")
        if row.get("plane") != "control-plane" or row.get("status") != "copied":
            continue
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not _SAFE_RUN_ID.fullmatch(run_id):
            raise GateViolation("copied control-plane run has an unsafe run_id")
        if run_id in seen_runs:
            raise GateViolation(f"duplicate run_id in corpus: {run_id}")
        seen_runs.add(run_id)
        series = classify_run(row)
        archive_path = row.get("archive_path")
        if not isinstance(archive_path, str):
            raise GateViolation(f"missing archive_path for run: {run_id}")
        archive_dir = (archive_root / archive_path).resolve()
        if archive_dir == archive_root or archive_root not in archive_dir.parents:
            raise GateViolation(f"archive_path escapes curated archive: {run_id}")
        alerts_gzip = archive_dir / "alerts.jsonl.gz"
        if not alerts_gzip.is_file():
            raise GateViolation(f"missing alerts.jsonl.gz for run: {run_id}")
        relation_rows = row.get("relations", [])
        result_ids = tuple(
            sorted(
                {
                    relation["result_id"]
                    for relation in relation_rows
                    if isinstance(relation, dict) and isinstance(relation.get("result_id"), str)
                }
            )
        )
        origin = {
            "primary_dbe": "dbe",
            "primary_ebe": "ebe",
            "supplemental": "derived_ebe",
        }[series]
        result.append(
            CorpusRun(
                run_id=run_id,
                series=series,
                origin=origin,
                archive_dir=archive_dir,
                alerts_gzip=alerts_gzip,
                result_ids=result_ids,
            )
        )
    return tuple(sorted(result, key=lambda run: (run.series, run.run_id)))


def stage_alerts(run: CorpusRun, temp_root: Path) -> Path:
    temp_root = temp_root.resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    target_dir = temp_root / run.run_id
    try:
        target_dir.mkdir()
    except FileExistsError as exc:
        raise GateViolation(f"staging already exists for run: {run.run_id}") from exc
    target = target_dir / "alerts.jsonl"
    try:
        with gzip.open(run.alerts_gzip, "rb") as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
    except (OSError, EOFError) as exc:
        target.unlink(missing_ok=True)
        raise GateViolation(f"invalid gzip for run {run.run_id}: {exc}") from exc
    return target


def validate_alerts(path: Path) -> AlertFileStats:
    alert_ids: list[str] = []
    seen: set[str] = set()
    hasher = hashlib.sha256()
    lines = 0
    try:
        with path.open("rb") as stream:
            for raw_line in stream:
                lines += 1
                hasher.update(raw_line)
                if not raw_line.strip():
                    raise GateViolation(f"{path.name}: line {lines}: blank line")
                try:
                    parsed = json.loads(raw_line)
                    envelope = NotificationEnvelope.from_alert(parsed)
                except Exception as exc:
                    raise GateViolation(f"{path.name}: line {lines}: invalid alert contract") from exc
                if envelope.alert_id in seen:
                    raise GateViolation(
                        f"{path.name}: line {lines}: duplicate alert_id {envelope.alert_id}"
                    )
                seen.add(envelope.alert_id)
                alert_ids.append(envelope.alert_id)
    except OSError as exc:
        raise GateViolation(f"cannot read staged alerts: {path.name}: {exc}") from exc
    return AlertFileStats(
        lines=lines,
        valid=len(alert_ids),
        alert_ids=tuple(alert_ids),
        gzip_sha256="",
        jsonl_sha256=hasher.hexdigest(),
    )


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
