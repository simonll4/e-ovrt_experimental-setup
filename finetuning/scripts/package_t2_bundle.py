#!/usr/bin/env python3
"""Package the transportable T2 bundle (full fine-tuning, D-FT-14/D-FT-15).

Hermano de `package_t1_bundle.py`, cuyos helpers reutiliza sin modificarlo: aquel es
evidencia congelada de la corrida T1 y su inventario no debe cambiar.

Diferencias de inventario respecto de T1:
  - entra `configs/t2_yoloe26s_full.yaml`, `scripts/train_t2.py` y los dos scripts
    Slurm de T2;
  - **`scripts/train_t1.py` sigue entrando**: `train_t2.py` lo importa para reusar sus
    helpers puros (hashes, CSV de resultados, versiones de runtime). Sin él el bundle
    no arranca;
  - NO entran los scripts de autorización/finalización de T1: la puerta de T2 es propia
    (D-FT-15) y se arma en T-FT-063. El smoke no necesita ninguna.

La imagen Apptainer no se empaqueta acá (igual que en T1): se reutiliza la de T1, misma
ultralytics 8.4.86.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from materialize_t1_payload import sha256_file, verify_payload  # noqa: E402
from package_t1_bundle import _copy_tree, _git_state, _write_hashes  # noqa: E402

VERSIONED_FILES = (
    "configs/t2_yoloe26s_full.yaml",
    "containers/requirements-t1.txt",
    "containers/t1-yoloe.def",
    "manifests/finetuning_v1.summary.json",
    "manifests/finetuning_v1.split.csv",
    "manifests/t1_base_weights.json",
    "manifests/t1_container_image.json",
    "scripts/train_t1.py",
    "scripts/train_t2.py",
    "scripts/verify_t2_authorization.py",
    "scripts/evaluate_t2_coco_retention.py",
    "manifests/t2_coco_retention_protocol.json",
    "manifests/t2_yoloe26s_protocol.json",
    "manifests/t2_coco_retention_base_frozen.json",
    "slurm/run_t2_job.sh",
    "slurm/t2_smoke.sbatch",
    "slurm/t2_full.sbatch",
)


def package(*, finetuning_root: Path, payload: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing bundle: {output}")
    verify_payload(payload)
    weight_manifest = json.loads(
        (finetuning_root / "manifests" / "t1_base_weights.json").read_text(encoding="utf-8")
    )
    source_assets = finetuning_root / "weights" / "base"
    for record in weight_manifest["artifacts"]:
        source = source_assets / record["filename"]
        if source.stat().st_size != int(record["size_bytes"]) or sha256_file(source) != record["sha256"]:
            raise ValueError(f"base asset differs from manifest: {source}")

    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"stale temporary bundle exists: {temporary}")
    temporary.mkdir(parents=True)
    try:
        for relative in VERSIONED_FILES:
            source = finetuning_root / relative
            if not source.is_file():
                raise FileNotFoundError(source)
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for prompt_name in ("coco_val2017_80.yaml", "cr01_cr02_bench_v2.yaml"):
            prompt_source = finetuning_root.parent / "prompts" / prompt_name
            if not prompt_source.is_file():
                raise FileNotFoundError(prompt_source)
            prompt_target = temporary / "prompts" / prompt_name
            prompt_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(prompt_source, prompt_target)
        _copy_tree(payload, temporary / "data" / "finetuning_v1")
        for record in weight_manifest["artifacts"]:
            target = temporary / "weights" / "base" / record["filename"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_assets / record["filename"], target)

        metadata = {
            "schema_version": "eovrt.t2-bundle.v1",
            "name": "t2_yoloe26s_full",
            "tier": "T2",
            "decision": "D-FT-14/D-FT-15",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_repository": _git_state(finetuning_root.parent),
            "payload_manifest_sha256": sha256_file(payload / "payload.json"),
            "split_manifest_sha256": sha256_file(
                finetuning_root / "manifests" / "finetuning_v1.split.csv"
            ),
            "base_weight_manifest_sha256": sha256_file(
                finetuning_root / "manifests" / "t1_base_weights.json"
            ),
            "trainer_config_sha256": sha256_file(
                finetuning_root / "configs" / "t2_yoloe26s_full.yaml"
            ),
            # El brazo one-shot contra bench_v3 no se toca desde acá; el smoke tampoco
            # produce cifra citable. La autorización del full T2 es T-FT-063.
            "full_job_authorized": False,
            "files": sum(1 for item in temporary.rglob("*") if item.is_file()) + 1,
        }
        (temporary / "bundle.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        actual_files = _write_hashes(temporary)
        if actual_files != metadata["files"]:
            raise RuntimeError(
                f"bundle file count changed while packaging: {actual_files} != {metadata['files']}"
            )
        temporary.replace(output)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return metadata


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finetuning-root", type=Path, default=root)
    parser.add_argument("--payload", type=Path, default=root / "data" / "payloads" / "finetuning_v1")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = package(
        finetuning_root=args.finetuning_root.resolve(),
        payload=args.payload.resolve(),
        output=args.output.resolve(),
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
