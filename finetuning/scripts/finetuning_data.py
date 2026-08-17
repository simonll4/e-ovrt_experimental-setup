"""Shared data-contract helpers for the E-OVRT fine-tuning dataset.

The module intentionally has no workspace-specific absolute paths.  It inventories
``canonical_v2`` images, groups exact/source/perceptual relatives, and exposes deterministic
helpers used by both the auditor and the split builder.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

SCHEMA_VERSION = "eovrt.finetuning-inventory.v1"
SPLIT_SCHEMA_VERSION = "eovrt.finetuning-split.v1"
CANONICAL_CLASSES = ("person", "helmet", "vest", "bare_head")
APPROVED_SOURCES = (
    ("construction_site_safety", "train"),
    ("ppe_siabar", "train"),
    ("ppe_siabar", "val"),
    ("ppe_siabar", "test"),
)
SOURCE_CONTRACTS = {
    "construction_site_safety": {
        "source_url": (
            "https://universe.roboflow.com/roboflow-universe-projects/"
            "construction-site-safety"
        ),
        "license_spdx": "CC-BY-4.0",
        "source_version": "27",
    },
    "ppe_siabar": {
        "source_url": "https://universe.roboflow.com/siabar/ppe-plsuk",
        "license_spdx": "CC-BY-4.0",
        "source_version": "1",
    },
}
DEFAULT_BENCH_JSON = Path("datasets/processed/coco/bench/curated/bench_v3.json")
DEFAULT_BENCH_MANIFEST = Path(
    "datasets/processed/coco/bench/curated/bench_v3_manifest.json"
)

_ROBOFLOW_STEM = re.compile(r"^(?P<source>.+)\.rf\.[0-9a-fA-F]{8,}$")
_SPLIT_PREFERENCE = {"train": 0, "val": 1, "test": 2}


@dataclass(frozen=True)
class ImageRecord:
    """One candidate or benchmark image with stable identity and audit metadata."""

    record_id: str
    role: str
    dataset_id: str
    source_split: str
    image_path: str
    label_path: str
    label_sha256: str
    sha256: str
    source_key: str
    lineage_id: str
    ahash64: str
    dhash64: str
    class_counts: tuple[int, int, int, int]
    perceptual_gray16: bytes = b""
    component_id: str = ""
    bench_overlap: bool = False
    bench_overlap_reason: str = ""

    @property
    def annotation_count(self) -> int:
        return sum(self.class_counts)

    def with_component(self, component_id: str) -> ImageRecord:
        return ImageRecord(**{**self.__dict__, "component_id": component_id})

    def with_lineage(self, lineage_id: str) -> ImageRecord:
        return ImageRecord(**{**self.__dict__, "lineage_id": lineage_id})

    def with_bench_overlap(self, reason: str) -> ImageRecord:
        return ImageRecord(
            **{
                **self.__dict__,
                "bench_overlap": bool(reason),
                "bench_overlap_reason": reason,
            }
        )

    def to_csv_row(self) -> dict[str, str]:
        row = {
            "schema_version": SCHEMA_VERSION,
            "record_id": self.record_id,
            "role": self.role,
            "dataset_id": self.dataset_id,
            "source_split": self.source_split,
            "image_path": self.image_path,
            "label_path": self.label_path,
            "label_sha256": self.label_sha256,
            "sha256": self.sha256,
            "source_key": self.source_key,
            "lineage_id": self.lineage_id,
            "ahash64": self.ahash64,
            "dhash64": self.dhash64,
            "gray16_sha256": (
                hashlib.sha256(self.perceptual_gray16).hexdigest()
                if self.perceptual_gray16
                else ""
            ),
            "component_id": self.component_id,
            "bench_overlap": "true" if self.bench_overlap else "false",
            "bench_overlap_reason": self.bench_overlap_reason,
        }
        row.update(
            {
                f"instances_{name}": str(self.class_counts[index])
                for index, name in enumerate(CANONICAL_CLASSES)
            }
        )
        return row

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> ImageRecord:
        if row.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"inventory schema {row.get('schema_version')!r} is not {SCHEMA_VERSION!r}"
            )
        return cls(
            record_id=row["record_id"],
            role=row["role"],
            dataset_id=row["dataset_id"],
            source_split=row["source_split"],
            image_path=row["image_path"],
            label_path=row["label_path"],
            label_sha256=row["label_sha256"],
            sha256=row["sha256"],
            source_key=row["source_key"],
            lineage_id=row["lineage_id"],
            ahash64=row["ahash64"],
            dhash64=row["dhash64"],
            class_counts=tuple(
                int(row[f"instances_{name}"]) for name in CANONICAL_CLASSES
            ),
            perceptual_gray16=b"",
            component_id=row["component_id"],
            bench_overlap=row["bench_overlap"].lower() == "true",
            bench_overlap_reason=row["bench_overlap_reason"],
        )


@dataclass(frozen=True)
class SplitGroup:
    """Connected image group that must stay wholly in one model-selection split."""

    component_id: str
    rows: tuple[ImageRecord, ...]

    @property
    def datasets(self) -> frozenset[str]:
        return frozenset(row.dataset_id for row in self.rows)

    @property
    def class_counts(self) -> tuple[int, int, int, int]:
        return tuple(sum(row.class_counts[index] for row in self.rows) for index in range(4))

    @property
    def class_presence(self) -> tuple[int, int, int, int]:
        counts = self.class_counts
        return tuple(1 if value else 0 for value in counts)


class UnionFind:
    """Small deterministic disjoint-set implementation."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1


