"""Escritura atómica de manifiestos in-repo (experiments/), Spec B §5.3."""
from __future__ import annotations

import os
import re
import shutil
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


def write_manifest_dir(
    experiments_dir: Path,
    name: str,
    files: dict[str, dict],
    *,
    protected_groups: frozenset[str] = frozenset(),
) -> Path:
    """Escribe un manifiesto paraguas multi-archivo de forma atómica.

    La unidad atómica es el DIRECTORIO, no el archivo: tres escrituras atómicas
    no son atómicas como conjunto, y un directorio a medio construir deja un
    manifest.yaml válido apuntando a payloads inexistentes. Se arma todo en un
    temporal hermano y se publica con un único os.replace; `os.replace` sobre un
    destino inexistente es atómico dentro del mismo filesystem.
    """
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"Nombre de manifiesto inválido: {name!r} (usar [a-z0-9_-])")

    target = experiments_dir / name
    # Sin `target.exists()` a propósito: con esa condición el guard era
    # inalcanzable (si el destino existe, el ManifestExistsError de abajo salta
    # igual) y los grupos protegidos quedaban sin protección real. Acá el nombre
    # ES el directorio destino, así que un manifiesto paraguas nunca puede
    # ocupar el nombre de un grupo curado (p. ej. experiments/bench_v2/) — ni
    # creándolo de cero, que es justo el caso que el guard viejo dejaba pasar.
    if name in protected_groups:
        raise ProtectedManifestError(
            f"{name!r} es un grupo protegido (curado/versionado): un manifiesto paraguas no "
            "puede ocupar ese directorio; elegí otro nombre"
        )
    if target.exists():
        raise ManifestExistsError(str(target))

    experiments_dir.mkdir(parents=True, exist_ok=True)
    tmp = experiments_dir / f".{name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    try:
        for filename, payload in files.items():
            (tmp / filename).write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        os.replace(tmp, target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return target
