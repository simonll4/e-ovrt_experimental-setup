import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from eovrt_webconsole.recording.oakd_recorder import (
    InterpreterUnavailable,
    OakDSubprocessRecorder,
    check_interpreter,
)
from eovrt_webconsole.recording.types import RecordingSpec

SCRIPT_REAL = Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"
STUBS = Path(__file__).resolve().parent / "stubs"

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="requiere ffmpeg en el sistema"
)


def _spec() -> RecordingSpec:
    return RecordingSpec(
        plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take1", label="oak_d_lab"
    )


def test_check_interpreter_acepta_el_interprete_actual():
    check_interpreter(Path(sys.executable))  # no levanta (no valida depthai acá)


def test_check_interpreter_rechaza_una_ruta_inexistente():
    with pytest.raises(InterpreterUnavailable):
        check_interpreter(Path("/no/existe/python"))


def test_graba_contra_el_stub_y_muxea_a_mp4(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(STUBS))
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = OakDSubprocessRecorder(
        _spec(), destino, interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    recorder.start()
    time.sleep(1.5)
    assert recorder.poll().state == "recording"
    result = recorder.stop()

    assert destino.exists()
    assert result.size_bytes > 0
    assert result.truncated is False
    assert not destino.with_suffix(".h264").exists()  # el crudo se limpia tras muxear


def test_falla_el_muxeo_conserva_el_h264_crudo_y_marca_truncado(tmp_path, monkeypatch):
    """Regla de oro del módulo: si el mux a mp4 falla, el .h264 crudo NUNCA se borra
    y la toma queda truncated=True (material de rodaje irrepetible).

    El subproceso de grabación corre de verdad contra el stub y termina limpio
    (rc=0, vía SIGTERM en stop()); lo único que se rompe a propósito es el paso
    de muxeo, apuntando "ffmpeg" a un binario falso que siempre falla.
    """
    monkeypatch.setenv("PYTHONPATH", str(STUBS))

    ffmpeg_falso_dir = tmp_path / "bin"
    ffmpeg_falso_dir.mkdir()
    ffmpeg_falso = ffmpeg_falso_dir / "ffmpeg"
    ffmpeg_falso.write_text("#!/bin/sh\necho 'mux roto a proposito' >&2\nexit 1\n")
    ffmpeg_falso.chmod(0o755)
    monkeypatch.setenv("PATH", f"{ffmpeg_falso_dir}:{os.environ.get('PATH', '')}")

    destino = tmp_path / "P1-a-take1.mp4"
    recorder = OakDSubprocessRecorder(
        _spec(), destino, interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    recorder.start()
    time.sleep(1.5)
    assert recorder.poll().state == "recording"
    result = recorder.stop()  # SIGTERM -> el script cierra limpio (rc=0) y después falla el mux

    raw = destino.with_suffix(".h264")
    assert raw.exists()
    assert raw.stat().st_size > 0
    assert result.truncated is True
    assert result.error is not None


def test_script_inexistente_deja_la_toma_en_error(tmp_path):
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = OakDSubprocessRecorder(
        _spec(), destino, interpreter=Path(sys.executable), script=tmp_path / "no-existe.py"
    )
    recorder.start()
    deadline = time.monotonic() + 10
    while recorder.poll().state == "recording" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "error"
    result = recorder.stop()
    assert result.truncated is True
    assert result.error is not None


def test_stop_sin_start_es_error_explicito(tmp_path):
    recorder = OakDSubprocessRecorder(
        _spec(), tmp_path / "P1-a-take1.mp4", interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    with pytest.raises(RuntimeError, match="sin arrancar"):
        recorder.stop()
