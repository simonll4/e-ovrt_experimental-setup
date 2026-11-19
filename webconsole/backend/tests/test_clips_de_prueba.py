"""«Mostrar un run»: un clip de una prueba con su referencia, sus alertas, sus cuadros y su video (revisión del
2026-11-19). Workspace sintético: el repo con su results/gen2, el de datasets y las corridas."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.clips_de_prueba import ClipNoDisponible, ClipsDePrueba, tolerancia_de_bordes

EXP, MEDIA = "exp_20261031T000000Z_gen2_alr01_a_p1_c01", "run_20261030_000000_dbe_grounding_dino_aaaaaa"
FA = "11111111-2222-3333-4444-555555555555"


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(datos if isinstance(datos, str) else json.dumps(datos), encoding="utf-8")


def _alerta(aid: str, cond: str, ms: float, cuadro: int, caja=None) -> dict:
    return {"event_type": "alert_event", "state": "open", "alert_id": aid, "condition_id": cond,
            "subject_key": f"{cond}:a_p1_c01:subject_001", "frame_index": cuadro, "timestamp_ms": ms,
            "first_evidence_frame_index": cuadro - 30,
            "evidence": {"subject": {"bbox_xyxy": caja or [10.0, 10.0, 40.0, 60.0]}}}


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    repo = tmp_path / "e-ovrt_experimental-setup"
    gen2 = repo / "results" / "gen2"
    _escribir(gen2 / "ALR-01" / "corridas.json", {"corridas": {"a_p1_c01": {
        "estado": "ok", "experiment_id": EXP, "media_run_id": MEDIA, "control_run_id": "ctl",
        "variantes": {"sujeto": {"estado": "ok", "experiment_id": EXP + "_sujeto", "media_run_id": MEDIA}}}}})
    # Dos episodios: CR-01 se acierta (dentro de la ventana solo por la tolerancia) y CR-02 se pierde.
    _escribir(gen2 / "ALR-01" / "evals" / "eval_a_p1_c01.json", {
        "schema_version": "control.eval.temporal.v2", "expected_alerts_count": 2, "matched_alerts_count": 1,
        "missed_alerts_count": 1, "unexpected_alerts_count": 1, "re_alerts_count": 1, "censored_episodes_count": 0,
        "missed_alerts": [], "censored_episodes": [],
        "unexpected_alerts": [{"alert_id": FA, "condition_id": "CR-01", "frame_index": 25, "reason": "outside_all_episode_windows"}],
        "effective_matching_windows": {"CR-01": {"persistencia_min_ms": 400.0, "t_alert_max_ms": 800.0},
                                       "CR-02": {"persistencia_min_ms": 700.0, "t_alert_max_ms": 900.0}}})
    _escribir(gen2 / "ERR-01" / "evals" / "principal_alertas.json",
              [{"alert_id": FA, "clip": "a_p1_c01", "condicion": "CR-01", "causa": "P-no-detectado", "cuadro_alerta": 25}])
    _escribir(tmp_path / "e-ovrt_datasets" / "datasets" / "processed" / "clip_bench" / "gt" / "a_p1_c01.json", {
        "fps_nominal": 30, "duration_ms": 1000, "annotation": {"start_end_tolerance_ms": 50},
        "episodes": [{"id": "ep1", "condition_id": "CR-01", "start_ms": 100, "end_ms": 900},
                     {"id": "ep2", "condition_id": "CR-02", "start_ms": 0, "end_ms": 1000}]})
    runs = repo / "runs" / EXP / "control"
    _escribir(runs / "alerts.jsonl", "\n".join(json.dumps(a) for a in [
        _alerta(FA, "CR-01", 833.3, 25),             # fuera de toda ventana: la evaluación la lista como falsa
        _alerta("acierto-1", "CR-01", 460.0, 14),    # 100 + 400 − 50 = 450 ≤ 460: entra por la tolerancia
        _alerta("re-1", "CR-01", 700.0, 21),         # mismo episodio, ya acertado: re-alerta
    ]))
    _escribir(tmp_path / "e-ovrt_media-plane" / "runs" / MEDIA / "detections.jsonl", "\n".join(json.dumps({
        "source": {"frame_index": i, "timestamp_ms": i * 1000 / 30}, "detections": [
            {"label": "person", "confidence": 0.9, "bbox_xyxy": [10, 10, 40, 60]},
            {"label": "vest", "confidence": 0.5, "bbox_xyxy": [15, 30, 35, 50]}]}) for i in range(0, 30, 2)))
    if shutil.which("ffmpeg"):
        video = tmp_path / "e-ovrt_datasets" / "datasets" / "raw" / "clip_bench" / "clips" / "a_p1_c01.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=1",
                        "-pix_fmt", "yuv420p", str(video)], check=True, timeout=60)
    return repo


def test_cada_alerta_y_cada_episodio_como_los_cuenta_el_evaluador(ws: Path):
    d = ClipsDePrueba(ws).clip("ALR-01", "a_p1_c01")
    tipos = {a["alert_id"]: a["tipo"] for a in d["alertas"]}
    assert tipos == {"acierto-1": "acierto", "re-1": "re_alerta", FA: "falsa_alarma"}
    assert [(e["id"], e["estado"]) for e in d["episodios"]] == [("ep1", "acierto"), ("ep2", "perdido")]
    # La ventana incluye la tolerancia de bordes de la referencia, como el evaluador.
    assert d["episodios"][0]["ventana_ms"] == [450.0, 950.0]
    assert d["conteos"]["aciertos"] == 1 and d["conteos"]["perdidos"] == 1 and d["conteos"]["falsas_alarmas"] == 1
    fa = next(a for a in d["alertas"] if a["alert_id"] == FA)
    assert (fa["causa"], fa["motivo"], fa["sujeto"]) == ("P-no-detectado", "outside_all_episode_windows", "subject_001")
    assert d["lecturas"] == [None, "sujeto"] and d["alertas_completas"] is True and d["tipo_clip"] == "rodaje"
    assert d["origen"]["evaluacion"] == "results/gen2/ALR-01/evals/eval_a_p1_c01.json"


def test_sin_la_corrida_en_el_equipo_lo_dice_y_muestra_solo_lo_que_sabe(ws: Path):
    shutil.rmtree(ws / "runs")
    d = ClipsDePrueba(ws).clip("ALR-01", "a_p1_c01")
    assert d["alertas_completas"] is False
    assert [(a["alert_id"], a["tipo"], a["ms"]) for a in d["alertas"]] == [(FA, "falsa_alarma", 833.3)]
    # Un acierto y un perdido sobre dos episodios: sin las alertas no se puede decir cuál es cuál.
    assert [e["estado"] for e in d["episodios"]] == [None, None]
    assert any("alertas de la corrida" in f for f in d["faltan"])
    # La lectura por sujeto no tiene su evaluación en git: sin la corrida, lo dice.
    assert ClipsDePrueba(ws).clip("ALR-01", "a_p1_c01", "sujeto")["conteos"] is None


def test_lo_que_no_es_de_la_prueba_no_se_sirve(ws: Path):
    clips = ClipsDePrueba(ws)
    for pid, clip, lectura in [("ALR-01", "v99_c01", None), ("ALR-01", "../x", None), ("alr-01", "a_p1_c01", None),
                               ("ALR-01", "a_p1_c01", "otra"), ("ALR-02", "a_p1_c01", None)]:
        with pytest.raises(ClipNoDisponible):
            clips.clip(pid, clip, lectura)
    with pytest.raises(ClipNoDisponible):
        clips.cuadro("ALR-01", "a_p1_c01", 3, alerta="no es un id; rm -rf")
    with pytest.raises(ClipNoDisponible):
        clips.cuadro("ALR-01", "a_p1_c01", 3, acercar=True)  # acercar sin alerta


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="sin ffmpeg")
def test_el_cuadro_sale_del_video_con_sus_cajas_y_se_puede_acercar(ws: Path):
    from PIL import Image
    import io

    clips = ClipsDePrueba(ws)
    entero = clips.cuadro("ALR-01", "a_p1_c01", 13, alerta="acierto-1")
    assert entero[:2] == b"\xff\xd8" and Image.open(io.BytesIO(entero)).size == (320, 240)
    cerca = clips.cuadro("ALR-01", "a_p1_c01", 13, alerta="acierto-1", acercar=True)
    assert Image.open(io.BytesIO(cerca)).size[0] == 640
    assert clips.cuadro("ALR-01", "a_p1_c01", 13, alerta="acierto-1") is entero  # de la caché


def test_la_tolerancia_de_bordes_se_lee_como_el_evaluador():
    assert tolerancia_de_bordes({"annotation": {"start_end_tolerance_ms": 500}}) == 500.0
    assert tolerancia_de_bordes({"annotation": {}}) == 0.0 and tolerancia_de_bordes(None) == 0.0
    assert tolerancia_de_bordes({"annotation": {"start_end_tolerance_ms": "x"}}) == 0.0


def test_las_rutas_de_la_api(ws: Path, monkeypatch):
    from eovrt_webconsole.app import create_app
    from eovrt_webconsole.settings import ConsoleSettings

    app = create_app(ConsoleSettings(service_url="http://ignored", repo_root=ws, frozen_set_ids=frozenset()))
    with TestClient(app) as c:
        assert c.get("/api/gen2/pruebas/ALR-01/clips/a_p1_c01").json()["clip"] == "a_p1_c01"
        assert c.get("/api/gen2/pruebas/ALR-01/clips/v99_c01").status_code == 404
        fa = c.get("/api/gen2/pruebas/ERR-01/falsas-alarmas").json()
        assert fa["prueba_de_las_alertas"] == "ALR-08" and fa["falsas_alarmas"][0]["causa"] == "P-no-detectado"
        if shutil.which("ffmpeg"):
            r = c.get("/api/gen2/pruebas/ALR-01/clips/a_p1_c01/cuadro/13", params={"alerta": "acierto-1"})
            assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
            assert c.get("/api/gen2/pruebas/ALR-01/clips/a_p1_c01/video").status_code == 200
