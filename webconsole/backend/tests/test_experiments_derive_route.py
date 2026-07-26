"""Endpoint POST /api/experiments/manifests/{slug}/derive."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.experiment.manifest import load_manifest


@pytest.fixture
def repo(tmp_path):
    """Repo mínimo: experiments/ con un paraguas, prompts/ y cameras/."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "cameras").mkdir()
    exp = tmp_path / "experiments" / "base"
    exp.mkdir(parents=True)

    (exp / "manifest.yaml").write_text(yaml.safe_dump({
        "schema_version": "experiment.manifest.v1",
        "slug": "base",
        "runs": {
            "media": {"service": "media-plane", "config": str(exp / "media.yaml"), "mode": "run"},
            "control": {"service": "control-plane", "config": str(exp / "control.yaml"), "mode": "live"},
        },
        "sequencing": "control_first",
        "report": {},
        "frozen": {},
    }))
    (exp / "media.yaml").write_text(yaml.safe_dump({
        "ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137", "warmup_frames": 20}},
        "prompts": {"set_inline": {"id": "viejo", "classes": []}},
        "run": {"name": "base"},
    }))
    (exp / "control.yaml").write_text(yaml.safe_dump({
        "run": {"name": "control_base"},
        "patterns": {"file": "/p/v2.yaml", "active_ids": ["CR-01", "CR-02"]},
    }))

    (tmp_path / "prompts" / "corto.yaml").write_text(yaml.safe_dump({
        "prompt_set": {
            "id": "corto",
            "classes": [{"id": "person", "phrasings": {"default": ["person"]}}],
        }
    }))
    (tmp_path / "cameras" / "dvr.yaml").write_text(yaml.safe_dump({
        "camera": {"id": "dvr", "name": "DVR", "plugin": "rtsp",
                   "config": {"url": "rtsp://1.2.3.4:554/s"}}
    }))
    # Preset con credenciales en claro, como el rtsp_dvr_1 real del repo. cameras/
    # está gitignoreado; experiments/ NO. Derivar hacia esta cámara tiene que fallar.
    (tmp_path / "cameras" / "dvr_creds.yaml").write_text(yaml.safe_dump({
        "camera": {"id": "dvr_creds", "name": "DVR con credenciales", "plugin": "rtsp",
                   "config": {"url": "rtsp://usuario:clave@169.254.31.140:554/s"}}
    }))
    return tmp_path


@pytest.fixture
def client(repo, monkeypatch):
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(repo))
    return TestClient(create_app())


def _derive(client, body):
    return client.post("/api/experiments/manifests/base/derive", json=body)


def test_deriva_y_reapunta_rutas(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "changes": "warmup 30",
                         "overrides": {"warmup_frames": 30}})
    assert r.status_code == 201, r.text
    assert r.json() == {"slug": "nuevo"}

    nuevo = repo / "experiments" / "nuevo"
    manifest = load_manifest(nuevo / "manifest.yaml")
    assert manifest.slug == "nuevo"
    assert manifest.derives_from == "base"
    assert manifest.changes == "warmup 30"

    # GUARD ANTI-FALLO-SILENCIOSO: los paths del derivado resuelven dentro de su
    # propio directorio, y el valor leído es el override — no el del fuente.
    media_path = Path(manifest.runs["media"].config)
    assert media_path.parent == nuevo
    assert yaml.safe_load(media_path.read_text())["ingest"]["config"]["warmup_frames"] == 30
    # el fuente quedó intacto
    base_media = repo / "experiments" / "base" / "media.yaml"
    assert yaml.safe_load(base_media.read_text())["ingest"]["config"]["warmup_frames"] == 20


def test_aparece_en_el_listado(client):
    _derive(client, {"new_slug": "nuevo", "overrides": {}})
    slugs = [m["slug"] for m in client.get("/api/experiments/manifests").json()]
    assert "nuevo" in slugs


def test_expande_prompt_set(client, repo):
    _derive(client, {"new_slug": "nuevo", "overrides": {"prompt_set_id": "corto"}})
    media = yaml.safe_load((repo / "experiments" / "nuevo" / "media.yaml").read_text())
    assert media["prompts"]["set_inline"]["id"] == "corto"
    assert media["prompts"]["set_inline"]["classes"][0]["id"] == "person"


def test_cambia_camara(client, repo):
    _derive(client, {"new_slug": "nuevo", "overrides": {"camera_id": "dvr"}})
    media = yaml.safe_load((repo / "experiments" / "nuevo" / "media.yaml").read_text())
    assert media["ingest"]["plugin"] == "rtsp"
    assert media["ingest"]["config"]["url"] == "rtsp://1.2.3.4:554/s"


