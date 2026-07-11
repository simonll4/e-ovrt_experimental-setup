import pytest
import yaml

from eovrt_webconsole.manifest_writer import (
    ManifestExistsError,
    ProtectedManifestError,
    write_manifest,
)


def test_escritura_atomica_y_contenido(repo):
    path = write_manifest(
        repo / "experiments", "nuevo_exp", None, {"run": {"scenario": "DBE"}}
    )
    assert path == repo / "experiments" / "nuevo_exp.yaml"
    assert yaml.safe_load(path.read_text()) == {"run": {"scenario": "DBE"}}
    assert not path.with_suffix(".yaml.tmp").exists()


def test_grupo_crea_subdir(repo):
    path = write_manifest(repo / "experiments", "exp_b", "grupo_x", {"a": 1})
    assert path == repo / "experiments" / "grupo_x" / "exp_b.yaml"


def test_colision_sin_overwrite(repo):
    write_manifest(repo / "experiments", "dup", None, {"a": 1})
    with pytest.raises(ManifestExistsError):
        write_manifest(repo / "experiments", "dup", None, {"a": 2})
    write_manifest(repo / "experiments", "dup", None, {"a": 2}, overwrite=True)


def test_nombre_invalido(repo):
    for bad in ("../evil", "CON ESPACIOS", "", "Mayus"):
        with pytest.raises(ValueError):
            write_manifest(repo / "experiments", bad, None, {})


def test_grupo_protegido_bloquea_incluso_con_overwrite(repo):
    write_manifest(repo / "experiments", "curated", "bench_v2", {"a": 1})
    with pytest.raises(ProtectedManifestError):
        write_manifest(
            repo / "experiments",
            "curated",
            "bench_v2",
            {"a": 2},
            overwrite=True,
            protected_groups=frozenset({"bench_v2"}),
        )
    # el archivo original no cambió
    assert yaml.safe_load(
        (repo / "experiments" / "bench_v2" / "curated.yaml").read_text()
    ) == {"a": 1}


def test_grupo_protegido_permite_crear_nuevo(repo):
    path = write_manifest(
        repo / "experiments",
        "curated_nuevo",
        "bench_v2",
        {"a": 1},
        protected_groups=frozenset({"bench_v2"}),
    )
    assert path.exists()


def test_grupo_no_protegido_sigue_con_overwrite_normal(repo):
    write_manifest(repo / "experiments", "libre", "otro_grupo", {"a": 1})
    write_manifest(
        repo / "experiments",
        "libre",
        "otro_grupo",
        {"a": 2},
        overwrite=True,
        protected_groups=frozenset({"bench_v2"}),
    )
    assert yaml.safe_load(
        (repo / "experiments" / "otro_grupo" / "libre.yaml").read_text()
    ) == {"a": 2}


def test_endpoint_guarda_con_modelo_del_target(client, repo):
    body = {
        "name": "desde_consola",
        "composition": {
            "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
            "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
            "run": {"stride": 2},
        },
    }
    r = client.post("/api/manifests", json=body)
    assert r.status_code == 201
    assert r.json() == {"path": "desde_consola.yaml"}
    saved = yaml.safe_load((repo / "experiments" / "desde_consola.yaml").read_text())
    assert saved["model"] == {"ref": "mock"}  # completado con el modelo del target
    assert saved["source"] == {"ref": "demo_v2"}
    assert saved["prompts"] == {"ref": "demo_set", "active_ids": ["person"]}
    # segunda escritura sin overwrite → 409
    assert client.post("/api/manifests", json=body).status_code == 409


def test_endpoint_set_inexistente_422(client):
    body = {
        "name": "x",
        "composition": {
            "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
            "prompts": {"set_id": "nope", "active_ids": None},
        },
    }
    assert client.post("/api/manifests", json=body).status_code == 422


def test_manifest_grupo_protegido_no_sobrescribe(client, repo):
    # El repo fixture ya trae experiments/bench_v2/bench_manifest.yaml (curado).
    original = (repo / "experiments" / "bench_v2" / "bench_manifest.yaml").read_text()
    body = {
        "name": "bench_manifest",
        "group": "bench_v2",
        "overwrite": True,
        "composition": {
            "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
            "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        },
    }
    r = client.post("/api/manifests", json=body)
    assert r.status_code == 409
    assert "bench_v2" in r.json()["detail"]
    # El archivo curado no cambió (ni con overwrite=true).
    assert (repo / "experiments" / "bench_v2" / "bench_manifest.yaml").read_text() == original

    # Crear uno NUEVO en el mismo grupo protegido sí se permite.
    body["name"] = "bench_manifest_nuevo"
    r2 = client.post("/api/manifests", json=body)
    assert r2.status_code == 201
    assert r2.json() == {"path": "bench_v2/bench_manifest_nuevo.yaml"}


def test_endpoint_plugin_no_soportado_422(client):
    # Schema-válido (Composition acepta cualquier str en ingest.plugin) pero sin mapeo
    # en _PLUGIN_TO_SOURCE_TYPE y sin "dataset" (no toma el camino source.ref): antes
    # del fix, composition_to_manifest hacía un KeyError sin capturar -> 500. Debe dar
    # 422, no 500. (rtsp ya está soportado; usamos oak_d, que sigue fuera del mapeo.)
    body = {
        "name": "oak_d_no_soportado",
        "composition": {
            "ingest": {"plugin": "oak_d", "config": {}},
            "prompts": {"set_id": "demo_set", "active_ids": None},
        },
    }
    r = client.post("/api/manifests", json=body)
    assert r.status_code == 422
    assert r.status_code != 500
