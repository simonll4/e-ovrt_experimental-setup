#!/usr/bin/env python3
"""Comando CONGELADO de evaluación de retención open-vocabulary (T-FT-062, D-FT-04).

Única vía admitida para evaluar los brazos `base` y `tuned` contra COCO val2017. Espeja
la disciplina de `evaluate_t1_bench_v3.py`:

  - verifica por sha256 TODOS los insumos que el protocolo congela (GT y prompt set)
    antes de computar nada;
  - exige cobertura completa del benchmark (aborta si falta una imagen);
  - computa con el MISMO evaluador congelado del repo `e-ovrt_datasets`
    (`evaluate_bench.py`), cargado por path — el mismo que produjo las cifras de
    `bench_v3`, para que retención y ganancia se midan con un solo instrumento;
  - emite `eval_retention.aggregate.json` (AP50 por clase + mAP50) y `artifact.sha256`.

Regla one-shot: un brazo, una evaluación. El brazo `base` se evalúa y se congela ANTES
de que exista el checkpoint T2.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROTOCOL_SCHEMA = "eovrt.t2-coco-retention-protocol.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_evaluator(datasets_root: Path):
    module_path = datasets_root / "datasets" / "scripts" / "bench" / "evaluate_bench.py"
    if not module_path.is_file():
        raise FileNotFoundError(f"evaluador congelado ausente: {module_path}")
    spec = importlib.util.spec_from_file_location("eovrt_evaluate_bench", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, sha256_file(module_path)


def evaluate(*, run_dir: Path, arm: str, protocol_path: Path, datasets_root: Path, out: Path) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise ValueError(f"protocolo inesperado: {protocol.get('schema_version')}")

    benchmark = protocol["benchmark"]
    annotations = Path(benchmark["annotations_path"])
    actual = sha256_file(annotations)
    if actual != benchmark["annotations_sha256"]:
        raise RuntimeError(
            f"el GT de COCO cambió respecto del protocolo: {actual} != {benchmark['annotations_sha256']}"
        )
    prompts_path = Path(protocol["prompts"]["path"])
    actual_prompts = sha256_file(prompts_path)
    if actual_prompts != protocol["prompts"]["sha256"]:
        raise RuntimeError(
            f"el prompt set cambió respecto del protocolo: {actual_prompts} != {protocol['prompts']['sha256']}"
        )

    detections = run_dir / "detections.jsonl"
    if not detections.is_file():
        raise FileNotFoundError(f"la corrida no tiene detections.jsonl: {detections}")

    module, evaluator_sha256 = _load_evaluator(datasets_root)
    detections_by_image = module.load_detections([detections])
    images_by_basename, gt_by_image_id, cat_by_id = module.load_bench_coco(annotations)

    expected_images = int(benchmark["images"])
    covered = sum(1 for name in images_by_basename if name in detections_by_image)
    if covered != expected_images:
        raise RuntimeError(
            f"cobertura incompleta: {covered}/{expected_images} imágenes evaluadas; "
            "el protocolo exige el benchmark completo"
        )

    iou_threshold = float(protocol["metric"]["iou_threshold"])
    class_names = [str(name) for name in protocol["prompts"]["class_ids"]]
    per_class = [
        module.evaluate_class(
            class_name=name,
            detections_by_img=detections_by_image,
            images_by_filename=images_by_basename,
            gt_by_image_id=gt_by_image_id,
            cat_by_id=cat_by_id,
            iou_threshold=iou_threshold,
        )
        for name in class_names
    ]
    scored = [row["AP50"] for row in per_class if row.get("AP50") is not None]
    m_ap50 = round(sum(scored) / len(scored), 6) if scored else None

    aggregate = {
        "protocol_id": PROTOCOL_SCHEMA,
        "task_id": "T-FT-062",
        "arm": arm,
        "run_dir": str(run_dir),
        "benchmark": "coco_val2017",
        "iou_threshold": iou_threshold,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "images": expected_images,
        "classes_scored": len(scored),
        "classes_total": len(class_names),
        "per_class": per_class,
        "mAP50": m_ap50,
        "evaluator_sha256": evaluator_sha256,
        "annotations_sha256": benchmark["annotations_sha256"],
        "prompts_sha256": protocol["prompts"]["sha256"],
        "note": (
            "mAP50 = media de los AP50 no nulos, mismo criterio que el protocolo de bench_v3. "
            "Cifra de RETENCIÓN: no se compara con benchmarks COCO publicados (vocabulario "
            "servido por prompts, umbrales del proyecto, no el protocolo COCO oficial)."
        ),
    }

    out.mkdir(parents=True, exist_ok=True)
    aggregate_path = out / "eval_retention.aggregate.json"
    aggregate_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = [
        f"{sha256_file(aggregate_path)}  {aggregate_path.name}",
        f"{sha256_file(detections)}  detections.jsonl",
    ]
    (out / "artifact.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return aggregate


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--arm", choices=("base", "tuned"), required=True)
    parser.add_argument(
        "--protocol", type=Path, default=root / "manifests" / "t2_coco_retention_protocol.json"
    )
    parser.add_argument("--datasets-root", type=Path, default=root.parents[1] / "e-ovrt_datasets")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    run_dir = args.run.resolve()
    aggregate = evaluate(
        run_dir=run_dir,
        arm=args.arm,
        protocol_path=args.protocol.resolve(),
        datasets_root=args.datasets_root.resolve(),
        out=(args.out or run_dir / "eval").resolve(),
    )
    print(
        json.dumps(
            {
                "arm": aggregate["arm"],
                "mAP50": aggregate["mAP50"],
                "classes_scored": aggregate["classes_scored"],
                "images": aggregate["images"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
