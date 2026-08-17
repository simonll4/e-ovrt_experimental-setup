#!/usr/bin/env python3
"""Materialize and verify a flat, read-only BENCH v3 view using relative symlinks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPECTED_BENCH_SHA256 = "4557024ecc4ee497ab1fad01d6819206395c10fd794010ed8c1d9198b19a4462"
EXPECTED_TOTAL = 6477
EXPECTED_STRATA = {
    "bench_obra_test": 62,
    "bench_obra_val": 85,
    "chv": 1330,
    "shel5k": 5000,
}
SUPPORTED_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


class ProtocolError(RuntimeError):
    """The protocol, BENCH source, or derived view violates its frozen contract."""


@dataclass(frozen=True)
class ViewEntry:
    name: str
    source: Path
    stratum: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path, *, enforce_frozen_bench: bool = True) -> dict[str, Any]:
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"cannot load protocol {path}: {exc}") from exc

    if protocol.get("schema_version") != "eovrt.t1-bench-evaluation-protocol.v1":
        raise ProtocolError("unexpected protocol schema_version")
    if protocol.get("task_id") != "T-FT-031":
        raise ProtocolError("protocol is not bound to T-FT-031")

    try:
        benchmark = protocol["benchmark"]
        coco = benchmark["coco"]
        flat_view = benchmark["flat_view"]
        strata = {name: data["images"] for name, data in benchmark["strata"].items()}
    except (KeyError, TypeError) as exc:
        raise ProtocolError(f"protocol is missing benchmark contract field: {exc}") from exc

    if benchmark.get("id") != "bench_v3":
        raise ProtocolError("protocol benchmark id must be bench_v3")
    if coco.get("images") != flat_view.get("expected_entries"):
        raise ProtocolError("COCO image count and flat-view expected_entries differ")
    if sum(strata.values()) != coco.get("images"):
        raise ProtocolError("stratum image counts do not sum to the COCO image count")

    if enforce_frozen_bench:
        if coco.get("sha256") != EXPECTED_BENCH_SHA256:
            raise ProtocolError("protocol does not reference the frozen BENCH v3 SHA-256")
        if coco.get("images") != EXPECTED_TOTAL:
            raise ProtocolError(f"protocol must require exactly {EXPECTED_TOTAL} images")
        if strata != EXPECTED_STRATA:
            raise ProtocolError(f"protocol strata differ from frozen BENCH v3: {strata!r}")
        if flat_view.get("expected_symlinks") != EXPECTED_TOTAL:
            raise ProtocolError(f"protocol must require exactly {EXPECTED_TOTAL} symlinks")
        if flat_view.get("expected_missing") != 0 or flat_view.get("expected_extras") != 0:
            raise ProtocolError("protocol must require zero missing entries and zero extras")
        if flat_view.get("copy_images") is not False:
            raise ProtocolError("protocol must forbid copying BENCH images")
        if flat_view.get("modify_sources") is not False:
            raise ProtocolError("protocol must forbid modifying BENCH sources")

    return protocol


def _safe_repository_file(datasets_root: Path, relative_path: object, *, label: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ProtocolError(f"invalid {label} path: {relative_path!r}")
    relative = Path(relative_path)
    if relative.is_absolute():
        raise ProtocolError(f"absolute {label} path is forbidden: {relative_path}")

    root = datasets_root.resolve()
    source = (root / relative).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ProtocolError(f"{label} path escapes datasets root: {relative_path}") from exc
    if not source.is_file():
        raise ProtocolError(f"{label} is missing or not a file: {source}")
    return source


def _safe_source(datasets_root: Path, file_name: object) -> Path:
    source = _safe_repository_file(datasets_root, file_name, label="BENCH source")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ProtocolError(f"unsupported BENCH image extension: {source.name}")
    return source


def verify_source_manifest(protocol: dict[str, Any], datasets_root: Path) -> None:
    benchmark = protocol["benchmark"]
    coco_contract = benchmark["coco"]
    contract = benchmark["source_manifest"]
    manifest_path = _safe_repository_file(
        datasets_root,
        contract["repository_relative_path"],
        label="BENCH source manifest",
    )
    actual_sha = sha256_file(manifest_path)
    if actual_sha != contract["sha256"]:
        raise ProtocolError(
            "BENCH source manifest SHA-256 mismatch: "
            f"expected {contract['sha256']}, got {actual_sha}"
        )

    try:
        source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"cannot parse BENCH source manifest {manifest_path}: {exc}") from exc

    expected_strata = {
        name: data["images"] for name, data in benchmark["strata"].items()
    }
    if source_manifest.get("total_images") != coco_contract["images"]:
        raise ProtocolError("BENCH source manifest total_images differs from the protocol")
    if source_manifest.get("total_annotations") != coco_contract["annotations"]:
        raise ProtocolError("BENCH source manifest total_annotations differs from the protocol")
    if source_manifest.get("images_by_stratum") != expected_strata:
        raise ProtocolError("BENCH source manifest strata differ from the protocol")
    if source_manifest.get("bench_v3_sha256") != coco_contract["sha256"]:
        raise ProtocolError("BENCH source manifest references a different consolidated COCO hash")

    source_paths = source_manifest.get("source_paths")
    source_hashes = source_manifest.get("source_sha256")
    if not isinstance(source_paths, dict) or set(source_paths) != set(expected_strata):
        raise ProtocolError("BENCH source manifest source_paths do not cover exactly all strata")
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(expected_strata):
        raise ProtocolError("BENCH source manifest source_sha256 does not cover exactly all strata")

    for stratum, data in benchmark["strata"].items():
        repository_relative = (Path("datasets") / source_paths[stratum]).as_posix()
        if repository_relative != data["source_coco_repository_relative_path"]:
            raise ProtocolError(f"source COCO path mismatch for stratum {stratum}")
        if source_hashes[stratum] != data["source_coco_sha256"]:
            raise ProtocolError(f"source COCO declared hash mismatch for stratum {stratum}")
        source_path = _safe_repository_file(
            datasets_root,
            repository_relative,
            label=f"BENCH source COCO {stratum}",
        )
        actual_source_sha = sha256_file(source_path)
        if actual_source_sha != source_hashes[stratum]:
            raise ProtocolError(
                f"source COCO SHA-256 mismatch for {stratum}: "
                f"expected {source_hashes[stratum]}, got {actual_source_sha}"
            )


def build_view_entries(
    protocol: dict[str, Any],
    datasets_root: Path,
    *,
    enforce_frozen_bench: bool = True,
) -> list[ViewEntry]:
    benchmark = protocol["benchmark"]
    coco_contract = benchmark["coco"]
    verify_source_manifest(protocol, datasets_root)
    coco_path = _safe_repository_file(
        datasets_root,
        coco_contract["repository_relative_path"],
        label="BENCH COCO",
    )

    actual_sha = sha256_file(coco_path)
    if actual_sha != coco_contract["sha256"]:
        raise ProtocolError(
            f"BENCH COCO SHA-256 mismatch: expected {coco_contract['sha256']}, got {actual_sha}"
        )

    try:
        coco = json.loads(coco_path.read_text(encoding="utf-8"))
        images = coco["images"]
        annotations = coco["annotations"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ProtocolError(f"cannot parse BENCH COCO {coco_path}: {exc}") from exc

    expected_total = coco_contract["images"]
    if len(images) != expected_total:
        raise ProtocolError(f"BENCH image count mismatch: expected {expected_total}, got {len(images)}")
    if len(annotations) != coco_contract["annotations"]:
        raise ProtocolError(
            "BENCH annotation count mismatch: "
            f"expected {coco_contract['annotations']}, got {len(annotations)}"
        )

    entries: list[ViewEntry] = []
    image_ids: set[object] = set()
    file_names: set[str] = set()
    basenames: set[str] = set()
    strata: Counter[str] = Counter()
    extensions: Counter[str] = Counter()

    for image in images:
        if not isinstance(image, dict):
            raise ProtocolError("every COCO image entry must be an object")
        image_id = image.get("id")
        if image_id in image_ids:
            raise ProtocolError(f"duplicate COCO image id: {image_id!r}")
        image_ids.add(image_id)

        file_name = image.get("file_name")
        if not isinstance(file_name, str):
            raise ProtocolError(f"invalid COCO file_name: {file_name!r}")
        if file_name in file_names:
            raise ProtocolError(f"duplicate COCO file_name: {file_name}")
        file_names.add(file_name)

        basename = Path(file_name).name
        if not basename or basename in {".", ".."}:
            raise ProtocolError(f"invalid image basename: {file_name}")
        if basename in basenames:
            raise ProtocolError(f"flat-view basename collision: {basename}")
        basenames.add(basename)

        stratum = image.get("stratum")
        if not isinstance(stratum, str) or stratum not in benchmark["strata"]:
            raise ProtocolError(f"unknown or missing stratum for {file_name}: {stratum!r}")
        strata[stratum] += 1

        source = _safe_source(datasets_root, file_name)
        extensions[source.suffix.lower()] += 1
        entries.append(ViewEntry(name=basename, source=source, stratum=stratum))

    expected_strata = {
        name: data["images"] for name, data in benchmark["strata"].items()
    }
    if dict(strata) != expected_strata:
        raise ProtocolError(
            f"BENCH stratum counts mismatch: expected {expected_strata!r}, got {dict(strata)!r}"
        )

    expected_extensions = benchmark.get("image_extensions")
    if expected_extensions is not None and dict(sorted(extensions.items())) != expected_extensions:
        raise ProtocolError(
            "BENCH extension counts mismatch: "
            f"expected {expected_extensions!r}, got {dict(sorted(extensions.items()))!r}"
        )

    if enforce_frozen_bench:
        if len(entries) != EXPECTED_TOTAL:
            raise ProtocolError(f"frozen view must contain exactly {EXPECTED_TOTAL} entries")
        if dict(strata) != EXPECTED_STRATA:
            raise ProtocolError("frozen view does not match the four canonical strata")

    return sorted(entries, key=lambda item: item.name)


def verify_view(entries: list[ViewEntry], output: Path) -> dict[str, int]:
    if output.is_symlink() or not output.is_dir():
        raise ProtocolError(f"flat view is missing or is not a real directory: {output}")

    expected = {entry.name: entry for entry in entries}
    actual = {child.name: child for child in output.iterdir()}
    missing = sorted(set(expected) - set(actual))
    extras = sorted(set(actual) - set(expected))
    if missing or extras:
        raise ProtocolError(
            "flat-view membership mismatch: "
            f"missing={len(missing)} {missing[:3]!r}, extras={len(extras)} {extras[:3]!r}"
        )

    for name, entry in expected.items():
        link = actual[name]
        if not link.is_symlink():
            raise ProtocolError(f"flat-view entry is not a symlink: {link}")
        try:
            target = link.resolve(strict=True)
        except OSError as exc:
            raise ProtocolError(f"broken flat-view symlink: {link}: {exc}") from exc
        if target != entry.source.resolve():
            raise ProtocolError(
                f"flat-view symlink target mismatch for {name}: expected {entry.source}, got {target}"
            )

    return {
        "entries": len(actual),
        "symlinks": len(actual),
        "missing": 0,
        "extras": 0,
    }


def materialize_view(entries: list[ViewEntry], output: Path) -> dict[str, int]:
    if os.path.lexists(output):
        return verify_view(entries, output)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if os.path.lexists(temporary):
        raise ProtocolError(f"refusing to overwrite stale temporary view: {temporary}")

    created_temporary = False
    try:
        temporary.mkdir()
        created_temporary = True
        for entry in entries:
            relative_target = os.path.relpath(entry.source, start=temporary)
            (temporary / entry.name).symlink_to(relative_target)
        result = verify_view(entries, temporary)
        if os.path.lexists(output):
            raise ProtocolError(f"flat view appeared concurrently; refusing to replace it: {output}")
        temporary.rename(output)
        created_temporary = False
        return result
    finally:
        if created_temporary and temporary.is_dir() and not temporary.is_symlink():
            shutil.rmtree(temporary)


def default_paths() -> tuple[Path, Path, Path]:
    finetuning_root = Path(__file__).resolve().parents[1]
    workspace_root = finetuning_root.parent.parent
    return (
        finetuning_root / "manifests" / "t1_yoloe26s_bench_v3_protocol.json",
        workspace_root / "e-ovrt_datasets",
        finetuning_root / "cache" / "bench_v3_flat",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_protocol, default_datasets, default_output = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=default_protocol)
    parser.add_argument("--datasets-root", type=Path, default=default_datasets)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify an existing view without creating directories or symlinks",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        protocol = load_protocol(args.protocol)
        entries = build_view_entries(protocol, args.datasets_root)
        result = verify_view(entries, args.output) if args.verify_only else materialize_view(
            entries, args.output
        )
    except ProtocolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result.update(
        {
            "benchmark_images": len(entries),
            "materialization": "relative_symlink",
        }
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
