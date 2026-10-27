"""Piezas compartidas por las familias: banco de clips, artefactos de corridas y los
instrumentos de medición de los repos hermanos (los mismos que usó la generación 1).
"""
from __future__ import annotations

import importlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .entorno import Entorno


class InsumoFaltante(RuntimeError):
    pass


# --- instrumentos de los repos hermanos ----------------------------------------------


def importar_datasets(ent: Entorno, modulo: str):
    """Importa un script de `e-ovrt_datasets/datasets/scripts` (p.ej. `bench.evaluate_bench`).

    Son stdlib puros; se cargan desde el repo (nunca copias), así lo que mide la generación 2
    es el mismo código que midió la 1.
    """
    raiz = str(ent.scripts_datasets)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    return importlib.import_module(modulo)


def importar_media_plane(ent: Entorno, modulo: str):
    """Módulos livianos del media-plane (p.ej. `eovrt_media.evaluation.runner`: pydantic)."""
    raiz = str(ent.media_plane / "src")
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    return importlib.import_module(modulo)


def eovrt_control_bin(ent: Entorno) -> str:
    configurado = os.environ.get("EOVRT_EVIDENCIA_EOVRT_CONTROL")
    if configurado:
        return configurado
    en_path = shutil.which("eovrt-control")
    if en_path:
        return en_path
    venv = ent.control_plane / ".venv" / "bin" / "eovrt-control"
    if venv.is_file():
        return str(venv)
    raise InsumoFaltante("no se encontró `eovrt-control` (PATH, venv del control-plane o EOVRT_EVIDENCIA_EOVRT_CONTROL)")


def evaluar_alertas(
    ent: Entorno,
    *,
    alertas: Path,
    gt: Path,
    detecciones: Path,
    patrones: Path,
    salida: Path,
) -> list[str]:
    """`eovrt-control evaluate-alerts`, idéntico a los runners 81/85/87/88/89/96/102."""
    cmd = [
        eovrt_control_bin(ent),
        "evaluate-alerts",
        str(alertas),
        str(gt),
        "--detections",
        str(detecciones),
        "--patterns",
        str(patrones),
        "-o",
        str(salida),
    ]
    salida.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not salida.is_file():
        raise RuntimeError(
            f"evaluate-alerts rc={proc.returncode}: {(proc.stderr or proc.stdout)[-400:]}"
        )
    return cmd


# --- banco de clips -------------------------------------------------------------------


def manifiesto_banco(ent: Entorno) -> dict[str, dict]:
    datos = yaml.safe_load((ent.banco / "manifest.yaml").read_text(encoding="utf-8"))
    return {c["clip_id"]: c for c in datos["clips"]}


def clips_de(ent: Entorno, seleccion) -> list[str]:
    """`rodaje` (34 `a_*`), `internet` (13 `v*`) o una lista explícita."""
    banco = manifiesto_banco(ent)
    if isinstance(seleccion, list):
        faltan = [c for c in seleccion if c not in banco]
        if faltan:
            raise InsumoFaltante(f"clips fuera del banco: {faltan}")
        return list(seleccion)
    if seleccion == "rodaje":
        return sorted(c for c in banco if c.startswith("a_"))
    if seleccion == "internet":
        return sorted(c for c in banco if c.startswith("v"))
    raise ValueError(f"selección de clips inválida: {seleccion!r}")


def ruta_video(ent: Entorno, clip_id: str) -> Path:
    """Ruta del mp4 en el workspace. El manifiesto la da relativa a su carpeta
    (`../../raw/clip_bench/clips/<clip>.mp4`); se normaliza sin resolver symlinks, porque
    `Entorno.ruta_medios` la traduce por prefijo."""
    entrada = manifiesto_banco(ent)[clip_id]
    return Path(os.path.normpath(ent.banco / entrada["file"]))


def cuadros_esperados(ent: Entorno, clip_id: str, stride: int) -> int:
    entrada = manifiesto_banco(ent)[clip_id]
    n = round(entrada["duration_ms"] / 1000 * entrada["fps"])
    return math.ceil(n / stride)


# --- artefactos de corridas -----------------------------------------------------------


def resumen_media(ent: Entorno, run_id: str) -> dict:
    ruta = ent.media_runs / run_id / "summary.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}


def resumen_control(ent: Entorno, control_run_id: str) -> dict:
    ruta = ent.control_runs / control_run_id / "summary.json"
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {}


def escribir_yaml(ruta: Path, datos: dict) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(yaml.safe_dump(datos, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return ruta
