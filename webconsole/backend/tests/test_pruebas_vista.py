"""El vocabulario de cada prueba en la consola (results/evidence-vista/pruebas.yaml; plan de la consola
de evidencia, §2.4, §3 y §4) y el desglose del detalle de una prueba."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from eovrt_webconsole.gen2 import Gen2

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / "results" / "evidence-vista"
NUMERO = re.compile(r"(?<![\w\-−.,])\d+(?:[.,]\d+)?(?![\w\-−])")
# La jerga que el plan saca de las pantallas principales (§4): la de la campaña y la de la implementación.
# Lo que va entre comillas angulares es una frase literal que se le manda al modelo y se deja tal cual.
JERGA = re.compile(
    r"campe[oó]n|generaci[oó]n|\bgen ?[12]\b|\b(person|helmet|vest|bare_head|machinery|vehicle|worker)\b"
    r"|\b[TGRDHBI][0-9]\b|\bC[0-9]_|bench[ _]v3|media[ _]plane|compose|n_gt|\b[FP]-[a-z]|prompt set:|pattern set:|@",
    re.IGNORECASE,
)


def _vocabulario() -> dict:
    return yaml.safe_load((VISTA / "pruebas.yaml").read_text(encoding="utf-8"))["pruebas"]


def test_cada_prueba_del_catalogo_tiene_su_pregunta_y_que_midio():
    vocabulario = _vocabulario()
    catalogo = {p["id"] for p in Gen2(REPO).pruebas()}
    preguntas = {p["id"] for p in yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))["preguntas"]}
    assert set(vocabulario) == catalogo
    for pid, v in vocabulario.items():
        assert v.get("pregunta") in preguntas, pid
        assert isinstance(v.get("que_midio"), str) and v["que_midio"], pid
        assert not NUMERO.search(v["que_midio"]), f"{pid}: cifra escrita a mano en «{v['que_midio']}»"
        assert not JERGA.search(v["que_midio"]), f"{pid}: jerga en «{v['que_midio']}»"


def test_las_siete_preguntas_tienen_pruebas():
    usadas = {v["pregunta"] for v in _vocabulario().values()}
    preguntas = [p["id"] for p in yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))["preguntas"]]
    assert set(preguntas) == usadas


def test_ningun_nombre_de_cifra_que_muestra_la_consola_usa_jerga():
    g = Gen2(REPO)
    malos = []
    for fila in g.pruebas():
        lecturas = [fila["resumen"]] + [l["resumen"] for l in g.prueba(fila["id"])["lecturas"]]
        for resumen in lecturas:
            for c in resumen:
                sin_frases = re.sub(r"«[^»]*»", "", c["nombre_consola"])
                if JERGA.search(sin_frases):
                    malos.append(f"{fila['id']} {c['clave']}: {c['nombre_consola']}")
    assert malos == []


def test_los_nombres_del_vocabulario_son_de_claves_que_existen():
    # Un nombre para una clave que el resultado no tiene es un error de tipeo que nadie vería.
    g = Gen2(REPO)
    for pid, v in _vocabulario().items():
        claves = {c["clave"] for c in g.prueba(pid)["resumen"]}
        for l in g.prueba(pid)["lecturas"]:
            claves |= {c["clave"] for c in l["resumen"]}
        assert set(v.get("cifras") or {}) <= claves, (pid, set(v.get("cifras") or {}) - claves)


def test_el_desglose_real_de_un_banco_de_clips_y_de_imagenes():
    g = Gen2(REPO)
    clips = g.prueba("ALR-01")["desglose"]
    assert clips["tipo"] == "clips" and len(clips["clips"]) >= 30
    resumen = {c["clave"]: c["valor"] for c in g.prueba("ALR-01")["resumen"]}
    # El desglose suma lo mismo que el resultado: no se calcula, se lee de las mismas evaluaciones.
    assert sum(c["aciertos"] for c in clips["clips"]) == resumen["aciertos"]
    imagenes = g.prueba("IMG-01")["desglose"]
    assert imagenes["tipo"] == "imagenes" and {f["fuente"] for f in imagenes["fuentes"]} >= {"chv", "shel5k"}
    assert g.prueba("RT-04")["desglose"] is None


def _repo(tmp_path: Path) -> Path:
    cat = tmp_path / "experiments" / "evidencia" / "ALR-01"
    cat.mkdir(parents=True)
    (cat / "prueba.yaml").write_text(yaml.safe_dump({"id": "ALR-01", "titulo": "t"}), encoding="utf-8")
    res = tmp_path / "results" / "gen2" / "ALR-01"
    (res / "evals").mkdir(parents=True)
    (res / "resultado.json").write_text(json.dumps({
        "estado": "completo",
        "resumen": [{"clave": "f1", "nombre": "F1 del programa", "valor": 0.8}, {"clave": "x", "nombre": "X", "valor": 1}],
        "variantes": {"sujeto": {"resumen": [{"clave": "f1", "nombre": "F1 del programa", "valor": 0.9}]}},
    }), encoding="utf-8")
    (res / "evals" / "eval_c1.json").write_text(json.dumps({
        "schema_version": "control.eval.temporal.v1", "scenario_id": "c1", "expected_alerts_count": 1,
        "matched_alerts_count": 1, "missed_alerts_count": 0, "unexpected_alerts_count": 2, "re_alerts_count": 0,
        "avg_latency_ms_from_episode_start": 4000.0, "avg_sdr": 0.5}), encoding="utf-8")
    vista = tmp_path / "results" / "evidence-vista"
    vista.mkdir(parents=True)
    (vista / "pruebas.yaml").write_text(yaml.safe_dump({"pruebas": {"ALR-01": {
        "pregunta": "que-agrega", "que_midio": "Qué mide.", "cifras": {"f1": "F1 por episodio"}}}},
        allow_unicode=True), encoding="utf-8")
    return tmp_path


def test_la_fila_y_el_detalle_llevan_el_vocabulario_de_la_consola(tmp_path):
    g = Gen2(_repo(tmp_path))
    fila = g.pruebas()[0]
    assert (fila["pregunta_consola"], fila["que_midio"]) == ("que-agrega", "Qué mide.")
    assert [c["nombre_consola"] for c in fila["resumen"]] == ["F1 por episodio", "X"]
    # El nombre del programa no se pierde: queda al lado.
    assert fila["resumen"][0]["nombre"] == "F1 del programa"
    detalle = g.prueba("ALR-01")
    assert detalle["lecturas"][0]["resumen"][0]["nombre_consola"] == "F1 por episodio"
    assert detalle["desglose"] == {"tipo": "clips", "clips": [{
        "clip": "c1", "episodios": 1, "aciertos": 1, "perdidos": 0, "falsas_alarmas": 2, "re_alertas": 0,
        "t_alert_ms": 4000.0, "sdr": 0.5}]}


def test_sin_vocabulario_se_muestra_el_nombre_del_programa(tmp_path):
    repo = _repo(tmp_path)
    (repo / "results" / "evidence-vista" / "pruebas.yaml").unlink()
    fila = Gen2(repo).pruebas()[0]
    assert fila["que_midio"] is None and fila["resumen"][0]["nombre_consola"] == "F1 del programa"
