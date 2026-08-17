#!/usr/bin/env python3
"""Verify the independent scientific authorization required before full T1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SCHEMA = "eovrt.t1-full-authorization.v1"
EXPECTED_DECISION = "D-FT-08"
EXPECTED_GATES = {
    "T-FT-005": "fixed_vocabulary_decision_approved",
    "T-FT-023": "provenance_frozen",
    "T-FT-026": "dual_authorization_gate_implemented",
    "T-FT-030": "fixed_vocabulary_serving_passed",
    "T-FT-031": "checkpoint_evaluation_passed",
    "T-FT-032": "bench_v3_baseline_frozen",
    "T-FT-042R": "technical_smoke_passed",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_authorization(
    *, authorization_path: Path, bundle_manifest: Path, smoke_gate: Path
) -> dict[str, object]:
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if authorization.get("schema_version") != EXPECTED_SCHEMA:
        raise ValueError(f"full authorization schema must be {EXPECTED_SCHEMA}")
    if authorization.get("status") != "authorized_for_manual_full_t1":
        raise ValueError("full authorization does not authorize manual T1 submission")
    if authorization.get("experiment_id") != "t1_yoloe26s_lp":
        raise ValueError("full authorization names a different experiment")
    if authorization.get("decision") != {
        "id": EXPECTED_DECISION,
        "status": "approved",
    }:
        raise ValueError(f"{EXPECTED_DECISION} is not explicitly approved")
    if authorization.get("gates") != EXPECTED_GATES:
        raise ValueError("full authorization does not close the exact required gate set")

    bindings = authorization.get("bindings")
    expected_bindings = {
        "bundle_manifest_sha256": sha256_file(bundle_manifest),
        "smoke_gate_sha256": sha256_file(smoke_gate),
    }
    if bindings != expected_bindings:
        raise ValueError("full authorization is not bound to the active bundle and smoke")

    evidence = authorization.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(EXPECTED_GATES):
        raise ValueError("full authorization lacks the exact evidence inventory")
    authorization_root = authorization_path.parent.resolve()
    for task_id, record in evidence.items():
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise ValueError(f"invalid evidence record for {task_id}")
        relative = Path(str(record["path"]))
        if relative.is_absolute():
            raise ValueError(f"evidence path must be relative: {task_id}")
        target = (authorization_root / relative).resolve()
        try:
            target.relative_to(authorization_root)
        except ValueError as error:
            raise ValueError(f"evidence path escapes authorization root: {task_id}") from error
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"missing evidence file for {task_id}: {relative}")
        if sha256_file(target) != record["sha256"]:
            raise ValueError(f"evidence hash mismatch for {task_id}")
    return authorization


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--bundle-manifest", type=Path, required=True)
    parser.add_argument("--smoke-gate", type=Path, required=True)
    args = parser.parse_args(argv)
    authorization = verify_authorization(
        authorization_path=args.authorization,
        bundle_manifest=args.bundle_manifest,
        smoke_gate=args.smoke_gate,
    )
    print(
        "full_authorization_ok="
        f"{args.authorization.resolve()} decision={authorization['decision']['id']} "
        f"gates={len(authorization['gates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
