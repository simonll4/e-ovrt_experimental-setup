from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from eovrt_control.transport.alert_bus import ALERT_TOPIC_PREFIX, AlertBusPublisher

from .model import GateViolation


@dataclass(frozen=True)
class PublishStats:
    control_run_id: str
    alerts: int
    send_failures: int
    subscriptions_ready: bool
    sentinel_sent: bool


def publish_run(
    alerts: Iterable[dict],
    control_run_id: str,
    endpoint: str,
    *,
    readiness_timeout_ms: int = 5000,
    subscriptions_expected: int = 2,
) -> PublishStats:
    """Republica un run con timestamps nuevos usando el publisher productivo."""
    publisher = AlertBusPublisher(endpoint)
    ready = False
    count = 0
    sentinel_sent = False
    try:
        ready = publisher.wait_for_subscriber(
            readiness_timeout_ms, expected=subscriptions_expected
        )
        if not ready:
            raise GateViolation(
                f"publisher readiness incomplete: expected {subscriptions_expected} subscriptions"
            )
        for alert in alerts:
            if alert.get("control_run_id") != control_run_id:
                raise GateViolation(
                    f"alert control_run_id does not match series run: {control_run_id}"
                )
            payload = json.dumps(alert, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            publisher.publish(
                f"{ALERT_TOPIC_PREFIX}{control_run_id}",
                str(alert.get("source_id", control_run_id)),
                payload,
            )
            count += 1
        publisher.publish_run_finished(control_run_id, "completed")
        sentinel_sent = True
        if publisher.send_failures:
            raise GateViolation(f"publisher send_failures={publisher.send_failures}")
        return PublishStats(
            control_run_id=control_run_id,
            alerts=count,
            send_failures=publisher.send_failures,
            subscriptions_ready=ready,
            sentinel_sent=sentinel_sent,
        )
    finally:
        publisher.close()
