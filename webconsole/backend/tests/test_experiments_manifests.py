"""CRUD del manifiesto paraguas experiment.manifest.v1 (Spec 44 B, tarea 2)."""
from __future__ import annotations

import yaml

VALID_UMBRELLA = {
    "schema_version": "experiment.manifest.v1",
    "slug": "mi_experimento",
    "runs": {
        "media": {
            "service": "media-plane",
            "config": "configs/media_run.yaml",
            "mode": "run",
        },
        "control": {
            "service": "control-plane",
            "config": "configs/control_run.yaml",
            "mode": "live",
        },
    },
    "sequencing": "control_first",
}


def test_post_manifest_valido_201_y_archivo(client, repo):
    r = client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    assert r.status_code == 201
    assert r.json() == {"slug": "mi_experimento"}
    saved_path = repo / "experiments" / "mi_experimento.yaml"
    assert saved_path.exists()
    saved = yaml.safe_load(saved_path.read_text())
    assert saved["schema_version"] == "experiment.manifest.v1"
    assert saved["slug"] == "mi_experimento"
    assert saved["runs"]["media"]["service"] == "media-plane"


def test_get_lista_incluye_umbrella_y_excluye_single_plane(client, repo):
    client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    r = client.get("/api/experiments/manifests")
    assert r.status_code == 200
    slugs = [item["slug"] for item in r.json()]
    assert "mi_experimento" in slugs
    # Los manifiestos single-plane pre-sembrados por el fixture repo (demo_manifest,
    # bench_v2/bench_manifest) no tienen schema_version: experiment.manifest.v1 y no
    # deben aparecer en el listado paraguas.
    assert "demo_manifest" not in slugs
    assert "bench_manifest" not in slugs


def test_get_por_slug_200(client, repo):
    client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    r = client.get("/api/experiments/manifests/mi_experimento")
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == "experiment.manifest.v1"
    assert body["slug"] == "mi_experimento"
    assert body["runs"]["control"]["mode"] == "live"


def test_get_por_slug_inexistente_404(client):
    r = client.get("/api/experiments/manifests/no_existe")
    assert r.status_code == 404


def test_post_manifest_invalido_422(client):
    bad = dict(VALID_UMBRELLA)
    bad.pop("schema_version")  # rompe el schema: campo requerido faltante
    r = client.post("/api/experiments/manifests", json=bad)
    assert r.status_code == 422


def test_post_manifest_duplicado_sin_overwrite_409(client):
    r1 = client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    assert r1.status_code == 201
    r2 = client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    assert r2.status_code == 409


def test_post_manifest_duplicado_con_overwrite_201(client):
    client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    r = client.post("/api/experiments/manifests?overwrite=true", json=VALID_UMBRELLA)
    assert r.status_code == 201


def test_yaml_mal_formado_se_salta_no_500(client, repo):
    # Un YAML sintacticamente invalido en experiments_dir no debe romper el listado
    # ni el get por slug: yaml.safe_load lanza yaml.YAMLError, que no es ValueError,
    # asi que debe estar contemplado explicitamente en el except de
    # _iter_umbrella_manifests para saltear el archivo en vez de propagar un 500.
    client.post("/api/experiments/manifests", json=VALID_UMBRELLA)
    (repo / "experiments" / "roto.yaml").write_text("{ esto no: es: yaml: valido")

    r_list = client.get("/api/experiments/manifests")
    assert r_list.status_code == 200
    slugs = [item["slug"] for item in r_list.json()]
    assert "mi_experimento" in slugs
    assert "roto" not in slugs

    r_get = client.get("/api/experiments/manifests/mi_experimento")
    assert r_get.status_code == 200
    assert r_get.json()["slug"] == "mi_experimento"
