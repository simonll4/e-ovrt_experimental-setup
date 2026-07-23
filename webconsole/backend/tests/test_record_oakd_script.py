import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "tools" / "record_oakd.py"
)
STUBS = Path(__file__).resolve().parent / "stubs"


def _run(args, env_extra=None, timeout=20):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout, env=env,
    )


def test_el_script_existe():
    assert SCRIPT.is_file()


def test_argumentos_invalidos_salen_con_2(tmp_path):
    completed = _run(["--device", "192.168.1.50", "--out", str(tmp_path / "x.h264"),
                      "--resolution", "8k"])
    assert completed.returncode == 2


def test_sin_sdk_sale_con_3(tmp_path):
    completed = _run(
        ["--device", "192.168.1.50", "--out", str(tmp_path / "x.h264")],
        env_extra={"PYTHONPATH": "/ruta/que/no/tiene/depthai"},
    )
    assert completed.returncode == 3
    assert "depthai" in (completed.stdout + completed.stderr).lower()


def test_graba_contra_el_stub_y_corta_con_sigterm(tmp_path):
    salida = tmp_path / "toma.h264"
    proc = subprocess.Popen(
        # --warmup-ms 0: este test verifica el contrato grabar->cortar->cerrar,
        # no el descarte de calentamiento (que tiene sus propios tests abajo).
        # Con el default de producción, los 3 paquetes de calentamiento del
        # stub (fps=60 -> descarta ~18) se comerían también el único paquete
        # con datos reales, rompiendo la aserción de bytes_written > 0.
        [sys.executable, str(SCRIPT), "--device", "192.168.1.50", "--out", str(salida),
         "--fps", "60", "--resolution", "1080p", "--bitrate", "25000000",
         "--warmup-ms", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(STUBS)},
    )
    primera = proc.stdout.readline()
    assert json.loads(primera)["event"] == "started"

    time.sleep(1.0)
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate(timeout=15)

    assert proc.returncode == 0
    ultima = json.loads([line for line in stdout.splitlines() if line.strip()][-1])
    assert ultima["event"] == "finished"
    assert ultima["bytes_written"] > 0
    assert salida.stat().st_size == ultima["bytes_written"]
    # warmup=0 no descarta nada: los bytes de calentamiento (reconocibles,
    # ver stub) quedan en el archivo tal cual.
    assert b"\xaa" * 8 in salida.read_bytes()


def test_descarta_los_frames_de_calentamiento_por_defecto(tmp_path):
    """Dry-run 2026-07-22: el sensor real tarda ~150 ms (9 de 60 frames) en
    converger exposición/balance de blancos; los primeros frames salen
    subexpuestos (confirmado con ffprobe signalstats + inspección visual).
    El default de producción (300 ms) tiene que descartarlos sin que el
    operador tenga que saberlo. fps=10 hace que 300 ms -> exactamente 3
    frames, el mismo número de paquetes de calentamiento que emite el stub:
    el cuarto paquete (el stream real) tiene que sobrevivir intacto."""
    salida = tmp_path / "toma.h264"
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--device", "192.168.1.50", "--out", str(salida),
         "--fps", "10", "--resolution", "1080p", "--bitrate", "25000000"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(STUBS)},
    )
    proc.stdout.readline()  # "started"
    time.sleep(1.0)
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate(timeout=15)

    assert proc.returncode == 0
    ultima = json.loads([line for line in stdout.splitlines() if line.strip()][-1])
    assert ultima["event"] == "finished"

    contenido = salida.read_bytes()
    assert b"\xaa" * 8 not in contenido, "los frames de calentamiento no deben llegar al archivo"
    from tests.stubs.depthai import _STUB_H264

    assert contenido == _STUB_H264
    assert ultima["bytes_written"] == len(_STUB_H264)
    assert ultima["discarded_bytes"] == 3 * 8


def test_warmup_completo_descarta_toda_la_toma_y_sale_con_error(tmp_path):
    """Si la toma es tan corta que ni siquiera sobrevive el calentamiento (p.
    ej. cortar sin querer a los pocos ms), no puede salir "finished" con un
    archivo vacío como si nada hubiera pasado -- eso sería el mismo tipo de
    falla silenciosa que F5 (master corrupto marcado sano) del ledger."""
    salida = tmp_path / "toma.h264"
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--device", "192.168.1.50", "--out", str(salida),
         "--fps", "10", "--resolution", "1080p", "--bitrate", "25000000",
         "--warmup-ms", "100000"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "PYTHONPATH": str(STUBS)},
    )
    proc.stdout.readline()  # "started"
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate(timeout=15)

    assert proc.returncode != 0
    ultima = json.loads([line for line in stdout.splitlines() if line.strip()][-1])
    assert ultima["event"] == "error"
    assert ultima["bytes_written"] == 0
    assert salida.stat().st_size == 0


def test_warmup_ms_negativo_sale_con_2(tmp_path):
    completed = _run(["--device", "192.168.1.50", "--out", str(tmp_path / "x.h264"),
                      "--warmup-ms", "-1"])
    assert completed.returncode == 2
