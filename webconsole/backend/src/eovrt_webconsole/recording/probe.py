"""Medición del master ya cerrado con ffprobe (sin recorrer el archivo)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Measured:
    width: int
    height: int
    fps: float
    duration_ms: int


def _parse_rate(raw: str) -> float:
    if not raw or raw in {"0/0", "N/A"}:
        return 0.0
    if "/" in raw:
        num, den = raw.split("/", 1)
        return float(num) / float(den) if float(den) else 0.0
    return float(raw)


def measure(path: Path) -> Measured:
    try:
        completed = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError(f"ffprobe falló sobre {path}: {exc}") from exc
    if completed.returncode != 0:
        raise ProbeError(f"ffprobe devolvió {completed.returncode} sobre {path}: {completed.stderr.strip()}")
    try:
        data = json.loads(completed.stdout)
        stream = data["streams"][0]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise ProbeError(f"{path} no tiene stream de video legible") from exc
    duration_raw = data.get("format", {}).get("duration")
    return Measured(
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=_parse_rate(str(stream.get("avg_frame_rate", "0/0"))),
        duration_ms=int(round(float(duration_raw) * 1000)) if duration_raw else 0,
    )
