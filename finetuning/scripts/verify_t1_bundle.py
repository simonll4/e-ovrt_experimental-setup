#!/usr/bin/env python3
"""Verify every file declared by a packaged T1 bundle."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(root: Path) -> int:
    root = root.resolve()
    manifest = root / "bundle.sha256"
    if not manifest.is_file():
        raise ValueError(f"missing bundle hash manifest: {manifest}")
    declared: set[str] = set()
    for line_number, raw_line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        expected, separator, relative = raw_line.partition("  ")
        if not separator or len(expected) != 64:
            raise ValueError(f"{manifest}:{line_number}: malformed hash row")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as error:
            raise ValueError(f"bundle hash path escapes root: {relative}") from error
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"missing or linked bundle file: {relative}")
        actual = sha256_file(target)
        if actual != expected:
            raise ValueError(f"bundle hash mismatch: {relative} ({actual} != {expected})")
        declared.add(relative)
    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "bundle.sha256"
    }
    undeclared = sorted(actual_files - declared)
    missing = sorted(declared - actual_files)
    if undeclared or missing:
        raise ValueError(f"bundle inventory mismatch: undeclared={undeclared}, missing={missing}")
    return len(declared)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    count = verify_bundle(args.bundle)
    print(f"bundle_ok={args.bundle.resolve()} files={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

