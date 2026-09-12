"""Corridas por clase y agrupadas por resultado (Task 7).

`runs_client` no lo trae ningún fixture compartido: se siembra acá, con el
mismo patrón que `archive_client` de `test_evidence_archive.py` — archivos
locales bajo `settings.repo_root`, `TestClient` sin entrar al lifespan (nunca
se abre un cliente HTTP real). La única diferencia es que estas rutas SÍ tocan
`app.state.backend` (`list_runs()` lo necesita para leer el listado base), así
que acá se lo asigna a mano con un backend falso mínimo — un objeto con
`list_runs()`, nada de red — en vez de dejarlo sin setear como hace
`archive_client` (que nunca ejercita rutas de `/api/runs`).
"""
from __future__ import annotations

import csv
import datetime as dt
import json

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.evidence import CLASES, CSV_FILES
from eovrt_webconsole.run_backend import UnknownRun

FIELDS = ["collection", "result_id", "role", "plane", "run_id", "status", "source_ref", "artifact_path"]

# Los grupos de la fixture, deliberadamente heterogéneos: la mayoría del
# volumen es 'resultado' (como en la plataforma real: 412 de 472), pero hay
# representantes de las otras tres clases del registro y un puñado de
# corridas que no citan ningún resultado (exploratorias/fallidas), que tienen
# que colapsar en el ÚNICO grupo 'sin_clasificar'.
RESULTADO = {
    "clip_bench/t1": 6,
    "clip_bench/g1": 5,
    "clip_bench/r1": 4,
    "bench_imagenes/s1": 3,
    "realtime/descarte_irregular": 2,
}
INSTRUMENTO = {"realtime/claqueta_reloj_externo": 3}
ENSAYO = {"clip_bench/ensayo_x": 3}
PLATAFORMA = {"bench_imagenes/plataforma_check": 2}
SIN_CLASIFICAR_N = 6

BASE_TS = dt.datetime(2026, 8, 1, 0, 0, 0, tzinfo=dt.UTC)


def _rid(i: int) -> str:
    t = BASE_TS + dt.timedelta(minutes=i)
    return f"run_{t.strftime('%Y%m%d_%H%M%S')}_r{i:03d}"


class _FakeRunsBackend:
    """Lo mínimo que `list_runs()` y `list_grupos()` (Task 7) necesitan de
    `app.state.backend`: `/grupos` nunca hidrata, pero el listado plano SÍ
    hidrata la página que devuelve incluso en el orden por defecto
    (`created_at`) — `_hidratar` llama a `.status()` por cada fila de esa
    página, así que hace falta implementarlo."""

    def __init__(self, rows: list[dict]) -> None:
        self._by_id = {r["run_id"]: r for r in rows}

    async def list_runs(self) -> list[dict]:
        return list(self._by_id.values())

    async def status(self, run_id: str) -> dict:
        try:
            return self._by_id[run_id]
        except KeyError:
            raise UnknownRun(run_id) from None


