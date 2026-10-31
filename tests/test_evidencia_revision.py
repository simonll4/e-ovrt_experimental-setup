"""La revisión ciega de ERR-01 asistida por Claude (doc 134 §13.12)."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from tools.evidencia import revision_ciega as rc
from tools.evidencia.__main__ import main as cli
from tools.evidencia.familias import errores, figuras


def _carpeta(tmp_path: Path) -> Path:
    """Lo que deja VIS-01: el CSV ciego y los cuadros; además, lo que la revisión NO puede ver."""
    carpeta = tmp_path / "defensa" / "figuras" / "VIS-01"
    (carpeta / "revision_ciega").mkdir(parents=True)
    with (carpeta / rc.CSV_CIEGO).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=figuras.CSV_COLUMNAS)
        w.writeheader()
        for n, cond in ((1, "CR-01"), (2, "CR-02"), (3, "CR-01")):
            w.writerow({"n": n, "imagen": f"revision_ciega/{n:03d}.png", "condicion": cond,
                        "es_persona": "", "epp_visible": "", "nota": ""})
            (carpeta / "revision_ciega" / f"{n:03d}.png").write_bytes(b"png")
    (carpeta / "revision_ciega" / "001_recorte.png").write_bytes(b"png")
    (carpeta / "muestra.json").write_text(json.dumps([{"n": 1, "causa": "P-intermitente", "clip": "v06_c01"}]))
    return carpeta


def _propuestas(carpeta: Path) -> None:
    (carpeta / rc.PROPUESTAS).write_text(json.dumps({"propuestas": [
        {"n": 1, "es_persona": "sí", "epp_visible": "si", "razon": "casco blanco visible"},
        {"n": 2, "es_persona": "no", "epp_visible": "", "razon": "es un poste"},
        {"n": 3, "es_persona": "si", "epp_visible": "no se puede", "razon": "de espaldas y lejos"},
    ]}, ensure_ascii=False), encoding="utf-8")


def _datos_de(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="datos">(.*?)</script>', html, re.DOTALL).group(1))


def _bajado(carpeta: Path, filas: list[tuple]) -> Path:
    """El CSV tal como lo descarga la página."""
    ruta = carpeta / rc.COMPLETO
    cols = ["n", "imagen", "condicion", "es_persona", "epp_visible", "nota",
            "propuesta_ia_es_persona", "propuesta_ia_epp_visible", "revisado_por_persona"]
    with ruta.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for n, es, epp, conf in filas:
            w.writerow([n, f"revision_ciega/{n:03d}.png", "", es, epp, "", "", "", conf])
    return ruta


def test_la_pagina_lleva_solo_lo_que_esta_en_los_cuadros_ciegos(tmp_path):
    carpeta = _carpeta(tmp_path)
    _propuestas(carpeta)
    ruta, cuadros, propuestas = rc.pagina(carpeta)
    html = ruta.read_text(encoding="utf-8")
    assert (cuadros, propuestas) == (3, 3)
    datos = _datos_de(html)
    assert {k for c in datos["cuadros"] for k in c} == {"n", "imagen", "condicion", "recorte", "propuesta"}
    assert datos["cuadros"][0]["recorte"] == "revision_ciega/001_recorte.png"
    assert datos["cuadros"][1]["recorte"] is None
    assert datos["cuadros"][2]["propuesta"] == {"es_persona": "si", "epp_visible": "no_se_puede",
                                                "razon": "de espaldas y lejos"}
    assert "P-intermitente" not in html and "v06_c01" not in html


def test_sin_propuestas_la_pagina_sirve_para_una_revision_solo_humana(tmp_path):
    carpeta = _carpeta(tmp_path)
    _, cuadros, propuestas = rc.pagina(carpeta)
    assert (cuadros, propuestas) == (3, 0)


def test_una_propuesta_invalida_no_arma_la_pagina(tmp_path):
    carpeta = _carpeta(tmp_path)
    (carpeta / rc.PROPUESTAS).write_text(json.dumps({"propuestas": [{"n": 1, "es_persona": "quizas"}]}))
    with pytest.raises(rc.RevisionInvalida, match="es_persona"):
        rc.pagina(carpeta)
    (carpeta / rc.PROPUESTAS).write_text(json.dumps({"propuestas": [{"n": 9, "es_persona": "no"}]}))
    with pytest.raises(rc.RevisionInvalida, match="cuadro 9"):
        rc.pagina(carpeta)


def test_cerrar_guarda_la_propuesta_al_lado_y_cuenta_los_cambios(tmp_path):
    carpeta = _carpeta(tmp_path)
    _propuestas(carpeta)
    completo = _bajado(carpeta, [(1, "si", "si", "si"), (2, "si", "no", "si"), (3, "si", "no_se_puede", "si")])
    destino = tmp_path / "ERR-01" / "revision_humana.csv"
    informe = rc.cerrar(carpeta, completo, destino)
    assert (informe["cuadros"], informe["con_propuesta_ia"], informe["cambios_de_la_persona"]) == (3, 3, 1)
    filas = list(csv.DictReader(destino.open(encoding="utf-8")))
    assert [f["revisado_por_persona"] for f in filas] == ["si"] * 3
    assert (filas[1]["es_persona"], filas[1]["propuesta_ia_es_persona"]) == ("si", "no")
    assert filas[0]["razon_ia"] == "casco blanco visible"
    assert filas[0]["condicion"] == "CR-01"
    # ERR-01 lee ese archivo e informa la asistencia
    muestra = [{"n": 1, "causa": "P-intermitente"}, {"n": 2, "causa": "F-sin-persona"}, {"n": 3, "causa": "U"}]
    c = errores.concordancia(muestra, destino)
    assert (c["estado"], c["asistida_por_ia"], c["con_propuesta_ia"], c["cambios_de_la_persona"]) == (
        "completa", True, 3, 1)


def test_cerrar_rechaza_lo_que_no_confirmo_la_persona_o_le_faltan_cuadros(tmp_path):
    carpeta = _carpeta(tmp_path)
    destino = tmp_path / "revision_humana.csv"
    sin_confirmar = _bajado(carpeta, [(1, "si", "si", "si"), (2, "no", "", "no"), (3, "si", "no", "si")])
    with pytest.raises(rc.RevisionInvalida, match="cuadro 2 no está confirmado"):
        rc.cerrar(carpeta, sin_confirmar, destino)
    incompleto = _bajado(carpeta, [(1, "si", "si", "si"), (3, "si", "no", "si")])
    with pytest.raises(rc.RevisionInvalida, match=r"faltan \[2\]"):
        rc.cerrar(carpeta, incompleto, destino)
    sin_epp = _bajado(carpeta, [(1, "si", "", "si"), (2, "no", "", "si"), (3, "si", "no", "si")])
    with pytest.raises(rc.RevisionInvalida, match="epp_visible"):
        rc.cerrar(carpeta, sin_epp, destino)
    assert not destino.exists()


def test_una_nota_con_saltos_de_linea_no_rompe_el_cierre(tmp_path):
    carpeta = _carpeta(tmp_path)
    completo = carpeta / rc.COMPLETO
    completo.write_text('n,imagen,condicion,es_persona,epp_visible,nota,propuesta_ia_es_persona,'
                        'propuesta_ia_epp_visible,revisado_por_persona\n'
                        '1,a,CR-01,si,si,"casco, blanco\nal fondo",,,si\n2,a,CR-02,no,,,,,si\n'
                        '3,a,CR-01,si,no,,,,si\n', encoding="utf-8")
    informe = rc.cerrar(carpeta, completo, tmp_path / "r.csv")
    assert informe["cuadros"] == 3
    assert errores.leer_revision(tmp_path / "r.csv")[1]["nota"] == "casco, blanco\nal fondo"


def test_la_cli_arma_la_pagina_y_cierra_en_la_carpeta_de_err01(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path))
    monkeypatch.setenv("EOVRT_WORKSPACE", str(tmp_path / "ws"))
    carpeta = _carpeta(tmp_path)
    _propuestas(carpeta)
    assert cli(["revision-ciega", "pagina"]) == 0
    assert (carpeta / rc.PAGINA).is_file()
    _bajado(carpeta, [(1, "si", "si", "si"), (2, "no", "", "si"), (3, "si", "no_se_puede", "si")])
    assert cli(["revision-ciega", "cerrar"]) == 0
    assert (tmp_path / "results" / "gen2" / "ERR-01" / "revision_humana.csv").is_file()
    assert "0 cambiados por la persona" in capsys.readouterr().out


def test_la_plantilla_tiene_un_solo_lugar_para_los_datos():
    assert rc.PLANTILLA.read_text(encoding="utf-8").count("__DATOS__") == 1
