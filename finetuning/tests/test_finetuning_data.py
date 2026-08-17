from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from finetuning_data import (
    ImageRecord,
    SplitGroup,
    assign_components,
    choose_representatives,
    hamming_distance,
    image_hashes,
    make_lineage_id,
    mark_bench_overlaps,
    normalize_roboflow_stem,
    read_inventory,
    refine_ppe_lineages,
    select_validation_groups,
    write_inventory,
)


def _record(
    record_id: str,
    *,
    role: str = "candidate",
    dataset: str = "ppe_siabar",
    split: str = "train",
    sha: str | None = None,
    lineage: str | None = None,
    label_sha: str = "label-default",
    ahash: str = "0000000000000000",
    dhash: str = "0000000000000000",
    pixels: bytes = bytes([0]) * 256,
    counts: tuple[int, int, int, int] = (1, 1, 1, 0),
) -> ImageRecord:
    return ImageRecord(
        record_id=record_id,
        role=role,
        dataset_id=dataset,
        source_split=split,
        image_path=f"datasets/raw/{dataset}/{split}/images/{record_id}.jpg",
        label_path=f"labels/{record_id}.txt" if role == "candidate" else "",
        label_sha256=label_sha if role == "candidate" else "",
        sha256=sha or f"sha-{record_id}",
        source_key=lineage or f"{dataset}:{record_id}",
        lineage_id=lineage or f"{dataset}:{record_id}",
        ahash64=ahash,
        dhash64=dhash,
        class_counts=counts,
        perceptual_gray16=pixels,
    )


def test_normalizes_roboflow_lineage() -> None:
    name = "youtube-51_jpg.rf.1234567890abcdef1234567890abcdef.jpg"
    assert normalize_roboflow_stem(name) == "youtube-51_jpg"
    assert make_lineage_id("construction_site_safety", name) == (
        "construction_site_safety:youtube-51_jpg"
    )


def test_non_roboflow_filename_keeps_stem() -> None:
    assert normalize_roboflow_stem("hard_hat_workers994.png") == "hard_hat_workers994"


def test_image_hashes_are_stable_across_lossless_reencoding(tmp_path: Path) -> None:
    image = Image.new("RGB", (32, 32), "white")
    for coordinate in range(32):
        image.putpixel((coordinate, coordinate), (0, 0, 0))
    first = tmp_path / "one.png"
    second = tmp_path / "two.bmp"
    image.save(first)
    image.save(second)
    assert image_hashes(first) == image_hashes(second)
    assert hamming_distance(image_hashes(first)[0], image_hashes(second)[0]) == 0


def test_components_join_lineage_and_perceptual_neighbors() -> None:
    records = [
        _record("a", lineage="ppe_siabar:source", ahash="0", dhash="0"),
        _record("b", split="val", lineage="ppe_siabar:source", ahash="ffff", dhash="ffff"),
        _record("c", ahash="1", dhash="1"),
    ]
    grouped = assign_components(records, ahash_distance=2, dhash_distance=2)
    assert len({record.component_id for record in grouped}) == 1


def test_hash_collision_without_low_pixel_mae_does_not_join() -> None:
    records = [
        _record("dark", pixels=bytes([0]) * 256),
        _record("light", pixels=bytes([255]) * 256),
    ]
    grouped = assign_components(records, ahash_distance=2, dhash_distance=2)
    assert len({record.component_id for record in grouped}) == 2


def test_ppe_reused_stem_is_refined_by_visual_compatibility() -> None:
    source_key = "ppe_siabar:image_150_jpg"
    records = [
        _record("same-a", lineage=source_key, pixels=bytes([10]) * 256),
        _record("same-b", lineage=source_key, pixels=bytes([11]) * 256),
        _record("different", lineage=source_key, pixels=bytes([200]) * 256),
    ]
    refined = refine_ppe_lineages(records)
    assert refined[0].lineage_id == refined[1].lineage_id
    assert refined[2].lineage_id != refined[0].lineage_id
    assert all(record.source_key == source_key for record in refined)


def test_bench_component_excludes_candidate_by_lineage() -> None:
    lineage = "construction_site_safety:youtube-51_jpg"
    records = [
        _record("train", dataset="construction_site_safety", lineage=lineage),
        _record(
            "bench",
            role="bench",
            dataset="construction_site_safety",
            split="val",
            lineage=lineage,
        ),
    ]
    audited = mark_bench_overlaps(assign_components(records))
    candidate = next(record for record in audited if record.role == "candidate")
    assert candidate.bench_overlap
    assert candidate.bench_overlap_reason == "bench_source_lineage"


def test_ppe_reencodings_collapse_to_most_complete_representative() -> None:
    lineage = "ppe_siabar:00001_jpg"
    records = [
        _record("train", lineage=lineage, counts=(1, 1, 0, 0)),
        _record("val", split="val", lineage=lineage, counts=(1, 1, 1, 0)),
    ]
    selected, exclusions, stats = choose_representatives(records)
    assert [record.record_id for record in selected] == ["val"]
    assert exclusions == {"train": "deduplicated_ppe_lineage"}
    assert stats["deduplicated_ppe_lineage"] == 1


def test_ppe_annotation_variants_still_collapse_by_refined_visual_lineage() -> None:
    lineage = "ppe_siabar:00001_jpg"
    records = [
        _record("train", lineage=lineage, label_sha="labels-a"),
        _record("val", split="val", lineage=lineage, label_sha="labels-b"),
    ]
    selected, exclusions, _ = choose_representatives(records)
    assert [record.record_id for record in selected] == ["train"]
    assert exclusions == {"val": "deduplicated_ppe_lineage"}


def test_validation_selection_is_deterministic_and_covers_all_classes() -> None:
    groups = []
    for index in range(20):
        dataset = "construction_site_safety" if index < 10 else "ppe_siabar"
        counts = (1, 1, 1, 1 if index < 10 else 0)
        row = _record(f"r{index}", dataset=dataset, counts=counts)
        groups.append(SplitGroup(component_id=f"g{index}", rows=(row,)))
    first = select_validation_groups(groups, val_ratio=0.2, seed=42)
    second = select_validation_groups(groups, val_ratio=0.2, seed=42)
    assert first == second
    assert len(first) == 4
    selected = [group for group in groups if group.component_id in first]
    assert {dataset for group in selected for dataset in group.datasets} == {
        "construction_site_safety",
        "ppe_siabar",
    }
    assert sum(group.class_counts[3] for group in selected) > 0


def test_validation_requires_more_than_one_group() -> None:
    with pytest.raises(ValueError, match="at least two groups"):
        select_validation_groups(
            [SplitGroup(component_id="only", rows=(_record("only"),))]
        )


def test_inventory_roundtrip_keeps_audit_identity_without_pixels(tmp_path: Path) -> None:
    original = assign_components([_record("one")])[0]
    path = tmp_path / "inventory.csv"
    write_inventory(path, [original])
    loaded = read_inventory(path)
    assert loaded[0].record_id == original.record_id
    assert loaded[0].source_key == original.source_key
    assert loaded[0].lineage_id == original.lineage_id
    assert loaded[0].label_sha256 == original.label_sha256
    assert loaded[0].component_id == original.component_id
    assert loaded[0].perceptual_gray16 == b""
