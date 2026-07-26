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
    # Trazabilidad spec 43 SS6 (experiment_id -> clip_id -> gt/*.json), campos
    # OPTATIVOS y aditivos: un manifiesto sin ellos sigue siendo valido (corrida
    # sin video-gt-lab detras). Cuando `clip_id` esta presente, el runner lo
    # inyecta como `ingest.config.source_id` en la config que le manda al
    # media-plane (ver runner._inject_source_id). Cuando `ground_truth` esta
    # presente (path a un clip_gt.v2), el runner corre la evaluacion temporal
    # tras el replay y liga el resultado al reporte consolidado (ver
    # runner._run_temporal_evaluation / report._temporal_evaluation).
    # El path de `ground_truth` se resuelve igual que `runs.*.config`: relativo
    # al cwd del proceso del runner (no hay resolucion propia aca), o absoluto.
    clip_id: str | None = None
    ground_truth: str | None = None
    # Procedencia de la derivación (espejo de prompt_store.derive_set): de qué
    # manifiesto salió este y por qué. Opcionales — los manifiestos escritos a
    # mano no los declaran.
    derives_from: str | None = None
    changes: str | None = None


def generate_experiment_id(slug: str, now: datetime) -> str:
    """Genera el experiment_id a partir del slug y un instante inyectado."""
    return f"exp_{now.strftime('%Y%m%dT%H%M%SZ')}_{slug}"


def load_manifest(path: str | Path) -> ExperimentManifest:
    """Carga y valida el manifiesto paraguas desde un archivo YAML."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ExperimentManifest.model_validate(data)
