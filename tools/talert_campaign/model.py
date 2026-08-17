from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Series = Literal["primary_dbe", "primary_ebe", "supplemental"]
AttemptStatus = Literal["prepared", "running", "succeeded", "invalid", "aborted"]


class GateViolation(RuntimeError):
    """Invariante de campaña incumplido; el mensaje es seguro para el operador."""


@dataclass(frozen=True)
class CorpusRun:
    run_id: str
    series: Series
    origin: Literal["dbe", "ebe", "derived_ebe"]
    archive_dir: Path
    alerts_gzip: Path
    result_ids: tuple[str, ...]


@dataclass(frozen=True)
class AlertFileStats:
    lines: int
    valid: int
    alert_ids: tuple[str, ...]
    gzip_sha256: str
    jsonl_sha256: str


@dataclass(frozen=True)
class AttemptState:
    attempt_id: str
    status: AttemptStatus
    root: Path


@dataclass(frozen=True)
class RunExecution:
    run_id: str
    series: Series
    status: Literal["succeeded", "invalid"]
    output_dir: Path
    reason: str | None = None


@dataclass(frozen=True)
class WitnessMessage:
    notification_id: str
    control_run_id: str
    topic: str
    qos: int
    payload_bytes: int
    received_at: str
