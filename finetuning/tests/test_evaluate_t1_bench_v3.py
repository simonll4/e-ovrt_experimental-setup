"""Tests sintéticos del comando de evaluación congelado (T-FT-031).

No requieren torch ni datos reales: el protocolo, el bench COCO, las
detecciones y el person GT se generan acá con hashes computados en el
propio test. El evaluador subyacente es un `evaluate_bench.py` mínimo
sintético con la MISMA interfaz que el real — la identidad del real la
garantiza el hash congelado en el protocolo, no este test.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from evaluate_t1_bench_v3 import (  # noqa: E402
    CoverageError,
    FrozenInputMismatch,
    run_frozen_evaluation,
)

FAKE_EVALUATOR = '''
def load_detections(jsonl_paths):
    import json
    out = {}
    for p in jsonl_paths:
        for line in open(p, encoding="utf-8"):
            rec = json.loads(line)
            out.setdefault(rec["file_name"], []).extend(rec.get("detections", []))
    return out


def load_bench_coco(path):
    import json
    data = json.load(open(path, encoding="utf-8"))
    images_by_filename = {img["file_name"]: img for img in data["images"]}
    gt_by_image_id = {}
    for ann in data["annotations"]:
        gt_by_image_id.setdefault(ann["image_id"], []).append(ann)
    cat_by_id = {c["id"]: c["name"] for c in data["categories"]}
    return images_by_filename, gt_by_image_id, cat_by_id


def load_person_gt(path):
    import json
    return json.load(open(path, encoding="utf-8")).get("records", [])


def evaluate_class(class_name, detections_by_img, images_by_filename,
                   gt_by_image_id, cat_by_id, iou_threshold):
    cat_id = next((k for k, v in cat_by_id.items() if v == class_name), None)
    n_gt = sum(
        1
        for anns in gt_by_image_id.values()
        for a in anns
        if a["category_id"] == cat_id
    )
    n_det = sum(
        1
        for fname in images_by_filename
        for d in detections_by_img.get(fname, [])
        if d.get("prompt_id") == class_name
    )
    ap = 1.0 if (n_gt and n_det >= n_gt) else (0.0 if n_gt else None)
    return {"class": class_name, "AP50": ap, "n_gt": n_gt, "n_det": n_det}


def evaluate_cr01(person_gt_records, detections_by_filename,
                  images_by_filename, iou_threshold):
    violators = [r for r in person_gt_records if not r.get("has_helmet", True)]
    detected = sum(
        1
        for r in violators
        if any(
            d.get("prompt_id") == "bare_head"
            for d in detections_by_filename.get(r["file_name"], [])
        )
    )
    n = len(violators)
    return {
        "cr01_recall": round(detected / n, 4) if n else None,
        "n_violators": n,
        "n_detected": detected,
        "n_violators_gt_total": n,
    }
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _coco(images: list[str], anns: list[tuple[int, int]]) -> dict:
    return {
        "images": [{"id": i, "file_name": name} for i, name in enumerate(images)],
        "annotations": [
            {"id": j, "image_id": img_id, "category_id": cat, "bbox": [0, 0, 10, 10]}
            for j, (img_id, cat) in enumerate(anns)
        ],
        "categories": [
            {"id": 0, "name": "person"},
            {"id": 1, "name": "helmet"},
            {"id": 2, "name": "vest"},
            {"id": 3, "name": "bare_head"},
        ],
    }


@pytest.fixture()
def world(tmp_path: Path) -> dict:
    datasets = tmp_path / "datasets_repo"
    curated = datasets / "coco"
    curated.mkdir(parents=True)

    evaluator = datasets / "evaluate_bench.py"
    evaluator.write_text(FAKE_EVALUATOR, encoding="utf-8")

    bench = curated / "bench_v3.json"
    bench.write_text(
        json.dumps(_coco(["a.jpg", "b.jpg"], [(0, 0), (0, 3), (1, 0)])),
        encoding="utf-8",
    )
    stratum_a = curated / "stratum_a.json"
    stratum_a.write_text(json.dumps(_coco(["a.jpg"], [(0, 0), (0, 3)])), encoding="utf-8")
    stratum_b = curated / "stratum_b.json"
    stratum_b.write_text(json.dumps(_coco(["b.jpg"], [(0, 0)])), encoding="utf-8")

    gt_a = curated / "person_gt_a.json"
    gt_a.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "file_name": "a.jpg",
                        "person_bbox": [0, 0, 10, 30],
                        "has_helmet": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    detections = run_dir / "detections.jsonl"
    detections.write_text(
        "\n".join(
            json.dumps(rec)
            for rec in [
                {
                    "file_name": "a.jpg",
                    "detections": [
                        {"prompt_id": "person", "confidence": 0.9,
                         "bbox_xyxy": [0, 0, 10, 30]},
                        {"prompt_id": "bare_head", "confidence": 0.8,
                         "bbox_xyxy": [1, 1, 9, 9]},
                    ],
                },
                {
                    "file_name": "b.jpg",
                    "detections": [
                        {"prompt_id": "person", "confidence": 0.7,
                         "bbox_xyxy": [0, 0, 10, 30]},
                    ],
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    protocol = {
        "protocol_id": "synthetic_v1",
        "evaluator": {"relative_path": "evaluate_bench.py", "sha256": _sha(evaluator)},
        "benchmark": {
            "coco": {"relative_path": "coco/bench_v3.json", "sha256": _sha(bench)},
            "strata": {
                "stratum_a": {
                    "relative_path": "coco/stratum_a.json",
                    "sha256": _sha(stratum_a),
                },
                "stratum_b": {
                    "relative_path": "coco/stratum_b.json",
                    "sha256": _sha(stratum_b),
                },
            },
        },
        "cr01_sources": {
            "src_a": {"relative_path": "coco/person_gt_a.json", "sha256": _sha(gt_a)},
        },
        "inference": {"iou_threshold": 0.5},
    }
    return {
        "datasets_root": datasets,
        "run_dir": run_dir,
        "protocol": protocol,
        "out": tmp_path / "out",
    }


def test_happy_path_emits_all_artifacts(world):
    result = run_frozen_evaluation(
        protocol=world["protocol"],
        datasets_root=world["datasets_root"],
        run_dir=world["run_dir"],
        output_dir=world["out"],
        arm="baseline",
    )

    out = world["out"]
    aggregate = json.loads((out / "eval_perception.aggregate.json").read_text())
    by_stratum = json.loads((out / "eval_perception.by_stratum.json").read_text())
    cr01 = json.loads((out / "eval_cr01.by_source.json").read_text())
    snapshot = json.loads((out / "protocol_snapshot.json").read_text())
    shas = (out / "artifact.sha256").read_text()

    assert aggregate["arm"] == "baseline"
    assert aggregate["mAP50"] is not None
    names = {c["class_name"] for c in aggregate["per_class"]}
    assert names == {"person", "helmet", "vest", "bare_head"}
    assert set(by_stratum["strata"]) == {"stratum_a", "stratum_b"}
    assert cr01["sources"]["src_a"]["cr01_recall"] == 1.0
    # agregado transparente por conteos
    assert cr01["count_weighted_aggregate"]["n_violators"] == 1
    assert snapshot["protocol_id"] == "synthetic_v1"
    for artifact in (
        "eval_perception.aggregate.json",
        "eval_perception.by_stratum.json",
        "eval_cr01.by_source.json",
        "protocol_snapshot.json",
        "detections.jsonl",
    ):
        assert artifact in shas
    assert result["coverage"]["bench_images"] == 2


def test_hash_mismatch_aborts_before_computing(world):
    world["protocol"]["benchmark"]["coco"]["sha256"] = "0" * 64

    with pytest.raises(FrozenInputMismatch, match="bench_v3.json"):
        run_frozen_evaluation(
            protocol=world["protocol"],
            datasets_root=world["datasets_root"],
            run_dir=world["run_dir"],
            output_dir=world["out"],
            arm="baseline",
        )
    assert not world["out"].exists()


def test_incomplete_coverage_aborts(world):
    detections = world["run_dir"] / "detections.jsonl"
    lines = detections.read_text().strip().splitlines()
    detections.write_text(lines[0] + "\n", encoding="utf-8")  # sólo a.jpg

    with pytest.raises(CoverageError, match="b.jpg"):
        run_frozen_evaluation(
            protocol=world["protocol"],
            datasets_root=world["datasets_root"],
            run_dir=world["run_dir"],
            output_dir=world["out"],
            arm="baseline",
        )


def test_rejects_unknown_arm(world):
    with pytest.raises(ValueError, match="arm"):
        run_frozen_evaluation(
            protocol=world["protocol"],
            datasets_root=world["datasets_root"],
            run_dir=world["run_dir"],
            output_dir=world["out"],
            arm="candidate",
        )
