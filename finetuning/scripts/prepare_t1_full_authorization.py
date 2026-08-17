#!/usr/bin/env python3
"""Create the hash-bound scientific authorization for a manual full T1 run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from verify_t1_full_authorization import (
    EXPECTED_GATES,
    EXPECTED_SCHEMA,
    sha256_file,
    verify_authorization,
)


def _parse_evidence(values: list[str], root: Path) -> dict[str, dict[str, str]]:
    parsed: dict[str, Path] = {}
    for value in values:
        task_id, separator, raw_path = value.partition("=")
        if not separator or not task_id or not raw_path:
            raise ValueError(f"evidence must use TASK_ID=relative/path: {value!r}")
        if task_id in parsed:
            raise ValueError(f"duplicate evidence task: {task_id}")
        relative = Path(raw_path)
        if relative.is_absolute():
            raise ValueError(f"evidence path must be relative: {value!r}")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ValueError(f"evidence path escapes authorization root: {value!r}") from error
        parsed[task_id] = target
    if set(parsed) != set(EXPECTED_GATES):
        missing = sorted(set(EXPECTED_GATES) - set(parsed))
        extra = sorted(set(parsed) - set(EXPECTED_GATES))
        raise ValueError(f"evidence task inventory mismatch: missing={missing}, extra={extra}")

    evidence = {}
    for task_id, target in parsed.items():
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"evidence must be a regular file: {task_id}={target}")
        evidence[task_id] = {
            "path": target.relative_to(root).as_posix(),
            "sha256": sha256_file(target),
        }
    return evidence


def create_authorization(
    *,
    approval: str,
    bundle_manifest: Path,
    smoke_gate: Path,
    evidence_values: list[str],
    output: Path,
) -> dict[str, object]:
    if approval != "APPROVE_D_FT_08":
        raise ValueError("D-FT-08 requires the exact approval token APPROVE_D_FT_08")
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite authorization: {output}")
    root = output.parent
    root.mkdir(parents=True, exist_ok=True)
    bundle_manifest = bundle_manifest.resolve()
    smoke_gate = smoke_gate.resolve()
    evidence = _parse_evidence(evidence_values, root)
    authorization = {
        "schema_version": EXPECTED_SCHEMA,
        "status": "authorized_for_manual_full_t1",
        "experiment_id": "t1_yoloe26s_lp",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "decision": {"id": "D-FT-08", "status": "approved"},
        "gates": EXPECTED_GATES,
        "bindings": {
            "bundle_manifest_sha256": sha256_file(bundle_manifest),
            "smoke_gate_sha256": sha256_file(smoke_gate),
        },
        "evidence": evidence,
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(authorization, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    verify_authorization(
        authorization_path=output,
        bundle_manifest=bundle_manifest,
        smoke_gate=smoke_gate,
    )
    return authorization


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--bundle-manifest", type=Path, required=True)
    parser.add_argument("--smoke-gate", type=Path, required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    authorization = create_authorization(
        approval=args.approval,
        bundle_manifest=args.bundle_manifest,
        smoke_gate=args.smoke_gate,
        evidence_values=args.evidence,
        output=args.output,
    )
    print(
        f"full_authorization_created={args.output.resolve()} "
        f"gates={len(authorization['gates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
