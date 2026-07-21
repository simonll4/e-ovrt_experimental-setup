"""Gates de arranque de una grabación: destino y espacio libre."""

from __future__ import annotations

import shutil
from pathlib import Path

# El filesystem cruzado de WSL es lo bastante lento como para perder frames por
# I/O durante una toma; se rechaza antes de grabar, no después.
_FORBIDDEN_PREFIXES = ("/mnt/c", "/mnt/d", "/mnt/e")


class GateError(ValueError):
    pass


def check_destination(raw_dir: Path) -> None:
    resolved = raw_dir.expanduser().resolve()
    for prefix in _FORBIDDEN_PREFIXES:
        if str(resolved) == prefix or str(resolved).startswith(prefix + "/"):
            raise GateError(
                f"destino bajo {prefix}: el filesystem cruzado de WSL es demasiado "
                "lento para grabar sin perder frames"
            )
    if resolved.exists() and not resolved.is_dir():
        raise GateError(f"el destino no es un directorio: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)


def check_free_space(raw_dir: Path, min_gb: float = 5.0) -> None:
    target = raw_dir if raw_dir.exists() else raw_dir.parent
    free_gb = shutil.disk_usage(target).free / (1024**3)
    if free_gb < min_gb:
        raise GateError(
            f"espacio insuficiente en {target}: {free_gb:.1f} GB libres, "
            f"se requieren {min_gb:.1f} GB"
        )
