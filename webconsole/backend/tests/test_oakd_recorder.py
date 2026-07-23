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
from eovrt_webconsole.recording.types import CaptureSpec, RecordingSpec

SCRIPT_REAL = Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"
STUBS = Path(__file__).resolve().parent / "stubs"

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="requiere ffmpeg en el sistema"
)


@pytest.fixture
def nuevo_recorder():
    """Crea recorders garantizando que ningún subproceso sobreviva al test.

    Sin esto, un assert que falla antes de `recorder.stop()` deja vivo el
    `record_oakd.py`: contra el stub la cola nunca bloquea, así que el huérfano
    quema un core entero hasta que alguien lo nota. Pasó de verdad en el
    dry-run 2026-07-22 (18 minutos al 100% tras una fase RED).
    """
    creados = []

    def _crear(*args, **kwargs):
        recorder = OakDSubprocessRecorder(*args, **kwargs)
        creados.append(recorder)
        return recorder

    yield _crear

    for recorder in creados:
        proc = recorder._proc
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def _spec() -> RecordingSpec:
    return RecordingSpec(
        plugin="oak_d", config={"url": "192.168.1.50"}, basename="P1-a-take1", label="oak_d_lab",
        # fps=10: con el default de record_oakd.py (300 ms de calentamiento
        # descartados, ver dry-run 2026-07-22) eso son exactamente los 3
        # paquetes de calentamiento que emite el stub antes del stream real;
        # a fps=60 (default de CaptureSpec) el descarte se comería también
        # el único paquete con datos reales del stub.
        capture=CaptureSpec(fps=10),
    )


def test_check_interpreter_acepta_el_interprete_actual():
    check_interpreter(Path(sys.executable))  # no levanta (no valida depthai acá)


def test_check_interpreter_rechaza_una_ruta_inexistente():
    with pytest.raises(InterpreterUnavailable):
        check_interpreter(Path("/no/existe/python"))


def test_graba_contra_el_stub_y_muxea_a_mp4(tmp_path, monkeypatch, nuevo_recorder):
    monkeypatch.setenv("PYTHONPATH", str(STUBS))
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = nuevo_recorder(
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


def test_falla_el_muxeo_conserva_el_h264_crudo_y_marca_truncado(tmp_path, monkeypatch, nuevo_recorder):
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
    recorder = nuevo_recorder(
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


def test_poll_reporta_starting_mientras_el_device_inicializa(tmp_path, monkeypatch, nuevo_recorder):
    """F-DR6 (dry-run 2026-07-22): la OAK-D PoE tarda ~9 s en conectar antes de
    entregar el primer frame. Si el panel dice "● REC" durante ese lapso, el
    operador actúa la infracción antes de que la cámara capture y la toma se
    pierde -- material irrepetible. Hasta que el subproceso avisa que arrancó
    de verdad (evento "started"), el estado tiene que ser "starting".
    """
    monkeypatch.setenv("PYTHONPATH", str(STUBS))
    monkeypatch.setenv("EOVRT_STUB_OAKD_INIT_S", "2.0")

    destino = tmp_path / "P1-a-take1.mp4"
    recorder = nuevo_recorder(
        _spec(), destino, interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    recorder.start()

    time.sleep(0.7)
    en_init = recorder.poll()
    assert en_init.state == "starting"
    # El cronómetro no puede correr todavía: no se está grabando nada.
    assert en_init.elapsed_ms == 0

    deadline = time.monotonic() + 15
    while recorder.poll().state == "starting" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "recording"
    recorder.stop()


def test_elapsed_cuenta_desde_la_captura_no_desde_el_lanzamiento(tmp_path, monkeypatch, nuevo_recorder):
    """El cronómetro que ve el operador tiene que medir GRABACIÓN real, no
    tiempo de inicialización: con 40 s en pantalla salían 28 s de video."""
    monkeypatch.setenv("PYTHONPATH", str(STUBS))
    monkeypatch.setenv("EOVRT_STUB_OAKD_INIT_S", "2.0")

    destino = tmp_path / "P1-a-take1.mp4"
    recorder = nuevo_recorder(
        _spec(), destino, interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    t_popen = time.monotonic()
    recorder.start()
    deadline = time.monotonic() + 15
    while recorder.poll().state == "starting" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "recording"

    time.sleep(1.0)
    elapsed = recorder.poll().elapsed_ms
    desde_popen_ms = (time.monotonic() - t_popen) * 1000
    # Lo que importa no es el valor absoluto sino que el init (2 s del stub) NO
    # esté contado: el cronómetro tiene que ir MUY por detrás del reloj de pared
    # desde el lanzamiento del subproceso.
    assert desde_popen_ms - elapsed >= 1500, (
        f"elapsed_ms={elapsed:.0f} vs {desde_popen_ms:.0f} ms desde Popen: "
        "el cronómetro está contando el init del device"
    )
    assert elapsed >= 500
    recorder.stop()


def test_script_inexistente_deja_la_toma_en_error(tmp_path, nuevo_recorder):
    destino = tmp_path / "P1-a-take1.mp4"
    recorder = nuevo_recorder(
        _spec(), destino, interpreter=Path(sys.executable), script=tmp_path / "no-existe.py"
    )
    recorder.start()
    deadline = time.monotonic() + 10
    # "starting" también es un estado no-terminal: se espera hasta que el
    # subproceso muera de verdad (script inexistente -> rc != 0).
    while recorder.poll().state in {"starting", "recording"} and time.monotonic() < deadline:
        time.sleep(0.1)
    assert recorder.poll().state == "error"
    result = recorder.stop()
    assert result.truncated is True
    assert result.error is not None


def test_stop_sin_start_es_error_explicito(tmp_path, nuevo_recorder):
    recorder = nuevo_recorder(
        _spec(), tmp_path / "P1-a-take1.mp4", interpreter=Path(sys.executable), script=SCRIPT_REAL
    )
    with pytest.raises(RuntimeError, match="sin arrancar"):
        recorder.stop()
