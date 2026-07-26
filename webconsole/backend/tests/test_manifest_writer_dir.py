"""Escritura atómica del directorio derivado (spec 2026-07-25 §Escritura)."""
from __future__ import annotations

import pytest
import yaml

from eovrt_webconsole.manifest_writer import (
    ManifestExistsError,
    ProtectedManifestError,
    write_manifest_dir,
)

FILES = {
    "manifest.yaml": {"schema_version": "experiment.manifest.v1", "slug": "nuevo"},
    "media.yaml": {"ingest": {"plugin": "oak_d"}},
    "control.yaml": {"patterns": {"file": "/p.yaml"}},
}


def test_escribe_los_tres_archivos(tmp_path):
    target = write_manifest_dir(tmp_path, "nuevo", FILES)
    assert target == tmp_path / "nuevo"
    for name, payload in FILES.items():
        assert yaml.safe_load((target / name).read_text()) == payload


def test_no_deja_temporal(tmp_path):
    write_manifest_dir(tmp_path, "nuevo", FILES)
    assert list(tmp_path.glob(".*.tmp")) == []


def test_rechaza_slug_existente(tmp_path):
    write_manifest_dir(tmp_path, "nuevo", FILES)
    otros = {**FILES, "media.yaml": {"ingest": {"plugin": "rtsp"}}}
    with pytest.raises(ManifestExistsError):
        write_manifest_dir(tmp_path, "nuevo", otros)
    # el original queda intacto
    assert yaml.safe_load((tmp_path / "nuevo" / "media.yaml").read_text()) == FILES["media.yaml"]


def test_rechaza_nombre_invalido(tmp_path):
    for malo in ["Mayus", "../fuga", "", "-arranca-con-guion"]:
        with pytest.raises(ValueError):
            write_manifest_dir(tmp_path, malo, FILES)
    assert list(tmp_path.iterdir()) == []


def test_rechaza_nombre_de_grupo_protegido(tmp_path):
    """El guard tiene que valer ANTES de que el directorio exista: si sólo
    disparara con destino existente sería inalcanzable (ManifestExistsError
    cubre ese caso igual) y los grupos protegidos quedarían sin protección real.
    `experiments/bench_v2/` es un grupo curado: un manifiesto paraguas nunca
    puede ocupar ese nombre."""
    with pytest.raises(ProtectedManifestError):
        write_manifest_dir(tmp_path, "bench_v2", FILES, protected_groups=frozenset({"bench_v2"}))
    assert not (tmp_path / "bench_v2").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_fallo_a_mitad_no_deja_nada(tmp_path, monkeypatch):
    """Si la segunda escritura revienta, no queda ni destino ni temporal."""
    import eovrt_webconsole.manifest_writer as mw

    original = mw.yaml.safe_dump
    llamadas = {"n": 0}

    def explota(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise OSError("disco lleno simulado")
        return original(*args, **kwargs)

    monkeypatch.setattr(mw.yaml, "safe_dump", explota)

    with pytest.raises(OSError):
        write_manifest_dir(tmp_path, "nuevo", FILES)

    assert not (tmp_path / "nuevo").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
