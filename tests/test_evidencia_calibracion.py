"""La calibración de encuadre (doc 134 §13.19, 2026-11-05; `tools/evidencia/calibracion.py`).

Los criterios son geométricos y están fijados en `experiments/demo_defensa/calibracion.json`. Acá se
los ejercita con los tres encuadres conocidos, reconstruidos a partir de sus números medidos
(doc 142 §3.2 y el análisis del 2026-11-05):
- el rodaje de julio (cámara alta mirando hacia abajo: cabeza al 1–15 % del cuadro, ancho/alto 0,35–0,46):
  tiene que pasar;
- la OAK-D del 11-01 (a la altura del pecho, de frente y de cerca: cabeza al 30 %, ancho/alto 0,52–0,86,
  cortada en la cadera): NO tiene que pasar;
- la cámara IP del 11-01 (alta, pies cortados): pasa, con la observación de los pies.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tools.evidencia import calibracion as cal
from tools.evidencia.__main__ import main as cli
from tools.evidencia.entorno import REPO, Entorno

T0 = 1_000_000
W, H = 960, 540


def _entorno(tmp_path: Path) -> Entorno:
    ent = Entorno(ws=tmp_path / "ws", repo=REPO, modo="docker", consola_url="http://consola",
                  datasets_medios="/e-ovrt_datasets")
    ent.media_runs.mkdir(parents=True, exist_ok=True)
    return ent


def _caja(top: float, bot: float, ancho_alto: float, cx: float = 0.5) -> list[float]:
    alto = (bot - top) * H
    ancho = ancho_alto * alto
    return [cx * W - ancho / 2, top * H, cx * W + ancho / 2, bot * H]


def _vest(persona: list[float]) -> dict:
    x1, y1, x2, y2 = persona
    return {"label": "vest", "confidence": 0.8,
            "bbox_xyxy": [x1 + 0.2 * (x2 - x1), y1 + 0.35 * (y2 - y1), x2 - 0.2 * (x2 - x1), y1 + 0.6 * (y2 - y1)]}


def _sesion(ent: Entorno, sesiones: Path, sid: str, cerca: dict, lejos: dict, *, altura=1.9, camara=None,
            con_chaleco=True, intruso=False, fase="done") -> Path:
    """Una sesión CAL a 5 fps: la persona parada en la marca cercana (2–12 s), la lejana (12–22 s) y
    de vuelta (22–30 s); `cerca`/`lejos` dan (top, bot, ancho_alto) de su caja."""
    media_id = f"run_{sid}"
    d = sesiones / sid
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({
        "session_id": sid, "escena": "CAL", "fase": fase, "experiment_id": f"exp_{sid}",
        "ids": {"media_run_id": media_id, "control_run_id": f"ctl_{sid}"}, "camara": camara,
        "terminada_en": "2026-11-07T10:00:30+00:00"}))
    marcas = {"desfase_contenedor_menos_host_ms": 0.0, "proposito": "calibracion", "escena": "CAL",
              "fisica": {"altura_m": altura, "distancia_cerca_m": 3.0, "distancia_lejos_m": 6.0},
              "acciones": [{"accion": "cerca", "pared_ms": T0 + 2000}, {"accion": "lejos", "pared_ms": T0 + 12000},
                           {"accion": "cerca_2", "pared_ms": T0 + 22000}]}
    (d / "marcas.json").write_text("﻿" + json.dumps(marcas))
    mr = ent.media_runs / media_id
    mr.mkdir(parents=True)
    n = 150
    (mr / "metrics.jsonl").write_text("".join(json.dumps({
        "unit_id": f"u{i}", "capture_wallclock_ms": T0 + 200 * i}) + "\n" for i in range(n)))
    filas = []
    for i in range(n):
        t = 200 * i / 1000
        geo = lejos if 12 <= t < 22 else cerca
        persona = _caja(*geo)
        dets = [{"label": "person", "confidence": 0.9, "bbox_xyxy": persona}]
        if con_chaleco:
            dets.append(_vest(persona))
        if intruso:  # alguien chico al costado: no es la caja más grande, pero cuenta como segunda persona
            dets.append({"label": "person", "confidence": 0.7, "bbox_xyxy": _caja(0.3, 0.5, 0.4, cx=0.85)})
        filas.append({"unit_id": f"u{i}", "source": {"timestamp_ms": T0 + 200 * i, "width": W, "height": H},
                      "detections": dets})
    (mr / "detections.jsonl").write_text("".join(json.dumps(f) + "\n" for f in filas))
    return d


# Los tres encuadres conocidos, por (top, bot, ancho/alto) de la caja de la persona.
RODAJE = {"cerca": (0.10, 0.95, 0.38), "lejos": (0.08, 0.40, 0.38)}
OAKD_11_01 = {"cerca": (0.30, 1.00, 0.55), "lejos": (0.42, 0.75, 0.40)}
IP_11_01 = {"cerca": (0.10, 1.00, 0.45), "lejos": (0.08, 0.50, 0.38)}


@pytest.fixture
def spec():
    return cal.cargar_spec(REPO)


def test_el_pre_registro_de_la_calibracion_es_el_esperado(spec):
    assert spec["escena"] == "CAL" and [p["accion"] for p in spec["guion"]] == ["cerca", "lejos", "cerca_2"]
    assert set(spec["criterios"]["bloqueantes"]) == {"una_persona", "altura_declarada", "cabeza_visible", "cerca_no_cortada",
                                                     "cerca_tamano", "camara_alta", "lejos_tamano"}
    assert set(spec["criterios"]["recomendados"]) == {"pies_visibles", "altura_recomendada", "chaleco_puesto_visto", "repetible"}
    assert spec["umbrales"]["cerca_ancho_alto_max"] == 0.50 and spec["umbrales"]["cerca_cabeza_top_max"] == 0.20
    assert spec["_sha256"]
    # `rodaje.ps1` lee el mismo archivo (guion, escena y vigencia): tiene que seguir siendo JSON plano.
    assert spec["umbrales"]["vigencia_max_h"] == 12


def test_el_encuadre_del_rodaje_pasa_sin_observaciones(tmp_path, spec):
    ent = _entorno(tmp_path)
    _sesion(ent, tmp_path / "s", "demo_a_CAL", **RODAJE)
    ev = cal.evaluar(ent, cal.sesiones_cal(tmp_path / "s")[0], spec)
    assert ev["ok"] is True and ev["fallan"] == [] and ev["observaciones"] == []
    cerca, lejos = ev["segmentos"]["cerca"], ev["segmentos"]["lejos"]
    assert cerca["ancho_alto_p50"] == 0.38 and cerca["cabeza_top_p50"] == 0.1 and cerca["pies_visibles"] == 1.0
    assert lejos["alto_p50"] == 0.32 and lejos["persona_detectada"] == 1.0
    assert cerca["chaleco_puesto_visto"] == 1.0
    assert ev["camara"] == {"plugin": "oak_d", "id": None, "nombre": None, "resolucion": [960, 540]}
    assert "VEREDICTO: encuadre OK" in cal.informe(ev)


def test_el_encuadre_de_la_oakd_del_11_01_no_pasa_y_dice_que_mover(tmp_path, spec):
    ent = _entorno(tmp_path)
    _sesion(ent, tmp_path / "s", "demo_b_CAL", **OAKD_11_01)
    ev = cal.evaluar(ent, cal.sesiones_cal(tmp_path / "s")[0], spec)
    assert ev["ok"] is False
    assert set(ev["fallan"]) == {"cerca_no_cortada", "camara_alta"}
    assert "pies_visibles" in ev["observaciones"]
    assert any("cadera" in s for s in ev["sugerencias"]) and any("por encima de la cabeza" in s for s in ev["sugerencias"])
    assert "NO pasa" in cal.informe(ev)


def test_la_camara_ip_alta_pasa_con_la_observacion_de_los_pies(tmp_path, spec):
    ent = _entorno(tmp_path)
    _sesion(ent, tmp_path / "s", "demo_c_CAL", **IP_11_01, camara={"id": "rtsp_dvr_sub", "plugin": "rtsp", "nombre": "DVR"})
    ev = cal.evaluar(ent, cal.sesiones_cal(tmp_path / "s")[0], spec)
    assert ev["ok"] is True and ev["observaciones"] == ["pies_visibles"]
    assert ev["camara"]["plugin"] == "rtsp" and ev["camara"]["id"] == "rtsp_dvr_sub"


def test_altura_baja_intruso_y_chaleco_no_visto(tmp_path, spec):
    ent = _entorno(tmp_path)
    _sesion(ent, tmp_path / "s", "demo_d_CAL", **RODAJE, altura=1.5, intruso=True, con_chaleco=False)
    ev = cal.evaluar(ent, cal.sesiones_cal(tmp_path / "s")[0], spec)
    assert set(ev["fallan"]) == {"una_persona", "altura_declarada"}
    assert set(ev["observaciones"]) == {"altura_recomendada", "chaleco_puesto_visto"}


def test_sin_marcas_o_sin_detecciones_es_invalida(tmp_path, spec):
    ent = _entorno(tmp_path)
    d = _sesion(ent, tmp_path / "s", "demo_e_CAL", **RODAJE)
    (d / "marcas.json").unlink()
    with pytest.raises(cal.CalibracionInvalida, match="marcas.json"):
        cal.evaluar(ent, cal.sesiones_cal(tmp_path / "s")[0], spec)


def test_guardar_deja_la_constancia_y_la_vigente_por_camara_aunque_no_pase(tmp_path, spec, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    _sesion(ent, tmp_path / "s", "demo_f_CAL", **RODAJE)
    _sesion(ent, tmp_path / "s", "demo_g_CAL", **OAKD_11_01)
    buena, mala = cal.sesiones_cal(tmp_path / "s")
    ruta = cal.guardar(ent, cal.evaluar(ent, buena, spec))
    assert ruta == ent.resultados / "_calibraciones" / "demo_f_CAL.json"
    vig = cal.leer_vigente(ent)["por_camara"]["oak_d"]
    assert vig["session_id"] == "demo_f_CAL" and vig["ok"] is True and vig["altura_m"] == 1.9
    assert cal.vigencia(vig, spec)[0] is True
    # La siguiente calibración de la misma cámara la reemplaza, pase o no: la cámara se movió.
    cal.guardar(ent, cal.evaluar(ent, mala, spec))
    vig = cal.leer_vigente(ent)["por_camara"]["oak_d"]
    assert vig["session_id"] == "demo_g_CAL" and vig["ok"] is False and vig["aceptada"] is False
    sirve, detalle = cal.vigencia(vig, spec)
    assert sirve is False and "NO pasó" in detalle
    assert (ent.resultados / "_calibraciones" / "demo_f_CAL.json").is_file()


def test_vigencia_vence_a_las_12_h_y_una_aceptada_sirve(spec):
    ahora = datetime.now(UTC)
    base = {"session_id": "x", "ok": True, "aceptada": False, "fallan": [], "observaciones": []}
    assert cal.vigencia({**base, "fecha": (ahora - timedelta(hours=1)).isoformat()}, spec, ahora)[0] is True
    assert cal.vigencia({**base, "fecha": (ahora - timedelta(hours=13)).isoformat()}, spec, ahora)[0] is False
    aceptada = {**base, "ok": False, "aceptada": True, "motivo": "control", "fallan": ["camara_alta"],
                "fecha": ahora.isoformat()}
    sirve, detalle = cal.vigencia(aceptada, spec, ahora)
    assert sirve is True and "aceptada con motivo" in detalle
    assert cal.vigencia(None, spec, ahora)[0] is False


def test_cli_calibrar_mide_la_ultima_y_acepta_con_motivo(tmp_path, spec, monkeypatch, capsys):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    monkeypatch.setattr("tools.evidencia.__main__.detectar", lambda: ent)
    sesiones = tmp_path / "s"
    _sesion(ent, sesiones, "demo_h_CAL", **RODAJE)
    assert cli(["calibrar", "--sesiones", str(sesiones)]) == 0
    assert "encuadre OK" in capsys.readouterr().out
    _sesion(ent, sesiones, "demo_i_CAL", **OAKD_11_01)
    assert cli(["calibrar", "--sesiones", str(sesiones)]) == 1  # la última: no pasa
    with pytest.raises(SystemExit, match="--motivo"):
        cli(["calibrar", "--sesiones", str(sesiones), "--aceptar"])
    assert cli(["calibrar", "--sesiones", str(sesiones), "--aceptar", "--motivo", "control del encuadre del 11-01",
                "--quien", "equipo"]) == 0
    vig = cal.leer_vigente(ent)["por_camara"]["oak_d"]
    assert vig["session_id"] == "demo_i_CAL" and vig["ok"] is False and vig["aceptada"] is True
    constancia = cal.leer_constancia(ent, "demo_i_CAL")
    assert constancia["aceptada"]["quien"] == "equipo" and constancia["ok"] is False
    assert cli(["calibrar", "--sesiones", str(sesiones), "--sesion", "demo_h_CAL"]) == 0  # una en particular
    assert cal.leer_vigente(ent)["por_camara"]["oak_d"]["session_id"] == "demo_h_CAL"
    assert cli(["calibrar", "--sesiones", str(sesiones), "--listar"]) == 0
    assert "sirve" in capsys.readouterr().out
