"""Rama RTSP: ffmpeg -c copy, sin transcodificar. El host no toca los píxeles."""

from __future__ import annotations

import logging
import signal
import subprocess
import time
from pathlib import Path

from eovrt_webconsole.redact import redact_rtsp_credentials
from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus

logger = logging.getLogger(__name__)

_STOP_TIMEOUT_S = 15.0


def build_ffmpeg_args(url: str, out_path: Path) -> list[str]:
    # -rtsp_transport tcp NO es opcional: sobre UDP el DVR pierde paquetes y el
    # master queda con macrobloques, daño que ningún paso posterior repara.
    # Incondicional para cualquier URL (rtsp:// o rtsps://, RTSP sobre TLS):
    # esta función solo se llama para plugin=="rtsp" (ver RecordingSpec), nunca
    # con un input file:// real en producción.
    return [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", str(url),
        "-c", "copy",
        "-movflags", "+faststart",
        "-y",
        str(out_path),
    ]


class FfmpegCopyRecorder:
    def __init__(self, spec: RecordingSpec, out_path: Path) -> None:
        self._spec = spec
        self._path = out_path
        self._proc: subprocess.Popen | None = None
        self._started_ms: int = 0
        self._started_monotonic: float = 0.0
        self._stderr: str = ""

    def start(self) -> None:
        args = build_ffmpeg_args(str(self._spec.config.get("url", "")), self._path)
        self._started_ms = int(time.time() * 1000)
        self._started_monotonic = time.monotonic()
        self._proc = subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )
        logger.info("Grabación RTSP arrancada -> %s", self._path.name)

    def poll(self) -> RecordingStatus:
        if self._proc is None:
            return RecordingStatus("error", 0, 0, "grabación sin arrancar")
        elapsed = int((time.monotonic() - self._started_monotonic) * 1000)
        size = self._path.stat().st_size if self._path.exists() else 0
        rc = self._proc.poll()
        if rc is None:
            return RecordingStatus("recording", elapsed, size)
        if rc == 0:
            return RecordingStatus("finished", elapsed, size)
        return RecordingStatus("error", elapsed, size, self._read_stderr() or f"ffmpeg rc={rc}")

    def stop(self) -> RecordingResult:
        if self._proc is None:
            raise RuntimeError("no se puede detener una grabación sin arrancar")
        rc = self._proc.poll()
        murio_solo = rc is not None
        matado = False
        if not murio_solo:
            # SIGINT y no SIGKILL: ffmpeg finaliza el átomo moov y el mp4 queda
            # reproducible. Matarlo a lo bruto deja un archivo corrupto.
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=_STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                logger.warning("ffmpeg no cerró en %ss, se mata", _STOP_TIMEOUT_S)
                self._proc.kill()
                self._proc.wait(timeout=5)
                matado = True
            rc = self._proc.returncode
        error = self._read_stderr() if murio_solo and rc not in (0, None) else None
        if murio_solo and error is None and rc not in (0, None):
            error = f"ffmpeg terminó solo con rc={rc}"
        if matado:
            # kill() no le da tiempo a ffmpeg de escribir el átomo moov: el mp4
            # queda sin índice final y no es reproducible. Si esto no queda
            # marcado acá, `manager._finalize` recibe truncated=False/error=None
            # y el master corrupto sale del sistema como si fuera una toma sana.
            error = (
                f"cerrado a la fuerza tras no responder a SIGINT en "
                f"{_STOP_TIMEOUT_S:.0f}s: mp4 sin átomo moov, no reproducible"
            )
        return RecordingResult(
            path=self._path,
            started_wallclock_ms=self._started_ms,
            duration_ms=int((time.monotonic() - self._started_monotonic) * 1000),
            size_bytes=self._path.stat().st_size if self._path.exists() else 0,
            truncated=murio_solo or matado,
            error=error,
        )

    def _read_stderr(self) -> str:
        if self._stderr:
            return self._stderr
        if self._proc is not None and self._proc.stderr is not None:
            try:
                crudo = self._proc.stderr.read().strip()
            except (ValueError, OSError):
                crudo = ""
            # ffmpeg imprime la URL completa (con credenciales en claro) en su
            # stderr cuando falla la conexión. Este texto se propaga a
            # RecordingStatus.error / RecordingResult.error y de ahí lo escribe
            # write_sidecar() verbatim en el .rec.json que queda en disco junto
            # al video: hay que redactar antes de que salga del recorder.
            self._stderr = redact_rtsp_credentials(crudo)
        return self._stderr
