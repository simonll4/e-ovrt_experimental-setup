"""Enmienda del doc 137 (2026-10-29): reumbral, comparador de IMG-04, anatomía de las falsas
alarmas (ERR-01/02), fragmentación de identidad (SEG-01) y cuadros anotados (VIS-01).

Datos sintéticos; la geometría y los umbrales salen del pattern set real.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from test_evidencia_driver import (  # noqa: F401 (banco es un fixture)
    RECETA_INFERENCIA,
    ConsolaFalsa,
    _correr,
    _entorno,
    _prueba,
    banco,
)

from tools.evidencia import catalogo as cat
from tools.evidencia.entorno import REPO
from tools.evidencia.familias import Contexto, clips, errores, figuras, imagenes
from tools.evidencia.registro import Carpeta

PATRONES = REPO.parent / "e-ovrt_control-plane/configs/patterns/cr01_cr02_v2_subject.yaml"


# --- reumbral --------------------------------------------------------------------------


def _evento(frame: int, confs: list[float]) -> dict:
    return {"source": {"frame_index": frame, "timestamp_ms": frame * 33.33},
            "detections": [{"label": "helmet", "confidence": c, "bbox_xyxy": [0, 0, 1, 1]} for c in confs]}


def test_reumbralar_deja_solo_las_que_superan_el_umbral_y_cuenta_los_empates(tmp_path):
    origen = tmp_path / "det.jsonl"
    origen.write_text("".join(json.dumps(_evento(f, [0.30, 0.35, 0.36])) + "\n" for f in range(3)))
    stats = clips.reumbralar(origen, tmp_path / "out" / "detections.jsonl", 0.35)
    assert stats == {"detecciones_antes": 9, "detecciones_despues": 3, "puntaje_igual_al_umbral": 3}
    filas = [json.loads(x) for x in (tmp_path / "out" / "detections.jsonl").read_text().splitlines()]
    assert all([d["confidence"] for d in f["detections"]] == [0.36] for f in filas)


def test_reumbral_relee_por_carpeta_y_la_variante_tambien(banco):  # noqa: F811
    consola = ConsolaFalsa(banco)
    _, c1, _ = _correr(banco, {"receta": RECETA_INFERENCIA}, consola)
    for reg in c1.corridas().values():
        Path(reg["detecciones"]).write_text(json.dumps(_evento(0, [0.31, 0.5])) + "\n")
    receta = {"tipo": "reumbral", "reusa": "ALR-01", "umbral": 0.35, "clips": ["a_p1_c02", "a_p1_c03"],
              "control": {"patrones": "cr01_cr02_v2", "activos": ["CR-01", "CR-02"]},
              "variantes": [{"nombre": "sujeto", "control": {"patrones": "cr01_cr02_v2_subject",
                                                              "activos": ["CR-01", "CR-02"], "track_persons": True}}]}
    ruta = _prueba(banco.ws.parent / "cat10" / "ALR-10", "ALR-10", receta=receta, depende_de=["ALR-01"])
    p10 = cat.cargar_prueba(ruta)
    c10 = Carpeta(banco, p10)
    c10.preparar()
    ctx = Contexto(ent=banco, consola=consola, catalogo={"ALR-01": c1.prueba, "ALR-10": p10}, avisar=lambda *_: None)
    assert clips.correr(ctx, p10, c10)["estado"] == "completo"
    principal, variante = consola.manifiestos[-2:]
    assert Path(principal["runs"]["media"]["reuse_run_dir"]).name == "reumbral_a_p1_c03"
    assert variante["runs"]["media"]["reuse_run_dir"] == principal["runs"]["media"]["reuse_run_dir"]
    dir_ = Path(principal["runs"]["media"]["reuse_run_dir"])
    assert json.loads((dir_ / "summary.json").read_text())["reumbral"]["detecciones_despues"] == 1
    assert c10.corridas()["a_p1_c03"]["reuse_run_dir"] == str(dir_)


def test_comparador_de_imagenes_reumbrala_la_prueba_de_origen(banco, monkeypatch):  # noqa: F811
    origen_id = "run_img01_obra"
    (banco.media_runs / origen_id).mkdir(parents=True)
    (banco.media_runs / origen_id / "detections.jsonl").write_text(json.dumps(_evento(0, [0.31, 0.4])) + "\n")
    ruta = _prueba(banco.ws.parent / "cati" / "IMG-01", "IMG-01", familia="imagenes", fase="F4")
    p1 = cat.cargar_prueba(ruta)
    c1 = Carpeta(banco, p1)
    c1.preparar()
    c1.guardar_corrida("obra_test", {"estado": "ok", "media_run_id": origen_id})
    c1.resultado({"estado": "completo"})
    ruta4 = _prueba(banco.ws.parent / "cati" / "IMG-04", "IMG-04", familia="imagenes", fase="F4", depende_de=["IMG-01"])
    p4 = cat.cargar_prueba(ruta4)
    c4 = Carpeta(banco, p4)
    c4.preparar()
    vistos = []

    def evaluar(ctx, run_dir, coco, person_gt):
        vistos.append([json.loads(x) for x in (Path(run_dir) / "detections.jsonl").read_text().splitlines()])
        return {"per_class": []}

    monkeypatch.setattr(imagenes, "evaluar_estrato", evaluar)
    monkeypatch.setattr(imagenes, "metricas_bench", lambda ctx, evals, clases: {"mAP50": 0.5, "ap50_person": 0.6})
    ctx = Contexto(ent=banco, consola=None, catalogo={"IMG-01": p1, "IMG-04": p4}, avisar=lambda *_: None)
    out = imagenes._comparador(ctx, p4, c4, {"de": "IMG-01", "umbral": 0.35},
                               [{"id": "obra_test", "coco": "c.json", "person_gt": "p.json"}], ["person"],
                               {"mAP50": 0.55, "ap50_person": 0.6})
    assert [d["confidence"] for d in vistos[0][0]["detections"]] == [0.4]
    assert out["delta"]["mAP50"] == 0.05
    assert out["reumbral"]["obra_test"]["detecciones_despues"] == 1


# --- anatomía de las falsas alarmas ------------------------------------------------------


def _caja(i: int) -> list[float]:
    return [i * 200.0, 100.0, i * 200.0 + 100, 300.0]


def _casco(x: float, y: float) -> tuple:
    return ("helmet", [x - 10, y - 10, x + 10, y + 10], 0.6)


def _escenario():
    """Diez cuadros a 10 fps. Personas de la referencia g0…g8; tracks del sistema s0…s9."""
    attrs = {"g0": "true", "g1": "true", "g2": "true", "g3": "true", "g6": "unknown", "g7": "false"}
    referencia = {f: [(g, _caja(int(g[1])), {"has_helmet": v}, False) for g, v in attrs.items()] for f in range(10)}
    cuadros = {}
    for f in range(10):
        personas = {
            # g0 lo siguen dos tracks: s0 hasta el cuadro 4 y s9 después (fragmentación)
            ("s0" if f < 5 else "s9"): (_caja(0), 0.9),
            "s1": (_caja(1), 0.9), "s2": (_caja(2), 0.9), "s3": (_caja(3), 0.9),
            # s4 se superpone con s3: el casco en la región de s3 cae también en la de s4
            "s4": ([640.0, 100.0, 740.0, 300.0], 0.9),
            "s5": (_caja(5), 0.9),  # nadie en la referencia
            "s6": (_caja(6), 0.9), "s7": (_caja(7), 0.9),
        }
        epp = [
            _casco(250, 250),  # sobre s1, pero abajo: fuera de la región upper_body
            _casco(450, 120),  # en la región de s2 y de nadie más
            _casco(660, 120),  # en la región de s3 y de s4
        ]
        cuadros[f] = {"ts": f * 100.0, "ancho": 1920, "alto": 1080, "personas": personas, "epp": epp}
    return referencia, cuadros


def _alerta(track: str, frame: int, caja) -> dict:
    return {"event_type": "alert_event", "alert_id": f"a_{track}", "condition_id": "CR-01",
            "subject_key": f"CR-01:clip:{track}", "frame_index": frame, "timestamp_ms": frame * 100.0,
            "evidence": {"subject": {"bbox_xyxy": caja}}}


def test_anatomia_clasifica_cada_causa_y_cuenta_la_fragmentacion():
    referencia, cuadros = _escenario()
    tracks = {"s0": 4, "s9": 9, "s1": 9, "s2": 9, "s3": 9, "s5": 9, "s6": 9, "s7": 9}
    alertas = [_alerta(t, f, cuadros[f]["personas"][t][0]) for t, f in tracks.items()]
    eventos = [{"event_type": "pattern_state_changed", "state": "candidate", "subject_key": f"CR-01:clip:{t}",
                "frame_index": 5 if t == "s9" else 0} for t in tracks if t != "s7"]  # s7 sin traza
    filas = errores.anatomia_clip(
        clip="clip", gt_json={"recording": {"lighting": "diurna"}}, referencia=referencia, cuadros=cuadros,
        alertas=alertas, eventos=eventos, patrones=errores.patrones_por_condicion(PATRONES), tamano_entrada=560)
    causa = {f["track"]: f["causa"] for f in filas}
    assert causa == {"s0": "P-no-detectado", "s9": "P-no-detectado", "s1": "P-fuera-region",
                     "s2": "P-intermitente", "s3": "P-disputado", "s5": "F-sin-persona", "s6": "U", "s7": "V"}
    ventanas = {f["track"]: (f["cuadro_inicio"], f["ventana"]) for f in filas}
    assert ventanas["s9"] == (5, "traza")
    assert ventanas["s7"][1] == "confirmacion"
    assert all(f["coincide_con_reconstruccion"] for f in filas)
    # letterbox a 560×560: un 1920×1080 entra como 560×315 (escala sobre el lado mayor)
    assert {f["track"]: f["alto_px_entrada"] for f in filas}["s1"] == round(200 * 560 / 1920, 1)
    res = errores.resumir(filas, horas_persona=1.0, horas_clip=0.5, fa_escena=2)
    assert res["fragmentacion"]["alertas_extra"] == 1
    assert res["fragmentacion"]["pares_persona_condicion"] == 6
    assert res["por_causa"]["P-no-detectado"] == 2
    assert res["tasas"]["escena_por_clip_hora"] == 4.0


def test_alertas_no_contadas_por_el_evaluador_quedan_afuera():
    referencia, cuadros = _escenario()
    alertas = [_alerta("s1", 9, cuadros[9]["personas"]["s1"][0]), _alerta("s2", 9, cuadros[9]["personas"]["s2"][0])]
    filas = errores.anatomia_clip(
        clip="clip", gt_json={}, referencia=referencia, cuadros=cuadros, alertas=alertas, eventos=[],
        patrones=errores.patrones_por_condicion(PATRONES), tamano_entrada=560, ids_contados={"a_s2"})
    assert [f["track"] for f in filas] == ["s2"]


def test_una_caja_de_alerta_que_no_es_la_del_track_reconstruido_se_informa():
    referencia, cuadros = _escenario()
    filas = errores.anatomia_clip(
        clip="clip", gt_json={}, referencia=referencia, cuadros=cuadros,
        alertas=[_alerta("s1", 9, [0, 0, 10, 10])], eventos=[],
        patrones=errores.patrones_por_condicion(PATRONES), tamano_entrada=560)
    assert filas[0]["coincide_con_reconstruccion"] is False
    assert errores.resumir(filas, horas_persona=1, horas_clip=1, fa_escena=None)["discrepancias_reconstruccion"] == 1


def test_muestra_estable_por_semilla_y_con_tope_por_causa():
    filas = [{"clip": "c", "alert_id": f"a{i}", "condicion": "CR-01", "track": f"s{i}", "cuadro_alerta": i,
              "caja_sujeto": None, "causa": "P-no-detectado" if i < 8 else "U"} for i in range(10)]
    a, b = errores.muestra(filas, 5, 7), errores.muestra(filas, 5, 7)
    assert a == b
    assert sum(1 for x in a if x["causa"] == "P-no-detectado") == 5
    assert sum(1 for x in a if x["causa"] == "U") == 2
    assert [x["n"] for x in a] == list(range(1, 8))


def test_concordancia_con_la_revision_humana(tmp_path):
    m = [{"n": 1, "causa": "P-no-detectado"}, {"n": 2, "causa": "F-sin-persona"}, {"n": 3, "causa": "U"}]
    ruta = tmp_path / "revision.csv"
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=figuras.CSV_COLUMNAS)
        w.writeheader()
        w.writerow({"n": 1, "imagen": "x", "es_persona": "si", "epp_visible": "si", "nota": ""})
        w.writerow({"n": 2, "imagen": "x", "es_persona": "si", "epp_visible": "no", "nota": ""})
        w.writerow({"n": 3, "imagen": "x", "es_persona": "", "epp_visible": "", "nota": "sin revisar"})
    c = errores.concordancia(m, ruta)
    assert c["estado"] == "parcial"
    assert (c["revisadas"], c["acuerdo"]) == (2, 0.5)
    assert c["f_que_son_persona"] == 1


# --- fragmentación (SEG-01) ------------------------------------------------------------


def test_fragmentacion_cuenta_cambios_de_identidad_y_tracks_por_persona():
    referencia = {f: [("g0", _caja(0), {}, False)] for f in range(10)}
    cuadros = {f: {"personas": {("s1" if f < 5 else "s2"): (_caja(0), 0.9)}} for f in range(10)}
    cuadros[9] = {"personas": {}}  # el último cuadro sin detección: baja la cobertura
    res = errores.fragmentacion_clip(referencia, cuadros, fps=10)
    assert res["cambios_de_identidad"] == 1
    assert res["tracks_por_persona"] == [2]
    assert res["cobertura"] == 0.9
    assert res["cambios_por_persona_minuto"] == round(1 / (10 / 10 / 60), 4)


def test_emparejar_es_uno_a_uno_por_iou_descendente():
    gts = [("g0", [0, 0, 10, 10], {}, False), ("g1", [5, 0, 15, 10], {}, False)]
    sistema = {"s0": ([0, 0, 10, 10], 0.9), "s1": ([6, 0, 16, 10], 0.9)}
    assert errores.emparejar(gts, sistema, 0.5) == {"g0": "s0", "g1": "s1"}


# --- cuadros anotados (VIS-01) ---------------------------------------------------------


def test_dibujar_completa_y_ciega(tmp_path):
    from PIL import Image

    base = tmp_path / "crudo.png"
    Image.new("RGB", (1000, 400), (90, 90, 90)).save(base)
    _referencia, cuadros = _escenario()
    pat = errores.patrones_por_condicion(PATRONES)["CR-01"]
    completa = figuras.dibujar(base, tmp_path / "c.png", cuadro=cuadros[0], sujeto="s1", pat=pat,
                               referencia=_referencia[0], titulo="t")
    ciega = figuras.dibujar(base, tmp_path / "b.png", cuadro=cuadros[0], sujeto="s1", pat=pat, referencia=[],
                            titulo="#1", ciega=True)
    a, b = Image.open(completa), Image.open(ciega)
    assert a.size == b.size == (1000, 400)
    # la ciega no dibuja el casco de s2 (otra persona): ese píxel queda del fondo
    assert b.getpixel((440, 110)) == (90, 90, 90)
    assert a.getpixel((440, 110)) != (90, 90, 90)


def test_recorte_ampliado_sin_suavizar_y_con_las_cajas_a_escala(tmp_path):
    from PIL import Image

    base = tmp_path / "crudo.png"
    Image.new("RGB", (1920, 1080), (90, 90, 90)).save(base)
    _referencia, cuadros = _escenario()
    pat = errores.patrones_por_condicion(PATRONES)["CR-01"]
    rec = figuras.recortar(base, cuadros[0]["personas"]["s1"][0], tmp_path / "r.png", cuadro=cuadros[0],
                           sujeto="s1", pat=pat, referencia=_referencia[0], titulo="t")
    img = Image.open(rec)
    assert img.height == 640  # 200 px de persona + 80 % por lado = 520 px de recorte, ampliado a 640
    assert not list(tmp_path.glob(".*crudo.png"))  # el intermedio no queda


def test_episodios_perdidos_se_derivan_con_las_ventanas_del_evaluador():
    gt = {"fps_nominal": 30, "episodes": [
        {"id": "ep1", "condition_id": "CR-01", "start_ms": 1000, "end_ms": 9000},
        {"id": "ep2", "condition_id": "CR-02", "start_ms": 2000, "end_ms": 20000}]}
    ev = {"missed_alerts": [], "missed_alerts_count": 1,
          "effective_matching_windows": {"CR-01": {"persistencia_min_ms": 4000, "t_alert_max_ms": 10000},
                                         "CR-02": {"persistencia_min_ms": 7000, "t_alert_max_ms": 15000}}}
    alertas = [{"condition_id": "CR-01", "timestamp_ms": 5200}]
    assert figuras.episodios_perdidos(ev, gt, alertas) == [("CR-02", 270, "ep2")]
    assert figuras.episodios_perdidos({"missed_alerts_count": 0}, gt, []) == []


def test_los_cuadros_quedan_fuera_de_git(banco):  # noqa: F811
    ctx = Contexto(ent=banco, consola=None, catalogo={}, avisar=lambda *_: None)
    destino = figuras.carpeta_cuadros(ctx, "VIS-01")
    assert destino.parts[-3:] == ("defensa", "figuras", "VIS-01")
    assert "defensa/figuras/" in (REPO / ".gitignore").read_text()


# --- PLAT-01: la infraestructura declarada y el log del build ------------------------


def test_plat01_registra_la_infra_declarada_y_el_log_del_build(tmp_path):
    from tools.evidencia.familias import integridad

    ws = tmp_path / "ws"
    df = ws / "e-ovrt_media-plane/infra/docker/Dockerfile"
    df.parent.mkdir(parents=True)
    df.write_text("FROM python:3.12\n")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "compose_build.log").write_text(
        "#1 [internal] load build definition from Dockerfile\n"
        "#20 naming to docker.io/eovrt/console:latest done\n"
        "#31 naming to docker.io/eovrt/media-plane:latest done\n")
    ent = _entorno(tmp_path)
    datos = integridad.infra_declarada(ent, logs)
    assert datos["archivos"]["e-ovrt_media-plane/infra/docker/Dockerfile"]
    assert datos["archivos"]["e-ovrt_control-plane/infra/docker/Dockerfile"] is None
    assert datos["build"]["imagenes_nombradas"] == ["docker.io/eovrt/console:latest", "docker.io/eovrt/media-plane:latest"]
    assert integridad.infra_declarada(ent, tmp_path / "sin_logs")["build"] is None
    # el mismo log escrito por Tee-Object de Windows PowerShell 5.1 (UTF-16 con BOM)
    texto = (logs / "compose_build.log").read_text()
    (logs / "compose_build.log").write_bytes(texto.encode("utf-16"))
    assert integridad.infra_declarada(ent, logs)["build"]["imagenes_nombradas"] == datos["build"]["imagenes_nombradas"]
