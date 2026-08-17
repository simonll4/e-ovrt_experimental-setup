from __future__ import annotations

import pytest

from tools.talert_campaign.aggregate import _steady_state_metrics, nearest_rank
from tools.talert_campaign.model import GateViolation


def test_nearest_rank_percentiles() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert nearest_rank(values, 0.50) == 30.0
    assert nearest_rank(values, 0.95) == 50.0
    assert nearest_rank(values, 0.99) == 50.0
    assert nearest_rank([7.0], 0.95) == 7.0


@pytest.mark.parametrize("percentile", [0, -0.1, 1.1])
def test_nearest_rank_rejects_invalid_percentile(percentile: float) -> None:
    with pytest.raises(GateViolation):
        nearest_rank([1.0], percentile)


def test_nearest_rank_rejects_empty_values() -> None:
    with pytest.raises(GateViolation):
        nearest_rank([], 0.95)


def test_steady_state_splits_first_delivery_per_run_from_subsequent() -> None:
    rows = [
        {
            "series": "primary",
            "eligible_primary": True,
            "outcome": "delivered",
            "first_delivery": True,
            "talert_notification_ms": 10.0,
        },
        {
            "series": "primary",
            "eligible_primary": True,
            "outcome": "delivered",
            "first_delivery": False,
            "talert_notification_ms": 100.0,
        },
        {
            "series": "primary",
            "eligible_primary": True,
            "outcome": "delivered",
            "first_delivery": False,
            "talert_notification_ms": 110.0,
        },
        {
            "series": "primary",
            "eligible_primary": True,
            "outcome": "delivered",
            "first_delivery": True,
            "talert_notification_ms": 12.0,
        },
        {
            "series": "primary",
            "eligible_primary": True,
            "outcome": "delivered",
            "first_delivery": False,
            "talert_notification_ms": 90.0,
        },
    ]

    metrics = _steady_state_metrics(rows)

    assert metrics["first_delivery_per_run"]["count"] == 2
    assert metrics["subsequent_deliveries"]["count"] == 3
    assert metrics["subsequent_deliveries"]["p95"] == 110.0
