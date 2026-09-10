"""La vitrina funciona sin clientes HTTP, con fixtures de archivo local."""
import csv
import json

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.evidence import CSV_FILES

FIELDS = ['collection', 'result_id', 'role', 'plane', 'run_id', 'status',
          'source_ref', 'artifact_path']


@pytest.fixture
def archive_client(settings):
    root = settings.repo_root
    directory = root / 'results/evidence-runs'
    (directory / 'collections').mkdir(parents=True)
    rows = [
        ['shared', 'bench_imagenes/example', 'comparison', 'media-plane', 'm1', 'copied',
         'results/eval.json', 'artifacts/media-plane/m1'],
        ['shared', 'realtime/example', 'comparison', 'media-plane', 'm1', 'copied',
         'results/eval.json', 'artifacts/media-plane/m1'],
        ['dbe_video', 'clip_bench/campaign', 'control', 'control-plane', 'c1', 'archived_only',
         'results/control-eval.json', 'artifacts/archived-only/control-plane--c1'],
    ]
    for i in range(5):
        rows.append(['dbe_video', 'clip_bench/campaign', 'media', 'media-plane', f'm{i+2}',
                     'copied', 'results/provenance.json', f'artifacts/media-plane/m{i+2}'])
    for name in CSV_FILES:
        with (directory / 'collections' / name).open('w') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)
            writer.writerows([r for r in rows if (r[0] == 'shared') == (name == 'shared.csv')]
                             if name in {'shared.csv', 'dbe-video.csv'} else [])
    for row in rows:
        path = directory / row[-1]
        path.mkdir(parents=True, exist_ok=True)
        if row[5] == 'copied':
            (path / 'summary.json').write_text(json.dumps({'run_id': row[4], 'units_processed': 17}))
        else:
            (path / 'eval.json').write_text('{"precision": 0.75}')
    (directory / 'resolved-runs.json').write_text(json.dumps({'runs': [{
        'plane': 'control-plane', 'run_id': 'c1', 'reason': 'Original retirado; eval preservado.',
    }]}))
    (root / 'results/evidence-runs.yaml').write_text(yaml.safe_dump({'structured_sources': [{
        'result_id': 'bench_imagenes/example', 'document': '../docs/medicion.md',
    }]}))
    app = create_app(settings)
    # Sin entrar al lifespan, ni siquiera existen clientes de planos en app.state.
    return TestClient(app), directory


def test_index_comes_from_rows_and_shared_stays_in_both_results(archive_client):
    client, _ = archive_client
    assert not hasattr(client.app.state, 'http')
    data = client.get('/api/evidencia').json()
    assert data['available'] is True
    assert [(g['id'], g['n_results'], g['n_rows']) for g in data['collections']] == [
        ('bench_imagenes', 1, 1), ('clip_bench', 1, 6), ('realtime', 1, 1),
    ]
    for rid in ['bench_imagenes/example', 'realtime/example']:
        response = client.get('/api/evidencia/resultado', params={'id': rid})
        assert response.status_code == 200
        assert response.json()['items'][0]['run_id'] == 'm1'


def test_pagination_orders_by_role_and_does_not_lose_runs(archive_client):
    client, _ = archive_client
    items = []
    for page in range(1, 4):
        response = client.get('/api/evidencia/resultado', params={
            'id': 'clip_bench/campaign', 'page': page, 'page_size': 2,
        }).json()
        assert response['total'] == 6
        assert response['result']['roles'] == {'control': 1, 'media': 5}
        items.extend(response['items'])
    assert len({r['run_id'] for r in items}) == 6
    assert [r['role'] for r in items] == ['control', *['media'] * 5]


def test_archived_only_reason_substitute_and_no_live_link_even_if_dir_exists(archive_client):
    client, _ = archive_client
    root = client.app.state.settings.repo_root
    (root.parent / 'e-ovrt_control-plane/runs/c1').mkdir(parents=True)
    data = client.get('/api/evidencia/run?plane=control-plane&run_id=c1').json()
    assert data['run']['status'] == 'archived_only'
    assert data['run']['reason'] == 'Original retirado; eval preservado.'
    assert data['run']['tiene_detalle_vivo'] is False
    assert data['summary'] is None
    assert data['substitutes'] == [{'name': 'eval.json', 'data': {'precision': .75}}]


