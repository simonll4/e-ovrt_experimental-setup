from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
view = importlib.import_module("materialize_bench_v3_view")


def _synthetic_protocol(tmp_path: Path, images: list[dict[str, object]]) -> tuple[dict, Path]:
    datasets_root = tmp_path / "e-ovrt_datasets"
    coco_path = datasets_root / "datasets" / "processed" / "coco" / "bench.json"
    coco_path.parent.mkdir(parents=True)
    coco = {"images": images, "annotations": [], "categories": []}
    coco_path.write_text(json.dumps(coco, sort_keys=True), encoding="utf-8")

    strata: dict[str, dict[str, int]] = {}
    extensions: dict[str, int] = {}
    for image in images:
        stratum = str(image["stratum"])
        strata.setdefault(stratum, {"images": 0})["images"] += 1
        extension = Path(str(image["file_name"])).suffix.lower()
        extensions[extension] = extensions.get(extension, 0) + 1

    source_paths: dict[str, str] = {}
    source_hashes: dict[str, str] = {}
    for stratum in strata:
        source_relative = f"processed/coco/bench/source_{stratum}.json"
        source_path = datasets_root / "datasets" / source_relative
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(json.dumps({"stratum": stratum}), encoding="utf-8")
        source_paths[stratum] = source_relative
        source_hashes[stratum] = view.sha256_file(source_path)

    source_manifest_path = coco_path.with_name("bench_manifest.json")
    source_manifest = {
        "total_images": len(images),
        "total_annotations": 0,
        "images_by_stratum": {name: data["images"] for name, data in strata.items()},
        "source_paths": source_paths,
        "source_sha256": source_hashes,
        "bench_v3_sha256": view.sha256_file(coco_path),
    }
    source_manifest_path.write_text(json.dumps(source_manifest, sort_keys=True), encoding="utf-8")

    protocol_strata = {
        name: {
            **data,
            "source_coco_repository_relative_path": f"datasets/{source_paths[name]}",
            "source_coco_sha256": source_hashes[name],
        }
        for name, data in strata.items()
    }

    protocol = {
        "schema_version": "eovrt.t1-bench-evaluation-protocol.v1",
        "task_id": "T-FT-031",
        "benchmark": {
            "id": "bench_v3",
            "coco": {
                "repository_relative_path": str(coco_path.relative_to(datasets_root)),
                "sha256": view.sha256_file(coco_path),
                "images": len(images),
                "annotations": 0,
            },
            "source_manifest": {
                "repository_relative_path": str(source_manifest_path.relative_to(datasets_root)),
                "sha256": view.sha256_file(source_manifest_path),
            },
            "strata": protocol_strata,
            "image_extensions": dict(sorted(extensions.items())),
            "flat_view": {
                "expected_entries": len(images),
                "expected_symlinks": len(images),
                "expected_missing": 0,
                "expected_extras": 0,
                "copy_images": False,
                "modify_sources": False,
            },
        },
    }
    return protocol, datasets_root


def _write_sources(datasets_root: Path, images: list[dict[str, object]]) -> dict[str, bytes]:
    original: dict[str, bytes] = {}
    for index, image in enumerate(images):
        relative = str(image["file_name"])
        source = datasets_root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        content = f"immutable-image-{index}".encode()
        source.write_bytes(content)
        original[relative] = content
    return original


def test_materializes_relative_symlinks_and_preserves_sources(tmp_path: Path) -> None:
    images = [
        {"id": 1, "file_name": "datasets/raw/a/one.jpg", "stratum": "alpha"},
        {"id": 2, "file_name": "datasets/raw/b/two.png", "stratum": "beta"},
    ]
    protocol, datasets_root = _synthetic_protocol(tmp_path, images)
    original = _write_sources(datasets_root, images)
    entries = view.build_view_entries(protocol, datasets_root, enforce_frozen_bench=False)
    output = tmp_path / "flat"

    assert view.materialize_view(entries, output) == {
        "entries": 2,
        "symlinks": 2,
        "missing": 0,
        "extras": 0,
    }
    assert view.verify_view(entries, output)["entries"] == 2
    assert sorted(child.name for child in output.iterdir()) == ["one.jpg", "two.png"]
    for child in output.iterdir():
        assert child.is_symlink()
        assert not os.readlink(child).startswith("/")
    for relative, content in original.items():
        assert (datasets_root / relative).read_bytes() == content


@pytest.mark.parametrize("mutation", ["missing", "extra", "regular_file"])
def test_verify_rejects_missing_extra_or_non_symlink(tmp_path: Path, mutation: str) -> None:
    images = [
        {"id": 1, "file_name": "datasets/raw/a/one.jpg", "stratum": "alpha"},
        {"id": 2, "file_name": "datasets/raw/b/two.png", "stratum": "beta"},
    ]
    protocol, datasets_root = _synthetic_protocol(tmp_path, images)
    _write_sources(datasets_root, images)
    entries = view.build_view_entries(protocol, datasets_root, enforce_frozen_bench=False)
    output = tmp_path / "flat"
    view.materialize_view(entries, output)

    if mutation == "missing":
        (output / "one.jpg").unlink()
    elif mutation == "extra":
        (output / "extra.jpg").symlink_to("../unrelated.jpg")
    else:
        (output / "one.jpg").unlink()
        (output / "one.jpg").write_bytes(b"copied-image")

    with pytest.raises(view.ProtocolError):
        view.verify_view(entries, output)


def test_rejects_flat_basename_collision(tmp_path: Path) -> None:
    images = [
        {"id": 1, "file_name": "datasets/raw/a/same.jpg", "stratum": "alpha"},
        {"id": 2, "file_name": "datasets/raw/b/same.jpg", "stratum": "alpha"},
    ]
    protocol, datasets_root = _synthetic_protocol(tmp_path, images)
    _write_sources(datasets_root, images)

    with pytest.raises(view.ProtocolError, match="basename collision"):
        view.build_view_entries(protocol, datasets_root, enforce_frozen_bench=False)


def test_rejects_missing_source(tmp_path: Path) -> None:
    images = [{"id": 1, "file_name": "datasets/raw/missing.jpg", "stratum": "alpha"}]
    protocol, datasets_root = _synthetic_protocol(tmp_path, images)

    with pytest.raises(view.ProtocolError, match="source is missing"):
        view.build_view_entries(protocol, datasets_root, enforce_frozen_bench=False)


def test_rejects_tampered_bench_source_manifest(tmp_path: Path) -> None:
    images = [{"id": 1, "file_name": "datasets/raw/one.jpg", "stratum": "alpha"}]
    protocol, datasets_root = _synthetic_protocol(tmp_path, images)
    _write_sources(datasets_root, images)
    source_manifest = datasets_root / protocol["benchmark"]["source_manifest"][
        "repository_relative_path"
    ]
    source_manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(view.ProtocolError, match="source manifest SHA-256 mismatch"):
        view.build_view_entries(protocol, datasets_root, enforce_frozen_bench=False)


def test_frozen_protocol_requires_exact_bench_v3_contract(tmp_path: Path) -> None:
    images = [{"id": 1, "file_name": "datasets/raw/one.jpg", "stratum": "alpha"}]
    protocol, _ = _synthetic_protocol(tmp_path, images)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(view.ProtocolError, match="frozen BENCH v3 SHA-256"):
        view.load_protocol(protocol_path)
