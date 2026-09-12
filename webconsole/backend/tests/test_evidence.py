"""Visibilidad reversible del registro, independiente de servicios vivos."""
import csv
import json
from unittest.mock import AsyncMock

import pytest
import yaml

from eovrt_webconsole.evidence import CSV_FILES, EvidenceRegistry, corridas_consolidadas

FIELDS = ['collection', 'result_id', 'role', 'plane', 'run_id', 'status', 'source_ref', 'artifact_path']


def archive(root):
    directory = root / 'results/evidence-runs'
    (directory / 'collections').mkdir(parents=True)
    for name in CSV_FILES:
        with (directory / 'collections' / name).open('w', newline='') as file:
            writer = csv.DictWriter(file, FIELDS)
            writer.writeheader()
            if name == 'shared.csv':
                for result in ('bench_imagenes/example', 'realtime/example'):
                    writer.writerow(dict(zip(FIELDS, (
                        'shared', result, 'comparison', 'media-plane', 'run_evidence',
                        'copied', 'results/source.json', 'artifacts/media-plane/run_evidence',
                    ))))
    return directory


def test_absent_registry_is_empty_and_app_starts(client, tmp_path):
    registry = EvidenceRegistry(tmp_path / 'absent')
    assert registry.available is False
    assert registry.resultados() == []
    assert registry.relaciones('missing') == []
    assert registry.es_evidencia('missing') is False
    response = client.get('/api/runs')
    assert response.status_code == 200
    assert response.headers['X-Evidence-Available'] == 'false'


def test_shared_relations_and_groups_by_result_prefix(tmp_path):
    registry = EvidenceRegistry(archive(tmp_path))
    assert registry.available is True
    assert [r['result_id'] for r in registry.relaciones('run_evidence')] == [
        'bench_imagenes/example', 'realtime/example',
    ]
    assert registry.resultados() == [
        {'result_id': 'bench_imagenes/example', 'collection': 'bench_imagenes',
         'n_runs': 1, 'planes': ['media-plane']},
        {'result_id': 'realtime/example', 'collection': 'realtime',
         'n_runs': 1, 'planes': ['media-plane']},
    ]
    assert registry.describe(['run_evidence'])['collections'] == ['dbe_datasets', 'ebe_realtime']


def test_registry_loaded_once(settings, fake_state):
    import httpx
    from fastapi.testclient import TestClient

    from eovrt_webconsole.app import create_app
    from tests.fake_service import make_fake_service

    directory = archive(settings.repo_root)
    app = create_app(settings, service_transport=httpx.ASGITransport(app=make_fake_service(fake_state)))
    with TestClient(app) as client:
        for file in (directory / 'collections').iterdir():
            file.unlink()
        assert client.app.state.evidence.es_evidencia('run_evidence') is True
        assert client.get('/api/runs').headers['X-Evidence-Available'] == 'true'


@pytest.mark.parametrize('order', ['created_at', 'total_detections'])
def test_filters_partition_before_hydration_and_keep_default(client, repo, order):
    client.app.state.evidence = EvidenceRegistry(archive(repo))
    backend = client.app.state.backend
    original = [
        {'run_id': 'run_evidence', 'status': 'succeeded'},
        {'run_id': 'run_noise', 'status': 'succeeded'},
    ]
    backend.list_runs = AsyncMock(return_value=original)
    backend.status = AsyncMock(side_effect=lambda run_id: {
        'run_id': run_id, 'status': 'succeeded', 'summary': {'total_detections': 7},
    })
    default = client.get('/api/runs', params={'orden': order})
    all_rows = client.get('/api/runs', params={'orden': order, 'vista': 'todas'})
    assert default.json() == all_rows.json()
    assert {r['run_id'] for r in default.json()} == {'run_evidence', 'run_noise'}
    assert default.headers['X-Total-Count'] == '2'
    backend.status.reset_mock()
    evidence = client.get('/api/runs', params={'orden': order, 'vista': 'evidencia'})
    backend.status.assert_awaited_once_with('run_evidence')
    assert evidence.headers['X-Total-Count'] == '1'
    assert evidence.headers['X-Archived-Count'] == '1'
    assert evidence.json()[0]['evidence']['result_ids'] == [
        'bench_imagenes/example', 'realtime/example',
    ]
    backend.status.reset_mock()
    archived = client.get('/api/runs', params={'orden': order, 'vista': 'archivadas'})
    backend.status.assert_awaited_once_with('run_noise')
    ev = {r['run_id'] for r in evidence.json()}
    ar = {r['run_id'] for r in archived.json()}
    assert not ev & ar
    assert ev | ar == {r['run_id'] for r in default.json()}
    assert client.get('/api/runs?vista=invalid').status_code == 422


@pytest.mark.parametrize('force_evidence,force_archived', [
    (['noise'], ['measured']), (['exp_noise'], ['exp_measured']),
])
def test_exceptions_override_derived_in_both_directions(tmp_path, force_evidence, force_archived):
    directory = archive(tmp_path)
    vista = directory.parent / 'evidence-vista'
    vista.mkdir(parents=True, exist_ok=True)
    (vista / 'consola.yaml').write_text(yaml.safe_dump({
        'forzar_evidencia': force_evidence, 'forzar_archivado': force_archived,
    }))
    registry = EvidenceRegistry(directory)
    noise = registry.ejecucion('exp_noise', 'noise', [])
    measured = registry.ejecucion('exp_measured', 'measured', ['run_evidence'])
    assert noise['is_evidence'] is True
    assert measured['is_evidence'] is False
    assert registry.manifiesto('noise', [noise])['is_evidence'] is True
    assert registry.manifiesto('measured', [measured])['is_evidence'] is False


def test_contradictory_exception_is_explicit(tmp_path):
    directory = archive(tmp_path)
    vista = directory.parent / 'evidence-vista'
    vista.mkdir(parents=True, exist_ok=True)
    (vista / 'consola.yaml').write_text('forzar_evidencia: [x]\nforzar_archivado: [x]\n')
    with pytest.raises(ValueError, match='contradictoria'):
        EvidenceRegistry(directory)


def test_la_config_de_la_vista_vive_fuera_del_archivo_congelado(tmp_path):
    """El archivo congelado tiene integridad por hash: nada mutable adentro.

    `consola.yaml` dentro de `evidence-runs/` rompía
    `tools/evidence_runs.py --check` en cada edición. Este test existe para que
    no vuelva a caer ahí por descuido.
    """
    directory = archive(tmp_path)
    (directory / 'consola.yaml').write_text('forzar_evidencia: [x]\nforzar_archivado: []\n')
    registry = EvidenceRegistry(directory)
    assert registry.config_dir == directory.parent / 'evidence-vista'
    # Se ignora lo que esté dentro del archivo congelado: no altera el veredicto.
    assert registry.ejecucion('exp_x', 'x', [])['is_evidence'] is False


def test_persisted_identity_without_opening_ref_target(tmp_path):
    directory = tmp_path / 'exp'
    for plane in ('report', 'media', 'control'):
        (directory / plane).mkdir(parents=True)
    (directory / 'report/report.json').write_text(json.dumps({'identificacion': {
        'media_run_id': 'r1', 'control_run_id': 'c1',
    }}))
    (directory / 'media/detections.ref.json').write_text(json.dumps({
        'run_id': 'r2', 'path': '/does/not/exist',
    }))
    (directory / 'control/summary.json').write_text(json.dumps({'media_run_ids': ['r3']}))
    before = {str(p): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    assert corridas_consolidadas(directory) == ['c1', 'r1', 'r2', 'r3']
    assert before == {str(p): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