def test_summary_is_frozen_and_live_availability_only_checks_local_directory(archive_client):
    client, _ = archive_client
    root = client.app.state.settings.repo_root
    live = root.parent / 'e-ovrt_media-plane/runs/m1'
    live.mkdir(parents=True)
    (live / 'summary.json').write_text('{"units_processed":999}')
    data = client.get('/api/evidencia/run?plane=media-plane&run_id=m1').json()
    assert data['summary'] == {'run_id': 'm1', 'units_processed': 17}
    assert data['run']['tiene_detalle_vivo'] is True
    assert len(data['relations']) == 2


def test_archived_nested_summary_selects_only_the_requested_identity(archive_client):
    client, directory = archive_client
    summary = {'schema_version': 'control.summary.v1', 'control_run_id': 'c1', 'alerts': 3}
    (directory / 'artifacts/archived-only/control-plane--c1/eval.json').write_text(json.dumps([
        {'summary': {**summary, 'control_run_id': 'another', 'alerts': 99}},
        {'summary': summary},
    ]))
    data = client.get('/api/evidencia/run?plane=control-plane&run_id=c1').json()
    assert data['summary'] == summary
    assert data['summary_source'] == 'eval.json'
    assert data['run']['status'] == 'archived_only'
    assert data['run']['tiene_detalle_vivo'] is False


def test_absent_archive_returns_explanatory_empty_at_all_levels(settings):
    client = TestClient(create_app(settings))
    for url in ['/api/evidencia', '/api/evidencia/resultado?id=clip_bench/x',
                '/api/evidencia/run?plane=media-plane&run_id=x']:
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()['available'] is False
        assert 'docs/operacion/126' in response.json()['message']
        assert str(settings.repo_root / 'results/evidence-runs') in response.json()['message']


def test_archive_removed_after_start_is_not_served_from_stale_cache(archive_client):
    client, directory = archive_client
    directory.rename(directory.with_name('temporarily-absent'))
    assert client.get('/api/evidencia').json()['collections'] == []


def test_title_fallback_override_and_document_provenance(archive_client):
    client, directory = archive_client
    before = client.get('/api/evidencia/resultado?id=bench_imagenes/example').json()['result']
    assert before['titulo'] is None
    assert before['etiqueta'] == 'example'
    assert before['documents'] == ['../docs/medicion.md']
    (directory / 'titulos.yaml').write_text('resultados:\n  - result_id: bench_imagenes/example\n'
                                          '    titulo: Título escrito por el usuario\n')
    restarted = TestClient(create_app(client.app.state.settings))
    after = restarted.get('/api/evidencia/resultado?id=bench_imagenes/example').json()['result']
    assert after['titulo'] == 'Título escrito por el usuario'


@pytest.mark.parametrize('url', [
    '/api/evidencia/resultado?id=unknown/x',
    '/api/evidencia/run?plane=media-plane&run_id=../../outside',
])
def test_unknown_ids_do_not_read_arbitrary_paths(archive_client, url):
    assert archive_client[0].get(url).status_code == 404


def test_summary_symlink_cannot_escape_archive(archive_client, tmp_path):
    client, directory = archive_client
    outside = tmp_path / 'outside.json'
    outside.write_text('{"private": true}')
    path = directory / 'artifacts/media-plane/m1/summary.json'
    path.unlink()
    path.symlink_to(outside)
    assert client.get('/api/evidencia/run?plane=media-plane&run_id=m1').status_code == 400


@pytest.mark.parametrize('query', ['page=0', 'page_size=201'])
def test_invalid_pagination_is_rejected(archive_client, query):
    assert archive_client[0].get('/api/evidencia/resultado?id=clip_bench/campaign&' + query).status_code == 422
