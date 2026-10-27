"""Demo: render post-corrida con cuadros sintéticos de tiempos conocidos (spec §8)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from eovrt_webconsole.demo.render import (
    COLOR_ESTADO_RGB,
    Cuadro,
    duraciones_s,
    estados_por_cuadro,
    render_sesion,
)

REPO_REAL = Path(__file__).resolve().parents[3]
# 6 cuadros procesados a ~5 fps con un hueco (el motor tardó más en el 4.º).
TIEMPOS_MS = [1000.0, 1200.0, 1400.0, 2000.0, 2200.0, 2400.0]


def _jsonl(path: Path, filas: list[dict]) -> None:
    path.write_text("".join(json.dumps(f) + "\n" for f in filas), encoding="utf-8")


def _corrida(tmp_path: Path) -> tuple[Path, Path, Path]:
    media = tmp_path / "media_run"
    (media / "previews").mkdir(parents=True)
    filas = []
    for i, ts in enumerate(TIEMPOS_MS):
        unit = f"frame_{i:06d}"
        Image.new("RGB", (320, 180), (10 * i, 40, 90)).save(media / "previews" / f"{unit}.preview.jpg")
        filas.append({"unit_id": unit, "source": {"frame_index": i, "timestamp_ms": ts},
                      "detections": []})
    _jsonl(media / "detections.jsonl", filas)
    (media / "summary.json").write_text('{"status": "stopped"}')
    control = tmp_path / "control_run"
    control.mkdir()
    ev = lambda f, st: {"event_type": "pattern_state_changed", "condition_id": "CR-01",  # noqa: E731
                        "subject_key": "CR-01:oak", "frame_index": f, "unit_id": f"frame_{f:06d}",
                        "timestamp_ms": TIEMPOS_MS[f], "state": st}
    _jsonl(control / "pattern_events.jsonl",
           [ev(1, "candidate"), ev(3, "confirmed"), ev(4, "sustained"), ev(5, "resolved")])
    _jsonl(control / "alerts.jsonl", [{
        "alert_id": "al-1", "condition_id": "CR-01", "severity": "high", "subject_key": "CR-01:oak",
        "frame_index": 3, "unit_id": "frame_000003", "timestamp_ms": 2000.0,
        "first_evidence_unit_id": "frame_000001", "first_evidence_frame_index": 1,
    }])
    experimento = tmp_path / "exp"
    (experimento / "distribution").mkdir(parents=True)
    _jsonl(experimento / "distribution" / "notifications.jsonl",
           [{"alert_id": "al-1", "outcome": "delivered"}])
    return media, control, experimento


TESTIGO = [{
    "recibido_ms": 5_000_012.0, "topic": "eovrt/alerts/high",
    "payload": {"alert_id": "al-1", "condition_id": "CR-01", "confirmed_wall_ms": 5_000_000.0},
}]


def test_duraciones_hasta_el_siguiente_y_el_ultimo_un_segundo():
    cuadros = [Cuadro(i, f"u{i}", ts, None) for i, ts in enumerate(TIEMPOS_MS)]
    assert duraciones_s(cuadros) == pytest.approx([0.2, 0.2, 0.6, 0.2, 0.2, 1.0])


def test_estados_por_cuadro_siguen_los_eventos_del_motor():
    cuadros = [Cuadro(i, f"u{i}", ts, None) for i, ts in enumerate(TIEMPOS_MS)]
    eventos = [
        {"event_type": "pattern_state_changed", "condition_id": "CR-01", "subject_key": "k",
         "frame_index": f, "timestamp_ms": TIEMPOS_MS[f], "state": st}
        for f, st in ((1, "candidate"), (3, "confirmed"), (5, "resolved"))
    ]
    estados = estados_por_cuadro(cuadros, eventos)
    assert estados["CR-01"] == ["inactive", "candidate", "candidate", "confirmed", "confirmed", "resolved"]
    assert estados["CR-02"] == ["inactive"] * 6


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                    reason="sin ffmpeg/ffprobe")
def test_render_arma_video_cuadros_clave_y_linea_de_tiempo(tmp_path):
    media, control, experimento = _corrida(tmp_path)
    salida = tmp_path / "sesion" / "resultado"
    resumen = render_sesion(salida, media_dir=media, control_dir=control,
                            experimento_dir=experimento, testigo=TESTIGO)

    assert resumen["errores"] == [] and resumen["faltantes"] == []
    assert resumen["video"] == "video.mp4"
    duracion = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
         str(salida / "video.mp4")], capture_output=True, text=True, check=True,
    ).stdout.strip())
    # La suma de los intervalos entre cuadros (1,4 s) más el último (1 s).
    assert duracion == pytest.approx(2.4, abs=0.1)
    assert resumen["fps_efectivos"] == pytest.approx(5 / 1.4, abs=0.01)

    nombres = sorted(p.name for p in (salida / "cuadros").iterdir())
    assert nombres == [
        "alerta01_CR-01_1-evidencia.jpg",
        "alerta01_CR-01_2-confirmacion.jpg",
        "alerta01_CR-01_3-resolucion.jpg",
    ]
    (linea,) = json.loads((salida / "linea_de_tiempo.json").read_text())
    assert linea["tramos"] == {"evidencia_a_confirmacion_ms": 800.0, "confirmacion_a_broker_ms": 12.0}
    assert (linea["frame_primera_evidencia"], linea["frame_confirmacion"], linea["frame_resolucion"]) == (1, 3, 5)
    assert linea["entrega"] == "delivered"
    assert (salida / "log" / "control" / "alerts.jsonl").is_file()
    assert (salida / "log" / "distribucion" / "notifications.jsonl").is_file()
    assert not (salida / ".render").exists()  # los cuadros intermedios no quedan en disco


def test_render_sin_insumos_no_levanta_y_dice_que_falta(tmp_path):
    resumen = render_sesion(tmp_path / "r", media_dir=None, control_dir=None,
                            experimento_dir=None, testigo=[])
    assert resumen["video"] is None
    assert "detections.jsonl del media-plane" in resumen["faltantes"]
    assert (tmp_path / "r" / "resumen.json").is_file()


def test_colores_iguales_a_los_del_overlay_de_la_defensa():
    """Mismos colores que V1/VG1: COL_STATE de defensa/overlay_render.py (BGR)."""
    spec = importlib.util.spec_from_file_location("overlay_render", REPO_REAL / "defensa" / "overlay_render.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    assert {k: tuple(reversed(v)) for k, v in modulo.COL_STATE.items()} == COLOR_ESTADO_RGB
