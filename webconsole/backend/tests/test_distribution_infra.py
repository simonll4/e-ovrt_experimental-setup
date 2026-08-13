from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_mqtt_broker_is_scoped_to_loopback_for_single_host_lab() -> None:
    compose = yaml.safe_load(
        (REPO_ROOT / "infra" / "platform" / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
    )
    broker = compose["services"]["mosquitto"]

    assert broker["ports"] == ["127.0.0.1:1883:1883"]
    assert broker["healthcheck"]["test"][-2:] == ["-q", "1"]

    amqtt = yaml.safe_load(
        (REPO_ROOT / "infra" / "platform" / "mosquitto" / "amqtt.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert amqtt["listeners"]["default"]["bind"] == "127.0.0.1:1883"
