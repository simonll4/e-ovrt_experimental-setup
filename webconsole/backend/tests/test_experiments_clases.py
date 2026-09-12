"""Clase por fila del listado de manifiestos + cabeceras de pruebas de plataforma
(Task 8, spec 2026-09-11 tramo consola-evidencia-recorrido-taxonomia).

`manifests_client` no lo trae ningún fixture compartido: se siembra acá con el
mismo patrón que `runs_client` de `test_runs_clases.py` — un registro de
evidencia vacío (CSVs con sólo encabezado, así ninguna corrida "real" es
evidencia) más un `clasificacion.yaml` con la excepción de plataforma, y unas
cuantas ejecuciones consolidadas en `runs/` SIN manifiesto paraguas real: son
justamente la máquina probándose (la suite de tests las escribe), no
experimentos del catálogo.
"""
from __future__ import annotations

import csv
import json

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.evidence import CSV_FILES

FIELDS = ["collection", "result_id", "role", "plane", "run_id", "status", "source_ref", "artifact_path"]

# Los manifiestos que ya siembra `repo` (conftest.py) son single-plane
# (formato viejo, sin `runs:`) y `_iter_umbrella_manifests` los salta — con
# eso `filas` quedaría vacía y `test_manifiestos_traen_su_clase` pasaría al
# vacío, sin probar nada. Este manifiesto paraguas real es lo que hace que la
# lista tenga al menos una fila de verdad.
UMBRELLA = {
    "schema_version": "experiment.manifest.v1",
    "slug": "manifiesto_real",
    "runs": {
        "media": {"service": "media-plane", "config": "configs/media_run.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "configs/control_run.yaml", "mode": "live"},
    },
}
# Manifiestos paraguas con ejecución, uno por clase derivada de ROL (ruling
# R-26): la clase no sale de `is_evidence` sino de los roles de las corridas de
# sus ejecuciones. `manifiesto_evidencia` cita una corrida de rol `media`
# (clase resultado) y `manifiesto_ensayo` una de rol `trial` (clase ensayo) —
# las DOS son evidencia, así que sólo el rol las distingue.
UMBRELLA_CON_EVIDENCIA = {**UMBRELLA, "slug": "manifiesto_evidencia"}
UMBRELLA_ENSAYO = {**UMBRELLA, "slug": "manifiesto_ensayo"}
# Deriva `resultado` por rol, pero `clasificacion.yaml` lo fuerza a instrumento:
# la excepción explícita por slug manda sobre la derivación.
UMBRELLA_FORZADO = {**UMBRELLA, "slug": "manifiesto_forzado"}


def _ejecucion_sin_manifiesto(runs_dir, experiment_id: str, slug: str) -> None:
    d = runs_dir / experiment_id
    d.mkdir(parents=True)
    (d / "manifest.effective.yaml").write_text(
        yaml.safe_dump({"slug": slug, "schema_version": "experiment.manifest.v1"}),
        encoding="utf-8",
    )


def _ejecucion_con_evidencia(runs_dir, experiment_id: str, slug: str, run_id: str) -> None:
    """Como `_ejecucion_sin_manifiesto`, pero además deja un rastro con
    `run_id` en el directorio — lo que `corridas_consolidadas()` necesita
    para que la ejecución cite una corrida que el registro reconozca."""
    _ejecucion_sin_manifiesto(runs_dir, experiment_id, slug)
    (runs_dir / experiment_id / "identidad.json").write_text(
        json.dumps({"media_run_id": run_id}), encoding="utf-8")


@pytest.fixture
def manifests_client(settings):
    root = settings.repo_root
    runs_dir = root / "runs"
    (root / "experiments" / "manifiesto_real.yaml").write_text(
        yaml.safe_dump(UMBRELLA), encoding="utf-8")
    (root / "experiments" / "manifiesto_evidencia.yaml").write_text(
        yaml.safe_dump(UMBRELLA_CON_EVIDENCIA), encoding="utf-8")
    (root / "experiments" / "manifiesto_ensayo.yaml").write_text(
        yaml.safe_dump(UMBRELLA_ENSAYO), encoding="utf-8")
    (root / "experiments" / "manifiesto_forzado.yaml").write_text(
        yaml.safe_dump(UMBRELLA_FORZADO), encoding="utf-8")

    # Los slugs del orquestador: ninguno tiene manifest.yaml en experiments/,
    # sólo el rastro consolidado en runs/ (lo que escribe la suite de tests).
    for i in range(3):
        _ejecucion_sin_manifiesto(runs_dir, f"exp_orq1_{i}", "orq_1")
    for i in range(2):
        _ejecucion_sin_manifiesto(runs_dir, f"exp_orq2a_{i}", "orq_2a")
    # Una ejecución que NO es plataforma (sin excepción declarada): tiene que
    # quedar afuera del conteo de las cabeceras.
    _ejecucion_sin_manifiesto(runs_dir, "exp_ensayo_0", "otro_ensayo")
    # La única ejecución de `manifiesto_evidencia`: cita `evid_run_1`, que el
    # registro sí conoce (fila de abajo en dbe-video.csv).
    _ejecucion_con_evidencia(runs_dir, "exp_evidencia_0", "manifiesto_evidencia", "evid_run_1")
    # `manifiesto_ensayo` TAMBIÉN es evidencia (su corrida está en el registro),
    # pero el rol de esa corrida es `trial` -> clase ensayo. Es el caso que el
    # ternario viejo clasificaba mal.
    _ejecucion_con_evidencia(runs_dir, "exp_ensayo_rol_0", "manifiesto_ensayo", "ensayo_run_1")
    _ejecucion_con_evidencia(runs_dir, "exp_forzado_0", "manifiesto_forzado", "evid_run_1")

    directory = root / "results" / "evidence-runs"
    (directory / "collections").mkdir(parents=True)
    for name in CSV_FILES:
        with (directory / "collections" / name).open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)
            if name == "dbe-video.csv":
                writer.writerow([
                    "dbe_video", "clip_bench/x1", "media", "media-plane", "evid_run_1",
                    "copied", "results/eval.json", "artifacts/media-plane/evid_run_1",
                ])
                writer.writerow([
                    "dbe_video", "clip_bench/x2", "trial", "media-plane", "ensayo_run_1",
                    "copied", "results/eval.json", "artifacts/media-plane/ensayo_run_1",
                ])

    vista = directory.parent / "evidence-vista"
    vista.mkdir(parents=True, exist_ok=True)
    (vista / "clasificacion.yaml").write_text(yaml.safe_dump({
        "roles": {"resultado": ["media"], "ensayo": ["trial"]},
        "excepciones": {"plataforma": ["orq_1", "orq_2a"],
                        "instrumento": ["manifiesto_forzado"]},
    }, allow_unicode=True))

    app = create_app(settings)
    # Sin entrar al lifespan (mismo patrón que `runs_client`): estas rutas no
    # tocan `app.state.backend`.
    return TestClient(app)


