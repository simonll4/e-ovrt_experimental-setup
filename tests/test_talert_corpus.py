from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from tools.talert_campaign.corpus import (
    classify_run,
    stage_alerts,
    validate_alerts,
)
from tools.talert_campaign.model import GateViolation


def _relation(role: str, collection: str) -> dict:
    return {
        "role": role,
        "collection": collection,
        "result_id": "result/example",
        "source_ref": "source.json",
    }


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (_relation("campaign_control", "dbe_video"), "primary_dbe"),
        (_relation("rodaje_ebe_final", "ebe_realtime"), "primary_ebe"),
        (_relation("control_replay_empirico", "ebe_realtime"), "supplemental"),
    ],
)
def test_classifies_only_declared_groups(relation: dict, expected: str) -> None:
    row = {"plane": "control-plane", "status": "copied", "relations": [relation]}
    assert classify_run(row) == expected


def test_rejects_unknown_copied_control_group() -> None:
    row = {
        "plane": "control-plane",
        "status": "copied",
        "relations": [_relation("unknown", "ebe_realtime")],
    }
    with pytest.raises(GateViolation, match="unclassified"):
        classify_run(row)


def _alert(alert_id: str = "alert-001") -> dict:
    return {
        "schema_version": "control.alert.v1",
        "event_type": "alert_event",
        "control_run_id": "control-1",
        "media_run_id": "media-1",
        "alert_id": alert_id,
        "pattern_id": "cr01",
        "condition_id": "no_helmet",
        "source_id": "source-1",
        "subject_key": "person-1",
        "severity": "high",
        "state": "open",
        "timestamp_ms": 1000.0,
        "experiment_id": "experiment-1",
    }


def test_stages_gzip_without_modifying_archive(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    source = archive / "alerts.jsonl.gz"
    original = (json.dumps(_alert()) + "\n").encode()
    source.write_bytes(gzip.compress(original, mtime=0))
    from tools.talert_campaign.model import CorpusRun

    run = CorpusRun(
        run_id="control-1",
        series="primary_dbe",
        origin="dbe",
        archive_dir=archive,
        alerts_gzip=source,
        result_ids=("result/example",),
    )

    staged = stage_alerts(run, tmp_path / "staging")

    assert staged.read_bytes() == original
    assert gzip.decompress(source.read_bytes()) == original
    assert validate_alerts(staged).valid == 1


def test_rejects_invalid_contract_and_duplicate_ids(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text('{"schema_version":"wrong"}\n', encoding="utf-8")
    with pytest.raises(GateViolation, match="line 1"):
        validate_alerts(invalid)

    duplicate = tmp_path / "duplicate.jsonl"
    line = json.dumps(_alert())
    duplicate.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(GateViolation, match="duplicate alert_id"):
        validate_alerts(duplicate)


def test_rejects_corrupt_gzip(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    source = archive / "alerts.jsonl.gz"
    source.write_bytes(b"not-gzip")
    from tools.talert_campaign.model import CorpusRun

    run = CorpusRun(
        run_id="control-1",
        series="primary_dbe",
        origin="dbe",
        archive_dir=archive,
        alerts_gzip=source,
        result_ids=("result/example",),
    )
    with pytest.raises(GateViolation, match="gzip"):
        stage_alerts(run, tmp_path / "staging")
