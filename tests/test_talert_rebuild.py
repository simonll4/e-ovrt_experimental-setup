"""Regeneración del artefacto publicado de `t_alert-notification`.

Estos tests existen por un defecto concreto (doc `operacion/119`): los bloques
`steady_state` y `payload_bytes` se habían insertado a mano sobre el `metrics.json`
publicado, de modo que el pipeline ya no podía reproducir el artefacto y regenerar el
README habría borrado el steady-state en silencio. Cubren los dos caminos que cierran
esa brecha y la plantilla que la causó.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.talert_campaign.model import GateViolation
from tools.talert_campaign.render import (
    _accepted_metrics,
    _readme,
    rebuild_curated_metrics,
)
from tools.talert_campaign.workflows import load_attempt


def _candidate_metrics() -> dict:
    return {
        "schema_version": "talert_notification_metrics.v1",
        "attempt_id": "official-test-01",
        "definition": "puback_wall_ms - ts_publish_ms",
        "latency_mode": "live",
        "status": "candidate",
        "steady_state": {
            "first_delivery_per_run": {
                "count": 2, "min": 10.0, "mean": 11.0,
                "p50": 10.0, "p95": 12.0, "p99": 12.0, "max": 12.0,
            },
            "subsequent_deliveries": {
                "count": 3, "min": 90.0, "mean": 100.0,
                "p50": 100.0, "p95": 110.0, "p99": 110.0, "max": 110.0,
            },
        },
        "payload_bytes": {
            "count": 5, "min": 1022, "mean": 1050.0,
            "p50": 1037, "p95": 1078, "p99": 1374, "max": 1835,
        },
        "primary": {
            "runs": 413,
            "nonempty_runs": 356,
            "events": 836,
            "outcomes": {"delivered": 460, "suppressed_cooldown": 376},
            "mqtt_duplicates": 0,
            "latency_ms": {
                "count": 5, "min": 10.0, "mean": 64.0,
                "p50": 40.0, "p95": 110.0, "p99": 110.0, "max": 110.0,
            },
        },
        "supplemental": {"runs": 544},
    }


def _curated_integrated() -> dict:
    return {
        "schema_version": "talert_integrated.v1",
        "status": "succeeded",
        "selected_clip": "a_p1_c08",
        "admissions": [],
        "repetitions": [
            {"label": f"repetition-{i}", "latency_p95_ms": 100.0 + i} for i in range(1, 4)
        ],
        "included_in_primary_aggregate": False,
    }


def _publish(tmp_path: Path) -> tuple[Path, Path]:
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "candidate-metrics.json").write_text(json.dumps(_candidate_metrics()))
    destination = tmp_path / "curated"
    destination.mkdir()
    (destination / "integrated-runs.json").write_text(json.dumps(_curated_integrated()))
    return attempt, destination


def test_accepted_metrics_derives_citable_cooldown_and_gates() -> None:
    accepted = _accepted_metrics(_candidate_metrics())

    assert accepted["status"] == "accepted"
    assert accepted["citable"] == {
        "name": "t_alert-notification",
        "statistic": "p95",
        "unit": "ms",
        "value": 110.0,
        "sample_size": 5,
    }
    assert accepted["primary"]["cooldown_rate"] == 376 / 836
    assert accepted["gates"]["mqtt_duplicates_zero"] is True


def test_rebuild_regenerates_metrics_and_readme(tmp_path: Path) -> None:
    attempt, destination = _publish(tmp_path)

    result = rebuild_curated_metrics(attempt, destination)

    assert result["status"] == "rebuilt"
    assert result["p95_ms"] == 110.0
    published = json.loads((destination / "metrics.json").read_text())
    assert published["status"] == "accepted"
    # los bloques que se habían insertado a mano ahora salen del candidato
    assert published["steady_state"]["subsequent_deliveries"]["p95"] == 110.0
    assert published["payload_bytes"]["p95"] == 1078
    assert (destination / "README.md").exists()


def test_rebuild_does_not_touch_provenance_or_corpus(tmp_path: Path) -> None:
    attempt, destination = _publish(tmp_path)
    for name in ("provenance.json", "corpus.json", "campaign.yaml", "outcomes.csv"):
        (destination / name).write_text("intocable")

    rebuild_curated_metrics(attempt, destination)

    for name in ("provenance.json", "corpus.json", "campaign.yaml", "outcomes.csv"):
        assert (destination / name).read_text() == "intocable"


def test_rebuild_rejects_a_non_candidate_measurement(tmp_path: Path) -> None:
    attempt, destination = _publish(tmp_path)
    metrics = _candidate_metrics()
    metrics["status"] = "accepted"
    (attempt / "candidate-metrics.json").write_text(json.dumps(metrics))

    with pytest.raises(GateViolation, match="candidate is not available"):
        rebuild_curated_metrics(attempt, destination)


def test_rebuild_rejects_a_destination_that_was_never_published(tmp_path: Path) -> None:
    attempt, destination = _publish(tmp_path)

    with pytest.raises(GateViolation, match="destination does not exist"):
        rebuild_curated_metrics(attempt, destination.parent / "inexistente")


def test_readme_template_publishes_steady_state_and_payload() -> None:
    """Guard del defecto original: la plantilla debe emitir los bloques nuevos.

    Sin esto, regenerar el README borraría el steady-state publicado sin aviso.
    """
    readme = _readme(_accepted_metrics(_candidate_metrics()), _curated_integrated())

    assert "Régimen sostenido" in readme
    assert "Tamaño de payload" in readme
    assert "110.000 ms sobre n = 3" in readme
    assert "40.0 %" in readme  # 2 primeras entregas sobre 5 = 40 %
    assert "1078" in readme


def _attempt_with_status(tmp_path: Path, status: str) -> Path:
    root = tmp_path / "runs"
    attempt = root / "official-test-01"
    attempt.mkdir(parents=True)
    (attempt / "attempt.json").write_text(
        json.dumps({"attempt_id": "official-test-01", "status": status})
    )
    return root


def test_load_attempt_rejects_a_published_attempt_by_default(tmp_path: Path) -> None:
    root = _attempt_with_status(tmp_path, "succeeded")

    with pytest.raises(GateViolation, match="attempt is not prepared"):
        load_attempt(root, "official-test-01")


def test_load_attempt_admits_a_published_attempt_only_when_asked(tmp_path: Path) -> None:
    root = _attempt_with_status(tmp_path, "succeeded")

    assert load_attempt(root, "official-test-01", allow_completed=True).name == (
        "official-test-01"
    )


def test_load_attempt_still_rejects_an_invalidated_attempt(tmp_path: Path) -> None:
    root = _attempt_with_status(tmp_path, "invalid")

    with pytest.raises(GateViolation, match="not prepared nor published"):
        load_attempt(root, "official-test-01", allow_completed=True)
