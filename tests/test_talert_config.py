from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.talert_campaign.config import CampaignConfig
from tools.talert_campaign.model import GateViolation


def _manifest() -> dict:
    return {
        "schema_version": "talert_notification_campaign.v1",
        "python": "3.11",
        "broker": {
            "implementation": "amqtt",
            "version": "0.11.3",
            "host": "127.0.0.1",
            "port": 1883,
        },
        "bus": {
            "endpoint": "tcp://127.0.0.1:5558",
            "subscriptions_expected": 2,
        },
        "mqtt": {"topic_prefix": "eovrt/alerts", "qos": 1},
        "policy": {"cooldown_ms": 30000, "key": ["condition_id", "source_id"]},
        "corpus": {
            "resolved_runs": "results/evidence-runs/resolved-runs.json",
            "expected": {"copied_runs": 957, "nonempty_runs": 796, "events": 1410},
            "primary": {"runs": 413, "nonempty_runs": 356, "events": 836},
            "supplemental": {"runs": 544, "nonempty_runs": 440, "events": 574},
        },
    }


def _write(tmp_path: Path, data: dict) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    target = repo / "results/evidence-runs/resolved-runs.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"runs": []}\n', encoding="utf-8")
    path = repo / "campaign.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path, repo


def test_loads_strict_campaign_manifest(tmp_path: Path) -> None:
    path, repo = _write(tmp_path, _manifest())

    cfg = CampaignConfig.load(path, repo)

    assert cfg.python == "3.11"
    assert cfg.broker.version == "0.11.3"
    assert cfg.bus.endpoint == "tcp://127.0.0.1:5558"
    assert cfg.mqtt.qos == 1
    assert cfg.corpus.primary.events == 836
    assert cfg.corpus.resolved_runs == (repo / "results/evidence-runs/resolved-runs.json")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schema_version="other.v1"), "schema_version"),
        (lambda d: d.update(python="3.12"), "python"),
        (lambda d: d["broker"].update(host="0.0.0.0"), "broker.host"),
        (lambda d: d["broker"].update(version="0.11.2"), "broker.version"),
        (lambda d: d["bus"].update(endpoint="tcp://0.0.0.0:5558"), "bus.endpoint"),
        (lambda d: d["mqtt"].update(qos=0), "mqtt.qos"),
        (lambda d: d["corpus"]["primary"].update(runs=412), "corpus.primary.runs"),
        (lambda d: d.update(unexpected=True), "unexpected"),
        (lambda d: d["broker"].update(unexpected=True), "broker.unexpected"),
    ],
)
def test_rejects_manifest_drift(tmp_path: Path, mutate, message: str) -> None:
    data = _manifest()
    mutate(data)
    path, repo = _write(tmp_path, data)

    with pytest.raises(GateViolation, match=message.replace(".", r"\.")):
        CampaignConfig.load(path, repo)


def test_rejects_resolved_runs_outside_repo(tmp_path: Path) -> None:
    data = _manifest()
    data["corpus"]["resolved_runs"] = "../outside.json"
    path, repo = _write(tmp_path, data)

    with pytest.raises(GateViolation, match="contained"):
        CampaignConfig.load(path, repo)
