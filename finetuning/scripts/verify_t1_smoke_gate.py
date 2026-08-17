#!/usr/bin/env python3
"""Verify that a successful T1 smoke covers the exact training-critical inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from train_t1 import (
    expected_effective_profile,
    load_config,
    resolve_profile,
    validate_trainable_contract,
)

EXPECTED_SCHEMA = "eovrt.t1-smoke-gate.v2"
EXPECTED_CRITICAL_FILES = frozenset(
    {
        "configs/t1_yoloe26s_lp.yaml",
        "scripts/audit_t1_full.py",
        "scripts/finalize_t1_full_mendieta.sh",
        "scripts/submit_t1_full_mendieta.sh",
        "scripts/train_t1.py",
        "scripts/verify_t1_bundle.py",
        "scripts/prepare_t1_full_authorization.py",
        "scripts/verify_t1_full_authorization.py",
        "scripts/verify_t1_smoke_gate.py",
        "scripts/watch_finalize_t1_full_mendieta.sh",
        "slurm/run_t1_job.sh",
        "slurm/t1_full.sbatch",
        "data/finetuning_v1/data.yaml",
        "data/finetuning_v1/payload.json",
        "data/finetuning_v1/payload.sha256",
        "manifests/finetuning_v1.summary.json",
        "manifests/t1_base_weights.json",
        "weights/base/yoloe-26s-seg.pt",
        "weights/base/mobileclip2_b.ts",
        "weights/base/yolo26n.pt",
    }
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_gate(*, bundle: Path, image: Path, gate_path: Path) -> dict[str, object]:
    bundle = bundle.resolve()
    image = image.resolve()
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(f"smoke gate schema must be {EXPECTED_SCHEMA}")
    if gate.get("status") != "technical_smoke_ready":
        raise ValueError("smoke gate does not certify the technical T1 smoke")
    if gate.get("experiment_id") != "t1_yoloe26s_lp" or int(gate.get("full_epochs", 0)) != 10:
        raise ValueError("smoke gate does not cover the frozen 10-epoch T1 experiment")
    if sha256_file(image) != gate.get("container_image_sha256"):
        raise ValueError("container image differs from the smoke-tested image")

    critical = gate.get("critical_files")
    if not isinstance(critical, dict) or not critical:
        raise ValueError("smoke gate has no critical file inventory")
    if set(critical) != EXPECTED_CRITICAL_FILES:
        missing = sorted(EXPECTED_CRITICAL_FILES - set(critical))
        extra = sorted(set(critical) - EXPECTED_CRITICAL_FILES)
        raise ValueError(f"smoke gate critical inventory mismatch: missing={missing}, extra={extra}")
    for relative, expected in critical.items():
        target = (bundle / relative).resolve()
        try:
            target.relative_to(bundle)
        except ValueError as error:
            raise ValueError(f"critical path escapes bundle: {relative}") from error
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"missing critical file: {relative}")
        actual = sha256_file(target)
        if actual != expected:
            raise ValueError(f"critical file differs from smoke: {relative}")
    smoke = gate.get("smoke")
    if not isinstance(smoke, dict) or not str(smoke.get("job_id", "")).isdigit():
        raise ValueError("smoke gate has no valid Slurm job id")
    for key in (
        "run_manifest_sha256",
        "bundle_manifest_sha256",
        "checkpoint_smoke_sha256",
        "best_checkpoint_sha256",
        "last_checkpoint_sha256",
    ):
        value = smoke.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"smoke gate has invalid {key}")
    if not smoke.get("cuda_device") or float(smoke.get("elapsed_seconds", 0)) <= 0:
        raise ValueError("smoke gate does not record a valid CUDA execution")
    contract = smoke.get("trainable_contract")
    if not isinstance(contract, dict):
        raise ValueError("smoke gate has no trainable contract")
    config = load_config(bundle / "configs" / "t1_yoloe26s_lp.yaml")
    validate_trainable_contract(contract, config["trainer"], require_optimizer=True)
    optimizer = smoke.get("optimizer_evidence")
    expected_tensors = int(config["trainer"]["expected_trainable_tensors"])
    if not isinstance(optimizer, dict):
        raise ValueError("smoke gate has no independent optimizer evidence")
    expected_optimizer = {
        "checkpoint": "epoch0.pt",
        "epoch_zero_based": 0,
        "optimizer_parameter_tensors": expected_tensors,
        "optimizer_state_tensors": expected_tensors,
        "state_indices_match_parameter_groups": True,
        "effective_profile": expected_effective_profile(resolve_profile(config, "smoke")),
    }
    if any(optimizer.get(key) != value for key, value in expected_optimizer.items()):
        raise ValueError("smoke optimizer evidence differs from the frozen technical contract")
    for key in ("checkpoint_sha256",):
        value = optimizer.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"smoke optimizer evidence has invalid {key}")
    if int(optimizer.get("size_bytes", 0)) <= 0:
        raise ValueError("smoke optimizer checkpoint size is invalid")
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    args = parser.parse_args(argv)
    gate = verify_gate(bundle=args.bundle, image=args.image, gate_path=args.gate)
    print(
        "smoke_gate_ok="
        f"{args.gate.resolve()} job_id={gate['smoke']['job_id']} "
        f"critical_files={len(gate['critical_files'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
