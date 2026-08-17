#!/usr/bin/env python3
"""Create a deterministic, source-only T-FT-023 snapshot from an explicit inventory."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


INVENTORY_SCHEMA = "eovrt.t1-source-inventory.v1"
MANIFEST_SCHEMA = "eovrt.t1-source-snapshot.v1"
REPOSITORY_NAMES = ("experimental", "docs", "media")
ARCHIVE_ROOT = "t1-source-snapshot"
MAX_SOURCE_BYTES = 10 * 1024 * 1024

FORBIDDEN_COMPONENTS = {
    ".git",
    ".venv",
    "__pycache__",
    "artifacts",
    "cache",
    "data",
    "datasets",
    "node_modules",
    "payload",
    "payloads",
    "processed",
    "raw",
    "results",
    "runs",
    "venv",
    "weights",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".bmp",
    ".ckpt",
    ".csv",
    ".db",
    ".engine",
    ".gif",
    ".gz",
    ".jpeg",
    ".jpg",
    ".jsonl",
    ".key",
    ".mkv",
    ".mov",
    ".mp4",
    ".npy",
    ".npz",
    ".onnx",
    ".parquet",
    ".pem",
    ".pickle",
    ".pkl",
    ".png",
    ".pt",
    ".pth",
    ".safetensors",
    ".sif",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".tgz",
    ".ts",
    ".webm",
    ".webp",
    ".zip",
}
SENSITIVE_NAMES = {
    ".env",
    ".netrc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "secrets",
    "secrets.json",
}
HIGH_CONFIDENCE_SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("OpenAI-style token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)
SECRET_ASSIGNMENT = re.compile(
    r"(?im)^\s*(?:export\s+)?"
    r"(?:password|passwd|token|secret|api[_-]?key|access[_-]?key)"
    r"\s*[:=]\s*['\"]?([^\s'\"#]+)"
)
SAFE_PLACEHOLDER_FRAGMENTS = (
    "${",
    "$",
    "<",
    "changeme",
    "dummy",
    "example",
    "none",
    "placeholder",
    "redacted",
    "test",
)


class SnapshotError(RuntimeError):
    """The requested source snapshot violates the T-FT-023 contract."""


@dataclass(frozen=True)
class SourceFile:
    repository: str
    relative_path: str
    archive_path: str
    content: bytes
    sha256: str
    mode: int


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_git(root: Path, arguments: list[str], *, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "LC_ALL": "C"},
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise SnapshotError(f"git command failed for {root.name}: {detail}")
    return result.stdout


def _validate_root(name: str, root: Path) -> Path:
    if root.is_symlink():
        raise SnapshotError(f"repository root cannot be a symlink: {name}={root}")
    if not root.is_dir():
        raise SnapshotError(f"repository root is missing or not a directory: {name}={root}")
    resolved = root.resolve()
    top_level = Path(_run_git(resolved, ["rev-parse", "--show-toplevel"]).strip()).resolve()
    if top_level != resolved:
        raise SnapshotError(
            f"configured root is not the Git worktree root for {name}: {resolved} != {top_level}"
        )
    _run_git(resolved, ["rev-parse", "--verify", "HEAD"])
    return resolved


def _canonical_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotError(f"inventory path must be a non-empty string: {value!r}")
    if "\\" in value:
        raise SnapshotError(f"inventory paths must use POSIX separators: {value!r}")
    pure = PurePosixPath(value)
    if pure.is_absolute() or pure.as_posix() != value or any(part in {"", ".", ".."} for part in pure.parts):
        raise SnapshotError(f"inventory path must be canonical and repository-relative: {value!r}")
    return pure.as_posix()


def load_inventory(path: Path) -> dict[str, list[str]]:
    if path.is_symlink():
        raise SnapshotError(f"inventory file cannot be a symlink: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot load inventory {path}: {exc}") from exc

    if not isinstance(raw, dict) or raw.get("schema_version") != INVENTORY_SCHEMA:
        raise SnapshotError(f"inventory schema_version must be {INVENTORY_SCHEMA}")
    repositories = raw.get("repositories")
    if not isinstance(repositories, dict) or set(repositories) != set(REPOSITORY_NAMES):
        raise SnapshotError(
            f"inventory repositories must be exactly {list(REPOSITORY_NAMES)!r}"
        )

    normalized: dict[str, list[str]] = {}
    for name in REPOSITORY_NAMES:
        paths = repositories[name]
        if not isinstance(paths, list) or not paths:
            raise SnapshotError(f"inventory repository {name} must contain a non-empty path list")
        canonical = [_canonical_relative_path(value) for value in paths]
        duplicates = sorted(path for path in set(canonical) if canonical.count(path) > 1)
        if duplicates:
            raise SnapshotError(f"duplicate inventory paths for {name}: {duplicates!r}")
        normalized[name] = sorted(canonical)
    return normalized


def _reject_forbidden_path(repository: str, relative_path: str) -> None:
    pure = PurePosixPath(relative_path)
    lowered_parts = tuple(part.casefold() for part in pure.parts)
    forbidden = sorted(set(lowered_parts) & FORBIDDEN_COMPONENTS)
    if forbidden:
        raise SnapshotError(
            f"forbidden artifact directory in {repository}:{relative_path}: {forbidden!r}"
        )
    if any(part.startswith(".") for part in pure.parts):
        raise SnapshotError(f"hidden source path is forbidden: {repository}:{relative_path}")
    if pure.name.casefold() in SENSITIVE_NAMES or pure.stem.casefold() in SENSITIVE_NAMES:
        raise SnapshotError(f"credential-like filename is forbidden: {repository}:{relative_path}")
    if pure.suffix.casefold() in FORBIDDEN_SUFFIXES:
        raise SnapshotError(f"heavy/binary artifact suffix is forbidden: {repository}:{relative_path}")


def _reject_symlink_components(root: Path, relative_path: str) -> Path:
    current = root
    for part in PurePosixPath(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise SnapshotError(f"symlink inventory path is forbidden: {current}")
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"inventory path escapes repository root: {relative_path}") from exc
    return current


def _is_git_ignored(root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", relative_path],
        check=False,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    if result.returncode not in {0, 1}:
        raise SnapshotError(f"git check-ignore failed for {root.name}:{relative_path}")
    return result.returncode == 0


def _scan_credentials(text: str, repository: str, relative_path: str) -> None:
    for description, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS:
        if pattern.search(text):
            raise SnapshotError(
                f"possible {description} in source content: {repository}:{relative_path}"
            )
    for match in SECRET_ASSIGNMENT.finditer(text):
        value = match.group(1).casefold()
        if not any(fragment in value for fragment in SAFE_PLACEHOLDER_FRAGMENTS):
            raise SnapshotError(
                f"possible credential assignment in source content: {repository}:{relative_path}"
            )


def _read_source(repository: str, root: Path, relative_path: str) -> SourceFile:
    _reject_forbidden_path(repository, relative_path)
    source = _reject_symlink_components(root, relative_path)
    try:
        source_stat = source.stat()
    except FileNotFoundError as exc:
        raise SnapshotError(f"inventory source is missing: {repository}:{relative_path}") from exc
    if not stat.S_ISREG(source_stat.st_mode):
        raise SnapshotError(f"inventory source is not a regular file: {repository}:{relative_path}")
    if _is_git_ignored(root, relative_path):
        raise SnapshotError(f"Git-ignored source is forbidden: {repository}:{relative_path}")
    if source_stat.st_size > MAX_SOURCE_BYTES:
        raise SnapshotError(
            f"source exceeds {MAX_SOURCE_BYTES} bytes: {repository}:{relative_path}"
        )

    content = source.read_bytes()
    if len(content) != source_stat.st_size:
        raise SnapshotError(f"source changed while being read: {repository}:{relative_path}")
    if b"\x00" in content:
        raise SnapshotError(f"binary/NUL source is forbidden: {repository}:{relative_path}")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotError(f"source must be UTF-8 text: {repository}:{relative_path}") from exc
    _scan_credentials(text, repository, relative_path)

    normalized_mode = 0o755 if source_stat.st_mode & 0o111 else 0o644
    archive_path = f"{ARCHIVE_ROOT}/{repository}/{relative_path}"
    return SourceFile(
        repository=repository,
        relative_path=relative_path,
        archive_path=archive_path,
        content=content,
        sha256=sha256_bytes(content),
        mode=normalized_mode,
    )


def _git_metadata(root: Path, paths: list[str]) -> dict[str, Any]:
    head = _run_git(root, ["rev-parse", "--verify", "HEAD"]).strip()
    branch_result = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "LC_ALL": "C"},
    )
    if branch_result.returncode not in {0, 1}:
        raise SnapshotError(f"cannot resolve Git branch for {root.name}")
    branch = branch_result.stdout.strip() or None
    status_output = _run_git(
        root,
        ["--literal-pathspecs", "status", "--porcelain=v1", "--untracked-files=all", "--", *paths],
    )
    status = status_output.splitlines()
    return {
        "head": head,
        "branch": branch,
        "dirty_scoped": bool(status),
        "status_scope": "inventory_paths_only",
        "status_porcelain_v1": status,
    }


def _canonical_output(path: Path) -> Path:
    expanded = path.expanduser()
    parent = expanded.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or parent.absolute() != parent.resolve():
        raise SnapshotError(f"output parent cannot traverse symlinks: {parent}")
    return parent.resolve() / expanded.name


def _validate_outputs(output_tar: Path, output_manifest: Path) -> None:
    if output_tar == output_manifest:
        raise SnapshotError("tar and manifest outputs must be different paths")
    for output in (output_tar, output_manifest):
        if os.path.lexists(output):
            raise SnapshotError(f"refusing to overwrite existing output: {output}")


def _write_tar(path: Path, sources: list[SourceFile]) -> None:
    with tarfile.open(path, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for source in sorted(sources, key=lambda item: item.archive_path):
            info = tarfile.TarInfo(source.archive_path)
            info.size = len(source.content)
            info.mode = source.mode
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(source.content))


def _publish_new_file(temporary: Path, destination: Path) -> None:
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise SnapshotError(f"refusing to overwrite concurrently created output: {destination}") from exc


def create_snapshot(
    *,
    roots: dict[str, Path],
    inventory_path: Path,
    output_tar: Path,
    output_manifest: Path,
) -> dict[str, Any]:
    if set(roots) != set(REPOSITORY_NAMES):
        raise SnapshotError(f"roots must be exactly {list(REPOSITORY_NAMES)!r}")
    validated_roots = {name: _validate_root(name, roots[name]) for name in REPOSITORY_NAMES}
    inventory = load_inventory(inventory_path)

    sources = [
        _read_source(name, validated_roots[name], relative_path)
        for name in REPOSITORY_NAMES
        for relative_path in inventory[name]
    ]
    archive_paths = [source.archive_path for source in sources]
    if len(archive_paths) != len(set(archive_paths)):
        raise SnapshotError("duplicate archive paths after inventory normalization")

    tar_destination = _canonical_output(output_tar)
    manifest_destination = _canonical_output(output_manifest)
    inventory_sources = {
        (validated_roots[source.repository] / source.relative_path).resolve() for source in sources
    }
    if tar_destination in inventory_sources or manifest_destination in inventory_sources:
        raise SnapshotError("snapshot output cannot be one of the inventoried source files")
    _validate_outputs(tar_destination, manifest_destination)

    repositories = {
        name: {
            **_git_metadata(validated_roots[name], inventory[name]),
            "files": len(inventory[name]),
        }
        for name in REPOSITORY_NAMES
    }
    for source in sources:
        current = validated_roots[source.repository] / source.relative_path
        if sha256_file(current) != source.sha256:
            raise SnapshotError(
                f"source changed during snapshot preparation: {source.repository}:{source.relative_path}"
            )

    normalized_inventory = {
        "schema_version": INVENTORY_SCHEMA,
        "repositories": inventory,
    }
    inventory_digest = sha256_bytes(
        json.dumps(normalized_inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    tar_fd, tar_temp_name = tempfile.mkstemp(
        prefix=f".{tar_destination.name}.", suffix=".tmp", dir=tar_destination.parent
    )
    os.close(tar_fd)
    tar_temporary = Path(tar_temp_name)
    manifest_temporary: Path | None = None
    tar_published = False
    try:
        _write_tar(tar_temporary, sources)
        archive_sha256 = sha256_file(tar_temporary)
        archive_size = tar_temporary.stat().st_size
        manifest: dict[str, Any] = {
            "schema_version": MANIFEST_SCHEMA,
            "task_id": "T-FT-023",
            "archive": {
                "format": "uncompressed POSIX PAX tar",
                "root": ARCHIVE_ROOT,
                "size_bytes": archive_size,
                "sha256": archive_sha256,
                "determinism": {
                    "entry_order": "archive_path ascending",
                    "mtime": 0,
                    "uid": 0,
                    "gid": 0,
                    "owner_names": "empty",
                    "file_modes": "normalized 0644 or 0755",
                },
            },
            "inventory": {
                "schema_version": INVENTORY_SCHEMA,
                "normalized_sha256": inventory_digest,
                "repositories": inventory,
            },
            "repositories": repositories,
            "files": [
                {
                    "repository": source.repository,
                    "path": source.relative_path,
                    "archive_path": source.archive_path,
                    "size_bytes": len(source.content),
                    "sha256": source.sha256,
                    "mode": f"{source.mode:04o}",
                }
                for source in sorted(sources, key=lambda item: item.archive_path)
            ],
            "totals": {
                "files": len(sources),
                "source_bytes": sum(len(source.content) for source in sources),
            },
            "exclusions": {
                "selection": "explicit regular UTF-8 source files only",
                "symlinks": "forbidden",
                "git_ignored": "forbidden",
                "credentials": "filename and content guards applied",
                "weights_payload_bench_runs": "not inventoried; artifact directories and binary suffixes forbidden",
            },
        }
        manifest_content = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        manifest_fd, manifest_temp_name = tempfile.mkstemp(
            prefix=f".{manifest_destination.name}.",
            suffix=".tmp",
            dir=manifest_destination.parent,
        )
        os.close(manifest_fd)
        manifest_temporary = Path(manifest_temp_name)
        manifest_temporary.write_bytes(manifest_content)

        _publish_new_file(tar_temporary, tar_destination)
        tar_published = True
        _publish_new_file(manifest_temporary, manifest_destination)
        return manifest
    except BaseException:
        if tar_published and tar_destination.is_file() and not tar_destination.is_symlink():
            tar_destination.unlink()
        raise
    finally:
        tar_temporary.unlink(missing_ok=True)
        if manifest_temporary is not None:
            manifest_temporary.unlink(missing_ok=True)


def default_roots() -> dict[str, Path]:
    experimental = Path(__file__).resolve().parents[2]
    workspace = experimental.parent
    return {
        "experimental": experimental,
        "docs": workspace / "docs",
        "media": workspace / "e-ovrt_media-plane",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    defaults = default_roots()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experimental-root", type=Path, default=defaults["experimental"])
    parser.add_argument("--docs-root", type=Path, default=defaults["docs"])
    parser.add_argument("--media-root", type=Path, default=defaults["media"])
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output-tar", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        manifest = create_snapshot(
            roots={
                "experimental": args.experimental_root,
                "docs": args.docs_root,
                "media": args.media_root,
            },
            inventory_path=args.inventory,
            output_tar=args.output_tar,
            output_manifest=args.output_manifest,
        )
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
