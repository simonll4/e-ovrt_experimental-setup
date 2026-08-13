"""Consolidacion de artefactos del experimento (ADR-014, spec 44 SS4 Tarea 2).

Arma `dest_root/<experiment_id>/` copiando los artefactos LIVIANOS de ambos
planos (media + control) y REFERENCIANDO el `detections.jsonl` pesado del
media-plane por `run_id` (no se duplica el crudo). La consolidacion es
coleccion, no computo: el `runs/` de cada plano sigue siendo la fuente de
verdad (DA-03); esto solo arma una vista liviana y portable para el reporte.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import yaml

# Artefactos livianos comunes a ambos planos (mas los especificos de control).
_EFFECTIVE_CONFIG_NAMES = ("effective_config.yaml", "effective_config.json")
_MEDIA_LIGHT_ARTIFACTS = ("summary.json", "metrics.jsonl")
_CONTROL_LIGHT_ARTIFACTS = (
    "summary.json",
    "metrics.jsonl",
    "alerts.jsonl",
    "pattern_events.jsonl",
)
_CHUNK_SIZE = 1024 * 1024  # 1 MiB por lectura, para no cargar archivos grandes en memoria.


def sha256_file(path: str | Path) -> str:
    """Calcula el sha256 de un archivo leyendolo en chunks (no todo en memoria).

    Usado para el chequeo anti-drift: hash de la config enviada vs la
    `effective_config` persistida por cada plano.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_light_artifacts(src_dir: Path, dst_dir: Path, names: tuple[str, ...]) -> None:
    """Copia (shutil.copy2) los artefactos de `names` que existan en `src_dir`.

    Tolera ausencias: lo que no existe se omite, no rompe la consolidacion.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, dst_dir / name)


def _copy_effective_config(src_dir: Path, dst_dir: Path) -> None:
    """Copia effective_config.yaml o effective_config.json, lo que exista."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in _EFFECTIVE_CONFIG_NAMES:
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, dst_dir / name)


def _write_detections_ref(media_run_dir: Path, media_dest_dir: Path) -> None:
    """Escribe la referencia al detections.jsonl del media-plane (no lo copia).

    ADR-014: el crudo pesado se referencia por run_id + path, nunca se
    duplica dentro del consolidado.
    """
    ref = {
        "run_id": media_run_dir.name,
        "path": str(media_run_dir / "detections.jsonl"),
    }
    (media_dest_dir / "detections.ref.json").write_text(
        json.dumps(ref, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def consolidate_experiment(
    experiment_id: str,
    *,
    media_run_dir: Path,
    control_run_dir: Path,
    manifest_effective: dict,
    dest_root: Path,
) -> Path:
    """Arma el consolidado ADR-014 de un experimento en `dest_root/<experiment_id>/`.

    - `media/`: copia effective_config, summary.json, metrics.jsonl; escribe
      `detections.ref.json` con `{run_id, path}` (NO copia detections.jsonl).
    - `control/`: copia effective_config, summary.json, metrics.jsonl,
      alerts.jsonl, pattern_events.jsonl.
    - `distribution/`: si ya existe, se preserva. El distribuidor escribe
      directamente en ese sibling; no pertenece al directorio del control-plane.
    - `manifest.effective.yaml`: dump del manifiesto efectivo.
    - `report/`: directorio vacio, listo para el generador de reporte (Tarea 3).

    Tolera artefactos faltantes en cualquiera de los dos planos: los omite en
    vez de fallar. Devuelve el Path del directorio del experimento.
    """
    media_run_dir = Path(media_run_dir)
    control_run_dir = Path(control_run_dir)
    dest_root = Path(dest_root)

    experiment_dir = dest_root / experiment_id
    media_dest_dir = experiment_dir / "media"
    control_dest_dir = experiment_dir / "control"
    report_dir = experiment_dir / "report"

    _copy_effective_config(media_run_dir, media_dest_dir)
    _copy_light_artifacts(media_run_dir, media_dest_dir, _MEDIA_LIGHT_ARTIFACTS)
    _write_detections_ref(media_run_dir, media_dest_dir)

    _copy_effective_config(control_run_dir, control_dest_dir)
    _copy_light_artifacts(control_run_dir, control_dest_dir, _CONTROL_LIGHT_ARTIFACTS)
    experiment_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = experiment_dir / "manifest.effective.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest_effective, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    report_dir.mkdir(parents=True, exist_ok=True)

    return experiment_dir