def test_camara_con_credenciales_400_y_no_escribe_nada(client, repo):
    """Fuga a un directorio versionado: experiments/ va a git, cameras/ no."""
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"camera_id": "dvr_creds"}})
    assert r.status_code == 400, r.text
    assert "credenciales" in r.json()["detail"]
    assert not (repo / "experiments" / "nuevo").exists()
    assert list((repo / "experiments").glob(".*.tmp")) == []


def test_pattern_set_file_inexistente_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo",
                         "overrides": {"pattern_set_file": "/no/existe/patterns.yaml"}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()


def test_pattern_set_file_relativo_400(client, repo, monkeypatch):
    """ADR-009: los paths del manifiesto son absolutos. Una ruta relativa que
    existe respecto del cwd del BFF la resolvería el control-plane contra SU
    propio cwd — otro proceso, otro directorio: carga otro pattern set o falla
    al lanzar."""
    relativo = "patterns_relativo.yaml"
    (repo / relativo).write_text("patterns: {}\n")
    monkeypatch.chdir(repo)
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"pattern_set_file": relativo}})
    assert r.status_code == 400, r.text
    assert "absoluta" in r.json()["detail"]
    assert not (repo / "experiments" / "nuevo").exists()


def test_slug_repetido_409(client):
    _derive(client, {"new_slug": "nuevo", "overrides": {}})
    r = _derive(client, {"new_slug": "nuevo", "overrides": {}})
    assert r.status_code == 409


def test_slug_invalido_400(client, repo):
    r = _derive(client, {"new_slug": "Mayus", "overrides": {}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "Mayus").exists()


def test_fuente_desconocida_404(client):
    r = client.post("/api/experiments/manifests/noexiste/derive",
                    json={"new_slug": "n", "overrides": {}})
    assert r.status_code == 404


def test_camara_inexistente_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"camera_id": "fantasma"}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()


def test_prompt_set_inexistente_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"prompt_set_id": "fantasma"}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()


def test_derive_defaults_devuelve_las_claves_del_formulario(client):
    """El formulario precarga los valores del fuente (spec §Frontend). El shape
    es 1:1 con las claves de `overrides` para que no haya traducción que se
    pueda desincronizar."""
    r = client.get("/api/experiments/manifests/base/derive-defaults")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "warmup_frames", "fps", "camera_id", "prompt_set_id",
        "stride", "max_units", "pattern_set_file", "pattern_active_ids",
    }
    assert body["warmup_frames"] == 20
    assert body["fps"] is None
    assert body["prompt_set_id"] == "viejo"
    assert body["pattern_set_file"] == "/p/v2.yaml"
    assert body["pattern_active_ids"] == ["CR-01", "CR-02"]


def test_derive_defaults_resuelve_camera_id_contra_el_catalogo(client, repo):
    """El media.yaml guarda plugin+url, no el id del preset: se matchea."""
    (repo / "cameras" / "oak.yaml").write_text(yaml.safe_dump({
        "camera": {"id": "oak", "name": "OAK", "plugin": "oak_d",
                   "config": {"url": "169.254.31.137"}}
    }))
    body = client.get("/api/experiments/manifests/base/derive-defaults").json()
    assert body["camera_id"] == "oak"


def test_derive_defaults_sin_match_devuelve_camera_id_null(client):
    body = client.get("/api/experiments/manifests/base/derive-defaults").json()
    assert body["camera_id"] is None


def test_derive_defaults_nunca_filtra_la_url_de_la_camara(client, repo):
    """Contracara del hallazgo de credenciales: este endpoint alimenta al
    browser. La url cruda del preset no sale de acá bajo ninguna forma."""
    (exp := repo / "experiments" / "base" / "media.yaml").write_text(yaml.safe_dump({
        "ingest": {"plugin": "rtsp",
                   "config": {"url": "rtsp://usuario:clave@169.254.31.140:554/s"}},
        "prompts": {"set_inline": {"id": "viejo", "classes": []}},
        "run": {"name": "base"},
    }))
    assert exp.exists()
    r = client.get("/api/experiments/manifests/base/derive-defaults")
    assert r.status_code == 200, r.text
    crudo = r.text
    assert "usuario" not in crudo
    assert "clave" not in crudo
    assert "169.254.31.140" not in crudo
    assert "rtsp://" not in crudo


def test_derive_defaults_fuente_desconocida_404(client):
    r = client.get("/api/experiments/manifests/noexiste/derive-defaults")
    assert r.status_code == 404


def test_override_desconocido_400(client, repo):
    r = _derive(client, {"new_slug": "nuevo", "overrides": {"inventado": 1}})
    assert r.status_code == 400
    assert not (repo / "experiments" / "nuevo").exists()
