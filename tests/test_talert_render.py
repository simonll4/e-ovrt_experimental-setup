from __future__ import annotations

from tools.talert_campaign.render import _curate_integrated_row


def test_curated_integrated_row_removes_local_paths() -> None:
    row = {
        "label": "repetition-1",
        "clip_id": "a_p1_c08",
        "experiment_id": "exp_test",
        "media_run_id": "media_test",
        "control_run_id": "control_test",
        "delivered": 1,
        "delivered_ids": ["notification_test"],
        "latency_p95_ms": 42.0,
        "report_metric": {"status": "computed", "value": 42.0},
        "status": "succeeded",
        "consolidated_dir": "/private/run",
        "report_path": "/private/report.json",
    }

    result = _curate_integrated_row(row)

    assert "consolidated_dir" not in result
    assert "report_path" not in result
    assert result["latency_p95_ms"] == 42.0
