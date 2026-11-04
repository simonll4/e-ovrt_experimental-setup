"""Pruebas parciales (doc 134 §13.17, 2026-11-04).

- RT-03 corre por tomas en configuraciones pre-registradas; una configuración sin ninguna toma
  válida deja la prueba `parcial` y nombrada en `configs_sin_tomas` (en F7 salió `completo` con
  1080p@30 sin correr).
- `veredicto` se niega con una prueba parcial, salvo `--parcial`, que firma a propósito y deja
  escrito lo que falta. Una relectura por sujeto fallida no se firma nunca: se corrige.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tools.evidencia import catalogo as cat
from tools.evidencia.__main__ import main as cli
from tools.evidencia.entorno import REPO, Entorno
from tools.evidencia.familias import Contexto, vivo
from tools.evidencia.registro import Carpeta


def _entorno(tmp_path: Path) -> Entorno:
    return Entorno(ws=tmp_path / "ws", repo=REPO, modo="docker", consola_url="http://consola",
                   datasets_medios="/e-ovrt_datasets")


def _rt03(tmp_path: Path) -> cat.Prueba:
    carpeta = tmp_path / "cat" / "RT-03"
    carpeta.mkdir(parents=True)
    datos = {
        "schema": "prueba.gen2.v1", "id": "RT-03", "titulo": "latencia", "fase": "F7", "familia": "vivo",
        "gen1": {"result_id": "rodaje", "doc": "operacion/133", "relacion": "otra_combinacion", "motivo": "otra PC"},
        "veredictos_posibles": ["otra_combinacion"],
        "receta": {"instancia": "mp-gdino-tiny-560", "modelo": "grounding-dino/gdino-tiny-560",
                   "configs": {"960x540@5": {"camara": {"fps": 5}, "unidades": 300},
                               "1080p@30": {"camara": {"fps": 30}, "unidades": 250}},
                   "config_demo": "960x540@5"},
    }
    (carpeta / "prueba.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return cat.cargar_prueba(carpeta / "prueba.yaml")


def _toma(carpeta: Carpeta, clave: str, config: str) -> None:
    (carpeta.dir / "tomas" / clave).mkdir(parents=True, exist_ok=True)
    (carpeta.dir / "tomas" / clave / "series.json").write_text(json.dumps(
        {"g2a": [150.0, 160.0, 170.0], "captura_a_host": [60.0, 65.0, 70.0],
         "vidrio_a_resultado": [210.0, 225.0, 240.0]}), encoding="utf-8")
    carpeta.guardar_corrida(clave, {"estado": "ok", "config": config,
                                    "metricas": {"contaminada": False, "fps_efectivos": 3.9}})


def test_rt03_con_una_configuracion_sin_tomas_queda_parcial(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    prueba = _rt03(tmp_path)
    ent = _entorno(tmp_path)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    _toma(carpeta, "lat_960_a", "960x540@5")
    ctx = Contexto(ent=ent, consola=None, catalogo={"RT-03": prueba}, avisar=lambda *_: None, reagregar=True)

    assert vivo.correr(ctx, prueba, carpeta)["estado"] == "parcial"
    resultado = carpeta.leer("resultado.json")
    assert resultado["configs_sin_tomas"] == ["1080p@30"]
    assert resultado["tomas_validas"] == 1
    # Las cifras de la configuración que sí corrió no cambian por el estado.
    assert resultado["metricas"]["960x540@5"]["g2a"]["p95"] == 170.0
    assert resultado["veredicto"]["propuesto"] == "otra_combinacion"

    _toma(carpeta, "lat_1080_a", "1080p@30")
    assert vivo.correr(ctx, prueba, carpeta)["estado"] == "completo"
    assert carpeta.leer("resultado.json")["configs_sin_tomas"] == []


def _resultado_parcial(pid: str, **extra) -> Carpeta:
    """Un `resultado.json` parcial de una prueba REAL del catálogo, en la salida de ensayo."""
    ent = Entorno(ws=REPO.parent, repo=REPO, modo="nativo", consola_url="http://consola",
                  datasets_medios=str(REPO.parent / "e-ovrt_datasets"))
    carpeta = Carpeta(ent, cat.cargar_catalogo(ent.catalogo)[pid])
    carpeta.resultado({"estado": "parcial", "metricas": {},
                       "veredicto": {"propuesto": "otra_combinacion", "confirmado": None}, **extra})
    return carpeta


def test_veredicto_de_una_prueba_parcial_exige_parcial_y_anota_lo_que_falta(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    carpeta = _resultado_parcial("RT-03", configs_sin_tomas=["1080p@30"])
    args = ["veredicto", "RT-03", "otra_combinacion", "--motivo", "1080p@30 retirada: doc 134 §13.17",
            "--quien", "equipo"]

    with pytest.raises(SystemExit, match="parcial"):
        cli(args)
    assert carpeta.leer("resultado.json")["veredicto"]["confirmado"] is None

    assert cli(args + ["--parcial"]) == 0
    resultado = carpeta.leer("resultado.json")
    confirmado = resultado["veredicto"]["confirmado"]
    assert confirmado["valor"] == "otra_combinacion"
    assert confirmado["parcial"] is True
    assert confirmado["faltante"] == {"configs_sin_tomas": ["1080p@30"]}
    assert resultado["estado"] == "parcial"  # la firma cierra la prueba, no la completa


def test_veredicto_anota_las_escenas_y_tomas_que_faltan_por_stream(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    carpeta = _resultado_parcial("RT-06", metricas={
        "escenas_sin_tomas": ["P5"],
        "por_stream": {"secundario": {"faltan_tomas": {"P1": 0, "P5": 2}, "relecturas_fallidas": []},
                       "principal": {"faltan_tomas": {"P5": 1}, "relecturas_fallidas": []}},
    })
    assert cli(["veredicto", "RT-06", "otra_combinacion", "--motivo", "sin segundo actor", "--quien", "equipo",
                "--parcial"]) == 0
    assert carpeta.leer("resultado.json")["veredicto"]["confirmado"]["faltante"] == {
        "escenas_sin_tomas": ["P5"], "faltan_tomas": {"secundario:P5": 2, "principal:P5": 1}}


def test_veredicto_no_firma_una_relectura_fallida_ni_con_parcial(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    carpeta = _resultado_parcial("RT-07", metricas={"relecturas_fallidas": ["demo_x_P1"]})
    with pytest.raises(SystemExit, match="relectura"):
        cli(["veredicto", "RT-07", "otra_combinacion", "--motivo", "m", "--quien", "q", "--parcial"])
    assert carpeta.leer("resultado.json")["veredicto"]["confirmado"] is None
