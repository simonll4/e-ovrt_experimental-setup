#!/usr/bin/env python3
"""Audit a completed 10-epoch T1 run and emit a hash-bound completion record."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from train_t1 import (
    EXPECTED_CLASSES,
    _best_epoch,
    _validate_epoch_schedule,
    audit_optimizer_checkpoint,
    load_config,
    resolve_profile,
    sha256_file,
    validate_trainable_contract,
)


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def audit_full(
    *, bundle: Path, image: Path, run_manifest: Path, job_id: str, output: Path
) -> dict[str, object]:
    bundle = bundle.resolve()
    image = image.resolve()
    run_manifest = run_manifest.resolve()
    launch = json.loads(run_manifest.read_text(encoding="utf-8"))
    config_path = bundle / "configs" / "t1_yoloe26s_lp.yaml"
    config = load_config(config_path)
    if launch.get("schema_version") != "eovrt.t1-run.v1":
        raise ValueError("unexpected full run manifest schema")
    if launch.get("status") != "succeeded" or launch.get("profile") != "full":
        raise ValueError("run manifest is not a successful full T1 run")
    if str(launch.get("slurm", {}).get("SLURM_JOB_ID")) != job_id:
        raise ValueError("run manifest Slurm job id differs from requested audit")
    if launch.get("run_name") != f"full-{job_id}":
        raise ValueError("run manifest name differs from the full job id")
    profile = resolve_profile(config, "full")
    if launch.get("trainer") != profile:
        raise ValueError("full run did not use the complete frozen trainer profile")
    if launch.get("completed_epochs") != list(range(1, 11)):
        raise ValueError("full run manifest does not record exactly epochs 1..10")
    versions = launch.get("versions", {})
    if not versions.get("cuda_available") or int(versions.get("cuda_device_count", 0)) < 1:
        raise ValueError("full run did not execute with CUDA")
    if launch.get("container_image_sha256") != sha256_file(image):
        raise ValueError("full run container hash differs from the staged image")

    expected_inputs = {
        "bundle_manifest_sha256": sha256_file(bundle / "bundle.sha256"),
        "config_sha256": sha256_file(config_path),
        "data_yaml_sha256": sha256_file(bundle / config["data"]["yaml"]),
        "data_manifest_sha256": sha256_file(bundle / config["data"]["manifest"]),
        "base_weight_sha256": sha256_file(bundle / config["model"]["base_weight"]),
        "text_encoder_sha256": sha256_file(bundle / config["model"]["text_encoder"]),
    }
    for key, expected in expected_inputs.items():
        if launch.get(key) != expected:
            raise ValueError(f"full run input hash differs from active bundle: {key}")

    contract = launch.get("trainable_contract", {})
    validate_trainable_contract(contract, config["trainer"], require_optimizer=True)

    run_dir = run_manifest.parent
    artifacts = launch.get("artifacts", {})
    expected_artifacts = {
        "best.pt": run_dir / "weights" / "best.pt",
        "last.pt": run_dir / "weights" / "last.pt",
        "results.csv": run_dir / "results.csv",
        "epoch9.pt": run_dir / "weights" / "epoch9.pt",
    }
    if set(artifacts) != set(expected_artifacts):
        raise ValueError("full run artifact inventory is incomplete or has unexpected entries")
    for name, path in expected_artifacts.items():
        record = artifacts[name]
        if (
            not path.is_file()
            or path.stat().st_size != int(record.get("size_bytes", -1))
            or sha256_file(path) != record.get("sha256")
        ):
            raise ValueError(f"full run artifact integrity failure: {name}")
    results_csv = expected_artifacts["results.csv"]
    _validate_epoch_schedule(results_csv, 10)
    if launch.get("best_epoch") != _best_epoch(results_csv):
        raise ValueError("full run best-epoch record differs from results.csv")
    optimizer_evidence = audit_optimizer_checkpoint(
        expected_artifacts["epoch9.pt"],
        expected_epoch=9,
        expected_profile=profile,
        expected_parameter_tensors=int(config["trainer"]["expected_trainable_tensors"]),
    )
    if launch.get("optimizer_evidence") != optimizer_evidence:
        raise ValueError("full optimizer evidence differs from epoch9.pt")

    checkpoint_smoke_path = run_dir / "checkpoint_smoke.json"
    checkpoint_smoke = json.loads(checkpoint_smoke_path.read_text(encoding="utf-8"))
    vocabulary = [
        (int(key), value)
        for key, value in checkpoint_smoke.get("vocabulary", {}).items()
    ]
    if (
        checkpoint_smoke.get("status") != "passed"
        or vocabulary != list(EXPECTED_CLASSES.items())
    ):
        raise ValueError("full best-checkpoint inference smoke did not pass the fixed vocabulary")
    if checkpoint_smoke.get("checkpoint_sha256") != artifacts["best.pt"]["sha256"]:
        raise ValueError("full checkpoint smoke hash differs from best.pt")

    result = {
        "schema_version": "eovrt.t1-full-audit.v1",
        "status": "full_t1_completed_and_audited",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "run_name": launch["run_name"],
        "run_manifest_sha256": sha256_file(run_manifest),
        "bundle_manifest_sha256": expected_inputs["bundle_manifest_sha256"],
        "container_image_sha256": sha256_file(image),
        "completed_epochs": list(range(1, 11)),
        "best_epoch": launch["best_epoch"],
        "artifacts": artifacts,
        "checkpoint_smoke_sha256": sha256_file(checkpoint_smoke_path),
        "trainable_contract": contract,
        "optimizer_evidence": optimizer_evidence,
        "cuda_device": versions.get("cuda_device"),
        "elapsed_seconds": launch.get("elapsed_seconds"),
    }
    _write_json(output, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_full(
        bundle=args.bundle,
        image=args.image,
        run_manifest=args.run_manifest,
        job_id=args.job_id,
        output=args.output,
    )
    print(f"T1_FULL_AUDIT_OK job_id={result['job_id']} output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
