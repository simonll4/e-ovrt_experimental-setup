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

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eovrt_webconsole.figuras import CARPETA_PRIVADA, Figuras
from eovrt_webconsole.gen2 import Gen2
from eovrt_webconsole.routers import figuras as router_figuras

REPO = Path(__file__).resolve().parents[3]
VISTA = REPO / "results" / "evidence-vista"
NUMERO = re.compile(r"(?<![\w\-−.,§])\d+(?:[.,]\d+)?(?![\w\-−])")
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
    for f in graficos:
        g = f["grafico"]
        cifras = [b["cifra"] for b in g["barras"]] if g["tipo"] == "barras" else [v for p in g["puntos"] for v in p["valores"]]
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
            assert (REPO / fuente["archivo"]).is_file(), f["id"]
        if "recorte_arriba" in fuente:
            assert "archivo" in fuente and isinstance(fuente["recorte_arriba"], int) and fuente["recorte_arriba"] > 0, f["id"]
        if not f["privada"]:
            assert "grafico" in fuente or fuente.get("selector") in PANTALLAS_DE_TEXTO, f["id"]
            assert (REPO / "results" / "gen2" / f["prueba"]).is_dir(), f["id"]
        if f.get("solo_informe"):
            assert f["privada"] is True, f["id"]


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