def workspace_default_datasets_root(script_file: str | Path) -> Path:
    """Resolve the sibling datasets repository without embedding a personal path."""

    workspace = Path(script_file).resolve().parents[3]
    return workspace / "e-ovrt_datasets"


def normalize_roboflow_stem(filename: str | Path) -> str:
    """Return the source-image stem, stripping Roboflow's ``.rf.<hash>`` suffix."""

    stem = Path(filename).stem
    match = _ROBOFLOW_STEM.match(stem)
    return match.group("source") if match else stem


def make_lineage_id(dataset_id: str, filename: str | Path) -> str:
    """Namespace source lineage by dataset to avoid basename collisions."""

    return f"{dataset_id}:{normalize_roboflow_stem(filename)}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pixel_values(image: Image.Image) -> list[int]:
    flattened = getattr(image, "get_flattened_data", None)
    return list(flattened() if flattened else image.getdata())


def image_fingerprint(path: Path) -> tuple[str, str, bytes]:
    """Compute two hashes plus normalized pixels for conservative duplicate checks."""

    resampling = getattr(Image, "Resampling", Image).LANCZOS
    with Image.open(path) as source:
        gray = source.convert("L")
        average_image = gray.resize((8, 8), resampling)
        difference_image = gray.resize((9, 8), resampling)
        perceptual_image = gray.resize((16, 16), resampling)
        average_pixels = _pixel_values(average_image)
        difference_pixels = _pixel_values(difference_image)
        perceptual_pixels = bytes(_pixel_values(perceptual_image))

    average = sum(average_pixels) / len(average_pixels)
    ahash = 0
    for value in average_pixels:
        ahash = (ahash << 1) | int(value >= average)

    dhash = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            dhash = (dhash << 1) | int(
                difference_pixels[offset + column]
                >= difference_pixels[offset + column + 1]
            )
    return f"{ahash:016x}", f"{dhash:016x}", perceptual_pixels


def image_hashes(path: Path) -> tuple[str, str]:
    """Compatibility wrapper returning the public 64-bit image hashes."""

    ahash64, dhash64, _ = image_fingerprint(path)
    return ahash64, dhash64


def hamming_distance(left: str | int, right: str | int) -> int:
    left_value = int(left, 16) if isinstance(left, str) else left
    right_value = int(right, 16) if isinstance(right, str) else right
    return (left_value ^ right_value).bit_count()


def _hamming_neighbors(value: int, radius: int) -> Iterator[int]:
    yield value
    if radius < 1:
        return
    for first in range(64):
        yield value ^ (1 << first)
    if radius < 2:
        return
    for first in range(64):
        for second in range(first + 1, 64):
            yield value ^ (1 << first) ^ (1 << second)


