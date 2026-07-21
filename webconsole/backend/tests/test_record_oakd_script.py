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
        [sys.executable, str(SCRIPT), "--device", "192.168.1.50", "--out", str(salida),
         "--fps", "60", "--resolution", "1080p", "--bitrate", "25000000"],
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
