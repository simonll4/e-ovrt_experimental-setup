"""Invocación de prepare_clip.sh del repo datasets, tal cual está (spec §4).

D3: `duration` se pasa como --to, que en ese script es RELATIVO al punto de
corte (funciona como duración; verificado empíricamente con ffmpeg 8.0.1).
Nunca pasar acá un instante absoluto: no falla, produce en silencio un clip
más largo con el evento descolocado respecto del GT.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_TIMEOUT_S = 600  # re-encode x264 de ~30 s de master: minutos, no horas


class TrimFailed(RuntimeError):
    """El script falló; str(exc) es su salida real (spec §7)."""


def run_prepare_clip(
    script: Path,
    clips_dir: Path,
    master: Path,
    clip_id: str,
    ss: float,
    duration: float,
    fps: int = 30,
) -> dict:
    if not script.is_file():
        raise TrimFailed(f"prepare_clip.sh no encontrado en {script}")
    cmd = [
        "bash", str(script), str(master), clip_id,
        "--ss", f"{ss:.3f}",
        "--to", f"{duration:.3f}",   # DURACIÓN (D3)
        "--fps", str(fps),
    ]
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_TIMEOUT_S
        )
    except subprocess.TimeoutExpired as exc:
        raise TrimFailed(f"prepare_clip.sh superó los {_TIMEOUT_S} s: {exc}") from exc
    if completed.returncode != 0:
        salida = (completed.stdout + "\n" + completed.stderr).strip()
        raise TrimFailed(salida or f"prepare_clip.sh devolvió {completed.returncode}")
    info_path = clips_dir / f"{clip_id}.info.json"
    try:
        return json.loads(info_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TrimFailed(
            f"prepare_clip.sh terminó bien pero no dejó {info_path} legible: {exc}"
        ) from exc
