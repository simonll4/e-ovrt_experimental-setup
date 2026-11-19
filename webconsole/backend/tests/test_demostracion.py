"""«Correr un clip» (plan de la consola de evidencia, §7.2): tres clips fijos del rodaje por la cadena completa,
con la configuración del informe, por el mismo administrador de experimentos. No es evidencia."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from eovrt_webconsole import demostracion as dm
from eovrt_webconsole.demo.config import Despliegue
from eovrt_webconsole.demostracion import CLIPS, STRIDE, ClipNoListo, CorrerClip, armar_resultado
from eovrt_webconsole.plataforma import PERFIL_OPERATIVO

REF = {"clip_id": "a_p1_c04", "fps_nominal": 30, "duration_ms": 30667, "episodes": [
    {"id": "ep1", "condition_id": "CR-01", "start_ms": 3133, "end_ms": 27652}]}


def _workspace(tmp_path: Path, clips=("a_p1_c04", "a_p2_c03")) -> Path:
    ws = tmp_path / "ws"
    for clip in clips:
        gt = ws / "e-ovrt_datasets" / "datasets" / "processed" / "clip_bench" / "gt" / f"{clip}.json"
        gt.parent.mkdir(parents=True, exist_ok=True)
        gt.write_text(json.dumps({**REF, "clip_id": clip}), encoding="utf-8")
        video = ws / "e-ovrt_datasets" / "datasets" / "raw" / "clip_bench" / "clips" / f"{clip}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"mp4")
    return ws


def _app(tmp_path: Path, *, compose=True, activa=PERFIL_OPERATIVO, en_curso=None):
    class Http:
        def __init__(self, codigo=200, cuerpo=None):
            self.codigo, self.cuerpo = codigo, cuerpo or {}

        async def get(self, ruta):
            return SimpleNamespace(status_code=self.codigo, json=lambda: self.cuerpo)

    class Experimentos:
        def __init__(self):
            self.iniciados, self.estados = [], {}

        def current(self):
            return en_curso

        def start(self, manifest, **kw):
            self.iniciados.append((manifest, kw))
            self.estados[manifest.experiment_id] = {"status": "running", "media_run_id": "run_m"}
            return manifest.experiment_id

        def get(self, experiment_id):
            return self.estados.get(experiment_id)

    settings = SimpleNamespace(repo_root=tmp_path / "repo", compose_dir=tmp_path if compose else None,
                               experiment_poll_interval_s=0.01, service_url="http://127.0.0.1:8080",
                               control_service_url="http://control-plane:8081")
    (tmp_path / "repo").mkdir(parents=True, exist_ok=True)

    async def status(run_id):  # mientras corre, los cuadros vienen en el progreso
        return {"status": "running", "progress": {"units_processed": 40}}

    async def control_current():
        return {"control_run_id": "ctl", "progress": {"units_processed": 40}}

    state = SimpleNamespace(
        settings=settings, experiment_manager=Experimentos(),
        target_manager=SimpleNamespace(active=activa) if compose else None,
        http=Http(cuerpo={"ref": "grounding-dino/gdino-tiny-560"}), control_http=Http(), distribution_http=Http(),
        backend=SimpleNamespace(status=status), control_backend=SimpleNamespace(current=control_current),
        demo_manager=SimpleNamespace(estado=lambda: {"fase": "idle"}),
    )
    return SimpleNamespace(state=state)


class TestigoFalso:
    def __init__(self):
        self.lista = []
        self.cerrado = False

    def iniciar(self): pass
    def esperar_suscripcion(self, timeout): pass
    def mensajes(self): return list(self.lista)
    def escribir(self, ruta): ruta.write_text("\n".join(json.dumps(m) for m in self.lista), encoding="utf-8")
    def cerrar(self): self.cerrado = True


def _correr(tmp_path, monkeypatch, **kw):
    app = _app(tmp_path, **kw)
    testigo = TestigoFalso()
    monkeypatch.setattr(dm.demo_config, "resolver_configs", lambda repo, variante, desp: {
        "media": {"ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137"}},
                  "prompts": {"set_inline": {"id": "cr01_cr02_v2_short"}}, "bus": {"wait_for_subscriber_ms": 10000},
                  "run": {"name": "demo_defensa", "save_previews": True}},
        "control": {"input": "bus"}, "distribution": {"channels": ["mqtt"]}})
    monkeypatch.setattr(dm.demo_config, "verificar_congelado", lambda repo, configs, modelo: {
        "ok": True, "tag": "informe-2026", "items": [{"id": "prompt_set", "actual": "abc"}]})
    correr = CorrerClip(app, tmp_path / "salida", testigo_factory=lambda h, p: testigo,
                        ping=lambda h, p: {"ok": True, "detalle": "ida y vuelta en 3 ms"}, poll_s=0.01,
                        workspace=_workspace(tmp_path))
    return app, correr, testigo


def test_son_tres_clips_fijos_y_dice_cuales_estan_en_este_equipo(tmp_path):
    correr = CorrerClip(_app(tmp_path), tmp_path / "salida", workspace=_workspace(tmp_path))
    clips = correr.clips()
    assert [c["id"] for c in clips] == [c["id"] for c in CLIPS] == ["a_p1_c04", "a_p2_c03", "a_p3_c01"]
    assert [c["disponible"] for c in clips] == [True, True, False]
    assert clips[0]["referencia"] == [{"condicion": "CR-01", "desde_ms": 3133, "hasta_ms": 27652}]
    assert correr.cadencia() == {"uno_de_cada": 6, "cuadros_por_segundo": 5.0}


def test_el_clip_entra_como_video_a_cinco_cuadros_por_segundo_con_lo_demas_de_la_demo(tmp_path):
    correr = CorrerClip(_app(tmp_path), tmp_path / "salida")
    configs = {"media": {"ingest": {"plugin": "oak_d"}, "prompts": {"set_inline": {"id": "x"}},
                         "bus": {"wait_for_subscriber_ms": 10000}, "run": {"name": "demo_defensa", "save_previews": True}}}
    desp = Despliegue("compose", Path("/ws"), "tcp://mp:5557", "tcp://control-plane:5558", "mosquitto", 1883, "")
    media = correr.armar_media(configs, "a_p1_c04", desp)
    assert media["ingest"] == {"plugin": "video_file", "config": {
        "path": "/e-ovrt_datasets/datasets/raw/clip_bench/clips/a_p1_c04.mp4", "source_id": "a_p1_c04"}}
    assert media["run"] == {"name": "demostracion_a_p1_c04", "save_previews": False, "stride": STRIDE} and STRIDE == 6
    assert media["prompts"] == configs["media"]["prompts"] and media["bus"] == configs["media"]["bus"]
    nativo = Despliegue("nativo", Path("C:/ws"), "", "", "127.0.0.1", 1883, "")
    assert correr.armar_media(configs, "a_p1_c04", nativo)["ingest"]["config"]["path"].endswith(
        "e-ovrt_datasets/datasets/raw/clip_bench/clips/a_p1_c04.mp4")


def test_las_alertas_van_al_lado_de_la_referencia_con_su_demora_y_su_mensaje():
    alertas = [{"alert_id": "a1", "condition_id": "CR-01", "timestamp_ms": 7300.0, "first_evidence_frame_index": 99},
               {"alert_id": "a2", "condition_id": "CR-02", "timestamp_ms": 9000.0}]
    evaluacion = {"expected_alerts_count": 1, "observed_alerts_count": 2, "matched_alerts_count": 1,
                  "missed_alerts_count": 0, "unexpected_alerts_count": 1,
                  "effective_matching_windows": {"CR-01": {"t_alert_max_ms": 10000.0}}}
    mensajes = [{"topic": "eovrt/alerts/high", "recibido_en": "2026-11-15T12:00:00+00:00", "recibido_ms": 1000.0,
                 "payload": {"alert_id": "a1", "confirmed_wall_ms": 986.5}}]
    r = armar_resultado(REF, alertas, evaluacion, mensajes)
    primera, segunda = r["alertas"]
    assert primera["episodio"] == {"condicion": "CR-01", "desde_ms": 3133, "hasta_ms": 27652}
    assert (primera["demora_ms"], primera["primera_evidencia_ms"], primera["broker"]["demora_ms"]) == (4167.0, 3300.0, 13.5)
    assert segunda["episodio"] is None and segunda["broker"] is None
    assert r["sin_alerta"] == []
    assert r["evaluacion"] == {"expected": 1, "observed": 2, "matched": 1, "missed": 0, "unexpected": 1}
    # Sin la lista `unexpected_alerts` en la evaluación, lo que no se empareja es de más.
    assert (primera["tipo"], segunda["tipo"]) == ("acierto", "de_mas")
    sin = armar_resultado(REF, [], None, [])
    assert sin["sin_alerta"] == [{"condicion": "CR-01", "desde_ms": 3133, "hasta_ms": 27652}] and sin["evaluacion"] is None


def test_la_tabla_empareja_con_la_ventana_del_evaluador_y_no_marca_de_mas_una_re_alerta():
    """Revisión del 2026-11-19: antes se emparejaba en [inicio, fin + t_alert_max] y la tabla contradecía al
    conteo oficial; ahora es [inicio + persistencia, inicio + t_alert_max], como el evaluador, y lo «de más»
    sale de su `unexpected_alerts`."""
    ventana = {"CR-01": {"persistencia_min_ms": 4000.0, "t_alert_max_ms": 10000.0}}
    # Muy temprano (antes de la persistencia), en ventana, tardía y una segunda sobre el mismo episodio.
    alertas = [{"alert_id": "temprana", "condition_id": "CR-01", "timestamp_ms": 4000.0},
               {"alert_id": "buena", "condition_id": "CR-01", "timestamp_ms": 8000.0},
               {"alert_id": "re", "condition_id": "CR-01", "timestamp_ms": 12000.0},
               {"alert_id": "tarde", "condition_id": "CR-01", "timestamp_ms": 15000.0}]
    evaluacion = {"effective_matching_windows": ventana,
                  "unexpected_alerts": [{"alert_id": "temprana"}, {"alert_id": "tarde"}]}
    r = armar_resultado(REF, alertas, evaluacion, [])
    tipos = {a["alert_id"]: (a["tipo"], a["episodio"] is not None) for a in r["alertas"]}
    assert tipos == {"temprana": ("de_mas", False), "buena": ("acierto", True),
                     "re": ("no_penalizada", False), "tarde": ("de_mas", False)}


def test_en_nativo_o_sin_el_perfil_operativo_no_corre(tmp_path, monkeypatch):
    _, correr, _ = _correr(tmp_path, monkeypatch, compose=False)
    with pytest.raises(ClipNoListo) as exc:
        asyncio.run(correr.correr("a_p1_c04"))
    assert exc.value.preparacion["items"][0]["id"] == "orquestacion"
    _, correr, _ = _correr(tmp_path / "otro", monkeypatch, activa="mp-yoloe-26s")
    prep = asyncio.run(correr.preparacion())
    assert prep["listo"] is False and "mp-yoloe-26s" in prep["items"][0]["detalle"]


def test_con_algo_en_curso_no_corre(tmp_path, monkeypatch):
    _, correr, _ = _correr(tmp_path, monkeypatch, en_curso={"experiment_id": "exp_otro"})
    prep = asyncio.run(correr.preparacion())
    assert prep["items"][-1] == {"id": "libre", "nombre": "Nada en curso", "ok": False,
                                 "detalle": "hay una corrida en curso en la consola"}


def test_corre_por_el_administrador_de_experimentos_y_arma_el_resultado(tmp_path, monkeypatch):
    app, correr, testigo = _correr(tmp_path, monkeypatch)
    consolidado = tmp_path / "repo" / "runs" / "exp_x"
    (consolidado / "control").mkdir(parents=True)
    (consolidado / "control" / "alerts.jsonl").write_text(json.dumps(
        {"alert_id": "a1", "condition_id": "CR-01", "timestamp_ms": 7300.0}) + "\n", encoding="utf-8")
    (consolidado / "control" / "temporal_evaluation.json").write_text(json.dumps(
        {"expected_alerts_count": 1, "observed_alerts_count": 1, "matched_alerts_count": 1,
         "missed_alerts_count": 0, "unexpected_alerts_count": 0}), encoding="utf-8")

    async def escenario():
        r = await correr.correr("a_p1_c04")
        manifest, kw = app.state.experiment_manager.iniciados[0]
        assert manifest.slug == "demostracion_clip" and manifest.clip_id == "a_p1_c04"
        assert manifest.changes == "demostración: no es evidencia"
        assert [manifest.runs[p].mode for p in ("media", "control", "distribution")] == ["run", "live", "live"]
        assert Path(manifest.ground_truth).as_posix().endswith("gt/a_p1_c04.json") and kw["timeout_s"] == dm.TIMEOUT_S
        media = json.loads(json.dumps(__import__("yaml").safe_load(Path(manifest.runs["media"].config).read_text(encoding="utf-8"))))
        assert media["ingest"]["plugin"] == "video_file" and media["run"]["stride"] == 6
        await asyncio.sleep(0.05)
        assert correr.actual()["pasos"]["deteccion"] == {"estado": "en_curso", "cuadros": 40}
        assert correr.actual()["cuadros_esperados"] == 154  # 30,667 s × 30 cuadros/s ÷ 6
        testigo.lista.append({"topic": "eovrt/alerts/high", "recibido_ms": 2000.0, "recibido_en": "x",
                              "payload": {"alert_id": "a1", "confirmed_wall_ms": 1990.0}})
        app.state.experiment_manager.estados[manifest.experiment_id] = {
            "status": "succeeded", "consolidated_dir": str(consolidado)}
        for _ in range(100):
            if correr.actual()["fase"] != "corriendo":
                break
            await asyncio.sleep(0.01)
        return r

    r = asyncio.run(escenario())
    fin = correr.actual()
    assert fin["fase"] == "terminada" and fin["demostracion"] is True and testigo.cerrado
    assert fin["pasos"]["broker"] == {"estado": "ok", "mensajes": 1}
    assert fin["resultado"]["alertas"][0]["demora_ms"] == 4167.0
    assert fin["resultado"]["alertas"][0]["broker"]["demora_ms"] == 10.0
    assert fin["resultado"]["consolidado"] == "runs/exp_x"
    guardada = correr.corrida(r["id"])
    assert guardada["resultado"] == fin["resultado"]
    assert (tmp_path / "salida" / r["id"] / "testigo.jsonl").is_file()
    assert correr.corrida("../otra") is None
