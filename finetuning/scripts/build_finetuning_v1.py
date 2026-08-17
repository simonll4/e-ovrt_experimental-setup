#!/usr/bin/env python3
"""Build the approved group-aware finetuning_v1 train/val manifest."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from finetuning_data import (
    CANONICAL_CLASSES,
    SOURCE_CONTRACTS,
    SPLIT_SCHEMA_VERSION,
    choose_representatives,
    class_instance_counts,
    make_split_groups,
    read_inventory,
    select_validation_groups,
    sha256_file,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    manifests = Path(__file__).resolve().parents[1] / "manifests"
    parser = argparse.ArgumentParser(
        description="Genera el split train/val finetuning_v1 desde el inventario auditado."
    )
    parser.add_argument(
        "--inventory",
        type=Path,
        default=manifests / "finetuning_v1.inventory.csv",
    )
    parser.add_argument(
        "--audit-report",
        type=Path,
        default=manifests / "finetuning_v1.audit.json",
    )
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--manifest-out",
        type=Path,
        default=manifests / "finetuning_v1.split.csv",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=manifests / "finetuning_v1.summary.json",
    )
    return parser


def _split_counts(rows: list[dict[str, str]], split: str) -> dict[str, object]:
    selected = [row for row in rows if row["included"] == "true" and row["final_split"] == split]
    class_counts = {
        name: sum(int(row[f"instances_{name}"]) for row in selected)
        for name in CANONICAL_CLASSES
    }
    return {
        "images": len(selected),
        "groups": len({row["component_id"] for row in selected}),
        "datasets": dict(sorted(Counter(row["dataset_id"] for row in selected).items())),
        "class_instances": class_counts,
    }


def _write_split_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    audit = json.loads(args.audit_report.read_text(encoding="utf-8"))
    if audit.get("schema_version") != "eovrt.finetuning-audit.v1":
        raise ValueError("unsupported or missing audit report schema")
    if not audit.get("benchmark", {}).get("unchanged"):
        raise ValueError("audit did not prove an unchanged bench_v3")

    inventory = read_inventory(args.inventory)
    candidates = [record for record in inventory if record.role == "candidate"]
    selected, dedupe_exclusions, dedupe_stats = choose_representatives(candidates)
    groups = make_split_groups(selected)
    target_val_groups = max(1, round(len(groups) * args.val_ratio))
    val_groups = select_validation_groups(
        groups,
        val_ratio=args.val_ratio,
        seed=args.seed,
        target_group_count=target_val_groups,
    )

    selected_ids = {record.record_id for record in selected}
    split_by_record = {
        record.record_id: ("val" if record.component_id in val_groups else "train")
        for record in selected
    }
    output_rows: list[dict[str, str]] = []
    for record in sorted(candidates, key=lambda row: row.record_id):
        if record.bench_overlap:
            included = False
            final_split = "excluded"
            exclusion_reason = record.bench_overlap_reason
        elif record.record_id in dedupe_exclusions:
            included = False
            final_split = "excluded"
            exclusion_reason = dedupe_exclusions[record.record_id]
        elif record.record_id in selected_ids:
            included = True
            final_split = split_by_record[record.record_id]
            exclusion_reason = ""
        else:
            raise RuntimeError(f"unclassified candidate row {record.record_id}")
        row = {
            "schema_version": SPLIT_SCHEMA_VERSION,
            "record_id": record.record_id,
            "dataset_id": record.dataset_id,
            "source_url": SOURCE_CONTRACTS[record.dataset_id]["source_url"],
            "source_version": SOURCE_CONTRACTS[record.dataset_id]["source_version"],
            "license_spdx": SOURCE_CONTRACTS[record.dataset_id]["license_spdx"],
            "source_split": record.source_split,
            "image_path": record.image_path,
            "label_path": record.label_path,
            "label_sha256": record.label_sha256,
            "sha256": record.sha256,
            "source_key": record.source_key,
            "lineage_id": record.lineage_id,
            "component_id": record.component_id,
            "ahash64": record.ahash64,
            "dhash64": record.dhash64,
            "included": "true" if included else "false",
            "final_split": final_split,
            "exclusion_reason": exclusion_reason,
        }
        row.update(
            {
                f"instances_{name}": str(record.class_counts[index])
                for index, name in enumerate(CANONICAL_CLASSES)
            }
        )
        output_rows.append(row)

    train_components = {
        row["component_id"]
        for row in output_rows
        if row["included"] == "true" and row["final_split"] == "train"
    }
    val_components = {
        row["component_id"]
        for row in output_rows
        if row["included"] == "true" and row["final_split"] == "val"
    }
    if train_components & val_components:
        raise ValueError("a connected component was assigned to both train and val")
    val_counts = _split_counts(output_rows, "val")["class_instances"]
    missing_classes = [name for name in CANONICAL_CLASSES if val_counts[name] == 0]
    if missing_classes:
        raise ValueError(f"val has no instances for: {', '.join(missing_classes)}")

    selected_output = [row for row in output_rows if row["included"] == "true"]
    if any(row["exclusion_reason"].startswith("bench_") for row in selected_output):
        raise ValueError("a bench-overlap row was selected")
    selected_inventory = [
        record for record in selected if record.record_id in split_by_record
    ]
    selected_bench_overlap = sum(record.bench_overlap for record in selected_inventory)
    if selected_bench_overlap:
        raise ValueError(f"{selected_bench_overlap} selected rows overlap bench_v3")

    _write_split_manifest(args.manifest_out, output_rows)
    manifest_sha256 = sha256_file(args.manifest_out)
    exclusions = Counter(
        row["exclusion_reason"] for row in output_rows if row["included"] == "false"
    )
    selected_records = selected_inventory
    summary = {
        "schema_version": "eovrt.finetuning-summary.v1",
        "decision": "D-FT-11",
        "name": "finetuning_v1",
        "seed": args.seed,
        "target_val_group_ratio": args.val_ratio,
        "inventory_sha256": sha256_file(args.inventory),
        "audit_report_sha256": sha256_file(args.audit_report),
        "split_manifest_sha256": manifest_sha256,
        "bench_v3_sha256": audit["benchmark"]["sha256"],
        "sources": SOURCE_CONTRACTS,
        "test_contract": "bench_v3 external final evaluation only; absent from this manifest",
        "candidate_images": len(candidates),
        "selected_images": len(selected_records),
        "selected_class_instances": class_instance_counts(selected_records),
        "excluded_images": sum(exclusions.values()),
        "exclusions": dict(sorted(exclusions.items())),
        "deduplication": dedupe_stats,
        "ppe_representative_policy": (
            "one image per refined visual lineage; highest canonical annotation count, "
            "then source split train-val-test, then path"
        ),
        "splits": {
            "train": _split_counts(output_rows, "train"),
            "val": _split_counts(output_rows, "val"),
        },
        "gates": {
            "bench_rows_in_manifest": 0,
            "bench_overlap_selected": selected_bench_overlap,
            "shared_components_train_val": 0,
            "val_all_canonical_classes": True,
        },
    }
    write_json(args.summary_out, summary)
    print(f"manifest={args.manifest_out}")
    print(f"summary={args.summary_out}")
    print(
        "selected={} train={} val={} excluded={}".format(
            len(selected_records),
            summary["splits"]["train"]["images"],
            summary["splits"]["val"]["images"],
            summary["excluded_images"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
