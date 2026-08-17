from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.talert_campaign.model import CorpusRun, GateViolation
from tools.talert_campaign.workflows import _gate_replay, _load_jsonl, create_attempt


def _run(tmp_path: Path) -> CorpusRun:
    return CorpusRun(
        run_id="run-1",
        series="primary_dbe",
        origin="dbe",
        archive_dir=tmp_path,
        alerts_gzip=tmp_path / "alerts.jsonl.gz",
        result_ids=("result",),
    )


def _summary(read: int, counts: dict[str, int], mode: str = "wall_clock_dbe") -> dict:
    return {
        "counts": counts,
        "source_stats": {"read": read, "skipped_malformed": 0},
        "skipped_invalid_alerts": 0,
        "talert_notification_ms": ({mode: {"count": counts.get("delivered", 0)}} if counts else None),
    }


def test_attempt_is_new_and_immutable(tmp_path: Path) -> None:
    attempt = create_attempt(tmp_path, "rehearsal-01")
    assert json.loads((attempt / "attempt.json").read_text())["status"] == "prepared"
    with pytest.raises(GateViolation, match="already exists"):
        create_attempt(tmp_path, "rehearsal-01")


def test_replay_gate_accepts_stateful_idempotence(tmp_path: Path) -> None:
    first = _summary(2, {"delivered": 1, "suppressed_cooldown": 1})
    second = _summary(2, {"skipped_duplicate": 1, "suppressed_cooldown": 1})
    _gate_replay(_run(tmp_path), 2, first, second)


def test_replay_gate_rejects_redelivery_and_live_latency(tmp_path: Path) -> None:
    first = _summary(1, {"delivered": 1})
    with pytest.raises(GateViolation, match="redelivered"):
        _gate_replay(_run(tmp_path), 1, first, _summary(1, {"delivered": 1}))
    with pytest.raises(GateViolation, match="live latency"):
        _gate_replay(
            _run(tmp_path),
            1,
            _summary(1, {"delivered": 1}, mode="live"),
            _summary(1, {"skipped_duplicate": 1}),
        )


def test_missing_notifications_ledger_is_valid_only_for_empty_run(tmp_path: Path) -> None:
    missing = tmp_path / "notifications.jsonl"
    assert _load_jsonl(missing, missing_ok=True) == []
    with pytest.raises(GateViolation, match="cannot read JSONL"):
        _load_jsonl(missing)
