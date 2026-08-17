from __future__ import annotations

import pytest

from tools.talert_campaign.mqtt_witness import GateViolation, MqttWitness
from tools.talert_campaign.model import WitnessMessage


def _witness_message(notification_id: str) -> WitnessMessage:
    return WitnessMessage(
        notification_id=notification_id,
        control_run_id="cr",
        topic="eovrt/alerts/high",
        qos=1,
        payload_bytes=100,
        received_at="2026-01-01T00:00:00Z",
    )


def test_wait_for_ids_with_expired_deadline_raises_gate_violation():
    witness = MqttWitness("127.0.0.1", 1883)
    with pytest.raises(GateViolation) as exc:
        witness.wait_for_ids({"n1"}, timeout_s=0.0)
    assert "missing notification IDs" in str(exc.value)


def test_wait_for_ids_returns_when_expected_messages_already_present():
    witness = MqttWitness("127.0.0.1", 1883)
    witness._messages.extend([_witness_message("n1"), _witness_message("n2")])
    witness.wait_for_ids({"n1", "n2"}, timeout_s=0.0)


def test_snapshot_includes_message_multiplicity():
    witness = MqttWitness("127.0.0.1", 1883)
    witness._messages.extend(
        [_witness_message("n1"), _witness_message("n1"), _witness_message("n2")]
    )

    snapshot = witness.snapshot()
    assert snapshot["multiplicity"] == {"n1": 2, "n2": 1}


def test_wait_for_ids_raises_gate_violation_on_internal_error():
    witness = MqttWitness("127.0.0.1", 1883)
    witness._errors.append("boom interno")

    with pytest.raises(GateViolation) as exc:
        witness.wait_for_ids({"n1"}, timeout_s=0.1)
    assert "boom interno" in str(exc.value)
