"""Las diez figuras del informe (plan de la consola de evidencia, §8).

Los primeros tests revisan el archivo real: diez figuras numeradas, cada una en preguntas que existen,
las cifras de los gráficos resueltas contra results/gen2, y las dos carpetas respetadas —a la pública
(`results/gen2/<prueba>/capturas/`) solo van gráficos y pantallas sin imágenes; lo que se copia de un
archivo (cuadros con personas o de terceros) va a la privada—. El resto fija cómo se arma la vista y
cómo se sirve una imagen.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eovrt_webconsole.figuras import CARPETA_PRIVADA, Figuras
from eovrt_webconsole.gen2 import Gen2
from eovrt_webconsole.routers import figuras as router_figuras

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / "results" / "evidence-vista"
NUMERO = re.compile(r"(?<![\w\-−.,§])\d+(?:[.,]\d+)?(?![\w\-−])")
# Los cuadros que se copian a la carpeta privada: `defensa/figuras/<prueba>/…`, fuera de git (.gitignore). Los
# de VIS-01 los graba esa prueba; los de RT-09 y EXT-01, `webconsole/tools/armar_figuras_privadas.py`. Solo existen
# en el equipo que tiene las sesiones y las corridas. `defensa/figuras/` sola no alcanza para saberlo: el compose
# la monta en la consola y Docker la crea vacía donde no estaba; lo que se mira es la carpeta de cada prueba.
CUADROS_PRIVADOS = "defensa/figuras"
CUADRO_PRIVADO = re.compile(r"^defensa/figuras/(?P<prueba>[A-Z]+-\d+)/[\w./-]+\.png$")
# Las pantallas que se pueden publicar: solo texto, sin cuadros de video ni fotos.
PANTALLAS_DE_TEXTO = {"[data-figura='momento-mensaje']", "[data-figura='plataforma-servicios']"}


def _declaradas() -> list[dict]:
    return yaml.safe_load((VISTA / "figuras.yaml").read_text(encoding="utf-8"))["figuras"]


def _real() -> dict:
    return Figuras(REPO, Gen2(REPO)).vista()


def test_son_diez_numeradas_en_orden_y_en_preguntas_que_existen():
    figuras = _declaradas()
    assert [f["numero"] for f in figuras] == list(range(1, 11))
    assert len({f["id"] for f in figuras}) == 10
    preguntas = {p["id"] for p in yaml.safe_load((VISTA / "preguntas.yaml").read_text(encoding="utf-8"))["preguntas"]}
    for f in figuras:
        assert f["preguntas"] and set(f["preguntas"]) <= preguntas, f["id"]
        assert set(f) <= {"id", "numero", "titulo", "preguntas", "seccion", "prueba", "pie", "privada",
                          "solo_informe", "fuente", "pendiente"}, f["id"]


def test_las_cifras_de_los_graficos_resuelven():
    vista = _real()
    assert vista["errores"] == []
    graficos = [f for f in vista["figuras"] if f["grafico"]]
    assert {f["grafico"]["tipo"] for f in graficos} == {"barras", "lineas"}
    curvas = {f["id"] for f in _declaradas() if (f.get("fuente") or {}).get("grafico") == "curvas"}
    for f in graficos:
        g = f["grafico"]
        cifras = [b["cifra"] for b in g["barras"]] if g["tipo"] == "barras" else [v for p in g["puntos"] for v in p["valores"]]
        if f["id"] in curvas:
            # Una serie de curvas puede no tener todas las épocas: lo que hay tiene que ser número, y cada serie,
            # al menos dos puntos.
            assert all(c["ok"] and (c["valor"] is None or isinstance(c["valor"], float)) for c in cifras), f["id"]
            for si in range(len(g["series"])):
                assert sum(p["valores"][si]["valor"] is not None for p in g["puntos"]) >= 2, (f["id"], si)
        else:
            assert cifras and all(c["ok"] and isinstance(c["valor"], (int, float)) for c in cifras), f["id"]
        if g["tipo"] == "lineas":
            assert all(len(p["valores"]) == len(g["series"]) for p in g["puntos"]), f["id"]


def test_ninguna_cifra_escrita_a_mano_en_titulos_ni_pies():
    for f in _declaradas():
        for campo in ("titulo", "pie"):
            texto = str(f.get(campo) or "").replace("CC BY 4.0", "")
            assert not NUMERO.search(texto), (f["id"], campo, texto)


def test_a_la_carpeta_publica_solo_van_graficos_y_pantallas_de_texto():
    for f in _declaradas():
        if f.get("pendiente"):
            continue
        fuente = f["fuente"]
        if "archivo" in fuente:
            assert f["privada"] is True, f["id"]
            # Lo que se copia sale de la carpeta de una prueba: así el test de abajo sabe cuándo puede comprobarlo.
            m = CUADRO_PRIVADO.match(fuente["archivo"])
            assert m and (REPO / "results" / "gen2" / m["prueba"]).is_dir(), f["id"]
        if "recorte_arriba" in fuente:
            assert "archivo" in fuente and isinstance(fuente["recorte_arriba"], int) and fuente["recorte_arriba"] > 0, f["id"]
        if not f["privada"]:
            assert "grafico" in fuente or fuente.get("selector") in PANTALLAS_DE_TEXTO, f["id"]
            if f["prueba"] is None:
                # Solo las curvas del ajuste fino no tienen prueba de la campaña.
                assert fuente.get("grafico") == "curvas", f["id"]
            else:
                assert (REPO / "results" / "gen2" / f["prueba"]).is_dir(), f["id"]
        if f.get("solo_informe"):
            assert f["privada"] is True, f["id"]


def test_los_cuadros_privados_que_se_copian_existen_donde_esta_su_prueba():
    comprobadas = 0
    for f in _declaradas():
        if f.get("pendiente") or "archivo" not in f["fuente"]:
            continue
        m = CUADRO_PRIVADO.match(f["fuente"]["archivo"])
        if m and (REPO / CUADROS_PRIVADOS / m["prueba"]).is_dir():
            assert (REPO / f["fuente"]["archivo"]).is_file(), f["id"]
            comprobadas += 1
    if not comprobadas:
        pytest.skip(f"{CUADROS_PRIVADOS}/<prueba>/ no está en este equipo: no va a git")


def test_una_figura_pendiente_dice_por_que_y_no_tiene_fuente():
    pendientes = [f for f in _declaradas() if f.get("pendiente")]
    for f in pendientes:
        assert "fuente" not in f, f["id"]
        assert len(str(f["pendiente"]).split()) >= 8, f["id"]
    for f in _real()["figuras"]:
        if f["pendiente"]:
            assert f["destino"] is None and f["disponible"] is False, f["id"]


# --- La vista y la imagen, sobre un repo armado a mano -------------------------------------------------

def _armar(tmp_path: Path) -> Figuras:
    vista = tmp_path / "results" / "evidence-vista"
    vista.mkdir(parents=True)
    (vista / "figuras.yaml").write_text(yaml.safe_dump({"schema": "consola.figuras.v1", "figuras": [
        {"id": "barras", "numero": 2, "titulo": "B", "preguntas": ["q"], "prueba": "ERR-01", "privada": False,
         "fuente": {"grafico": "barras", "datos": [
             {"etiqueta": "Una", "prueba": "ERR-01", "clave": "a"},
             {"etiqueta": "Aparte", "prueba": "ERR-01", "clave": "b", "aparte": True}]}},
        {"id": "toma", "numero": 1, "titulo": "T", "preguntas": ["q"], "prueba": "RT-04", "privada": True,
         "fuente": {"archivo": "x.png"}},
        {"id": "falta", "numero": 3, "titulo": "F", "preguntas": ["q"], "prueba": "RT-09", "privada": True,
         "pendiente": "Hace falta elegir el cuadro."},
    ]}, allow_unicode=True), encoding="utf-8")
    err = tmp_path / "results" / "gen2" / "ERR-01"
    err.mkdir(parents=True)
    (err / "resultado.json").write_text(json.dumps({"metricas": {"a": 7, "b": 3}}), encoding="utf-8")
    return Figuras(tmp_path, Gen2(tmp_path))


def test_la_vista_ordena_resuelve_y_dice_donde_va_cada_una(tmp_path):
    vista = _armar(tmp_path).vista()
    assert vista["errores"] == []
    toma, barras, falta = vista["figuras"]
    assert toma["destino"] == f"{CARPETA_PRIVADA}/figura-01-toma.png"
    assert barras["destino"] == "results/gen2/ERR-01/capturas/figura-02-barras.png"
    assert [(b["etiqueta"], b["cifra"]["valor"], b["aparte"]) for b in barras["grafico"]["barras"]] == [
        ("Una", 7, False), ("Aparte", 3, True)]
    assert falta["destino"] is None and falta["pendiente"] == "Hace falta elegir el cuadro."
    assert not any(f["disponible"] for f in vista["figuras"])


def test_una_cifra_que_no_resuelve_es_un_error_de_la_vista(tmp_path):
    figuras = _armar(tmp_path)
    (tmp_path / "results" / "gen2" / "ERR-01" / "resultado.json").write_text(json.dumps({"metricas": {"a": 7}}), encoding="utf-8")
    vista = figuras.vista()
    assert len(vista["errores"]) == 1 and "figuras.barras.datos[1]" in vista["errores"][0]


def test_la_imagen_se_sirve_solo_si_existe(tmp_path):
    figuras = _armar(tmp_path)
    app = FastAPI()
    app.state.figuras = figuras
    app.include_router(router_figuras.router)
    with TestClient(app) as client:
        assert client.get("/api/figuras/toma/imagen").status_code == 404
        privada = tmp_path / CARPETA_PRIVADA / "figura-01-toma.png"
        privada.parent.mkdir(parents=True)
        privada.write_bytes(b"\x89PNG\r\n\x1a\n")
        r = client.get("/api/figuras/toma/imagen")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        vista = client.get("/api/figuras").json()
        toma = next(f for f in vista["figuras"] if f["id"] == "toma")
        assert toma["disponible"] is True and toma["url"] == "/api/figuras/toma/imagen"
        assert client.get("/api/figuras/falta/imagen").status_code == 404
        assert client.get("/api/figuras/..%2F..%2Fsecreto/imagen").status_code == 404


def test_las_curvas_salen_de_los_csv_de_su_carpeta_y_van_a_ella(tmp_path):
    vista = tmp_path / "results" / "evidence-vista"
    vista.mkdir(parents=True)
    curvas = tmp_path / "finetuning" / "curvas"
    curvas.mkdir(parents=True)
    # Ultralytics viejo rellena los encabezados con espacios; el nuevo no.
    (curvas / "a.results.csv").write_text("   epoch, metrics/mAP50(B)\n1,0.1\n2,0.2\n3,0.3\n", encoding="utf-8")
    (curvas / "b.results.csv").write_text("epoch,metrics/mAP50(B)\n1,0.5\n2,0.4\n", encoding="utf-8")
    (tmp_path / "afuera.csv").write_text("epoch,metrics/mAP50(B)\n1,0.9\n", encoding="utf-8")
    fuente = {"grafico": "curvas", "columna": "metrics/mAP50(B)", "eje": "mAP50", "eje_x": "época", "series": [
        {"nombre": "A", "csv": "finetuning/curvas/a.results.csv"},
        {"nombre": "B", "csv": "finetuning/curvas/b.results.csv"}]}
    (vista / "figuras.yaml").write_text(yaml.safe_dump({"figuras": [
        {"id": "curvas", "numero": 9, "titulo": "C", "preguntas": ["q"], "prueba": None, "privada": False,
         "fuente": fuente},
        {"id": "afuera", "numero": 10, "titulo": "X", "preguntas": ["q"], "prueba": None, "privada": False,
         "fuente": {**fuente, "series": [{"nombre": "X", "csv": "afuera.csv"}]}},
    ]}, allow_unicode=True), encoding="utf-8")
    v = Figuras(tmp_path, Gen2(tmp_path)).vista()
    c, afuera = v["figuras"]
    g = c["grafico"]
    assert c["destino"] == "finetuning/curvas/figura-09-curvas.png"
    assert (g["tipo"], g["eje"], g["eje_x"], g["series"]) == ("lineas", "mAP50", "época", ["A", "B"])
    assert [p["etiqueta"] for p in g["puntos"]] == ["1", "2", "3"]
    assert [[x["valor"] for x in p["valores"]] for p in g["puntos"]] == [[0.1, 0.5], [0.2, 0.4], [0.3, None]]
    # Un CSV fuera de finetuning/curvas/ no se lee: es un error de la vista.
    assert afuera["grafico"]["puntos"] == []
    assert len(v["errores"]) == 1 and "figuras.afuera.series[0]" in v["errores"][0]
