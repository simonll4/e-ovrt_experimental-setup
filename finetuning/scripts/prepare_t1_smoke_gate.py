#!/usr/bin/env python3
"""Create the manual-full gate from an audited successful T1 smoke run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from verify_t1_smoke_gate import (
    EXPECTED_CRITICAL_FILES,
    EXPECTED_SCHEMA,
    sha256_file,
    verify_gate,
)
from train_t1 import (
    audit_optimizer_checkpoint,
    load_config,
    resolve_profile,
    validate_trainable_contract,
)

CRITICAL_FILES = tuple(sorted(EXPECTED_CRITICAL_FILES))


def create_gate(
    *,
    bundle: Path,
    image: Path,
    run_manifest: Path,
    smoke_bundle_hash_manifest: Path,
    output: Path,
) -> dict[str, object]:
    bundle = bundle.resolve()
    image = image.resolve()
    run_manifest = run_manifest.resolve()
    launch = json.loads(run_manifest.read_text(encoding="utf-8"))
    smoke_bundle_hash_manifest = smoke_bundle_hash_manifest.resolve()
    smoke = launch.get("checkpoint_inference_smoke", {})
    versions = launch.get("versions", {})
    if launch.get("schema_version") != "eovrt.t1-run.v1":
        raise ValueError("unexpected smoke run manifest schema")
    if launch.get("status") != "succeeded" or launch.get("profile") != "smoke":
        raise ValueError("run manifest is not a successful smoke")
    config = load_config(bundle / "configs" / "t1_yoloe26s_lp.yaml")
    profile = resolve_profile(config, "smoke")
    if launch.get("trainer") != profile:
        raise ValueError("smoke run manifest differs from the complete frozen profile")
    if launch.get("completed_epochs") != [1]:
        raise ValueError("smoke did not complete exactly epoch 1")
    trainable_contract = launch.get("trainable_contract")
    if not isinstance(trainable_contract, dict):
        raise ValueError("smoke lacks the T1 trainable contract")
    validate_trainable_contract(
        trainable_contract, config["trainer"], require_optimizer=True
    )
    if smoke.get("status") != "passed":
        raise ValueError("checkpoint inference smoke did not pass")
    if not versions.get("cuda_available") or versions.get("cuda_device_count", 0) < 1:
        raise ValueError("smoke did not execute with CUDA")
    image_sha256 = sha256_file(image)
    if launch.get("container_image_sha256") != image_sha256:
        raise ValueError("run manifest container hash differs from staged image")
    smoke_bundle_manifest_sha256 = sha256_file(smoke_bundle_hash_manifest)
    if launch.get("bundle_manifest_sha256") != smoke_bundle_manifest_sha256:
        raise ValueError("archived bundle hash manifest does not belong to this smoke")
    smoke_bundle_hashes = {}
    for raw_line in smoke_bundle_hash_manifest.read_text(encoding="utf-8").splitlines():
        expected, separator, relative = raw_line.partition("  ")
        if not separator or len(expected) != 64:
            raise ValueError("archived smoke bundle hash manifest is malformed")
        smoke_bundle_hashes[relative] = expected

    expected_launch_hashes = {
        "configs/t1_yoloe26s_lp.yaml": "config_sha256",
        "data/finetuning_v1/data.yaml": "data_yaml_sha256",
        "manifests/finetuning_v1.summary.json": "data_manifest_sha256",
        "weights/base/yoloe-26s-seg.pt": "base_weight_sha256",
        "weights/base/mobileclip2_b.ts": "text_encoder_sha256",
    }
    critical = {}
    for relative in CRITICAL_FILES:
        target = bundle / relative
        if not target.is_file() or target.is_symlink():
            raise ValueError(f"missing critical smoke input: {relative}")
        actual = sha256_file(target)
        if smoke_bundle_hashes.get(relative) != actual:
            raise ValueError(f"current critical file differs from smoke bundle: {relative}")
        launch_key = expected_launch_hashes.get(relative)
        if launch_key and launch.get(launch_key) != actual:
            raise ValueError(f"smoke run did not use current {relative}")
        critical[relative] = actual

    run_dir = run_manifest.parent
    artifact_paths = {
        "best.pt": run_dir / "weights" / "best.pt",
        "last.pt": run_dir / "weights" / "last.pt",
        "results.csv": run_dir / "results.csv",
        "epoch0.pt": run_dir / "weights" / "epoch0.pt",
    }
    if set(launch.get("artifacts", {})) != set(artifact_paths):
        raise ValueError("smoke artifact inventory is incomplete or unexpected")
    for name, record in launch.get("artifacts", {}).items():
        artifact = artifact_paths.get(name)
        if (
            artifact is None
            or not artifact.is_file()
            or artifact.stat().st_size != record.get("size_bytes")
            or sha256_file(artifact) != record.get("sha256")
        ):
            raise ValueError(f"smoke artifact integrity failure: {name}")
    checkpoint_smoke = run_dir / "checkpoint_smoke.json"
    if not checkpoint_smoke.is_file():
        raise ValueError("smoke run is missing checkpoint_smoke.json")
    optimizer_evidence = audit_optimizer_checkpoint(
        artifact_paths["epoch0.pt"],
        expected_epoch=0,
        expected_profile=profile,
        expected_parameter_tensors=int(config["trainer"]["expected_trainable_tensors"]),
    )
    if launch.get("optimizer_evidence") != optimizer_evidence:
        raise ValueError("smoke optimizer evidence differs from epoch0.pt")

    gate = {
        "schema_version": EXPECTED_SCHEMA,
        "status": "technical_smoke_ready",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment_id": "t1_yoloe26s_lp",
        "full_epochs": 10,
        "container_image_sha256": image_sha256,
        "critical_files": critical,
        "smoke": {
            "job_id": str(launch.get("slurm", {}).get("SLURM_JOB_ID")),
            "run_name": launch.get("run_name"),
            "run_manifest_sha256": sha256_file(run_manifest),
            "bundle_manifest_sha256": launch.get("bundle_manifest_sha256"),
            "archived_bundle_hash_manifest": smoke_bundle_hash_manifest.name,
            "checkpoint_smoke_sha256": sha256_file(checkpoint_smoke),
            "best_checkpoint_sha256": launch["artifacts"]["best.pt"]["sha256"],
            "last_checkpoint_sha256": launch["artifacts"]["last.pt"]["sha256"],
            "cuda_device": versions.get("cuda_device"),
            "elapsed_seconds": launch.get("elapsed_seconds"),
            "trainable_contract": trainable_contract,
            "optimizer_evidence": optimizer_evidence,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    verify_gate(bundle=bundle, image=image, gate_path=output)
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--smoke-bundle-hash-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    gate = create_gate(
        bundle=args.bundle,
        image=args.image,
        run_manifest=args.run_manifest,
        smoke_bundle_hash_manifest=args.smoke_bundle_hash_manifest,
        output=args.output,
    )
    print(
        f"smoke_gate_created={args.output.resolve()} "
        f"job_id={gate['smoke']['job_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
