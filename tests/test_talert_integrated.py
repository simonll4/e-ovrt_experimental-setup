from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.talert_campaign.config import CampaignConfig
from tools.talert_campaign.integrated import _camera_result, materialize_video_manifest
from tools.talert_campaign.model import GateViolation


def test_materialized_video_manifest_is_portable_and_contract_valid(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    config = CampaignConfig.load(
        repo / "experiments/t_alert_notification/campaign.yaml", repo
    )
    manifest = materialize_video_manifest(
        config,
        tmp_path,
        repo / "experiments/t_alert_notification/video",
        clip_id="a_p1_c08",
        label="admission-1",
    )
    text = manifest.read_text(encoding="utf-8")
    assert "${" not in text
    assert "a_p1_c08" in text
    assert (manifest.parent / "media.yaml").is_file()
    assert (manifest.parent / "control.yaml").is_file()


def test_camera_result_accepts_successful_negative_smoke(tmp_path: Path) -> None:
    consolidated = tmp_path / "consolidated"
    distribution = consolidated / "distribution"
    distribution.mkdir(parents=True)
    (distribution / "distribution_summary.json").write_text(
        json.dumps(
            {
                "counts": {},
                "skipped_invalid_alerts": 0,
                "source_stats": {
                    "termination_reason": "run_finished",
                    "bus_dropped_events": 0,
                    "skipped_malformed": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "resultados": [
                    {
                        "name": "t_alert-notification",
                        "status": "applicable_not_computed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    execution = SimpleNamespace(
        ok=True,
        experiment_id="exp_camera",
        media_run_id="media_camera",
        control_run_id="control_camera",
        media_status="succeeded",
        control_status="succeeded",
        distribution_status="succeeded",
        consolidated_dir=str(consolidated),
        report_path=str(report),
    )

    result = _camera_result(execution)

    assert result["delivered"] == 0
    assert result["cause"] == "no_confirmed_alert"


def test_camera_result_rejects_infrastructure_failure() -> None:
    execution = SimpleNamespace(
        ok=False,
        experiment_id="exp_camera",
        media_run_id=None,
        control_run_id=None,
        media_status="failed",
        control_status="not_started",
        distribution_status="not_started",
        consolidated_dir=None,
        report_path=None,
    )

    with pytest.raises(GateViolation, match="integrated run failed"):
        _camera_result(execution)
