#!/usr/bin/env python3
"""Comando de evaluación CONGELADO del protocolo T1 sobre bench_v3 (T-FT-031/032).

Es la única vía admitida para evaluar la baseline YOLOE-26s y el checkpoint
fine-tuneado T1 contra `bench_v3`: verifica TODOS los insumos congelados del
protocolo (`t1_yoloe26s_bench_v3_protocol.json`) por sha256 antes de computar,
exige cobertura completa del benchmark, y emite exactamente los artefactos que
el protocolo declara:

  - eval_perception.aggregate.json   (AP50 por clase + mAP50, bench completo)
  - eval_perception.by_stratum.json  (lo mismo por estrato, COCO fuente por estrato)
  - eval_cr01.by_source.json         (recall CR-01 por fuente + agregado por conteos)
  - protocol_snapshot.json           (el protocolo exacto usado)
  - artifact.sha256                  (hashes de todo lo emitido + detections.jsonl)

El cómputo lo hace `evaluate_bench.py` del repo `e-ovrt_datasets` — el mismo
evaluador congelado que usa `eovrt_media.tools.evaluate` — cargado por path y
verificado por hash. El mAP50 replica el criterio de
`eovrt_media.evaluation.runner._mean_ap50`: media de los AP50 no nulos.

Uso (una vez por brazo, regla one-shot del protocolo):

    python3 finetuning/scripts/evaluate_t1_bench_v3.py \
        --run finetuning/runs/t1_yoloe26s_baseline_bench_v3 --arm baseline
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = (
    REPO_ROOT / "finetuning" / "manifests" / "t1_yoloe26s_bench_v3_protocol.json"
)
DEFAULT_DATASETS_ROOT = REPO_ROOT.parent / "e-ovrt_datasets"
ARMS = ("baseline", "tuned")


class FrozenInputMismatch(RuntimeError):
    """Un insumo congelado no coincide con el sha256 del protocolo."""


class CoverageError(RuntimeError):
    """El run no procesó todas las imágenes del benchmark."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FrozenInputMismatch(f"{label}: no existe {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise FrozenInputMismatch(
            f"{label}: sha256 {actual} != congelado {expected} ({path.name})"
        )


def _load_evaluator(path: Path):
    spec = importlib.util.spec_from_file_location("t1_frozen_evaluate_bench", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mean_ap50(per_class: list[dict]) -> float | None:
    values = [c["AP50"] for c in per_class if c.get("AP50") is not None]
    return round(sum(values) / len(values), 6) if values else None


def _eval_coco(ev, coco_path: Path, detections_by_img: dict, iou: float) -> dict:
    images_by_filename, gt_by_image_id, cat_by_id = ev.load_bench_coco(coco_path)
    per_class = [
        {
            "class_name": raw["class"],
            "AP50": raw.get("AP50"),
            "n_gt": raw.get("n_gt", 0),
            "n_det": raw.get("n_det", 0),
        }
        for raw in (
            ev.evaluate_class(
                name, detections_by_img, images_by_filename, gt_by_image_id,
                cat_by_id, iou,
            )
            for name in cat_by_id.values()
        )
    ]
    return {
        "per_class": per_class,
        "mAP50": _mean_ap50(per_class),
        "images": len(images_by_filename),
        "coverage_keys": set(images_by_filename),
    }


def normalize_real_protocol(raw: dict) -> dict:
    """Traduce el manifiesto real del protocolo a la forma que consume el core."""
    bench = raw["benchmark"]
    return {
        "protocol_id": raw["protocol_id"],
        "evaluator": {
            "relative_path": "datasets/scripts/bench/evaluate_bench.py",
            "sha256": next(
                s["sha256"]
                for s in raw["evaluation"]["source_files"]
                if s["repository"] == "e-ovrt_datasets"
            ),
        },
        "benchmark": {
            "coco": {
                "relative_path": bench["coco"]["repository_relative_path"],
                "sha256": bench["coco"]["sha256"],
            },
            "strata": {
                name: {
                    "relative_path": s["source_coco_repository_relative_path"],
                    "sha256": s["source_coco_sha256"],
                }
                for name, s in bench["strata"].items()
            },
        },
        "cr01_sources": {
            s["id"]: {
                "relative_path": s["repository_relative_path"],
                "sha256": s["sha256"],
            }
            for s in raw["ground_truth"]["cr01_person_level"]["sources"]
        },
        "inference": {
            "iou_threshold": raw["evaluation"]["detection_match_iou_threshold"]
        },
        "_raw": raw,
    }


def run_frozen_evaluation(
    *,
    protocol: dict,
    datasets_root: Path,
    run_dir: Path,
    output_dir: Path,
    arm: str,
) -> dict:
    if arm not in ARMS:
        raise ValueError(f"arm debe ser uno de {ARMS}, no {arm!r}")

    datasets_root = Path(datasets_root)
    run_dir = Path(run_dir)
    detections_path = run_dir / "detections.jsonl"
    if not detections_path.is_file():
        raise FileNotFoundError(f"no existe {detections_path}")

    # 1) Verificación TOTAL de insumos congelados, antes de computar o escribir.
    evaluator_path = datasets_root / protocol["evaluator"]["relative_path"]
    _verify(evaluator_path, protocol["evaluator"]["sha256"], "evaluador")
    bench_cfg = protocol["benchmark"]["coco"]
    bench_path = datasets_root / bench_cfg["relative_path"]
    _verify(bench_path, bench_cfg["sha256"], "bench COCO")
    strata_paths: dict[str, Path] = {}
    for name, cfg in protocol["benchmark"]["strata"].items():
        p = datasets_root / cfg["relative_path"]
        _verify(p, cfg["sha256"], f"estrato {name}")
        strata_paths[name] = p
    cr01_paths: dict[str, Path] = {}
    for name, cfg in protocol["cr01_sources"].items():
        p = datasets_root / cfg["relative_path"]
        _verify(p, cfg["sha256"], f"person GT {name}")
        cr01_paths[name] = p

    ev = _load_evaluator(evaluator_path)
    iou = float(protocol["inference"]["iou_threshold"])
    detections_by_img = ev.load_detections([detections_path])

    # 2) Cobertura completa: toda imagen del bench debe haber sido procesada
    #    (presente en detections.jsonl aunque tenga cero detecciones).
    aggregate = _eval_coco(ev, bench_path, detections_by_img, iou)
    missing = sorted(aggregate["coverage_keys"] - set(detections_by_img))
    if missing:
        raise CoverageError(
            f"el run no procesó {len(missing)} imágenes del bench; "
            f"primeras: {missing[:5]}"
        )

    # 3) Por estrato (el evaluador ignora detecciones de imágenes fuera del COCO).
    by_stratum = {}
    for name, path in strata_paths.items():
        result = _eval_coco(ev, path, detections_by_img, iou)
        result.pop("coverage_keys")
        by_stratum[name] = result

    # 4) CR-01 por fuente, cada fuente por separado (nunca el combinado histórico),
    #    más el agregado transparente por conteos.
    images_by_filename, _, _ = ev.load_bench_coco(bench_path)
    cr01_by_source = {}
    total_violators = 0
    total_detected = 0
    for name, path in cr01_paths.items():
        records = ev.load_person_gt(path)
        result = ev.evaluate_cr01(records, detections_by_img, images_by_filename, iou)
        cr01_by_source[name] = result
        total_violators += result.get("n_violators", 0)
        total_detected += result.get("n_detected", 0)

    evaluated_at = datetime.now(timezone.utc).isoformat()
    common = {
        "protocol_id": protocol["protocol_id"],
        "arm": arm,
        "run_dir": str(run_dir),
        "iou_threshold": iou,
        "evaluated_at": evaluated_at,
    }
    aggregate_out = {
        **common,
        "benchmark": bench_path.name,
        "per_class": aggregate["per_class"],
        "mAP50": aggregate["mAP50"],
        "images": aggregate["images"],
        "cr01_note": "el recall CR-01 vive en eval_cr01.by_source.json, por fuente",
    }
    by_stratum_out = {**common, "strata": by_stratum}
    cr01_out = {
        **common,
        "policy": "cada fuente elegible por separado; nunca el person_gt combinado",
        "sources": cr01_by_source,
        "count_weighted_aggregate": {
            "n_violators": total_violators,
            "n_detected": total_detected,
            "recall": (
                round(total_detected / total_violators, 4) if total_violators else None
            ),
        },
    }

    # 5) Persistencia + hashes de artefactos.
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "eval_perception.aggregate.json": aggregate_out,
        "eval_perception.by_stratum.json": by_stratum_out,
        "eval_cr01.by_source.json": cr01_out,
        "protocol_snapshot.json": protocol.get("_raw", protocol),
    }
    for name, payload in artifacts.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
    sha_lines = [
        f"{sha256_file(output_dir / name)}  {name}" for name in artifacts
    ] + [f"{sha256_file(detections_path)}  detections.jsonl"]
    (output_dir / "artifact.sha256").write_text(
        "\n".join(sha_lines) + "\n", encoding="utf-8"
    )

    return {
        "arm": arm,
        "output_dir": str(output_dir),
        "mAP50": aggregate["mAP50"],
        "coverage": {"bench_images": aggregate["images"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--datasets-root", type=Path, default=DEFAULT_DATASETS_ROOT)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="default: <run>/eval (los artefactos del protocolo)",
    )
    args = parser.parse_args()

    raw = json.loads(args.protocol.read_text(encoding="utf-8"))
    protocol = normalize_real_protocol(raw)
    output_dir = args.out if args.out is not None else args.run / "eval"
    result = run_frozen_evaluation(
        protocol=protocol,
        datasets_root=args.datasets_root,
        run_dir=args.run,
        output_dir=output_dir,
        arm=args.arm,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
