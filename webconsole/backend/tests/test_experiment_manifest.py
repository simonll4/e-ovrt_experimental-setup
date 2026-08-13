"""Tests del manifiesto paraguas experiment.manifest.v1 (spec 44 SS2)."""
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eovrt_webconsole.experiment.manifest import ExperimentManifest


def test_generate_experiment_id_format():
    from eovrt_webconsole.experiment.manifest import generate_experiment_id

    got = generate_experiment_id("d1-fase1", datetime(2026, 7, 12, 14, 0, 0, tzinfo=UTC))
    assert got == "exp_20260712T140000Z_d1-fase1"


def test_manifest_parses_umbrella_schema():
    from eovrt_webconsole.experiment.manifest import ExperimentManifest

    m = ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "http://localhost:8080", "config": "./media_run.yaml", "mode": "run"},
                "control": {"service": "http://localhost:8081", "config": "./control_run.yaml", "mode": "live"},
            },
            "sequencing": "control_first",
            "report": {"output": "report/"},
            "frozen": {"prompt_set": "eind_v1", "pattern_set": "cr01_cr02_v2", "model_ref": "gdino-tiny"},
        }
    )
    assert m.runs["control"].mode == "live" and m.sequencing == "control_first"


def test_manifest_clip_id_and_ground_truth_default_to_none():
    """Aditivo: un manifiesto sin clip_id/ground_truth sigue siendo valido."""
    from eovrt_webconsole.experiment.manifest import ExperimentManifest

    m = ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "u", "config": "c", "mode": "run"},
                "control": {"service": "u", "config": "c", "mode": "replay"},
            },
            "sequencing": "media_first",
            "report": {},
            "frozen": {},
        }
    )
    assert m.clip_id is None
    assert m.ground_truth is None


def test_manifest_accepts_clip_id_and_ground_truth():
    """Spec 43 SS6: experiment_id -> clip_id -> gt/*.json. Los campos viajan
    tal cual por model_dump (usado para el manifest.effective.yaml)."""
    from eovrt_webconsole.experiment.manifest import ExperimentManifest

    m = ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "u", "config": "c", "mode": "run"},
                "control": {"service": "u", "config": "c", "mode": "replay"},
            },
            "sequencing": "media_first",
            "report": {},
            "frozen": {},
            "clip_id": "clip_0007",
            "ground_truth": "gt/clip_0007.gt.json",
        }
    )
    assert m.clip_id == "clip_0007"
    assert m.ground_truth == "gt/clip_0007.gt.json"
    dumped = m.model_dump(mode="json")
    assert dumped["clip_id"] == "clip_0007"
    assert dumped["ground_truth"] == "gt/clip_0007.gt.json"


def test_manifest_rejects_unknown_sequencing():
    import pytest

    from eovrt_webconsole.experiment.manifest import ExperimentManifest

    with pytest.raises(ValueError):
        ExperimentManifest.model_validate(
            {
                "schema_version": "experiment.manifest.v1",
                "slug": "d1",
                "runs": {
                    "media": {"service": "u", "config": "c", "mode": "run"},
                    "control": {"service": "u", "config": "c", "mode": "replay"},
                },
                "sequencing": "media_first_wrong",
                "report": {},
                "frozen": {},
            }
        )


def test_manifest_accepts_distribution_block_with_optional_endpoint_and_idle_timeout():
    """ADR-016: `runs.distribution` es opcional y acepta endpoint/timeout para
    la integración con `eovrt-distribute` sin romper el manifiesto existente."""
    from eovrt_webconsole.experiment.manifest import ExperimentManifest

    manifest = ExperimentManifest.model_validate(
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "d1",
            "runs": {
                "media": {"service": "u", "config": "c", "mode": "run"},
                "control": {"service": "u", "config": "c", "mode": "replay"},
                "distribution": {
                    "service": "u-distribution",
                    "config": "d.yaml",
                    "mode": "replay",
                    "endpoint": "mqtt://localhost:1883",
                    "idle_timeout_ms": 1200.5,
                },
            },
            "sequencing": "media_first",
            "report": {},
            "frozen": {},
        }
    )

    distribution = manifest.runs["distribution"]
    assert distribution.endpoint == "mqtt://localhost:1883"
    assert distribution.idle_timeout_ms == 1200.5


@pytest.mark.parametrize("idle_timeout_ms", [0, -1, float("inf"), float("nan")])
def test_manifest_rejects_invalid_distribution_idle_timeout(idle_timeout_ms):
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(
            {
                "schema_version": "experiment.manifest.v1",
                "slug": "d1",
                "runs": {
                    "media": {"service": "u", "config": "c", "mode": "run"},
                    "control": {"service": "u", "config": "c", "mode": "live"},
                    "distribution": {
                        "service": "u",
                        "config": "d.yaml",
                        "mode": "live",
                        "idle_timeout_ms": idle_timeout_ms,
                    },
                },
                "sequencing": "control_first",
            }
        )
