"""Sidecar <basename>.rec.json: procedencia técnica del master grabado."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eovrt_webconsole.recording.probe import Measured
from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec

_CHUNK = 1024 * 1024


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def write_sidecar(
    spec: RecordingSpec, result: RecordingResult, measured: Measured | None
) -> Path:
    # `requested` sale vacío en rtsp: no se pidió nada, manda el DVR. La asimetría
    # con `measured` es deliberada -- si el DVR entregó 12 fps cuando se esperaban
    # 60, tiene que quedar registrado y no descubrirse meses después.
    requested: dict = {}
    if spec.capture is not None:
        requested = {
            "fps": spec.capture.fps,
            "resolution": spec.capture.resolution,
            "codec": "h264",
            "bitrate_bps": spec.capture.bitrate_bps,
        }
    payload = {
        "basename": spec.basename,
        "file": f"raw/{result.path.name}",
        "camera_id": spec.label,
        "plugin": spec.plugin,
        "requested": requested,
        "measured": {
            "fps": measured.fps if measured else None,
            "resolution": f"{measured.width}x{measured.height}" if measured else None,
            "duration_ms": measured.duration_ms if measured else result.duration_ms,
            "size_bytes": result.size_bytes,
        },
        "started_wallclock_ms": result.started_wallclock_ms,
        "truncated": result.truncated,
        "error": result.error,
        "sha256": sha256_of(result.path),
    }
    out = result.path.with_suffix(".rec.json")
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