def _validate_categories(data: dict, path: Path) -> dict[int, str]:
    category_map = {int(item["id"]): str(item["name"]) for item in data["categories"]}
    expected = {index: name for index, name in enumerate(CANONICAL_CLASSES)}
    if category_map != expected:
        raise ValueError(f"{path}: categories {category_map!r} do not match {expected!r}")
    return category_map


def _class_counts_by_image(data: dict, path: Path) -> dict[int, tuple[int, int, int, int]]:
    _validate_categories(data, path)
    counters: dict[int, Counter[int]] = defaultdict(Counter)
    for annotation in data["annotations"]:
        category_id = int(annotation["category_id"])
        if category_id not in range(4):
            raise ValueError(f"{path}: invalid category id {category_id}")
        counters[int(annotation["image_id"])][category_id] += 1
    return {
        int(image["id"]): tuple(counters[int(image["id"])][index] for index in range(4))
        for image in data["images"]
    }


def _yolo_class_counts(label_path: Path) -> tuple[int, int, int, int]:
    counts: Counter[int] = Counter()
    for line_number, raw_line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split()
        try:
            category_id = int(fields[0])
        except (IndexError, ValueError) as error:
            raise ValueError(f"{label_path}:{line_number}: malformed YOLO row") from error
        if category_id not in range(4):
            raise ValueError(
                f"{label_path}:{line_number}: class {category_id} is outside canonical_v2"
            )
        counts[category_id] += 1
    return tuple(counts[index] for index in range(4))


def _canonical_coco_path(datasets_root: Path, dataset_id: str, split: str) -> Path:
    return (
        datasets_root
        / "datasets"
        / "processed"
        / "coco"
        / "canonical_v2"
        / dataset_id
        / f"{split}.json"
    )


def _canonical_label_path(
    datasets_root: Path, dataset_id: str, split: str, image_path: str
) -> tuple[Path, str]:
    relative = (
        Path("datasets")
        / "processed"
        / "yolo"
        / "canonical_v2"
        / dataset_id
        / "labels"
        / split
        / f"{Path(image_path).stem}.txt"
    )
    return datasets_root / relative, relative.as_posix()


def load_candidate_records(
    datasets_root: Path,
    sources: Sequence[tuple[str, str]] = APPROVED_SOURCES,
) -> list[ImageRecord]:
    """Load and validate approved canonical candidates, including canonical YOLO labels."""

    records: list[ImageRecord] = []
    for dataset_id, split in sources:
        if dataset_id not in SOURCE_CONTRACTS:
            raise ValueError(f"missing source contract for {dataset_id}")
        coco_path = _canonical_coco_path(datasets_root, dataset_id, split)
        data = json.loads(coco_path.read_text(encoding="utf-8"))
        counts_by_image = _class_counts_by_image(data, coco_path)
        for image in data["images"]:
            image_path = str(image["file_name"])
            absolute_image = datasets_root / image_path
            if not absolute_image.is_file():
                raise FileNotFoundError(f"missing candidate image: {absolute_image}")
            absolute_label, label_path = _canonical_label_path(
                datasets_root, dataset_id, split, image_path
            )
            if not absolute_label.is_file():
                raise FileNotFoundError(f"missing canonical label: {absolute_label}")
            coco_counts = counts_by_image[int(image["id"])]
            label_counts = _yolo_class_counts(absolute_label)
            if label_counts != coco_counts:
                raise ValueError(
                    f"COCO/YOLO count mismatch for {image_path}: "
                    f"COCO={coco_counts}, YOLO={label_counts}"
                )
            sha256 = sha256_file(absolute_image)
            ahash64, dhash64, perceptual_gray16 = image_fingerprint(absolute_image)
            record_id = f"candidate:{dataset_id}:{split}:{image_path}"
            source_key = make_lineage_id(dataset_id, image_path)
            records.append(
                ImageRecord(
                    record_id=record_id,
                    role="candidate",
                    dataset_id=dataset_id,
                    source_split=split,
                    image_path=image_path,
                    label_path=label_path,
                    label_sha256=sha256_file(absolute_label),
                    sha256=sha256,
                    source_key=source_key,
                    lineage_id=source_key,
                    ahash64=ahash64,
                    dhash64=dhash64,
                    class_counts=coco_counts,
                    perceptual_gray16=perceptual_gray16,
                )
            )
    return records


