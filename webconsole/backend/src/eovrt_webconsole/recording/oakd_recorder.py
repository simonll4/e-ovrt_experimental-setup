"""Rama OAK-D: lanza tools/record_oakd.py con el intérprete que tiene depthai."""

from __future__ import annotations

import json
import logging
import signal
import subprocess
import threading
import time
from pathlib import Path

from eovrt_webconsole.recording.types import RecordingResult, RecordingSpec, RecordingStatus

logger = logging.getLogger(__name__)

_STOP_TIMEOUT_S = 20.0


class InterpreterUnavailable(RuntimeError):
    pass


def mux_h264_to_mp4(raw: Path, mp4: Path, fps: int, *, delete_raw: bool = True) -> str | None:
    """Muxea el elemental H.264 crudo a un mp4 reproducible (sin transcodificar).

    Devuelve el mensaje de error si ffmpeg falla, o `None` si el muxeo salió bien.
    `delete_raw=False` conserva el `.h264` aun con éxito: lo usa el rescate de
    huérfanos (`RecordingManager.recover_orphans`), donde el resultado es
    best-effort y no hay margen para perder el único material de la toma si el
    mux resultó silenciosamente incompleto.
    """
    completed = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "h264", "-r", str(fps), "-i", str(raw),
            "-c", "copy", str(mp4),
        ],
        capture_output=True, text=True,
    )
    if completed.returncode != 0:
        return f"muxeo a mp4 falló (rc={completed.returncode}): {completed.stderr.strip()}"
    if delete_raw:
        raw.unlink(missing_ok=True)
    return None


def check_interpreter(interpreter: Path) -> None:
    """Se llama al arrancar el backend: el fallo se descubre ahí, no en el rodaje."""
    if not Path(interpreter).is_file():
        raise InterpreterUnavailable(
            f"intérprete para la rama OAK-D inexistente: {interpreter}. "
            "Definí EOVRT_CONSOLE_OAKD_PYTHON apuntando a un Python con depthai."
        )


class OakDSubprocessRecorder:
    def __init__(
        self, spec: RecordingSpec, out_path: Path, interpreter: Path, script: Path
    ) -> None:
        self._spec = spec
        self._path = out_path
        self._raw = out_path.with_suffix(".h264")
        self._interpreter = Path(interpreter)
        self._script = Path(script)
        self._proc: subprocess.Popen | None = None
        self._started_ms: int = 0
        self._started_monotonic: float = 0.0
        self._stderr: str = ""
        # Momento en que el subproceso avisó que la cámara EMPEZÓ A CAPTURAR
        # (evento "started"), que es hasta 9 s después del Popen en la OAK-D
        # PoE. None mientras el device inicializa.
        self._capture_monotonic: float | None = None
        self._watcher: threading.Thread | None = None

    def _vigilar_arranque(self) -> None:
        """Espera el evento "started" en stdout del subproceso.

        Corre en un hilo daemon porque leer stdout bloquea: el device puede
        tardar ~9 s en conectar y `poll()` tiene que seguir respondiendo
        (la UI lo consulta cada segundo). El SDK DepthAI ensucia stdout con
        warnings, así que las líneas que no son JSON se ignoran.
        """
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for linea in proc.stdout:
                try:
                    evento = json.loads(linea)
                except (json.JSONDecodeError, ValueError):
                    continue
                if evento.get("event") == "started":
                    self._capture_monotonic = time.monotonic()
                    return
        except (ValueError, OSError):
            return

    def start(self) -> None:
        capture = self._spec.capture
        assert capture is not None  # RecordingSpec lo garantiza para oak_d
        args = [
            str(self._interpreter), str(self._script),
            "--device", str(self._spec.config.get("url", "")),
            "--out", str(self._raw),
            "--fps", str(capture.fps),
            "--resolution", capture.resolution,
            "--bitrate", str(capture.bitrate_bps),
            "--keyframe-hz", str(capture.keyframe_hz),
        ]
        self._started_ms = int(time.time() * 1000)
        self._started_monotonic = time.monotonic()
        self._proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        self._watcher = threading.Thread(target=self._vigilar_arranque, daemon=True)
        self._watcher.start()
        logger.info("Grabación OAK-D lanzada -> %s (esperando al device)", self._path.name)

    def poll(self) -> RecordingStatus:
        if self._proc is None:
            return RecordingStatus("error", 0, 0, "grabación sin arrancar")
        capture = self._capture_monotonic
        # El cronómetro mide CAPTURA, no el init del device: con 40 s en
        # pantalla salían 28 s de video (F-DR6).
        elapsed = int((time.monotonic() - capture) * 1000) if capture is not None else 0
        size = self._raw.stat().st_size if self._raw.exists() else 0
        rc = self._proc.poll()
        if rc is None:
            return RecordingStatus("recording" if capture is not None else "starting", elapsed, size)
        if rc == 0:
            return RecordingStatus("finished", elapsed, size)
        return RecordingStatus("error", elapsed, size, self._read_stderr() or f"record_oakd rc={rc}")

    def stop(self) -> RecordingResult:
        if self._proc is None:
            raise RuntimeError("no se puede detener una grabación sin arrancar")
        rc = self._proc.poll()
        murio_solo = rc is not None
        if not murio_solo:
            self._proc.send_signal(signal.SIGTERM)
            try:
                self._proc.wait(timeout=_STOP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                logger.warning("record_oakd no cerró en %ss, se mata", _STOP_TIMEOUT_S)
                self._proc.kill()
                self._proc.wait(timeout=5)
            rc = self._proc.returncode

        error = None
        if murio_solo or rc != 0:
            error = self._read_stderr() or f"record_oakd terminó con rc={rc}"
        truncated = murio_solo or rc != 0

        if self._raw.exists() and self._raw.stat().st_size > 0:
            mux_error = self._mux_to_mp4()
            if mux_error is not None:
                # Se conserva el .h264: nunca se borra material que no se pudo remuxear.
                truncated = True
                error = error or mux_error

        # Duración de CAPTURA (no del subproceso): el init del device no es
        # video. Es el fallback del sidecar cuando ffprobe no puede medir.
        referencia = self._capture_monotonic or self._started_monotonic
        return RecordingResult(
            path=self._path,
            started_wallclock_ms=self._started_ms,
            duration_ms=int((time.monotonic() - referencia) * 1000),
            size_bytes=self._path.stat().st_size if self._path.exists() else 0,
            truncated=truncated,
            error=error,
        )

    def _mux_to_mp4(self) -> str | None:
        capture = self._spec.capture
        fps = capture.fps if capture is not None else 60
        return mux_h264_to_mp4(self._raw, self._path, fps)

    def _read_stderr(self) -> str:
        if self._stderr:
            return self._stderr
        if self._proc is not None and self._proc.stderr is not None:
            try:
                self._stderr = self._proc.stderr.read().strip()
            except (ValueError, OSError):
                self._stderr = ""
        return self._stderr
