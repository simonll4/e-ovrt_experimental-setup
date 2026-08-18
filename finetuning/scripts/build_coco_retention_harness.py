#!/usr/bin/env python3
"""Construye el arnés de retención open-vocabulary sobre COCO val2017 (T-FT-062, D-FT-04).

Qué produce, de forma determinística (mismo COCO -> mismos hashes):

  1. `prompts/coco_val2017_80.yaml`  — prompt set de las 80 categorías COCO. El `id` de
     cada clase es el **nombre COCO exacto**, espacios incluidos ("traffic light"),
     porque el evaluador congelado matchea `prompt_id == class_name` contra el nombre de
     la categoría. Un id con guiones bajos rompería el match en silencio.
  2. `manifests/t2_coco_retention_protocol.json` — el protocolo congelado: hashes del GT,
     inventario de categorías, conteos e insumos. Es lo que hace verificable que el brazo
     base y el brazo tuned se midieron contra exactamente lo mismo.

Por qué existe: T1 no podía medir retención generalista (su head quedó fusionado a 4
clases, D-FT-08). T2 conserva la interfaz de texto, así que la erosión open-vocabulary
pasa de ser una preocupación declarada a una cifra. La baseline de retención se corre y
se congela ANTES de entrenar T2 — si se corriera después, dejaría de ser una vara.

No descarga nada ni entrena nada: sólo lee el COCO ya presente y escribe dos archivos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "eovrt.t2-coco-retention-protocol.v1"
EXPECTED_CATEGORIES = 80
EXPECTED_IMAGES = 5000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_coco(annotations: Path) -> dict[str, object]:
    data = json.loads(annotations.read_text(encoding="utf-8"))
    categories = sorted(data["categories"], key=lambda c: int(c["id"]))
    if len(categories) != EXPECTED_CATEGORIES:
        raise ValueError(f"COCO val2017 debe traer {EXPECTED_CATEGORIES} categorías")
    if len(data["images"]) != EXPECTED_IMAGES:
        raise ValueError(f"COCO val2017 debe traer {EXPECTED_IMAGES} imágenes")
    return {
        "categories": categories,
        "images": data["images"],
        "annotations": data["annotations"],
    }


def render_prompts(categories: list[dict]) -> str:
    lines = [
        "prompt_set:",
        "  id: coco_val2017_80",
        "  description: >",
        "    Vocabulario COCO val2017 (80 categorías) para medir RETENCIÓN",
        "    open-vocabulary del checkpoint T2 (D-FT-04/T-FT-062). Generado por",
        "    finetuning/scripts/build_coco_retention_harness.py — no editar a mano.",
        "    El id de cada clase es el nombre COCO EXACTO: el evaluador congelado",
        "    matchea prompt_id contra el nombre de la categoría.",
        "  language: en",
        "  status: frozen",
        "  track: retention",
        "  classes:",
    ]
    for category in categories:
        name = str(category["name"])
        lines.append(f'    - id: "{name}"')
        lines.append("      role: coco_generalist")
        lines.append("      strategy: canonical_positive")
        lines.append(f'      phrasings: {{ default: ["{name}"] }}')
    return "\n".join(lines) + "\n"


def build(*, annotations: Path, images_dir: Path, prompts_out: Path, manifest_out: Path) -> dict:
    coco = load_coco(annotations)
    categories = coco["categories"]
    names = [str(c["name"]) for c in categories]

    present = sorted(p.name for p in images_dir.iterdir() if p.suffix.lower() == ".jpg")
    declared = sorted(str(img["file_name"]) for img in coco["images"])
    if present != declared:
        missing = set(declared) - set(present)
        extra = set(present) - set(declared)
        raise ValueError(
            f"el directorio de imágenes no coincide con el GT: faltan {len(missing)}, sobran {len(extra)}"
        )

    prompts_out.parent.mkdir(parents=True, exist_ok=True)
    prompts_out.write_text(render_prompts(categories), encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "T-FT-062",
        "decision": "D-FT-04 (subset y métrica de retención OV), habilitada por D-FT-14",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "medir la erosión open-vocabulary del checkpoint T2 contra el peso base, "
            "sobre un subset generalista ajeno al dominio de obra"
        ),
        "benchmark": {
            "id": "coco_val2017",
            "policy": "read_only_external_benchmark",
            "images": len(coco["images"]),
            "annotations": len(coco["annotations"]),
            "categories": len(categories),
            "images_dir": str(images_dir),
            "annotations_path": str(annotations),
            "annotations_sha256": sha256_file(annotations),
            "image_basenames_sha256": _sha256_text("\n".join(declared)),
            "license": "CC BY 4.0 (COCO 2017; anotaciones bajo CC BY 4.0)",
            "source_url": "http://images.cocodataset.org/zips/val2017.zip",
        },
        "prompts": {
            "path": str(prompts_out),
            "set_id": "coco_val2017_80",
            "sha256": sha256_file(prompts_out),
            "class_ids_sha256": _sha256_text("\n".join(names)),
            "class_ids": names,
            "id_convention": "nombre COCO exacto (con espacios); el evaluador matchea prompt_id == class_name",
        },
        "metric": {
            "primary": "mAP50 sobre las 80 clases (media de los AP50 no nulos)",
            "iou_threshold": 0.5,
            "gate": "caída relativa <= 10 % del tuned respecto del base (D-FT-15 §3)",
            "reporting": (
                "se reporta SIEMPRE junto al resultado in-domain; una erosión mayor al gate "
                "implica NO-GO y es a la vez la medición central del tier"
            ),
        },
        "arms": {
            "base": {
                "model_ref": "yoloe/yoloe-26s",
                "status": "pendiente de correr y congelar ANTES de entrenar T2",
            },
            "tuned": {
                "model_ref": "yoloe/yoloe-26s-ft-t2",
                "status": "pendiente del checkpoint T2",
            },
        },
        "one_shot_rule": (
            "un brazo, una evaluación; el brazo base se congela antes de que exista el "
            "checkpoint T2 para que no pueda elegirse después de ver el resultado"
        ),
    }
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    temporary = manifest_out.with_suffix(manifest_out.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(manifest_out)
    return manifest


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    datasets_root = root.parents[1] / "e-ovrt_datasets" / "datasets" / "raw" / "coco_val2017"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=datasets_root / "annotations" / "instances_val2017.json")
    parser.add_argument("--images", type=Path, default=datasets_root / "val2017")
    parser.add_argument("--prompts-out", type=Path, default=root.parent / "prompts" / "coco_val2017_80.yaml")
    parser.add_argument("--manifest-out", type=Path, default=root / "manifests" / "t2_coco_retention_protocol.json")
    args = parser.parse_args(argv)
    manifest = build(
        annotations=args.annotations.resolve(),
        images_dir=args.images.resolve(),
        prompts_out=args.prompts_out.resolve(),
        manifest_out=args.manifest_out.resolve(),
    )
    print(
        json.dumps(
            {
                "status": "coco_retention_harness_built",
                "images": manifest["benchmark"]["images"],
                "categories": manifest["benchmark"]["categories"],
                "annotations_sha256": manifest["benchmark"]["annotations_sha256"],
                "prompts_sha256": manifest["prompts"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
