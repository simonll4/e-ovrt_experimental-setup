"""Tests del modelo de aplicabilidad + join t_capture->alert (spec 40 SS5.2.4, ADR-006)."""
from __future__ import annotations

from eovrt_webconsole.experiment.applicability import (
    APPLICABILITY_STATES,
    MetricResult,
    join_capture_to_alert,
)


def test_applicability_states_enum_exacto():
    assert APPLICABILITY_STATES == (
        "computed",
        "applicable_not_computed",
        "not_applicable",
        "not_interpretable",
    )


def test_metric_result_acepta_status_valido():
    m = MetricResult(name="G2A", value=12.5, unit="ms", status="computed", cause=None)
    assert m.status == "computed"
    assert m.value == 12.5


def test_wallclock_single_host_computed_con_join_ns_a_ms():
    # capture_monotonic_ns=1_000_000_000 -> 1000.0 ms; alert_registered_ms=1500.0
    # t_capture_to_alert_ms = 1500.0 - 1000.0 = 500.0
    alerts = [
        {
            "alert_id": "al-1",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": 1500.0,
            "first_evidence_ms": 1000.0,
            "confirmed_at_ms": 1200.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="wallclock")

    assert len(out) == 1
    row = out[0]
    assert row["alert_id"] == "al-1"
    assert row["first_evidence_unit_id"] == "u1"
    assert row["status"] == "computed"
    assert row["cause"] is None
    assert row["t_capture_to_alert_ms"] == 500.0
    # T_persistencia_efectiva = confirmed_at_ms - first_evidence_ms = 200.0
    # t_compute_budget_ms = 500.0 - 200.0 = 300.0
    assert row["t_compute_budget_ms"] == 300.0


def test_wallclock_sin_confirmed_at_t_compute_budget_none():
    alerts = [
        {
            "alert_id": "al-2",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": 1500.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="wallclock")

    row = out[0]
    assert row["status"] == "computed"
    assert row["t_capture_to_alert_ms"] == 500.0
    assert row["t_compute_budget_ms"] is None


def test_source_clock_media_not_interpretable_pero_compute_budget_computed():
    alerts = [
        {
            "alert_id": "al-3",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": 1500.0,
            "first_evidence_ms": 1000.0,
            "confirmed_at_ms": 1200.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="media")

    row = out[0]
    assert row["status"] == "not_interpretable"
    assert row["cause"] == "dbe_media_time"
    assert row["t_capture_to_alert_ms"] is None
    # t_compute_budget sigue siendo computable: aca no depende de t_capture_to_alert
    # (T_persistencia_efectiva=200.0), y se resta al mismo t_capture calculado
    # a partir de los monotonicos disponibles.
    assert row["t_compute_budget_ms"] == 300.0


def test_source_clock_media_sin_monotonicos_compute_budget_none():
    alerts = [
        {
            "alert_id": "al-4",
            "first_evidence_unit_id": "u2",
            "alert_registered_ms": 1500.0,
            "first_evidence_ms": 1000.0,
            "confirmed_at_ms": 1200.0,
        }
    ]
    media_metrics_by_unit: dict[str, dict] = {}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="media")

    row = out[0]
    assert row["status"] == "not_interpretable"
    assert row["cause"] == "dbe_media_time"
    assert row["t_capture_to_alert_ms"] is None
    assert row["t_compute_budget_ms"] is None


def test_source_clock_none_not_applicable_non_temporal_source():
    alerts = [
        {
            "alert_id": "al-5",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": 1500.0,
            "first_evidence_ms": 1000.0,
            "confirmed_at_ms": 1200.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="none")

    row = out[0]
    assert row["status"] == "not_applicable"
    assert row["cause"] == "non_temporal_source"
    assert row["t_capture_to_alert_ms"] is None
    # t_compute_budget sigue siendo computed (fuente no temporal, pero
    # los monotonicos del media-plane siguen disponibles)
    assert row["t_compute_budget_ms"] == 300.0


def test_two_node_not_interpretable_clock_skew():
    alerts = [
        {
            "alert_id": "al-6",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": 1500.0,
            "first_evidence_ms": 1000.0,
            "confirmed_at_ms": 1200.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(
        alerts, media_metrics_by_unit, source_clock="wallclock", two_node=True
    )

    row = out[0]
    assert row["status"] == "not_interpretable"
    assert row["cause"] == "clock_skew"
    assert row["t_capture_to_alert_ms"] is None
    assert row["t_compute_budget_ms"] is None


def test_missing_unit_id_en_alerta_applicable_not_computed():
    alerts = [
        {
            "alert_id": "al-7",
            "first_evidence_unit_id": None,
            "alert_registered_ms": 1500.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="wallclock")

    row = out[0]
    assert row["status"] == "applicable_not_computed"
    assert row["cause"] == "missing_join_key"
    assert row["t_capture_to_alert_ms"] is None
    assert row["t_compute_budget_ms"] is None


def test_unit_id_no_presente_en_media_metrics_applicable_not_computed():
    alerts = [
        {
            "alert_id": "al-8",
            "first_evidence_unit_id": "u-no-existe",
            "alert_registered_ms": 1500.0,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="wallclock")

    row = out[0]
    assert row["status"] == "applicable_not_computed"
    assert row["cause"] == "missing_join_key"


def test_alert_registered_ms_none_applicable_not_computed():
    alerts = [
        {
            "alert_id": "al-9",
            "first_evidence_unit_id": "u1",
            "alert_registered_ms": None,
        }
    ]
    media_metrics_by_unit = {"u1": {"capture_monotonic_ns": 1_000_000_000}}

    out = join_capture_to_alert(alerts, media_metrics_by_unit, source_clock="wallclock")

    row = out[0]
    assert row["status"] == "applicable_not_computed"
    assert row["cause"] == "missing_join_key"
