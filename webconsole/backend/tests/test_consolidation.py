"""Tests de la consolidacion de artefactos (ADR-014, spec 44 Tarea 2)."""
from __future__ import annotations

import hashlib
import json

import yaml

from eovrt_webconsole.experiment.consolidation import consolidate_experiment, sha256_file


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _build_media_run_dir(tmp_path, run_id="media-run-1"):
    media_run_dir = tmp_path / "media_runs" / run_id
    _write(media_run_dir / "effective_config.yaml", "modelo: gdino\n")
    _write(media_run_dir / "summary.json", json.dumps({"status": "succeeded"}))
    _write(media_run_dir / "metrics.jsonl", '{"unit_id": "u1"}\n')
    # detections.jsonl "pesado": no debe copiarse, solo referenciarse.
    _write(media_run_dir / "detections.jsonl", '{"unit_id": "u1", "boxes": []}\n' * 100)
    return media_run_dir


def _build_control_run_dir(tmp_path, run_id="control-run-1"):
    control_run_dir = tmp_path / "control_runs" / run_id
    _write(control_run_dir / "effective_config.yaml", "engine: pattern\n")
    _write(control_run_dir / "summary.json", json.dumps({"status": "succeeded"}))
    _write(control_run_dir / "metrics.jsonl", '{"alert_id": "al-1"}\n')
    _write(control_run_dir / "alerts.jsonl", '{"alert_id": "al-1"}\n')
    _write(control_run_dir / "pattern_events.jsonl", '{"event": "cr01_confirmed"}\n')
    return control_run_dir


def test_consolidate_experiment_copia_livianos_y_referencia_detections(tmp_path):
    media_run_dir = _build_media_run_dir(tmp_path)
    control_run_dir = _build_control_run_dir(tmp_path)
    manifest_effective = {"schema_version": "experiment.manifest.v1", "slug": "smoke"}
    dest_root = tmp_path / "runs"

    result = consolidate_experiment(
        "exp_20260711T000000Z_smoke",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective=manifest_effective,
        dest_root=dest_root,
    )

    assert result == dest_root / "exp_20260711T000000Z_smoke"

    # Livianos copiados en ambos planos.
    assert (result / "media" / "summary.json").exists()
    assert (result / "media" / "effective_config.yaml").exists()
    assert (result / "media" / "metrics.jsonl").exists()
    assert (result / "control" / "summary.json").exists()
    assert (result / "control" / "effective_config.yaml").exists()
    assert (result / "control" / "metrics.jsonl").exists()
    assert (result / "control" / "alerts.jsonl").exists()
    assert (result / "control" / "pattern_events.jsonl").exists()

    # manifest.effective.yaml presente y con el contenido correcto.
    manifest_path = result / "manifest.effective.yaml"
    assert manifest_path.exists()
    assert yaml.safe_load(manifest_path.read_text(encoding="utf-8")) == manifest_effective

    # report/ vacio creado.
    assert (result / "report").is_dir()
    assert list((result / "report").iterdir()) == []


def test_consolidate_experiment_no_copia_detections_pero_lo_referencia(tmp_path):
    media_run_dir = _build_media_run_dir(tmp_path, run_id="media-run-42")
    control_run_dir = _build_control_run_dir(tmp_path)
    dest_root = tmp_path / "runs"

    result = consolidate_experiment(
        "exp_ref",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective={},
        dest_root=dest_root,
    )

    # ADR-014: el crudo detections.jsonl NUNCA se copia dentro del consolidado.
    assert not (result / "media" / "detections.jsonl").exists()

    ref_path = result / "media" / "detections.ref.json"
    assert ref_path.exists()
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert ref == {
        "run_id": "media-run-42",
        "path": str(media_run_dir / "detections.jsonl"),
    }


def test_consolidate_experiment_tolera_artefactos_faltantes(tmp_path):
    # Directorio de media sin metrics.jsonl y sin detections.jsonl.
    media_run_dir = tmp_path / "media_runs" / "media-run-vacio"
    _write(media_run_dir / "summary.json", json.dumps({"status": "succeeded"}))

    # Directorio de control practicamente vacio (falta todo).
    control_run_dir = tmp_path / "control_runs" / "control-run-vacio"
    control_run_dir.mkdir(parents=True)

    dest_root = tmp_path / "runs"

    result = consolidate_experiment(
        "exp_incompleto",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective={"slug": "incompleto"},
        dest_root=dest_root,
    )

    # No debe romper: lo que existe se copia, lo que no, se omite.
    assert (result / "media" / "summary.json").exists()
    assert not (result / "media" / "metrics.jsonl").exists()
    assert not (result / "control" / "summary.json").exists()
    assert not (result / "control" / "alerts.jsonl").exists()

    # La referencia a detections se escribe igual (aunque el archivo no exista
    # fisicamente todavia), con la ruta convencional derivada del run_id.
    ref_path = result / "media" / "detections.ref.json"
    assert ref_path.exists()
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert ref["run_id"] == "media-run-vacio"
    assert ref["path"] == str(media_run_dir / "detections.jsonl")

    # manifest.effective.yaml y report/ siempre se crean.
    assert (result / "manifest.effective.yaml").exists()
    assert (result / "report").is_dir()


def test_consolidate_experiment_prefiere_effective_config_json_si_no_hay_yaml(tmp_path):
    media_run_dir = tmp_path / "media_runs" / "media-json"
    _write(media_run_dir / "effective_config.json", json.dumps({"modelo": "gdino"}))
    control_run_dir = tmp_path / "control_runs" / "control-json"
    control_run_dir.mkdir(parents=True)
    dest_root = tmp_path / "runs"

    result = consolidate_experiment(
        "exp_json",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective={},
        dest_root=dest_root,
    )

    assert (result / "media" / "effective_config.json").exists()


def test_sha256_file_es_deterministico(tmp_path):
    file_a = _write(tmp_path / "a.txt", "contenido identico\n")
    file_b = _write(tmp_path / "b.txt", "contenido identico\n")
    file_c = _write(tmp_path / "c.txt", "contenido distinto\n")

    hash_a = sha256_file(file_a)
    hash_b = sha256_file(file_b)
    hash_c = sha256_file(file_c)

    assert hash_a == hash_b
    assert hash_a != hash_c
    assert hash_a == hashlib.sha256(b"contenido identico\n").hexdigest()


def test_sha256_file_stream_para_archivos_grandes(tmp_path):
    big_file = tmp_path / "grande.bin"
    contenido = b"x" * (5 * 1024 * 1024)  # 5 MiB, fuerza lectura en chunks.
    big_file.write_bytes(contenido)

    assert sha256_file(big_file) == hashlib.sha256(contenido).hexdigest()