def test_manifiestos_traen_su_clase(manifests_client):
    filas = manifests_client.get('/api/experiments/manifests?vista=todas').json()
    assert all('clase' in f['evidence'] for f in filas)


def test_cabecera_cuenta_las_pruebas_de_plataforma(manifests_client):
    respuesta = manifests_client.get('/api/experiments/manifests?vista=todas')
    assert int(respuesta.headers['X-Platform-Test-Count']) > 0


def test_cabecera_desglosa_los_slugs(manifests_client):
    respuesta = manifests_client.get('/api/experiments/manifests?vista=todas')
    desglose = dict(
        par.split('=') for par in respuesta.headers['X-Platform-Test-Slugs'].split(','))
    assert all(v.isdigit() for v in desglose.values())


def test_la_respuesta_sigue_siendo_una_lista(manifests_client):
    """Cambiar la forma a objeto rompería el contrato congelado."""
    assert isinstance(manifests_client.get('/api/experiments/manifests').json(), list)


def _filas(client) -> dict:
    return {f['slug']: f for f in
            client.get('/api/experiments/manifests?vista=todas').json()}


def test_clase_del_manifiesto_sale_de_los_roles_no_de_is_evidence(manifests_client):
    """Ruling R-26: la clase se deriva de los ROLES de las corridas.

    Este test reemplaza a `test_clase_por_default_resultado_si_es_evidencia_
    ensayo_si_no`, que fijaba el comportamiento que el spec §3 prohíbe («nada
    sube a otra clase por heurística»). `manifiesto_evidencia` y
    `manifiesto_ensayo` son LOS DOS evidencia: sólo el rol de su corrida los
    distingue, así que con el ternario viejo los dos daban 'resultado'.
    """
    filas = _filas(manifests_client)
    assert filas['manifiesto_evidencia']['evidence']['is_evidence'] is True
    assert filas['manifiesto_evidencia']['evidence']['clase'] == 'resultado'
    assert filas['manifiesto_ensayo']['evidence']['is_evidence'] is True
    assert filas['manifiesto_ensayo']['evidence']['clase'] == 'ensayo'


def test_manifiesto_sin_ejecuciones_cae_a_sin_clasificar(manifests_client):
    """Nada sube de clase por descarte: sin ejecuciones no hay rol que leer, y
    'sin_clasificar' es el default del spec §3 — no 'ensayo' por ser un
    manifiesto del catálogo."""
    fila = _filas(manifests_client)['manifiesto_real']
    assert fila['evidence']['is_evidence'] is False
    assert fila['evidence']['n_executions'] == 0
    assert fila['evidence']['clase'] == 'sin_clasificar'


def test_la_excepcion_explicita_por_slug_manda_sobre_la_derivacion(manifests_client):
    """`manifiesto_forzado` derivaría 'resultado' por rol; la excepción gana."""
    assert _filas(manifests_client)['manifiesto_forzado']['evidence']['clase'] == 'instrumento'


def test_cabecera_total_cuenta_todo_lo_que_hay_en_disco(manifests_client):
    """El denominador de la proporción (Task 8, ronda de arreglo 1): TODO lo
    que hay en runs/, no sólo lo archivado — evidencia + plataforma + ensayos
    archivados. En esta fixture: 3 orq_1 + 2 orq_2a + 1 otro_ensayo + 1
    manifiesto_evidencia + 1 manifiesto_ensayo + 1 manifiesto_forzado = 9."""
    respuesta = manifests_client.get('/api/experiments/manifests?vista=todas')
    assert respuesta.headers['X-Total-Executions-Count'] == '9'
    # El total nunca puede ser menor que lo archivado: es archivadas + evidencia.
    assert int(respuesta.headers['X-Total-Executions-Count']) >= int(
        respuesta.headers['X-Archived-Executions-Count'])


def test_cabecera_cuenta_exactamente_los_slugs_de_la_excepcion(manifests_client):
    respuesta = manifests_client.get('/api/experiments/manifests?vista=todas')
    assert respuesta.headers['X-Platform-Test-Count'] == '5'
    desglose = dict(
        par.split('=') for par in respuesta.headers['X-Platform-Test-Slugs'].split(','))
    assert desglose == {'orq_1': '3', 'orq_2a': '2'}
    assert 'otro_ensayo' not in desglose
