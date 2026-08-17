#!/usr/bin/env python3
"""Inventory fine-tuning candidates and prove disjunction from frozen bench_v3."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from finetuning_data import (
    APPROVED_SOURCES,
    DEFAULT_BENCH_JSON,
    DEFAULT_BENCH_MANIFEST,
    SOURCE_CONTRACTS,
    assign_components,
    class_instance_counts,
    lineage_annotation_conflicts,
    lineage_split_overlap,
    load_bench_records,
    load_candidate_records,
    mark_bench_overlaps,
    records_by_source,
    refine_ppe_lineages,
    workspace_default_datasets_root,
    write_inventory,
    write_json,
)
from PIL import __version__ as pillow_version


def build_parser() -> argparse.ArgumentParser:
    script = Path(__file__)
    manifests = script.resolve().parents[1] / "manifests"
    parser = argparse.ArgumentParser(
        description="Audita linajes, hashes y cruces de CSS+PPE contra bench_v3."
    )
    parser.add_argument(
        "--datasets-root",
        type=Path,
        default=workspace_default_datasets_root(script),
        help="Raíz del repositorio e-ovrt_datasets.",
    )
    parser.add_argument("--bench-json", type=Path, default=DEFAULT_BENCH_JSON)
    parser.add_argument("--bench-manifest", type=Path, default=DEFAULT_BENCH_MANIFEST)
    parser.add_argument("--ahash-distance", type=int, default=2, choices=(0, 1, 2))
    parser.add_argument("--dhash-distance", type=int, default=2)
    parser.add_argument("--pixel-mae-threshold", type=float, default=2.0)
    parser.add_argument(
        "--inventory-out",
        type=Path,
        default=manifests / "finetuning_v1.inventory.csv",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=manifests / "finetuning_v1.audit.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    datasets_root = args.datasets_root.resolve()
    candidates = load_candidate_records(datasets_root)
    bench, bench_sha256 = load_bench_records(
        datasets_root,
        bench_json=args.bench_json,
        bench_manifest=args.bench_manifest,
    )
    lineage_parameters = {
        "ahash_max_hamming_distance": 4,
        "dhash_max_hamming_distance": 4,
        "gray_pixel_mae_max_0_255": 5.0,
    }
    refined = refine_ppe_lineages(
        [*candidates, *bench],
        ahash_distance=lineage_parameters["ahash_max_hamming_distance"],
        dhash_distance=lineage_parameters["dhash_max_hamming_distance"],
        pixel_mae_threshold=lineage_parameters["gray_pixel_mae_max_0_255"],
    )
    grouped = assign_components(
        refined,
        ahash_distance=args.ahash_distance,
        dhash_distance=args.dhash_distance,
        pixel_mae_threshold=args.pixel_mae_threshold,
    )
    audited = mark_bench_overlaps(grouped)
    audited_candidates = [record for record in audited if record.role == "candidate"]
    excluded = [record for record in audited_candidates if record.bench_overlap]
    clean = [record for record in audited_candidates if not record.bench_overlap]
    reasons = Counter(record.bench_overlap_reason for record in excluded)
    rows_by_component: dict[str, list] = {}
    for record in audited:
        rows_by_component.setdefault(record.component_id, []).append(record)
    bench_matches = []
    for component_id, rows in sorted(rows_by_component.items()):
        candidate_rows = [row for row in rows if row.role == "candidate" and row.bench_overlap]
        bench_rows = [row for row in rows if row.role == "bench"]
        if candidate_rows and bench_rows:
            bench_matches.append(
                {
                    "component_id": component_id,
                    "candidate_images": sorted(row.image_path for row in candidate_rows),
                    "candidate_lineages": sorted({row.lineage_id for row in candidate_rows}),
                    "bench_images": sorted(row.image_path for row in bench_rows),
                    "bench_datasets": sorted({row.dataset_id for row in bench_rows}),
                }
            )

    report = {
        "schema_version": "eovrt.finetuning-audit.v1",
        "inputs": {
            "candidate_sources": [f"{dataset}/{split}" for dataset, split in APPROVED_SOURCES],
            "bench_json": args.bench_json.as_posix(),
            "bench_manifest": args.bench_manifest.as_posix(),
            "source_contracts": SOURCE_CONTRACTS,
        },
        "parameters": {
            "ahash": "average_hash_64",
            "ahash_max_hamming_distance": args.ahash_distance,
            "dhash": "difference_hash_64",
            "dhash_max_hamming_distance": args.dhash_distance,
            "gray_thumbnail": "16x16_luma_lanczos",
            "gray_pixel_mae_max_0_255": args.pixel_mae_threshold,
            "perceptual_match_rule": "both_hash_distances_and_pixel_mae_must_pass",
            "pillow_version": pillow_version,
            "ppe_lineage_refinement": {
                **lineage_parameters,
                "rule": "split reused source stems into visually compatible components",
            },
        },
        "benchmark": {
            "images": len(bench),
            "sha256": bench_sha256,
            "unchanged": True,
        },
        "candidates": {
            "images": len(audited_candidates),
            "lineages": len({record.lineage_id for record in audited_candidates}),
            "components": len({record.component_id for record in audited_candidates}),
            "class_instances": class_instance_counts(audited_candidates),
            "by_source": records_by_source(audited_candidates),
        },
        "source_split_overlap": {
            "construction_site_safety": lineage_split_overlap(
                audited_candidates, "construction_site_safety"
            ),
            "ppe_siabar": lineage_split_overlap(audited_candidates, "ppe_siabar"),
        },
        "source_annotation_conflicts": {
            "ppe_siabar": lineage_annotation_conflicts(
                audited_candidates, "ppe_siabar"
            )
        },
        "bench_leakage": {
            "candidate_images_excluded": len(excluded),
            "candidate_lineages_excluded": len({record.lineage_id for record in excluded}),
            "candidate_components_excluded": len(
                {record.component_id for record in excluded}
            ),
            "by_reason": dict(sorted(reasons.items())),
            "lineages": sorted({record.lineage_id for record in excluded}),
            "matches": bench_matches,
        },
        "eligible_after_bench_guard": {
            "images": len(clean),
            "lineages": len({record.lineage_id for record in clean}),
            "components": len({record.component_id for record in clean}),
            "class_instances": class_instance_counts(clean),
        },
    }
    write_inventory(args.inventory_out, audited_candidates)
    write_json(args.report_out, report)
    print(f"inventory={args.inventory_out}")
    print(f"report={args.report_out}")
    print(
        f"candidates={len(audited_candidates)} excluded_by_bench={len(excluded)} eligible={len(clean)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
