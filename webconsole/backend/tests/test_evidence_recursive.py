"""Regresión de campañas profundas y del flujo hasta la evidencia persistida."""
import json

import pytest
import yaml

from eovrt_webconsole.evidence import (
    EvidenceRegistry,
    clasificar_ejecuciones,
    corridas_consolidadas,
)
from eovrt_webconsole.routers.experiments import _ejecuciones_por_slug
from tests.test_evidence import archive
from tests.test_experiments_listing_fields import UMBRELLA


def consolidated(root, relative, slug, run_id):
    directory = root / 'runs' / relative
    (directory / 'deep/media/more').mkdir(parents=True)
    (directory / 'report').mkdir()
    (directory / 'control').mkdir()
    (directory / 'manifest.effective.yaml').write_text(yaml.safe_dump({'slug': slug}))
    (directory / 'deep/media/more/identity.json').write_text(json.dumps({
        'nested': [{'run_id': run_id}],
    }))
    (directory / 'report/report.json').write_text(json.dumps({
        'identificacion': {'experiment_id': directory.name}, 'resultados': [],
    }))
    (directory / 'control/alerts.jsonl').write_text('')
    return directory


@pytest.fixture
def campaign(repo, client):
    client.app.state.evidence = EvidenceRegistry(archive(repo))
    for slug in ('campaign', 'recipe'):
        assert client.post('/api/experiments/manifests', json={**UMBRELLA, 'slug': slug}).status_code == 201
    paths = [consolidated(repo, f'campaign/day/video/repetition-{n}/consolidated/exp_{n}',
                          'campaign', 'run_evidence' if n else 'run_admission') for n in range(4)]
    consolidated(repo, 'exp_orphan', 'orphan', 'run_noise')
    return paths


def test_recursive_discovery_and_deep_identity_are_separate_from_legacy_listing(repo, client, campaign):
    assert _ejecuciones_por_slug(repo / 'runs').keys() == {'orphan'}
    executions = clasificar_ejecuciones(repo / 'runs', client.app.state.evidence)
    assert len(executions) == 5
    linked = [e for e in executions if e['slug'] == 'campaign']
    assert len(linked) == 4
    assert sum(e['evidence']['is_evidence'] for e in linked) == 3
    assert next(e for e in executions if e['slug'] == 'orphan')['evidence']['is_evidence'] is False


def test_filtered_lists_partition_and_keep_original_fields(client, campaign):
    default = client.get('/api/experiments/manifests')
    explicit = client.get('/api/experiments/manifests?vista=todas')
    assert default.json() == explicit.json()
    rows = default.json()
    assert {r['slug'] for r in rows} == {'campaign', 'recipe'}
    assert all(r['n_runs'] == 0 and r['last_experiment_id'] is None for r in rows)
    evidence = client.get('/api/experiments/manifests?vista=evidencia')
    archived = client.get('/api/experiments/manifests?vista=archivadas')
    assert [r['slug'] for r in evidence.json()] == ['campaign']
    assert [r['slug'] for r in archived.json()] == ['recipe']
    assert evidence.headers['X-Archived-Executions-Count'] == '2'
    assert evidence.headers['X-Archived-Count'] == '1'
    assert evidence.json()[0]['evidence']['n_executions'] == 4
    assert evidence.json()[0]['evidence']['executions'] == ['exp_3', 'exp_2', 'exp_1']
    assert evidence.json()[0]['evidence']['result_ids'] == ['bench_imagenes/example', 'realtime/example']
    assert client.get('/api/experiments/manifests?vista=inventada').status_code == 422


def test_nested_evidence_links_open_detail_report_and_alerts_after_restart(client, campaign):
    for experiment_id in client.get('/api/experiments/manifests?vista=evidencia').json()[0]['evidence']['executions']:
        assert client.app.state.experiment_manager.get(experiment_id) is None
        detail = client.get(f'/api/experiments/{experiment_id}')
        assert detail.status_code == 200
        assert detail.json()['experiment_id'] == experiment_id
        assert detail.json()['slug'] == 'campaign'
        assert client.get(f'/api/experiments/{experiment_id}/report').status_code == 200
        assert client.get(f'/api/experiments/{experiment_id}/alerts').json() == []


def test_whole_subtree_handles_jsonl_yaml_and_symlink_containment(tmp_path):
    directory = tmp_path / 'exp'
    deep = directory / 'extra' / 'deep'
    deep.mkdir(parents=True)
    (deep / 'ids.yaml').write_text('nested:\n  control_run_id: control_a\n')
    (deep / 'events.jsonl').write_text('{"nested":{"media_run_ids":["media_a"]}}\n')
    (deep / 'identities.json').write_text('[{"nested":{"run_id":"media_b"}}]')
    outside = tmp_path / 'external.json'
    outside.write_text('{"run_id":"outside"}')
    (deep / 'escape.json').symlink_to(outside)
    assert corridas_consolidadas(directory) == ['control_a', 'media_a', 'media_b']


def test_nested_symlink_cannot_escape_runs(client, repo, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'manifest.effective.yaml').write_text('slug: escaped\n')
    nested = repo / 'runs' / 'campaign'
    nested.mkdir(parents=True)
    (nested / 'exp_escape').symlink_to(outside, target_is_directory=True)
    assert client.get('/api/experiments/exp_escape').status_code == 404


def test_ambiguous_nested_ids_are_not_silently_chosen(client, repo):
    consolidated(repo, 'a/exp_duplicate', 'campaign', 'run_evidence')
    consolidated(repo, 'b/exp_duplicate', 'campaign', 'run_evidence')
    assert client.get('/api/experiments/exp_duplicate').status_code == 409


def test_explicit_overrides_filter_both_directions(client, repo, campaign):
    path = repo / 'results/evidence-runs'
    (path / 'consola.yaml').write_text('forzar_evidencia: [recipe]\nforzar_archivado: [campaign]\n')
    client.app.state.evidence = EvidenceRegistry(path)
    assert [r['slug'] for r in client.get('/api/experiments/manifests?vista=evidencia').json()] == ['recipe']
    assert [r['slug'] for r in client.get('/api/experiments/manifests?vista=archivadas').json()] == ['campaign']
