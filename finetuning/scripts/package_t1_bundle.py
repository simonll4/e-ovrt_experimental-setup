#!/usr/bin/env python3
"""Package code, payload and base assets into one hash-addressed T1 bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from materialize_t1_payload import sha256_file, verify_payload

VERSIONED_FILES = (
    "configs/t1_yoloe26s_lp.yaml",
    "containers/requirements-t1.txt",
    "containers/t1-yoloe.def",
    "manifests/finetuning_v1.summary.json",
    "manifests/finetuning_v1.split.csv",
    "manifests/t1_base_weights.json",
    "manifests/t1_container_image.json",
    "scripts/build_t1_image_login.sh",
    "scripts/audit_t1_full.py",
    "scripts/finalize_t1_full_mendieta.sh",
    "scripts/finalize_t1_smoke_mendieta.sh",
    "scripts/prepare_t1_smoke_gate.py",
    "scripts/prepare_t1_full_authorization.py",
    "scripts/submit_t1_full_mendieta.sh",
    "scripts/train_t1.py",
    "scripts/verify_t1_bundle.py",
    "scripts/verify_t1_full_authorization.py",
    "scripts/verify_t1_smoke_gate.py",
    "scripts/watch_finalize_t1_smoke_mendieta.sh",
    "scripts/watch_finalize_t1_full_mendieta.sh",
    "slurm/run_t1_job.sh",
    "slurm/t1_smoke.sbatch",
    "slurm/t1_full.sbatch",
)


def _git_state(repo: Path) -> dict[str, object]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, check=True, text=True, capture_output=True
    ).stdout
    return {"revision": revision, "dirty": bool(status.strip())}


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, target, symlinks=False)
    links = [path for path in target.rglob("*") if path.is_symlink()]
    if links:
        raise ValueError(f"copied tree contains symlinks: {links[:3]}")


def _write_hashes(root: Path) -> int:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name == "bundle.sha256":
            continue
        rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "bundle.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows)


def package(
    *,
    finetuning_root: Path,
    payload: Path,
    output: Path,
) -> dict[str, object]:
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
        _copy_tree(payload, temporary / "data" / "finetuning_v1")
        for record in weight_manifest["artifacts"]:
            target = temporary / "weights" / "base" / record["filename"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_assets / record["filename"], target)

        metadata = {
            "schema_version": "eovrt.t1-bundle.v1",
            "name": "t1_yoloe26s_lp",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_repository": _git_state(finetuning_root.parent),
            "payload_manifest_sha256": sha256_file(payload / "payload.json"),
            "split_manifest_sha256": sha256_file(
                finetuning_root / "manifests" / "finetuning_v1.split.csv"
            ),
            "base_weight_manifest_sha256": sha256_file(
                finetuning_root / "manifests" / "t1_base_weights.json"
            ),
            "bench_payload_files": 0,
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
    parser.add_argument(
        "--payload", type=Path, default=root / "data" / "payloads" / "finetuning_v1"
    )
    parser.add_argument("--output", type=Path, default=root / "cache" / "t1_bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = package(
        finetuning_root=args.finetuning_root.resolve(),
        payload=args.payload.resolve(),
        output=args.output.resolve(),
    )
    print(f"bundle={args.output.resolve()} files={metadata['files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