def _infer_dataset_and_split(image_path: str) -> tuple[str, str]:
    parts = Path(image_path).parts
    try:
        raw_index = parts.index("raw")
        dataset_id = parts[raw_index + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(f"cannot infer dataset from bench path {image_path!r}") from error
    candidates = set(parts[raw_index + 2 :])
    if "train" in candidates:
        split = "train"
    elif "valid" in candidates or "val" in candidates:
        split = "val"
    elif "test" in candidates:
        split = "test"
    else:
        split = "unspecified"
    return dataset_id, split


def load_bench_records(
    datasets_root: Path,
    bench_json: Path = DEFAULT_BENCH_JSON,
    bench_manifest: Path = DEFAULT_BENCH_MANIFEST,
) -> tuple[list[ImageRecord], str]:
    """Load benchmark rows after proving the frozen aggregate has its declared hash."""

    bench_path = datasets_root / bench_json
    manifest_path = datasets_root / bench_manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hash = str(manifest["bench_v3_sha256"])
    actual_hash = sha256_file(bench_path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"bench_v3 hash mismatch: manifest={expected_hash}, actual={actual_hash}"
        )

    data = json.loads(bench_path.read_text(encoding="utf-8"))
    counts_by_image = _class_counts_by_image(data, bench_path)
    records: list[ImageRecord] = []
    for image in data["images"]:
        image_path = str(image["file_name"])
        absolute_image = datasets_root / image_path
        if not absolute_image.is_file():
            raise FileNotFoundError(f"missing bench image: {absolute_image}")
        dataset_id, split = _infer_dataset_and_split(image_path)
        sha256 = sha256_file(absolute_image)
        ahash64, dhash64, perceptual_gray16 = image_fingerprint(absolute_image)
        source_key = make_lineage_id(dataset_id, image_path)
        records.append(
            ImageRecord(
                record_id=f"bench:{dataset_id}:{split}:{image_path}",
                role="bench",
                dataset_id=dataset_id,
                source_split=split,
                image_path=image_path,
                label_path="",
                label_sha256="",
                sha256=sha256,
                source_key=source_key,
                lineage_id=source_key,
                ahash64=ahash64,
                dhash64=dhash64,
                class_counts=counts_by_image[int(image["id"])],
                perceptual_gray16=perceptual_gray16,
            )
        )
    if len(records) != int(manifest["total_images"]):
        raise ValueError(
            f"bench manifest declares {manifest['total_images']} images; loaded {len(records)}"
        )
    return records, actual_hash


def _pixel_mae(left: ImageRecord, right: ImageRecord) -> float:
    if not left.perceptual_gray16 or not right.perceptual_gray16:
        return float("inf")
    return sum(
        abs(left_value - right_value)
        for left_value, right_value in zip(
            left.perceptual_gray16,
            right.perceptual_gray16,
            strict=True,
        )
    ) / len(left.perceptual_gray16)


def _perceptually_compatible(
    left: ImageRecord,
    right: ImageRecord,
    ahash_distance: int,
    dhash_distance: int,
    pixel_mae_threshold: float,
) -> bool:
    return (
        hamming_distance(left.ahash64, right.ahash64) <= ahash_distance
        and hamming_distance(left.dhash64, right.dhash64) <= dhash_distance
        and _pixel_mae(left, right) <= pixel_mae_threshold
    )


def refine_ppe_lineages(
    records: Sequence[ImageRecord],
    ahash_distance: int = 4,
    dhash_distance: int = 4,
    pixel_mae_threshold: float = 5.0,
) -> list[ImageRecord]:
    """Split reused PPE stems into visually verified source-image lineages."""

    indices_by_source_key: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        if record.dataset_id == "ppe_siabar":
            indices_by_source_key[record.source_key].append(index)

    lineage_by_index: dict[int, str] = {}
    for source_key, indices in indices_by_source_key.items():
        union_find = UnionFind(len(indices))
        for left_position, left_index in enumerate(indices):
            for right_position in range(left_position + 1, len(indices)):
                right_index = indices[right_position]
                left = records[left_index]
                right = records[right_index]
                if left.sha256 == right.sha256 or _perceptually_compatible(
                    left,
                    right,
                    ahash_distance=ahash_distance,
                    dhash_distance=dhash_distance,
                    pixel_mae_threshold=pixel_mae_threshold,
                ):
                    union_find.union(left_position, right_position)

        members_by_root: dict[int, list[int]] = defaultdict(list)
        for position, record_index in enumerate(indices):
            members_by_root[union_find.find(position)].append(record_index)
        if len(members_by_root) == 1:
            for record_index in indices:
                lineage_by_index[record_index] = source_key
            continue
        for member_indices in members_by_root.values():
            identities = sorted(records[index].record_id for index in member_indices)
            suffix = hashlib.sha256("\n".join(identities).encode("utf-8")).hexdigest()[:12]
            for record_index in member_indices:
                lineage_by_index[record_index] = f"{source_key}@{suffix}"

    return [
        record.with_lineage(lineage_by_index.get(index, record.lineage_id))
        for index, record in enumerate(records)
    ]


def assign_components(
    records: Sequence[ImageRecord],
    ahash_distance: int = 2,
    dhash_distance: int = 2,
    pixel_mae_threshold: float = 2.0,
) -> list[ImageRecord]:
    """Connect exact hashes, source lineages, and conservative dual-hash neighbors."""

    if ahash_distance not in range(3):
        raise ValueError("ahash_distance must be 0, 1, or 2")
    if pixel_mae_threshold < 0:
        raise ValueError("pixel_mae_threshold must be non-negative")
    union_find = UnionFind(len(records))

    def union_equal(values: Iterable[tuple[str, int]]) -> None:
        first_by_value: dict[str, int] = {}
        for value, index in values:
            if value in first_by_value:
                union_find.union(first_by_value[value], index)
            else:
                first_by_value[value] = index

    union_equal((record.sha256, index) for index, record in enumerate(records))
    union_equal((record.lineage_id, index) for index, record in enumerate(records))

    indices_by_ahash: dict[int, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        indices_by_ahash[int(record.ahash64, 16)].append(index)

    known_ahashes = set(indices_by_ahash)
    for ahash in sorted(known_ahashes):
        left_indices = indices_by_ahash[ahash]
        for neighbor in _hamming_neighbors(ahash, ahash_distance):
            if neighbor not in known_ahashes or neighbor < ahash:
                continue
            right_indices = indices_by_ahash[neighbor]
            for left_index in left_indices:
                for right_index in right_indices:
                    if ahash == neighbor and left_index >= right_index:
                        continue
                    left = records[left_index]
                    right = records[right_index]
                    if _perceptually_compatible(
                        left,
                        right,
                        ahash_distance=ahash_distance,
                        dhash_distance=dhash_distance,
                        pixel_mae_threshold=pixel_mae_threshold,
                    ):
                        union_find.union(left_index, right_index)

    members_by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        members_by_root[union_find.find(index)].append(index)

    component_by_index: dict[int, str] = {}
    for member_indices in members_by_root.values():
        identities = sorted(records[index].record_id for index in member_indices)
        digest = hashlib.sha256("\n".join(identities).encode("utf-8")).hexdigest()[:16]
        component_id = f"grp_{digest}"
        for index in member_indices:
            component_by_index[index] = component_id

    return [
        record.with_component(component_by_index[index])
        for index, record in enumerate(records)
    ]


def mark_bench_overlaps(records: Sequence[ImageRecord]) -> list[ImageRecord]:
    """Annotate candidate rows belonging to any component that contains benchmark material."""

    bench_rows = [record for record in records if record.role == "bench"]
    bench_components = {record.component_id for record in bench_rows}
    bench_hashes = {record.sha256 for record in bench_rows}
    bench_lineages = {record.lineage_id for record in bench_rows}

    annotated: list[ImageRecord] = []
    for record in records:
        if record.role != "candidate" or record.component_id not in bench_components:
            annotated.append(record)
            continue
        if record.sha256 in bench_hashes:
            reason = "bench_exact_sha256"
        elif record.lineage_id in bench_lineages:
            reason = "bench_source_lineage"
        else:
            reason = "bench_perceptual_component"
        annotated.append(record.with_bench_overlap(reason))
    return annotated


def class_instance_counts(records: Iterable[ImageRecord]) -> dict[str, int]:
    totals = [0, 0, 0, 0]
    for record in records:
        for index, value in enumerate(record.class_counts):
            totals[index] += value
    return {name: totals[index] for index, name in enumerate(CANONICAL_CLASSES)}


def records_by_source(records: Iterable[ImageRecord]) -> dict[str, dict[str, object]]:
    grouped: dict[tuple[str, str], list[ImageRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.dataset_id, record.source_split)].append(record)
    return {
        f"{dataset_id}/{split}": {
            "images": len(rows),
            "lineages": len({row.lineage_id for row in rows}),
            "class_instances": class_instance_counts(rows),
        }
        for (dataset_id, split), rows in sorted(grouped.items())
    }


def lineage_split_overlap(records: Iterable[ImageRecord], dataset_id: str) -> dict[str, object]:
    selected = [record for record in records if record.dataset_id == dataset_id]
    rows_by_lineage: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in selected:
        rows_by_lineage[record.lineage_id].append(record)
    overlapping = {
        lineage: rows
        for lineage, rows in rows_by_lineage.items()
        if len({row.source_split for row in rows}) > 1
    }
    affected_by_split = Counter(
        row.source_split for rows in overlapping.values() for row in rows
    )
    return {
        "shared_lineages": len(overlapping),
        "affected_images": sum(len(rows) for rows in overlapping.values()),
        "affected_images_by_split": dict(sorted(affected_by_split.items())),
    }


def lineage_annotation_conflicts(
    records: Iterable[ImageRecord], dataset_id: str
) -> dict[str, object]:
    """Report repeated source lineages carrying more than one canonical label file."""

    rows_by_lineage: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        if record.dataset_id == dataset_id:
            rows_by_lineage[record.lineage_id].append(record)
    conflicts = {
        lineage: rows
        for lineage, rows in rows_by_lineage.items()
        if len({row.label_sha256 for row in rows}) > 1
    }
    return {
        "lineages": len(conflicts),
        "images": sum(len(rows) for rows in conflicts.values()),
        "lineage_ids": sorted(conflicts),
    }


def write_inventory(path: Path, records: Sequence[ImageRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].to_csv_row()) if records else ["schema_version"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(records, key=lambda row: row.record_id):
            writer.writerow(record.to_csv_row())
    temporary.replace(path)


def read_inventory(path: Path) -> list[ImageRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [ImageRecord.from_csv_row(row) for row in csv.DictReader(handle)]


def choose_representatives(
    candidates: Sequence[ImageRecord],
) -> tuple[list[ImageRecord], dict[str, str], dict[str, int]]:
    """Collapse safe re-encodings while retaining CSS training augmentations."""

    eligible = [record for record in candidates if not record.bench_overlap]
    excluded: dict[str, str] = {}
    stats: Counter[str] = Counter()

    ppe_by_lineage: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in eligible:
        if record.dataset_id == "ppe_siabar":
            ppe_by_lineage[record.lineage_id].append(record)
    for rows in ppe_by_lineage.values():
        if len(rows) < 2:
            continue
        representative = min(
            rows,
            key=lambda row: (
                -row.annotation_count,
                _SPLIT_PREFERENCE.get(row.source_split, 99),
                row.image_path,
            ),
        )
        for row in rows:
            if row.record_id != representative.record_id:
                excluded[row.record_id] = "deduplicated_ppe_lineage"
                stats["deduplicated_ppe_lineage"] += 1

    remaining = [row for row in eligible if row.record_id not in excluded]
    rows_by_sha_and_label: dict[tuple[str, str], list[ImageRecord]] = defaultdict(list)
    for row in remaining:
        rows_by_sha_and_label[(row.sha256, row.label_sha256)].append(row)
    for rows in rows_by_sha_and_label.values():
        if len(rows) < 2:
            continue
        representative = min(rows, key=lambda row: row.record_id)
        for row in rows:
            if row.record_id != representative.record_id:
                excluded[row.record_id] = "deduplicated_exact_sha256"
                stats["deduplicated_exact_sha256"] += 1

    selected = [row for row in eligible if row.record_id not in excluded]
    return selected, excluded, dict(sorted(stats.items()))


def make_split_groups(records: Sequence[ImageRecord]) -> list[SplitGroup]:
    grouped: dict[str, list[ImageRecord]] = defaultdict(list)
    for record in records:
        grouped[record.component_id].append(record)
    return [
        SplitGroup(
            component_id=component_id,
            rows=tuple(sorted(rows, key=lambda row: row.record_id)),
        )
        for component_id, rows in sorted(grouped.items())
    ]


def _stable_jitter(seed: int, component_id: str) -> float:
    digest = hashlib.sha256(f"{seed}:{component_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def select_validation_groups(
    groups: Sequence[SplitGroup],
    val_ratio: float = 0.15,
    seed: int = 42,
    target_group_count: int | None = None,
) -> set[str]:
    """Choose a deterministic group-level validation subset with multilabel balancing."""

    if not 0 < val_ratio < 1:
        raise ValueError("val_ratio must be between zero and one")
    if len(groups) < 2:
        raise ValueError("at least two groups are required")

    requested_target = (
        round(len(groups) * val_ratio) if target_group_count is None else target_group_count
    )
    target_groups = max(1, min(len(groups) - 1, requested_target))
    dataset_names = sorted({dataset for group in groups for dataset in group.datasets})
    dataset_totals = {
        dataset: sum(1 for group in groups if dataset in group.datasets)
        for dataset in dataset_names
    }
    dataset_targets = {
        dataset: max(1.0, total * val_ratio) for dataset, total in dataset_totals.items()
    }
    class_totals = [
        sum(group.class_counts[index] for group in groups) for index in range(4)
    ]
    class_targets = [max(1.0, total * val_ratio) for total in class_totals]
    presence_totals = [
        sum(group.class_presence[index] for group in groups) for index in range(4)
    ]
    presence_targets = [max(1.0, total * val_ratio) for total in presence_totals]

    selected: set[str] = set()
    selected_dataset: Counter[str] = Counter()
    selected_classes = [0, 0, 0, 0]
    selected_presence = [0, 0, 0, 0]

    def squared_error(current: float, target: float) -> float:
        return ((current - target) / target) ** 2

    while len(selected) < target_groups:
        best_group: SplitGroup | None = None
        best_score: float | None = None
        for group in groups:
            if group.component_id in selected:
                continue
            improvement = 0.0
            for dataset in dataset_names:
                before = selected_dataset[dataset]
                after = before + int(dataset in group.datasets)
                improvement += squared_error(before, dataset_targets[dataset])
                improvement -= squared_error(after, dataset_targets[dataset])
            for index in range(4):
                before = selected_classes[index]
                after = before + group.class_counts[index]
                improvement += squared_error(before, class_targets[index])
                improvement -= squared_error(after, class_targets[index])
                before_presence = selected_presence[index]
                after_presence = before_presence + group.class_presence[index]
                improvement += squared_error(before_presence, presence_targets[index])
                improvement -= squared_error(after_presence, presence_targets[index])
            score = improvement + _stable_jitter(seed, group.component_id) * 1e-9
            if best_score is None or score > best_score:
                best_score = score
                best_group = group
        if best_group is None:
            raise RuntimeError("could not select a validation group")
        selected.add(best_group.component_id)
        for dataset in best_group.datasets:
            selected_dataset[dataset] += 1
        for index, value in enumerate(best_group.class_counts):
            selected_classes[index] += value
            selected_presence[index] += best_group.class_presence[index]

    missing = [
        CANONICAL_CLASSES[index] for index, value in enumerate(selected_classes) if value == 0
    ]
    if missing:
        raise ValueError(f"validation split has no instances for: {', '.join(missing)}")
    missing_datasets = [dataset for dataset in dataset_names if selected_dataset[dataset] == 0]
    if missing_datasets:
        raise ValueError(f"validation split has no groups for: {', '.join(missing_datasets)}")
    return selected


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
