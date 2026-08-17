#!/usr/bin/env python3
"""Materialize the approved finetuning_v1 split as a portable YOLO payload."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLASSES = ("person", "helmet", "vest", "bare_head")
PROMPTS = ("person", "helmet", "vest", "bare head")
SPLIT_SCHEMA = "eovrt.finetuning-split.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"source path escapes datasets root: {relative}") from error
    return candidate


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("split manifest is empty")
    if any(row.get("schema_version") != SPLIT_SCHEMA for row in rows):
        raise ValueError(f"split manifest must use {SPLIT_SCHEMA}")
    return [row for row in rows if row["included"] == "true"]


def _write_hash_manifest(root: Path) -> None:
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "payload.sha256":
            continue
        entries.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "payload.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


def verify_payload(root: Path) -> None:
    hash_manifest = root / "payload.sha256"
    if not hash_manifest.is_file():
        raise ValueError(f"missing {hash_manifest}")
    for line_number, raw_line in enumerate(
        hash_manifest.read_text(encoding="utf-8").splitlines(), 1
    ):
        expected, separator, relative = raw_line.partition("  ")
        if not separator or len(expected) != 64:
            raise ValueError(f"{hash_manifest}:{line_number}: malformed hash row")
        target = (root / relative).resolve()
        try:
            target.relative_to(root.resolve())
        except ValueError as error:
            raise ValueError(f"hash path escapes payload: {relative}") from error
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"payload hash mismatch: {relative}")
    symlinks = [path for path in root.rglob("*") if path.is_symlink()]
    if symlinks:
        raise ValueError(f"payload contains symlinks: {symlinks[:3]}")


def materialize(
    *,
    split_manifest: Path,
    split_summary: Path,
    datasets_root: Path,
    output: Path,
) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing payload: {output}")
    summary = json.loads(split_summary.read_text(encoding="utf-8"))
    if summary.get("schema_version") != "eovrt.finetuning-summary.v1":
        raise ValueError("unsupported split summary schema")
    actual_split_hash = sha256_file(split_manifest)
    if actual_split_hash != summary["split_manifest_sha256"]:
        raise ValueError("split manifest hash does not match finetuning_v1 summary")

    rows = _read_rows(split_manifest)
    expected_images = {
        split: int(summary["splits"][split]["images"]) for split in ("train", "val")
    }
    actual_images = Counter(row["final_split"] for row in rows)
    if dict(actual_images) != expected_images:
        raise ValueError(f"selected split counts {dict(actual_images)} != {expected_images}")

    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary payload exists: {temporary}")
    temporary.mkdir(parents=True)
    copied_rows: list[dict[str, object]] = []
    total_bytes = 0
    try:
        for row in sorted(rows, key=lambda item: item["record_id"]):
            split = row["final_split"]
            if split not in {"train", "val"}:
                raise ValueError(f"included row has invalid split: {split}")
            image_source = _safe_source(datasets_root, row["image_path"])
            label_source = _safe_source(datasets_root, row["label_path"])
            if sha256_file(image_source) != row["sha256"]:
                raise ValueError(f"image changed since audit: {row['record_id']}")
            if sha256_file(label_source) != row["label_sha256"]:
                raise ValueError(f"label changed since audit: {row['record_id']}")

            nested = Path(row["dataset_id"]) / row["source_split"]
            image_relative = Path("images") / split / nested / image_source.name
            label_relative = Path("labels") / split / nested / f"{image_source.stem}.txt"
            image_target = temporary / image_relative
            label_target = temporary / label_relative
            if image_target.exists() or label_target.exists():
                raise ValueError(f"destination collision for {row['record_id']}")
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_source, image_target)
            shutil.copy2(label_source, label_target)
            total_bytes += image_target.stat().st_size + label_target.stat().st_size
            copied_rows.append(
                {
                    "record_id": row["record_id"],
                    "split": split,
                    "image": image_relative.as_posix(),
                    "label": label_relative.as_posix(),
                    "image_sha256": row["sha256"],
                    "label_sha256": row["label_sha256"],
                    "component_id": row["component_id"],
                }
            )

        yaml_lines = [
            "train: images/train",
            "val: images/val",
            "nc: 4",
            "names:",
            *(f"  {index}: {name}" for index, name in enumerate(PROMPTS)),
        ]
        (temporary / "data.yaml").write_text(
            "\n".join(yaml_lines) + "\n", encoding="utf-8"
        )
        payload_manifest = {
            "schema_version": "eovrt.finetuning-payload.v1",
            "name": "finetuning_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_split_manifest_sha256": actual_split_hash,
            "source_summary_sha256": sha256_file(split_summary),
            "bench_v3_sha256": summary["bench_v3_sha256"],
            "classes": list(CLASSES),
            "prompts": list(PROMPTS),
            "images": expected_images,
            "class_instances": {
                split: summary["splits"][split]["class_instances"]
                for split in ("train", "val")
            },
            "payload_bytes": total_bytes,
            "files": copied_rows,
            "test_contract": summary["test_contract"],
        }
        (temporary / "payload.json").write_text(
            json.dumps(payload_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_hash_manifest(temporary)
        verify_payload(temporary)
        temporary.replace(output)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return payload_manifest


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    workspace = root.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=root / "manifests" / "finetuning_v1.split.csv",
    )
    parser.add_argument(
        "--split-summary",
        type=Path,
        default=root / "manifests" / "finetuning_v1.summary.json",
    )
    parser.add_argument(
        "--datasets-root", type=Path, default=workspace / "e-ovrt_datasets"
    )
    parser.add_argument(
        "--output", type=Path, default=root / "data" / "payloads" / "finetuning_v1"
    )
    parser.add_argument("--verify-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verify_only:
        verify_payload(args.output)
        print(f"payload_ok={args.output}")
        return 0
    result = materialize(
        split_manifest=args.split_manifest,
        split_summary=args.split_summary,
        datasets_root=args.datasets_root,
        output=args.output,
    )
    print(
        f"payload={args.output} train={result['images']['train']} "
        f"val={result['images']['val']} bytes={result['payload_bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

