#!/usr/bin/env python3
"""Copy the declared T1 base assets into the ignored fine-tuning workspace."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from materialize_t1_payload import sha256_file


def stage(*, manifest: Path, source: Path, output: Path) -> int:
    records = json.loads(manifest.read_text(encoding="utf-8"))["artifacts"]
    output.mkdir(parents=True, exist_ok=True)
    copied = 0
    for record in records:
        source_path = source / record["filename"]
        target = output / record["filename"]
        if target.exists():
            raise FileExistsError(f"refusing to overwrite staged asset: {target}")
        if (
            source_path.stat().st_size != int(record["size_bytes"])
            or sha256_file(source_path) != record["sha256"]
        ):
            raise ValueError(f"source asset differs from manifest: {source_path}")
        shutil.copy2(source_path, target)
        if sha256_file(target) != record["sha256"]:
            raise ValueError(f"copied asset failed verification: {target}")
        copied += 1
    return copied


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    workspace = root.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=root / "manifests" / "t1_base_weights.json"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=workspace / "e-ovrt_media-plane" / "models" / "yoloe" / "original",
    )
    parser.add_argument("--output", type=Path, default=root / "weights" / "base")
    args = parser.parse_args(argv)
    count = stage(manifest=args.manifest, source=args.source, output=args.output)
    print(f"base_assets={args.output.resolve()} files={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

