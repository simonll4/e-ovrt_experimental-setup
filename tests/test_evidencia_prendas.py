"""RT-09 y el propósito de la toma (doc 134 §13.18, 2026-11-04).

- `rodaje.ps1 -Proposito prendas|ensayo` deja la toma fuera de RT-04…RT-08, con su motivo.
- RT-09 importa SOLO las tomas de prendas, mide el `vest` en el torso con la regla de CR-02 del
  pattern set desplegado (fracción y rachas continuas), agrupa por modo × escena × remera y propone
  la remera de RT-04 con la regla del pre-registro.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from tools.evidencia import catalogo as cat
from tools.evidencia.entorno import REPO, Entorno
from tools.evidencia.familias import Contexto, rodaje
from tools.evidencia.registro import Carpeta

PATRONES_REALES = REPO.parent / "e-ovrt_control-plane" / "configs" / "patterns"
T0 = 1_000_000  # reloj de pared del contenedor de la primera unidad (ms)
PERSONA = {"label": "person", "confidence": 0.9, "bbox_xyxy": [100, 100, 300, 500]}
VEST_TORSO = {"label": "vest", "confidence": 0.6, "bbox_xyxy": [150, 220, 250, 360]}  # centro en la banda
VEST_PISO = {"label": "vest", "confidence": 0.6, "bbox_xyxy": [500, 450, 560, 500]}   # fuera de la persona


def _entorno(tmp_path: Path) -> Entorno:
    ent = Entorno(ws=tmp_path / "ws", repo=REPO, modo="docker", consola_url="http://consola",
                  datasets_medios="/e-ovrt_datasets")
    for d in (ent.media_runs, ent.control_runs, ent.patrones):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy(PATRONES_REALES / "cr01_cr02_v2.yaml", ent.patrones)
    return ent


def _sesion(ent: Entorno, sesiones: Path, sid: str, escena: str, *, acciones: list[dict], cuadros,
            proposito="prendas", remera="negra lisa", chaleco="julio", modo=None, alertas=()):
    """Una toma de la demo a 5 fps: `cuadros(i)` da las detecciones de la unidad i."""
    media_id, control_id = f"run_{sid}", f"ctl_{sid}"
    d = sesiones / sid
    (d / "config").mkdir(parents=True)
    (d / "config" / "media.yaml").write_text("ingest: {plugin: oak_d}\n")
    (d / "session.json").write_text(json.dumps({
        "session_id": sid, "escena": escena, "fase": "done", "experiment_id": f"exp_{sid}",
        "ids": {"media_run_id": media_id, "control_run_id": control_id},
        "fin_pedido_en": "2026-11-07T10:00:00+00:00", "terminada_en": "2026-11-07T10:00:09+00:00",
        "exploracion": None, "camara": None,
        **({"modo_prompts": {"id": modo, "evidencia": "exploratoria"}} if modo else {})}))
    (d / "witness.jsonl").write_text("")
    marcas = {"desfase_contenedor_menos_host_ms": 0.0, "chaleco": chaleco, "remera": remera,
              "proposito": proposito, "modo": modo, "acciones": acciones}
    (d / "marcas.json").write_text("﻿" + json.dumps(marcas))  # con BOM, como PowerShell
    mr = ent.media_runs / media_id
    mr.mkdir(parents=True)
    n = 175  # 35 s a 5 fps
    (mr / "metrics.jsonl").write_text("".join(json.dumps({
        "unit_id": f"u{i}", "capture_wallclock_ms": T0 + 200 * i, "capture_monotonic_ns": i * 200_000_000,
        "capture_to_host_ms": 70.0, "g2a_ms": 150.0}) + "\n" for i in range(n)))
    (mr / "detections.jsonl").write_text("".join(json.dumps({
        "unit_id": f"u{i}", "source": {"timestamp_ms": T0 + 200 * i}, "detections": cuadros(i)}) + "\n"
        for i in range(n)))
    (mr / "summary.json").write_text(json.dumps({"units_processed": n, "fps_effective": 5.0}))
    cr = ent.control_runs / control_id
    cr.mkdir(parents=True)
    (cr / "alerts.jsonl").write_text("".join(json.dumps(a) + "\n" for a in alertas))
    (cr / "pattern_events.jsonl").write_text("")
    (cr / "summary.json").write_text(json.dumps({"bus_dropped_events": 0}))


P2 = [{"accion": "entrar", "condicion": None, "pared_ms": T0 + 2000},
      {"accion": "sacar_chaleco", "condicion": "CR-02", "pared_ms": T0 + 7000},
      {"accion": "poner_chaleco", "condicion": "CR-02", "pared_ms": T0 + 29000}]
P1 = [{"accion": "entrar", "condicion": None, "pared_ms": T0 + 2000},
      {"accion": "sacar_casco", "condicion": "CR-01", "pared_ms": T0 + 7000},
      {"accion": "poner_casco", "condicion": "CR-01", "pared_ms": T0 + 21000}]
CR02 = {"alert_id": "a2", "condition_id": "CR-02", "subject_key": "CR-02:oak", "unit_id": "u100"}


# El mecanismo de la familia con más de un modo y de una escena (como se diseñó la parte B, la
# distractora, que salió del pre-registro real por su piloto: doc 141 §4). La receta real se prueba aparte.
RECETA_AMPLIA = {
    "escenas_incluidas": ["P1", "P2"],
    "modos": ["campeon", "distractora"],
    "ventanas": {"P2": {"desde": "sacar_chaleco", "margen_s": 5, "hasta": "poner_chaleco", "vest": "ausente"},
                 "P1": {"desde": "entrar", "margen_s": 3, "hasta": None, "vest": "presente"}},
    "grupos_minimos": [
        {"modo": "campeon", "escena": "P2", "remeras_distintas": 2, "incluye": "referencia"},
        {"modo": "campeon", "escena": "P1", "remera": "referencia", "tomas": 1},
        {"modo": "distractora", "escena": "P2", "remera": "referencia", "tomas": 2},
        {"modo": "distractora", "escena": "P1", "remera": "referencia", "tomas": 2},
    ],
}


def _rt09(tmp_path: Path, sesiones: Path, **receta) -> cat.Prueba:
    datos = yaml.safe_load((REPO / "experiments/evidencia/RT-09/prueba.yaml").read_text(encoding="utf-8"))
    shutil.copy(REPO / "experiments/evidencia/RT-04/escenas.json", tmp_path / "escenas.json")
    datos["receta"] = {**datos["receta"], **receta, "escenas": str(tmp_path / "escenas.json"),
                       "sesiones": str(sesiones)}
    carpeta = tmp_path / "cat" / "RT-09"
    carpeta.mkdir(parents=True)
    (carpeta / "prueba.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return cat.cargar_prueba(carpeta / "prueba.yaml")


def test_perfil_vest_mide_la_fraccion_y_las_rachas_continuas():
    regla = rodaje.regla_cr02(PATRONES_REALES / "cr01_cr02_v2.yaml")
    assert regla["region"]["y_min_ratio"] == 0.25 and regla["evidencia"] == 0.25 and regla["confirma_ms"] == 7000.0
    # 2 s con vest en el torso, 1 s sin, 0,6 s con, y un vest en el piso que no cuenta.
    patron = [True] * 11 + [False] * 5 + [True] * 4
    cuadros = [(T0 + 200 * i, [PERSONA, VEST_TORSO] if hay else [PERSONA, VEST_PISO]) for i, hay in enumerate(patron)]
    cuadros.append((T0 + 200 * 20, [VEST_TORSO]))  # sin persona: no hay a quién aplicar la regla
    p = rodaje.perfil_vest(cuadros, regla)
    assert p["cuadros_con_persona"] == 20 and p["cuadros_con_vest"] == 15
    assert p["fraccion_con_vest"] == 0.75
    assert p["racha_max_con_vest_s"] == 2.0 and p["racha_max_sin_vest_s"] == 0.8
    assert p["confianza_vest_p50"] == 0.6


def test_rt04_no_cuenta_las_tomas_de_prendas_ni_los_ensayos(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    sesiones = tmp_path / "sesiones"
    con_vest = lambda i: [PERSONA, VEST_TORSO]
    _sesion(ent, sesiones, "demo_a_P1", "P1", acciones=P1, cuadros=con_vest, proposito="toma")
    _sesion(ent, sesiones, "demo_b_P2", "P2", acciones=P2, cuadros=con_vest, proposito="prendas")
    _sesion(ent, sesiones, "demo_c_DEMO", "DEMO", acciones=[], cuadros=con_vest, proposito="ensayo")
    datos = yaml.safe_load((REPO / "experiments/evidencia/RT-04/prueba.yaml").read_text(encoding="utf-8"))
    shutil.copy(REPO / "experiments/evidencia/RT-04/escenas.json", tmp_path / "escenas.json")
    datos["receta"] = {**datos["receta"], "escenas": str(tmp_path / "escenas.json"), "sesiones": str(sesiones)}
    (tmp_path / "cat" / "RT-04").mkdir(parents=True)
    (tmp_path / "cat" / "RT-04" / "prueba.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True))
    prueba = cat.cargar_prueba(tmp_path / "cat" / "RT-04" / "prueba.yaml")
    ctx = Contexto(ent=ent, consola=None, catalogo={"RT-04": prueba}, avisar=lambda *_: None, reagregar=True)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    rodaje.correr(ctx, prueba, carpeta)
    m = carpeta.leer("resultado.json")["metricas"]
    motivos = {x["session_id"]: x["motivo"] for x in m["no_evaluables"]}
    assert "prueba de prendas" in motivos["demo_b_P2"] and "-Proposito prendas" in motivos["demo_b_P2"]
    assert "ensayo del guion" in motivos["demo_c_DEMO"]
    assert m["tomas"] == 1  # solo la toma de verdad
    toma = carpeta.leer("tomas/demo_a_P1/toma.json")
    assert toma["remera"] == "negra lisa"


def test_rt09_importa_solo_prendas_perfila_el_vest_y_propone_la_remera(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    sesiones = tmp_path / "sesiones"

    def p2(con_falso):  # en la ventana sin chaleco (12–29 s), `vest` en el torso según `con_falso(i)`
        return lambda i: [PERSONA, VEST_TORSO] if (i < 60 or i > 145 or con_falso(i)) else [PERSONA]

    # A. Prendas con el campeón: la negra mantiene el falso todo el tiempo y CR-02 no alerta; la gris
    #    no tiene falso y CR-02 alerta como el guion.
    _sesion(ent, sesiones, "demo_a_P2", "P2", acciones=P2, cuadros=p2(lambda i: True), remera="negra lisa")
    _sesion(ent, sesiones, "demo_b_P2", "P2", acciones=P2, cuadros=p2(lambda i: False), remera="gris clara lisa",
            alertas=[CR02])
    # B. Distractora con la negra: el falso queda intermitente (rachas de 0,8 s) y CR-02 alerta.
    _sesion(ent, sesiones, "demo_c_P2_modo-distractora", "P2", acciones=P2, modo="distractora",
            cuadros=p2(lambda i: i % 10 < 4), alertas=[CR02])
    _sesion(ent, sesiones, "demo_d_P1", "P1", acciones=P1, cuadros=lambda i: [PERSONA, VEST_TORSO])
    # Una toma de RT-04 (sin -Proposito prendas) no es de RT-09; una sin remera, no evaluable.
    _sesion(ent, sesiones, "demo_e_P2", "P2", acciones=P2, cuadros=p2(lambda i: True), proposito="toma")
    _sesion(ent, sesiones, "demo_f_P2", "P2", acciones=P2, cuadros=p2(lambda i: True), remera="")

    prueba = _rt09(tmp_path, sesiones, **RECETA_AMPLIA)
    ctx = Contexto(ent=ent, consola=None, catalogo={"RT-09": prueba}, avisar=lambda *_: None)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    salida = rodaje.correr(ctx, prueba, carpeta)

    assert salida["tomas"] == 4
    assert salida["remera_propuesta"]["remera"] == "gris clara lisa" and salida["remera_propuesta"]["cr02_alerto"]
    resultado = carpeta.leer("resultado.json")
    m = resultado["metricas"]
    assert "demo_e_P2" not in json.dumps(carpeta.leer("configuracion.json"))
    assert [x["session_id"] for x in m["no_evaluables"]] == ["demo_f_P2"]
    grupos = {(g["modo"], g["escena"], g["remera"]): g for g in m["grupos"]}
    negra = grupos[("campeon", "P2", "negra lisa")]
    assert negra["cr02_como_el_guion"] == 0 and negra["fraccion_con_vest_p50"] == 1.0
    assert grupos[("campeon", "P2", "gris clara lisa")]["fraccion_con_vest_p50"] == 0.0
    distractora = grupos[("distractora", "P2", "negra lisa")]
    assert distractora["cr02_como_el_guion"] == 1 and distractora["racha_max_con_vest_s"] < 1.0
    assert grupos[("campeon", "P1", "negra lisa")]["fraccion_con_vest_p50"] == 1.0
    # Falta la mitad de B: la prueba queda parcial y lo dice.
    assert resultado["estado"] == "parcial"
    assert any("distractora · negra lisa: 1 de 2" in f for f in m["faltan"])
    assert any(f.startswith("P1 · distractora") for f in m["faltan"])
    assert resultado["veredicto"]["propuesto"] == "otra_combinacion"
    assert any(r["clave"] == "P2/campeon/gris clara lisa/cr02" and r["valor"] == "1/1" for r in resultado["resumen"])


def test_rt09_real_es_solo_la_prueba_de_prendas_con_el_campeon(tmp_path, monkeypatch):
    """El pre-registro real (doc 134 §13.18): P2 con el campeón, dos remeras como mínimo (una, la de
    referencia). Una toma con un modo de prompts queda no evaluable; con las dos remeras, completa."""
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    sesiones = tmp_path / "sesiones"
    sin_falso = lambda i: [PERSONA, VEST_TORSO] if (i < 60 or i > 145) else [PERSONA]
    _sesion(ent, sesiones, "demo_a_P2", "P2", acciones=P2, cuadros=lambda i: [PERSONA, VEST_TORSO])
    _sesion(ent, sesiones, "demo_b_P2_modo-edir", "P2", acciones=P2, cuadros=sin_falso, modo="edir")
    prueba = _rt09(tmp_path, sesiones)
    assert prueba.receta["modos"] == ["campeon"] and list(prueba.receta["ventanas"]) == ["P2"]
    ctx = Contexto(ent=ent, consola=None, catalogo={"RT-09": prueba}, avisar=lambda *_: None)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    assert rodaje.correr(ctx, prueba, carpeta)["estado"] == "parcial"  # una sola remera
    m = carpeta.leer("resultado.json")["metricas"]
    assert [x["session_id"] for x in m["no_evaluables"]] == ["demo_b_P2_modo-edir"]
    _sesion(ent, sesiones, "demo_c_P2", "P2", acciones=P2, cuadros=sin_falso, remera="blanca lisa", alertas=[CR02])
    salida = rodaje.correr(ctx, prueba, carpeta)
    assert salida["estado"] == "completo" and salida["remera_propuesta"]["remera"] == "blanca lisa"
