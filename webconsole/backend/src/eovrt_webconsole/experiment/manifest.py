"""Manifiesto paraguas del experimento (ADR-004, spec 44 SS2)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class PlaneRun(BaseModel):
    """Referencia a la corrida de un plano dentro del experimento paraguas."""

    model_config = ConfigDict(extra="forbid")

    service: str
    config: str  # ruta al YAML de config por payload de ese plano
    mode: str  # media: "run"; control: "live" | "replay"


class ExperimentManifest(BaseModel):
    """Manifiesto paraguas que coordina las corridas de ambos planos."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["experiment.manifest.v1"]
    slug: str
    experiment_id: str | None = None
    runs: dict[str, PlaneRun]
    sequencing: Literal["control_first", "media_first"] = "control_first"
    report: dict = Field(default_factory=dict)
    frozen: dict = Field(default_factory=dict)


def generate_experiment_id(slug: str, now: datetime) -> str:
    """Genera el experiment_id a partir del slug y un instante inyectado."""
    return f"exp_{now.strftime('%Y%m%dT%H%M%SZ')}_{slug}"


def load_manifest(path: str | Path) -> ExperimentManifest:
    """Carga y valida el manifiesto paraguas desde un archivo YAML."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ExperimentManifest.model_validate(data)