@pytest.fixture
def runs_client(settings):
    root = settings.repo_root
    directory = root / "results" / "evidence-runs"
    (directory / "collections").mkdir(parents=True)

    rows: list[list[str]] = []
    corridas: list[dict] = []
    contador = 0

    def sumar(grupos: dict[str, int], collection: str, role: str):
        nonlocal contador
        for result_id, n in grupos.items():
            for _ in range(n):
                run_id = _rid(contador)
                contador += 1
                rows.append([collection, result_id, role, "media-plane", run_id, "copied",
                             "results/eval.json", f"artifacts/media-plane/{run_id}"])
                corridas.append({"run_id": run_id, "name": None, "status": "succeeded", "live": False})

    sumar(RESULTADO, "dbe_video", "media")
    # La trampa de conteo que la consigna nombra explícita: la PRIMERA corrida
    # de 'clip_bench/t1' queda TAMBIÉN citada por 'clip_bench/g1' (mismo rol
    # 'media' en las dos, así que sigue siendo clase 'resultado' en ambas — no
    # se mezcla con la fila de precedencia de clase). No es una corrida nueva:
    # es una segunda fila de evidencia para un `run_id` que `sumar()` ya contó.
    rows.append(["dbe_video", "clip_bench/g1", "media", "media-plane", rows[0][4], "copied",
                 "results/eval.json", f"artifacts/media-plane/{rows[0][4]}"])
    sumar(INSTRUMENTO, "ebe_realtime", "instrument_check")
    sumar(ENSAYO, "dbe_video", "trial")
    sumar(PLATAFORMA, "dbe_datasets", "platform_check")
    for _ in range(SIN_CLASIFICAR_N):
        run_id = _rid(contador)
        contador += 1
        corridas.append({"run_id": run_id, "name": None, "status": "succeeded", "live": False})

    for name in CSV_FILES:
        with (directory / "collections" / name).open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)
            if name == "dbe-video.csv":
                writer.writerows(rows)

    vista = directory.parent / "evidence-vista"
    vista.mkdir(parents=True, exist_ok=True)
    (vista / "clasificacion.yaml").write_text(yaml.safe_dump({
        "roles": {
            "resultado": ["media"],
            "instrumento": ["instrument_check"],
            "ensayo": ["trial"],
            "plataforma": ["platform_check"],
        },
    }, allow_unicode=True))
    (vista / "titulos.yaml").write_text(yaml.safe_dump({"resultados": [
        {"result_id": "clip_bench/t1", "titulo": "Línea de base del Nivel B",
         "reclamo": "tiny-560 · escena"},
        {"result_id": "realtime/claqueta_reloj_externo", "titulo": "La claqueta con reloj externo",
         "reclamo": "OAK-D · EBE"},
    ]}, allow_unicode=True))
    # Un paso citado (cifra CITADA) y uno leído (cifra LEÍDA de metrics.json):
    # el mismo patrón que Entrada.tsx/Paso.tsx del frente de evidencia, no uno
    # nuevo. `clip_bench/g1` no tiene título en titulos.yaml a propósito: cae
    # al fallback de la pantalla.
    (root / "results" / "clip_bench" / "g1").mkdir(parents=True)
    (root / "results" / "clip_bench" / "g1" / "metrics.json").write_text(
        json.dumps({"f1_micro": 0.93}))
    (vista / "recorrido.yaml").write_text(yaml.safe_dump({
        "pasos": [
            {"n": 3, "titulo": "Paso tres", "claim": "Relato de ejemplo.",
             "cifra": "0,789", "cifra_label": "F1", "fuente": "results/evidence-runs.yaml",
             "resultados": ["clip_bench/t1"]},
            {"n": 4, "titulo": "Paso cuatro", "claim": "Relato de ejemplo.",
             "cifra_label": "F1 micro",
             "leer": [{"result_id": "clip_bench/g1", "campo": "f1_micro"}],
             "resultados": ["clip_bench/g1"]},
        ],
        "respaldo_instrumental": {"titulo": "Respaldo", "claim": "Relato.", "resultados": []},
    }, allow_unicode=True))

    app = create_app(settings)
    # Sin entrar al lifespan: como `archive_client`, nunca se abre un cliente
    # HTTP real. La diferencia es que estas rutas SÍ leen `app.state.backend`
    # (`list_runs()`), así que se lo asigna a mano.
    app.state.backend = _FakeRunsBackend(corridas)
    return TestClient(app)


def test_listado_filtra_por_clase(runs_client):
    client = runs_client
    todas = client.get('/api/runs?vista=todas&page_size=200').json()
    resultado = client.get('/api/runs?clase=resultado&page_size=200').json()
    assert len(resultado) < len(todas)
    assert all(r['evidence']['clase'] == 'resultado' for r in resultado)


def test_cada_corrida_trae_su_clase(runs_client):
    filas = runs_client.get('/api/runs?vista=todas&page_size=5').json()
    assert all('clase' in r['evidence'] for r in filas)


def test_grupos_colapsan_las_corridas_por_resultado(runs_client):
    grupos = runs_client.get('/api/runs/grupos').json()
    assert len(grupos) < 60, 'la gracia es colapsar cientos de filas en decenas'
    assert all({'result_id', 'titulo', 'clase', 'n_runs'} <= set(g) for g in grupos)


def test_corridas_fuera_del_registro_caen_en_un_grupo_propio(runs_client):
    grupos = runs_client.get('/api/runs/grupos').json()
    suelto = [g for g in grupos if g['clase'] == 'sin_clasificar']
    assert len(suelto) == 1
    assert suelto[0]['result_id'] is None
    assert suelto[0]['n_runs'] == SIN_CLASIFICAR_N


def test_grupos_suman_mas_que_el_total_de_corridas(runs_client):
    # La trampa de conteo explícita en la consigna: la fixture tiene UNA
    # corrida citada por 'clip_bench/t1' Y 'clip_bench/g1' (ver `runs_client`),
    # así que aparece en los DOS grupos y la suma de `n_runs` queda por encima
    # del total real — que nunca se deriva sumando esta lista, se lee de
    # `X-Total-Count` en `GET /api/runs`.
    total = int(runs_client.get('/api/runs?vista=todas&page_size=1').headers['X-Total-Count'])
    assert total == 6 + 5 + 4 + 3 + 2 + 3 + 3 + 2 + SIN_CLASIFICAR_N
    grupos = runs_client.get('/api/runs/grupos').json()
    suma = sum(g['n_runs'] for g in grupos)
    assert suma > total, 'la fixture no tiene ninguna corrida citada por dos resultados'
    assert suma == total + 1  # una única corrida compartida entre los dos grupos

    t1 = {r['run_id'] for r in runs_client.get('/api/runs?result_id=clip_bench/t1&page_size=200').json()}
    g1 = {r['run_id'] for r in runs_client.get('/api/runs?result_id=clip_bench/g1&page_size=200').json()}
    assert len(t1 & g1) == 1, 'la corrida compartida tiene que aparecer citada por los dos resultados'


