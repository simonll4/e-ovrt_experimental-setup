"""Ciclo de vida de la grabación: una activa por consola, con corte de seguridad."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from eovrt_webconsole.recording.ffmpeg_recorder import FfmpegCopyRecorder
from eovrt_webconsole.recording.guards import check_destination, check_free_space
from eovrt_webconsole.recording.naming import BASENAME_RE
from eovrt_webconsole.recording.oakd_recorder import OakDSubprocessRecorder, mux_h264_to_mp4
from eovrt_webconsole.recording.probe import ProbeError, measure
from eovrt_webconsole.recording.sidecar import write_sidecar
from eovrt_webconsole.recording.types import Recorder, RecordingResult, RecordingSpec

logger = logging.getLogger(__name__)


def _combinar_error(actual: str | None, nuevo: str) -> str:
    """Encadena motivos de error sin perder uno por pisar al otro."""
    return f"{actual}; {nuevo}" if actual else nuevo


class RecordingBusy(RuntimeError):
    pass


class BasenameTaken(RuntimeError):
    pass


class RecordingManager:
    def __init__(
        self,
        raw_dir: Path,
        oakd_interpreter: Path,
        oakd_script: Path,
        min_free_gb: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._raw_dir = Path(raw_dir)
        self._oakd_interpreter = Path(oakd_interpreter)
        self._oakd_script = Path(oakd_script)
        self._min_free_gb = min_free_gb
        self._clock = clock
        self._lock = threading.Lock()
        self._recorder: Recorder | None = None
        self._spec: RecordingSpec | None = None
        self._path: Path | None = None
        self._deadline: float | None = None
        self._last: dict | None = None

    # -- API pública -----------------------------------------------------

    def start(self, spec: RecordingSpec) -> dict:
        with self._lock:
            if self._recorder is not None:
                raise RecordingBusy(
                    f"ya hay una grabación activa: {self._spec.basename if self._spec else '?'}"
                )
            check_destination(self._raw_dir)
            check_free_space(self._raw_dir, self._min_free_gb)
            path = self._reserve(spec.basename)
            try:
                recorder = self._build_recorder(spec, path)
                recorder.start()
            except Exception:
                # Sin esto, la reserva vacía bloquea ese basename hasta el próximo
                # recover_orphans() (o sea, hasta reiniciar el backend): en pleno
                # rodaje el operador vería 409 sobre un nombre que nunca se grabó.
                path.unlink(missing_ok=True)
                raise
            self._recorder = recorder
            self._spec = spec
            self._path = path
            self._deadline = self._clock() + spec.max_duration_s
            self._last = None
        return self.status()

    def status(self) -> dict:
        with self._lock:
            if self._recorder is None:
                return self._last or {"state": "idle"}
            vencido = self._deadline is not None and self._clock() >= self._deadline
            estado = self._recorder.poll()
        if vencido:
            logger.warning("Corte automático por max_duration_s")
            try:
                return self.stop(truncar=True)
            except RecordingBusy:
                # Carrera real (reproducida con dos hilos): entre que status()
                # soltó el lock y stop() lo volvió a tomar, un stop() externo ya
                # cerró la toma. status() es de solo lectura y vive detrás de un
                # endpoint que la UI pollea mientras el operador puede apretar
                # Detener: nunca debe propagar, devuelve el resumen del ganador.
                with self._lock:
                    return self._last or {"state": "idle"}
        return {
            "state": estado.state,
            "basename": self._spec.basename if self._spec else None,
            "elapsed_ms": estado.elapsed_ms,
            "size_bytes": estado.size_bytes,
            "error": estado.error,
        }

    def stop(self, truncar: bool = False) -> dict:
        with self._lock:
            if self._recorder is None:
                raise RecordingBusy("no hay ninguna grabación activa")
            recorder, spec = self._recorder, self._spec
            self._recorder = self._spec = self._path = self._deadline = None
        result = recorder.stop()
        if truncar:
            result = RecordingResult(
                path=result.path,
                started_wallclock_ms=result.started_wallclock_ms,
                duration_ms=result.duration_ms,
                size_bytes=result.size_bytes,
                truncated=True,
                error=result.error or "corte automático por max_duration_s",
            )
        resumen = self._finalize(spec, result)
        with self._lock:
            self._last = resumen
        return resumen

    def recover_orphans(self) -> list[str]:
        """Masters sin sidecar = el backend cayó grabando. Se cierran y se marcan."""
        if not self._raw_dir.is_dir():
            return []
        recuperadas: list[str] = []
        # Primero el material OAK-D: la rama oak_d escribe <basename>.h264 y recién
        # muxea a mp4 al cortar (ver OakDSubprocessRecorder). Si el backend cae en
        # plena toma, el .h264 tiene todo el material y la reserva .mp4 de start()
        # sigue en 0 bytes. Sin este paso, el bucle de *.mp4 de abajo "recuperaría"
        # esa reserva vacía con plugin="rtsp" hardcodeado -- procedencia falsa,
        # justo en el archivo cuyo único propósito es registrarla -- y el .h264 con
        # el material real quedaría fuera del mecanismo. Procesar el .h264 primero
        # escribe el sidecar <basename>.rec.json correcto, que el bucle de *.mp4
        # respeta (mismo basename => lo salta).
        recuperadas.extend(self._recover_orphan_h264())
        for master in sorted(self._raw_dir.glob("*.mp4")):
            basename = master.stem
            if not BASENAME_RE.match(basename):
                continue  # material ajeno (lote de internet), no se toca
            if master.with_suffix(".rec.json").exists():
                continue
            spec = RecordingSpec(
                plugin="rtsp", config={}, basename=basename
            )
            result = RecordingResult(
                path=master,
                started_wallclock_ms=int(master.stat().st_mtime * 1000),
                duration_ms=0,
                size_bytes=master.stat().st_size,
                truncated=True,
                error="grabación huérfana: el backend cayó durante la toma",
            )
            self._finalize(spec, result)
            recuperadas.append(basename)
            logger.warning("Grabación huérfana recuperada: %s", basename)
        return recuperadas

    def _recover_orphan_h264(self) -> list[str]:
        recuperadas: list[str] = []
        for raw in sorted(self._raw_dir.glob("*.h264")):
            basename = raw.stem
            if not BASENAME_RE.match(basename):
                continue  # material ajeno, no se toca
            if raw.with_suffix(".rec.json").exists():
                continue
            mp4 = raw.with_suffix(".mp4")
            # fps=60 es el default de producción (CaptureSpec.fps); el rescate no
            # tiene forma de conocer el fps pedido en la toma perdida porque el
            # sidecar -que lo registraría- es justamente lo que nunca se escribió.
            mux_error = mux_h264_to_mp4(raw, mp4, fps=60, delete_raw=False)
            spec = RecordingSpec(plugin="oak_d", config={}, basename=basename)
            resultado_path = mp4 if mux_error is None else raw
            motivo = "grabación huérfana: el backend cayó durante la toma"
            if mux_error is not None:
                motivo = f"{motivo}; {mux_error}"
            result = RecordingResult(
                path=resultado_path,
                started_wallclock_ms=int(raw.stat().st_mtime * 1000),
                duration_ms=0,
                size_bytes=resultado_path.stat().st_size,
                truncated=True,
                error=motivo,
            )
            self._finalize(spec, result)
            recuperadas.append(basename)
            logger.warning("Grabación huérfana OAK-D recuperada: %s", basename)
        return recuperadas

    # -- Internos --------------------------------------------------------

    def _reserve(self, basename: str) -> Path:
        """Reserva atómica: O_EXCL falla si el archivo ya existe. Nunca se pisa una toma."""
        path = self._raw_dir / f"{basename}.mp4"
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError as exc:
            raise BasenameTaken(f"ya existe una toma con ese nombre: {basename}") from exc
        os.close(handle)
        return path

    def _build_recorder(self, spec: RecordingSpec, path: Path) -> Recorder:
        if spec.plugin == "oak_d":
            return OakDSubprocessRecorder(
                spec, path, interpreter=self._oakd_interpreter, script=self._oakd_script
            )
        return FfmpegCopyRecorder(spec, path)

    def _finalize(self, spec: RecordingSpec | None, result: RecordingResult) -> dict:
        assert spec is not None
        try:
            measured = measure(result.path)
        except ProbeError as exc:
            # Un master que no se puede medir con ffprobe es, en la práctica, un
            # master sospechoso (p. ej. sin átomo moov tras un kill()). Antes esto
            # solo se logueaba: el resumen y el sidecar salían con truncated=false
            # y error=null, como si la toma estuviera sana. Se combina acá para
            # que quede reflejado en ambos, no solo en un log que nadie mira en
            # pleno rodaje.
            logger.warning("No se pudo medir %s: %s", result.path.name, exc)
            measured = None
            result = replace(
                result, truncated=True, error=_combinar_error(result.error, str(exc))
            )
        try:
            sidecar: Path | None = write_sidecar(spec, result, measured)
        except OSError as exc:
            # Si el disco se llena justo al cerrar una toma larga, escribir el
            # sidecar (o el hash previo, sha256_of) puede fallar. Sin este try,
            # la excepción cruda atraviesa stop() hasta el DELETE y el operador
            # ve un 500 en el peor momento, perdiendo el resumen aunque el video
            # sí haya quedado en disco. Se marca el problema y se sigue.
            logger.error("No se pudo escribir el sidecar de %s: %s", result.path.name, exc)
            sidecar = None
            result = replace(
                result,
                truncated=True,
                error=_combinar_error(result.error, f"no se pudo escribir el sidecar: {exc}"),
            )
        # El substream de un DVR pasa desapercibido si nadie lo mira: se marca.
        substream = measured is not None and measured.width < 1280
        return {
            "state": "finished",
            "basename": spec.basename,
            "file": str(result.path),
            "sidecar": str(sidecar) if sidecar is not None else None,
            "duration_ms": measured.duration_ms if measured else result.duration_ms,
            "size_bytes": result.size_bytes,
            "fps": measured.fps if measured else None,
            "resolution": f"{measured.width}x{measured.height}" if measured else None,
            "truncated": result.truncated,
            "suspected_substream": substream,
            "error": result.error,
        }
