from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .model import GateViolation


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise GateViolation(f"{path} must be a mapping")
    return value


def _strict(data: dict[str, Any], expected: set[str], path: str) -> None:
    missing = expected - data.keys()
    if missing:
        raise GateViolation(f"{path}.{min(missing)} is required")
    extra = data.keys() - expected
    if extra:
        raise GateViolation(f"{path}.{min(extra)} is unexpected")


def _exact(value: Any, expected: Any, path: str) -> None:
    if value != expected or type(value) is not type(expected):
        raise GateViolation(f"{path} must be {expected!r}, got {value!r}")


@dataclass(frozen=True)
class BrokerConfig:
    implementation: str
    version: str
    host: str
    port: int


@dataclass(frozen=True)
class BusConfig:
    endpoint: str
    subscriptions_expected: int


@dataclass(frozen=True)
class MqttConfig:
    topic_prefix: str
    qos: int


@dataclass(frozen=True)
class PolicyConfig:
    cooldown_ms: int
    key: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedCounts:
    runs: int
    nonempty_runs: int
    events: int


@dataclass(frozen=True)
class CorpusConfig:
    resolved_runs: Path
    expected: ExpectedCounts
    primary: ExpectedCounts
    supplemental: ExpectedCounts


@dataclass(frozen=True)
class CampaignConfig:
    path: Path
    repo_root: Path
    schema_version: str
    python: str
    broker: BrokerConfig
    bus: BusConfig
    mqtt: MqttConfig
    policy: PolicyConfig
    corpus: CorpusConfig

    @classmethod
    def load(cls, path: Path, repo_root: Path) -> CampaignConfig:
        repo_root = repo_root.resolve()
        path = path.resolve()
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise GateViolation(f"cannot load campaign config: {path.name}: {exc}") from exc
        data = _mapping(raw, "campaign")
        _strict(
            data,
            {"schema_version", "python", "broker", "bus", "mqtt", "policy", "corpus"},
            "campaign",
        )
        _exact(data["schema_version"], "talert_notification_campaign.v1", "schema_version")
        _exact(data["python"], "3.11", "python")

        broker = _mapping(data["broker"], "broker")
        _strict(broker, {"implementation", "version", "host", "port"}, "broker")
        _exact(broker["implementation"], "amqtt", "broker.implementation")
        _exact(broker["version"], "0.11.3", "broker.version")
        _exact(broker["host"], "127.0.0.1", "broker.host")
        _exact(broker["port"], 1883, "broker.port")

        bus = _mapping(data["bus"], "bus")
        _strict(bus, {"endpoint", "subscriptions_expected"}, "bus")
        _exact(bus["endpoint"], "tcp://127.0.0.1:5558", "bus.endpoint")
        _exact(bus["subscriptions_expected"], 2, "bus.subscriptions_expected")
        parsed_bus = urlparse(bus["endpoint"])
        if parsed_bus.scheme != "tcp" or parsed_bus.hostname != "127.0.0.1":
            raise GateViolation("bus.endpoint must be loopback TCP")

        mqtt = _mapping(data["mqtt"], "mqtt")
        _strict(mqtt, {"topic_prefix", "qos"}, "mqtt")
        _exact(mqtt["topic_prefix"], "eovrt/alerts", "mqtt.topic_prefix")
        _exact(mqtt["qos"], 1, "mqtt.qos")

        policy = _mapping(data["policy"], "policy")
        _strict(policy, {"cooldown_ms", "key"}, "policy")
        _exact(policy["cooldown_ms"], 30000, "policy.cooldown_ms")
        if policy["key"] != ["condition_id", "source_id"]:
            raise GateViolation("policy.key must be ['condition_id', 'source_id']")

        corpus = _mapping(data["corpus"], "corpus")
        _strict(corpus, {"resolved_runs", "expected", "primary", "supplemental"}, "corpus")
        if not isinstance(corpus["resolved_runs"], str):
            raise GateViolation("corpus.resolved_runs must be a relative path")
        candidate = (repo_root / corpus["resolved_runs"]).resolve()
        if candidate == repo_root or repo_root not in candidate.parents:
            raise GateViolation("corpus.resolved_runs must be contained in the repository")
        if not candidate.is_file():
            raise GateViolation("corpus.resolved_runs does not exist")

        expected = _counts(corpus["expected"], "corpus.expected", (957, 796, 1410), copied=True)
        primary = _counts(corpus["primary"], "corpus.primary", (413, 356, 836))
        supplemental = _counts(
            corpus["supplemental"], "corpus.supplemental", (544, 440, 574)
        )
        return cls(
            path=path,
            repo_root=repo_root,
            schema_version=data["schema_version"],
            python=data["python"],
            broker=BrokerConfig(**broker),
            bus=BusConfig(**bus),
            mqtt=MqttConfig(**mqtt),
            policy=PolicyConfig(cooldown_ms=policy["cooldown_ms"], key=tuple(policy["key"])),
            corpus=CorpusConfig(
                resolved_runs=candidate,
                expected=expected,
                primary=primary,
                supplemental=supplemental,
            ),
        )


def _counts(
    value: Any,
    path: str,
    expected: tuple[int, int, int],
    *,
    copied: bool = False,
) -> ExpectedCounts:
    data = _mapping(value, path)
    runs_key = "copied_runs" if copied else "runs"
    _strict(data, {runs_key, "nonempty_runs", "events"}, path)
    for key, exact in zip((runs_key, "nonempty_runs", "events"), expected, strict=True):
        _exact(data[key], exact, f"{path}.{key}")
    return ExpectedCounts(
        runs=data[runs_key], nonempty_runs=data["nonempty_runs"], events=data["events"]
    )
