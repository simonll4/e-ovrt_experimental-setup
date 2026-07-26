"""Procedencia del manifiesto derivado (spec 2026-07-25 §Procedencia)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from eovrt_webconsole.experiment.manifest import ExperimentManifest

BASE = {
    "schema_version": "experiment.manifest.v1",
    "slug": "d1",
    "runs": {
        "media": {"service": "media-plane", "config": "/tmp/media.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "/tmp/control.yaml", "mode": "live"},
    },
    "sequencing": "control_first",
    "report": {},
    "frozen": {},
}


def test_acepta_procedencia():
    m = ExperimentManifest.model_validate(
        {**BASE, "derives_from": "ebe_oakd_live", "changes": "warmup 20 -> 30"}
    )
    assert m.derives_from == "ebe_oakd_live"
    assert m.changes == "warmup 20 -> 30"


def test_procedencia_es_opcional():
    """Los manifiestos existentes (sin procedencia) siguen validando."""
    m = ExperimentManifest.model_validate(BASE)
    assert m.derives_from is None
    assert m.changes is None


def test_sigue_rechazando_campos_desconocidos():
    """extra='forbid' no se relaja: solo se suman estos dos campos."""
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate({**BASE, "campo_inventado": 1})
