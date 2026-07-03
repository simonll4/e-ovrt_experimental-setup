"""Escritura atómica de manifiestos in-repo (experiments/), Spec B §5.3."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ManifestExistsError(Exception):
    pass


class ProtectedManifestError(Exception):
    """El grupo destino es curado/versionado (p.ej. bench_v2): nunca se pisa un existente."""


def write_manifest(
    experiments_dir: Path,
    name: str,
    group: str | None,
    manifest: dict,
    overwrite: bool = False,
    protected_groups: frozenset[str] = frozenset(),
) -> Path:
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"Nombre de manifiesto inválido: {name!r} (usar [a-z0-9_-])")
    if group and not _NAME_RE.match(group):
        raise ValueError(f"Grupo inválido: {group!r} (usar [a-z0-9_-])")
    target_dir = experiments_dir / group if group else experiments_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.yaml"
    if group and group in protected_groups and target.exists():
        # Independiente de overwrite: sobre grupos protegidos nunca se pisa un
        # manifiesto curado ya existente vía la API. Crear uno nuevo sí se permite.
        raise ProtectedManifestError(
            f"manifiesto curado en grupo protegido {group!r}; "
            "renombrá o escribí en otro grupo"
        )
    if target.exists() and not overwrite:
        raise ManifestExistsError(str(target))
    tmp = target.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    os.replace(tmp, target)  # atómico en el mismo filesystem
    return target