def test_filtro_de_clase_en_grupos(runs_client):
    instrumento = runs_client.get('/api/runs/grupos?clase=instrumento').json()
    assert [g['result_id'] for g in instrumento] == ['realtime/claqueta_reloj_externo']


def test_grupo_de_resultado_cita_el_paso_y_su_cifra_citada(runs_client):
    grupos = {g['result_id']: g for g in runs_client.get('/api/runs/grupos').json()}
    t1 = grupos['clip_bench/t1']
    assert t1['paso'] == 3
    assert t1['cifra'] == '0,789'
    assert t1['cifra_label'] == 'F1'
    assert t1['cifra_origen'] == 'citada'
    assert t1['titulo'] == 'Línea de base del Nivel B'


def test_grupo_de_resultado_con_cifra_leida_de_metrics_json(runs_client):
    grupos = {g['result_id']: g for g in runs_client.get('/api/runs/grupos').json()}
    g1 = grupos['clip_bench/g1']
    assert g1['paso'] == 4
    assert g1['cifra_origen'] == 'leida'
    assert g1['cifra'] == '0,930'


def test_grupo_sin_paso_declara_la_cifra_ausente_no_un_cero(runs_client):
    # Instrumento, ensayo, plataforma y sin_clasificar no sostienen ningún paso
    # del argumento: la cifra tiene que venir declarada (None), nunca 0.
    grupos = {g['result_id']: g for g in runs_client.get('/api/runs/grupos').json()}
    for result_id in ['realtime/claqueta_reloj_externo', 'clip_bench/ensayo_x',
                       'bench_imagenes/plataforma_check', None]:
        assert grupos[result_id]['cifra'] is None
        assert grupos[result_id]['cifra_label'] is None
        assert grupos[result_id]['paso'] is None


def _conteos(respuesta) -> dict[str, int]:
    """`X-Class-Counts: clase=n,…` -> dict. Mismo formato que
    `X-Platform-Test-Slugs`, que ya usa Experimentos."""
    return {clase: int(n) for clase, n in
            (par.split("=") for par in respuesta.headers["X-Class-Counts"].split(","))}


def test_los_conteos_por_clase_son_corridas_distintas_no_citaciones(runs_client):
    """C-1: el chip decía 'Resultado 693' arriba de un encabezado que decía
    '472 corridas', porque el frontend sumaba `n_runs` sobre los grupos — eso
    cuenta CITACIONES. El conteo tiene que ser exactamente lo que devuelve el
    filtro, y por lo tanto no puede superar el total."""
    respuesta = runs_client.get('/api/runs/grupos')
    conteos = _conteos(respuesta)
    total = int(runs_client.get('/api/runs?vista=todas&page_size=1').headers['X-Total-Count'])

    citaciones = sum(g['n_runs'] for g in respuesta.json())
    assert citaciones > total, 'la fixture no ejercita la pertenencia múltiple'
    assert sum(conteos.values()) == total
    assert all(n <= total for n in conteos.values())

    for clase, n in conteos.items():
        filas = runs_client.get(f'/api/runs?clase={clase}&page_size=200').json()
        assert len(filas) == n, f'el chip {clase} promete {n} y el filtro trae {len(filas)}'


def test_los_conteos_declaran_las_cinco_clases_incluso_en_cero(runs_client):
    """Un cero MEDIDO es un dato: se emite. Lo que no existe se declara, no se
    omite en silencio — el chip de cero no se dibuja, pero esa decisión es de
    la pantalla, no de la ausencia de la clave."""
    conteos = _conteos(runs_client.get('/api/runs/grupos'))
    assert set(conteos) == set(CLASES)


def test_los_conteos_no_dependen_del_filtro_aplicado(runs_client):
    """Los chips son globales: elegir uno no puede hacer desaparecer al resto."""
    todos = _conteos(runs_client.get('/api/runs/grupos'))
    filtrado = _conteos(runs_client.get('/api/runs/grupos?clase=instrumento'))
    assert filtrado == todos


def test_grupos_declaran_si_el_registro_y_la_clasificacion_estan(runs_client):
    """C-3: sin esas cabeceras la pantalla afirma una clasificación construida
    entera sobre un archivo ausente."""
    respuesta = runs_client.get('/api/runs/grupos')
    assert respuesta.headers['X-Evidence-Available'] == 'true'
    assert respuesta.headers['X-Clasificacion-Available'] == 'true'


def test_grupo_trae_la_etiqueta_derivada_del_backend(runs_client):
    """La `etiqueta()` vive en un solo lado (`evidence_archive.py`): el
    frontend ya no deriva su propio nombre a partir del result_id."""
    grupos = {g['result_id']: g for g in runs_client.get('/api/runs/grupos').json()}
    assert grupos['clip_bench/g1']['titulo'] is None, 'la fixture lo deja sin título a propósito'
    assert grupos['clip_bench/g1']['etiqueta'] == 'g1'
    assert grupos[None]['etiqueta'] is None
