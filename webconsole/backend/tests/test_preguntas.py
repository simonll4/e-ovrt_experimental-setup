"""La portada y las siete preguntas (plan de la consola de evidencia, §2 y §9).

Los tres primeros tests son las comprobaciones que pide el plan, sobre el archivo y los resultados
reales del repo: toda referencia resuelve, toda fila de las Tablas 51 a 54 está en alguna pregunta y
ningún texto trae una cifra escrita a mano. El resto fija cómo se resuelve una referencia.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from eovrt_webconsole.gen2 import Gen2
from eovrt_webconsole.preguntas import Preguntas, version_resultados

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / "results" / "evidence-vista"
# Un número suelto: no pegado a una palabra ni a un guion (deja pasar CR-01, G2A o YOLOE-26s).
NUMERO = re.compile(r"(?<![\w\-−.,])\d+(?:[.,]\d+)?(?![\w\-−])")
CAMPOS_DE_TEXTO = ("titulo", "titular", "respuesta")


def _real() -> dict:
    return Preguntas(REPO, Gen2(REPO)).vista()


def test_toda_referencia_del_archivo_real_resuelve():
    vista = _real()
    assert vista["available"] is True
    assert vista["errores"] == []
    assert len(vista["preguntas"]) == 7
    for p in vista["preguntas"]:
        assert p["cifras"], p["id"]
        assert all(c["ok"] for c in p["cifras"].values()), p["id"]
        for t in p["tablas"]:
            for f in t["filas"]:
                assert len(f["celdas"]) == len(t["columnas"]), (p["id"], f["nombre"])
                assert all(i["ok"] for c in f["celdas"] if c for i in c), (p["id"], f["nombre"])


def test_cada_fila_esta_bien_escrita():
    # Una coma sin comillas en un mapeo en línea de YAML parte el nombre en dos claves y la fila se
    # muestra cortada sin que nada falle: se exige que cada fila tenga solo las claves que se leen.
    preguntas = yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))["preguntas"]
    for p in preguntas:
        assert set(p) <= {"id", "titulo", "informe", "titular", "respuesta", "cifras", "tablas", "limites"}, p["id"]
        for t in p.get("tablas") or []:
            assert set(t) <= {"titulo", "informe", "columnas", "filas", "nota"}, (p["id"], t.get("titulo"))
            for f in t["filas"]:
                assert set(f) <= {"nombre", "prueba", "variante", "celdas"}, (p["id"], f)
                assert isinstance(f.get("nombre"), str) and f["nombre"], (p["id"], f)


def test_toda_fila_de_las_tablas_51_a_54_esta_en_alguna_pregunta():
    informe = yaml.safe_load((VISTA / "informe-tablas.yaml").read_text(encoding="utf-8"))["tablas"]
    assert set(informe) == {"Tabla 51", "Tabla 52", "Tabla 53", "Tabla 54"}
    preguntas = yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))["preguntas"]
    mostradas = {(t.get("informe"), f.get("nombre")) for p in preguntas for t in p.get("tablas") or []
                 for f in t.get("filas") or []}
    faltan = [(tabla, fila) for tabla, filas in informe.items() for fila in filas if (tabla, fila) not in mostradas]
    assert faltan == []


def test_ningun_texto_trae_una_cifra_escrita_a_mano():
    datos = yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))
    textos = [("proyecto.que_es", datos["proyecto"]["que_es"])]
    for p in datos["preguntas"]:
        textos += [(f"{p['id']}.{c}", p.get(c) or "") for c in CAMPOS_DE_TEXTO]
        textos += [(f"{p['id']}.limites", l) for l in p.get("limites") or []]
        textos += [(f"{p['id']}.nota", t.get("nota") or "") for t in p.get("tablas") or []]
    for donde, texto in textos:
        sin_marcadores = re.sub(r"\{[a-z0-9_]+\}", "", texto)
        assert not NUMERO.search(sin_marcadores), f"{donde}: «{NUMERO.search(sin_marcadores).group()}» en «{texto}»"
    # Y a lo sumo tres líneas de límites por pregunta (§1.3).
    assert all(len(p.get("limites") or []) <= 3 for p in datos["preguntas"])


def test_el_pie_dice_cuantas_pruebas_y_de_cuando():
    pie = _real()["pie"]
    assert pie["pruebas"] >= 49
    assert pie["desde"] <= pie["hasta"]


# --- cómo se resuelve una referencia (repo sintético) ------------------------------------------

def _repo(tmp_path: Path, preguntas: list[dict]) -> Path:
    for pid, veredicto in (("ALR-01", "identico"), ("ALR-13", "otra_combinacion")):
        cat = tmp_path / "experiments" / "evidencia" / pid
        cat.mkdir(parents=True)
        (cat / "prueba.yaml").write_text(yaml.safe_dump({"id": pid, "titulo": pid}), encoding="utf-8")
        res = tmp_path / "results" / "gen2" / pid
        res.mkdir(parents=True)
        (res / "resultado.json").write_text(json.dumps({
            "estado": "completo", "generado": "2026-10-30T04:10:31+00:00",
            "resumen": [{"clave": "t_alert_s", "nombre": "t", "valor": 5.39, "unidad": "s"}],
            "metricas": {"f1_micro": 0.84, "R2−R1.excluye_0": True, "anidado": {"p95": 12.5}},
            "variantes": {"sujeto": {"resumen": [{"clave": "f1", "valor": 0.9, "unidad": None}]}},
            "veredicto": {"propuesto": veredicto, "confirmado": {"valor": veredicto, "quien": "x"}},
        }), encoding="utf-8")
    (tmp_path / "results" / "gen2" / "ALR-01" / "entorno.json").write_text(
        json.dumps({"host": {"cpu": "Ryzen"}, "gpu": "RTX"}), encoding="utf-8")
    vista = tmp_path / "results" / "evidence-vista"
    vista.mkdir(parents=True)
    (vista / "preguntas.yaml").write_text(yaml.safe_dump({"proyecto": {"nombre": "X"}, "preguntas": preguntas},
                                                         allow_unicode=True), encoding="utf-8")
    return tmp_path


def _vista(tmp_path: Path, cifras: dict, **pregunta) -> dict:
    repo = _repo(tmp_path, [{"id": "p", "titulo": "¿?", "respuesta": "", "cifras": cifras, **pregunta}])
    return Preguntas(repo, Gen2(repo)).vista()


def test_resuelve_resumen_metricas_variante_archivo_y_calculos(tmp_path):
    v = _vista(tmp_path, {
        "resumen": {"prueba": "ALR-01", "clave": "t_alert_s", "decimales": 2},
        "metrica": {"prueba": "ALR-01", "clave": "f1_micro"},
        "anidada": {"prueba": "ALR-01", "clave": "anidado.p95"},
        "variante": {"prueba": "ALR-01", "variante": "sujeto", "clave": "f1"},
        "entorno": {"prueba": "ALR-01", "archivo": "entorno", "clave": "host.cpu"},
        "pruebas": {"calculo": "pruebas"},
        "identicas": {"calculo": "veredicto", "valor": "identico"},
        "conteo": {"calculo": "contar", "de": [{"prueba": "ALR-01", "clave": "R2−R1.excluye_0"},
                                                {"prueba": "ALR-13", "clave": "R2−R1.excluye_0"}]},
    })
    assert v["errores"] == []
    c = v["preguntas"][0]["cifras"]
    assert (c["resumen"]["valor"], c["resumen"]["unidad"], c["resumen"]["decimales"]) == (5.39, "s", 2)
    assert c["metrica"]["valor"] == 0.84 and c["anidada"]["valor"] == 12.5
    assert c["variante"]["valor"] == 0.9
    assert c["entorno"]["valor"] == "Ryzen"
    assert (c["pruebas"]["valor"], c["identicas"]["valor"]) == (2, 1)
    assert (c["conteo"]["valor"], c["conteo"]["total"]) == (2, 2)


def test_una_referencia_que_no_resuelve_lo_dice_sin_romper(tmp_path):
    v = _vista(tmp_path, {
        "clave": {"prueba": "ALR-01", "clave": "no_existe"},
        "prueba": {"prueba": "ZZZ-99", "clave": "f1"},
        "variante": {"prueba": "ALR-01", "variante": "otra", "clave": "f1"},
    }, respuesta="usa {sin_declarar}")
    c = v["preguntas"][0]["cifras"]
    assert not any(x["ok"] for x in c.values())
    assert len(v["errores"]) == 4
    assert any("sin_declarar" in e for e in v["errores"])


def test_las_celdas_heredan_la_prueba_y_la_variante_de_su_fila(tmp_path):
    v = _vista(tmp_path, {"f": {"prueba": "ALR-01", "clave": "f1_micro"}}, tablas=[{
        "titulo": "T", "informe": "Tabla 53", "columnas": ["F1", "Otra prueba"],
        "filas": [{"nombre": "sujeto", "prueba": "ALR-01", "variante": "sujeto",
                   "celdas": ["f1", {"prueba": "ALR-13", "clave": "t_alert_s"}]}],
    }])
    fila = v["preguntas"][0]["tablas"][0]["filas"][0]
    assert v["errores"] == []
    assert fila["celdas"][0][0]["valor"] == 0.9          # la variante de la fila
    assert fila["celdas"][1][0]["valor"] == 5.39         # otra prueba: sin la variante de la fila
    assert fila["pruebas"] == ["ALR-01", "ALR-13"]


def test_sin_archivo_lo_dice(client):
    d = client.get("/api/preguntas").json()
    assert d["available"] is False


def test_el_endpoint_sirve_la_vista(client, repo):
    _repo(repo, [{"id": "p", "titulo": "¿?", "respuesta": "{f}", "cifras": {"f": {"calculo": "pruebas"}}}])
    d = client.get("/api/preguntas").json()
    assert d["available"] is True and d["preguntas"][0]["cifras"]["f"]["valor"] == 2


def test_la_version_sale_de_git_o_de_la_cabeza_del_repo(tmp_path):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n")
    (git / "refs" / "heads" / "main").write_text("9d624fc" + "0" * 33 + "\n")
    v = version_resultados(tmp_path)
    # Con git instalado, el tmp no es un repo y cae a leer .git; sin git, lee .git directo.
    assert v == {"commit": "9d624fc", "fecha": None, "de": "repositorio"}
