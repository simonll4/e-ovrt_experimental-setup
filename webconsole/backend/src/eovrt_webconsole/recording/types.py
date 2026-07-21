"""Contratos de la grabación: request, resultado, estado e interfaz de recorder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from eovrt_webconsole.recording.naming import BASENAME_RE

RECORDABLE_PLUGINS = frozenset({"rtsp", "oak_d"})
OAK_D_RESOLUTIONS = frozenset({"720p", "1080p", "4k"})


class CaptureSpec(BaseModel):
    """Parámetros de captura. Solo aplican a oak_d (en rtsp manda el DVR)."""

    model_config = ConfigDict(extra="forbid")

    fps: int = 60
    resolution: str = "1080p"
    bitrate_bps: int = 25_000_000
    keyframe_hz: float = 1.0

    @field_validator("resolution")
    @classmethod
    def _resolucion_soportada(cls, v: str) -> str:
        if v not in OAK_D_RESOLUTIONS:
            raise ValueError(f"resolution debe ser una de {sorted(OAK_D_RESOLUTIONS)}")
        return v

    @field_validator("fps")
    @classmethod
    def _fps_positivo(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("fps debe ser > 0")
        return v


class RecordingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str
    config: dict
    basename: str
    label: str | None = None
    capture: CaptureSpec | None = None
    max_duration_s: int = 600

    @field_validator("plugin")
    @classmethod
    def _plugin_grabable(cls, v: str) -> str:
        if v not in RECORDABLE_PLUGINS:
            raise ValueError(f"plugin no grabable: {v!r} (esperado rtsp u oak_d)")
        return v

    @field_validator("basename")
    @classmethod
    def _basename_valido(cls, v: str) -> str:
        if not BASENAME_RE.match(v):
            raise ValueError(f"basename inválido: {v!r} (esperado P<n>-<x>-take<n>)")
        return v

    @model_validator(mode="after")
    def _capture_solo_para_oakd(self) -> "RecordingSpec":
        if self.plugin == "rtsp" and self.capture is not None:
            raise ValueError(
                "capture no aplica a plugin rtsp: se graba lo que emite el DVR"
            )
        if self.plugin == "oak_d" and self.capture is None:
            object.__setattr__(self, "capture", CaptureSpec())
        return self


@dataclass(frozen=True)
class RecordingResult:
    path: Path
    started_wallclock_ms: int
    duration_ms: int
    size_bytes: int
    truncated: bool
    error: str | None = None


@dataclass(frozen=True)
class RecordingStatus:
    state: Literal["recording", "finished", "error"]
    elapsed_ms: int
    size_bytes: int
    error: str | None = None


class Recorder(Protocol):
    def start(self) -> None: ...

    def stop(self) -> RecordingResult: ...

    def poll(self) -> RecordingStatus: ...
