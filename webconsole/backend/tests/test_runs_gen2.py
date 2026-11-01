"""Corridas: lo que cita una prueba de la generación 2 se agrupa bajo esa prueba."""
from __future__ import annotations

import json

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from tests.test_evidence import archive
from tests.test_runs_clases import _FakeRunsBackend


@pytest.fixture
def gen2_client(settings):
    root = settings.repo_root
    archive(root)  # el archivo congelado de la gen 1, con sus 2 resultados de ejemplo
    gen2 = root / "results" / "gen2" / "ALR-01"
    gen2.mkdir(parents=True)
    (gen2 / "corridas.json").write_text(json.dumps({"corridas": {
        "a_p1_c02": {"experiment_id": "exp_1", "media_run_id": "run_g2_media",
                     "control_run_id": "run_g2_control"},
    }}))
    prueba = root / "experiments" / "evidencia" / "ALR-01"
    prueba.mkdir(parents=True)
    (prueba / "prueba.yaml").write_text(yaml.safe_dump({
        "schema": "prueba.gen2.v1", "id": "ALR-01", "familia": "clips", "fase": "F3",
        "titulo": "Alerta por episodio, escena, campeón (T1)", "informe": ["Tabla 53"],
    }, allow_unicode=True))
    corridas = [
        {"run_id": rid, "name": None, "status": "succeeded", "live": False}
        for rid in ("run_g2_media", "run_g2_otra_media", "run_sin_citar")
    ]
    app = create_app(settings)
    app.state.backend = _FakeRunsBackend(corridas)
    return TestClient(app)


def test_la_corrida_de_la_gen2_ya_no_figura_fuera_del_registro(gen2_client):
    filas = {r["run_id"]: r for r in gen2_client.get("/api/runs?vista=todas&page_size=50").json()}
    citada = filas["run_g2_media"]["evidence"]
    assert citada["is_evidence"] is True
    assert citada["result_ids"] == ["ALR-01"]
    assert citada["clase"] == "resultado"
    # Una que nadie cita sigue sin clasificar: no se inventa.
    assert filas["run_sin_citar"]["evidence"]["is_evidence"] is False
    assert filas["run_sin_citar"]["evidence"]["clase"] == "sin_clasificar"


def test_la_vista_evidencia_incluye_la_gen2(gen2_client):
    ids = {r["run_id"] for r in gen2_client.get("/api/runs?vista=evidencia&page_size=50").json()}
    assert ids == {"run_g2_media"}


def test_el_grupo_lleva_el_titulo_de_la_prueba_y_dice_que_es_de_la_gen2(gen2_client):
    grupos = {g["result_id"]: g for g in gen2_client.get("/api/runs/grupos").json()}
    g = grupos["ALR-01"]
    assert g["titulo"] == "Alerta por episodio, escena, campeón (T1)"
    assert g["generacion"] == 2
    assert g["clase"] == "resultado"
    assert g["n_runs"] == 1
    # El grupo de lo no citado sigue existiendo, declarado como tal.
    assert grupos[None]["n_runs"] == 2
    assert grupos[None]["generacion"] is None


def test_filtrar_por_resultado_devuelve_las_corridas_de_esa_prueba(gen2_client):
    filas = gen2_client.get("/api/runs?result_id=ALR-01&vista=todas").json()
    assert [r["run_id"] for r in filas] == ["run_g2_media"]
