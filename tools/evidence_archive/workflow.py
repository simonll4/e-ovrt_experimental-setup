from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

from .archive import (
    ArchivePolicy,
    ArchivedFile,
    archive_run,
    validate_archive_tree,
)
from .catalog import manual_requests, resolve_catalog
from .manifest import campaign_requests, load_manifest, structured_requests
from .model import CheckReport, EvidenceError, Relation, ResolvedRun, RunKey
from .render import (
    render_archive_files,
    render_archive_readme,
    render_checksums,
    render_collections,
    render_inventory_markdown,
    render_resolved_runs,
)

GITIGNORE = """# Defensa en profundidad: el generador también inspecciona el contenido.
**/previews/
**/frames/
**/images/
**/annotated/
**/videos/
**/cameras/
**/camera_presets/
**/*.jpg
**/*.jpeg
**/*.png
**/*.webp
**/*.bmp
**/*.gif
**/*.tif
**/*.tiff
**/*.mp4
**/*.avi
**/*.mkv
**/*.mov
**/*.webm
**/*.m4v
"""


def _workspace_root(repo_root: Path) -> Path:
    return repo_root.resolve().parent


def _collect_requests(repo_root: Path, manifest_path: Path):
    manifest = load_manifest(manifest_path)
    return manifest, [
        *campaign_requests(manifest, repo_root),
        *structured_requests(manifest, repo_root),
        *manual_requests(manifest),
    ]


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _build(
    repo_root: Path,
    manifest_path: Path,
    archive_root: Path,
    inventory_path: Path,
) -> CheckReport:
    manifest, requests = _collect_requests(repo_root, manifest_path)
    workspace_root = _workspace_root(repo_root)
    runs = resolve_catalog(manifest, requests, workspace_root)
    invalid = [run for run in runs if run.status in {"missing", "conflict"}]
    if invalid:
        details = ", ".join(
            f"{run.key.plane}:{run.key.run_id}={run.status}" for run in invalid
        )
        raise EvidenceError(f"catálogo no archivable: {details}")

    policy = ArchivePolicy.from_manifest(manifest.archive_policy)
    archive_root.mkdir(parents=True)
    artifacts_root = archive_root / "artifacts"
    archived_files: list[ArchivedFile] = []
    for run in runs:
        archived_files.extend(archive_run(run, artifacts_root, policy))

    _write(archive_root / ".gitignore", GITIGNORE.encode("utf-8"))
    _write(
        archive_root / "README.md",
        render_archive_readme(manifest.generated_date, runs),
    )
    _write(
        archive_root / "resolved-runs.json",
        render_resolved_runs(runs, workspace_root),
    )
    _write(
        archive_root / "archive-files.json",
        render_archive_files(archived_files, workspace_root),
    )
    for name, content in render_collections(runs).items():
        _write(archive_root / "collections" / name, content)
    _write(
        inventory_path,
        render_inventory_markdown(manifest.generated_date, runs, archived_files),
    )
    validate_archive_tree(archive_root, policy)
    _write(archive_root / "files.sha256", render_checksums(archive_root))
    validate_archive_tree(archive_root, policy)

    counts = Counter(run.status for run in runs)
    counts.update(f"plane:{run.key.plane}" for run in runs)
    return CheckReport(
        ok=True,
        messages=(
            f"runs={len(runs)} copied={counts['copied']} "
            f"archived_only={counts['archived_only']}",
        ),
        counts=dict(counts),
    )


def sync(repo_root: Path, manifest_path: Path | None = None) -> CheckReport:
    repo_root = repo_root.resolve()
    manifest_path = (
        manifest_path or repo_root / "results/evidence-runs.yaml"
    ).resolve()
    results = repo_root / "results"
    results.mkdir(parents=True, exist_ok=True)
    build_parent = Path(tempfile.mkdtemp(prefix=".evidence-runs-build-", dir=results))
    build_tree = build_parent / "evidence-runs"
    build_inventory = build_parent / "evidence-runs.md"
    destination = results / "evidence-runs"
    inventory = results / "evidence-runs.md"
    backup_tree = build_parent / "previous-evidence-runs"
    backup_inventory = build_parent / "previous-evidence-runs.md"
    moved_tree = False
    moved_inventory = False
    try:
        report = _build(repo_root, manifest_path, build_tree, build_inventory)
        if destination.exists():
            os.replace(destination, backup_tree)
        if inventory.exists():
            os.replace(inventory, backup_inventory)
        try:
            os.replace(build_tree, destination)
            moved_tree = True
            os.replace(build_inventory, inventory)
            moved_inventory = True
        except Exception:
            if moved_inventory and inventory.exists():
                os.replace(inventory, build_inventory)
            if backup_inventory.exists():
                os.replace(backup_inventory, inventory)
            if moved_tree and destination.exists():
                os.replace(destination, build_tree)
            if backup_tree.exists():
                os.replace(backup_tree, destination)
            raise
        return report
    finally:
        shutil.rmtree(build_parent, ignore_errors=True)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_entries(root: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            entries[f"{relative}/"] = "directory"
        elif path.is_file():
            entries[relative] = _hash(path)
    return entries


def _compare_trees(expected: Path, actual: Path) -> list[str]:
    wanted = _tree_entries(expected)
    found = _tree_entries(actual)
    messages = [f"falta: {path}" for path in sorted(set(wanted) - set(found))]
    messages.extend(f"sobra: {path}" for path in sorted(set(found) - set(wanted)))
    messages.extend(
        f"difiere: {path}"
        for path in sorted(set(wanted) & set(found))
        if wanted[path] != found[path]
    )
    return messages


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} inválido") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} debe ser un objeto JSON")
    return value


def _offline_objects(
    archive_root: Path,
    workspace_root: Path,
) -> tuple[list[ResolvedRun], list[ArchivedFile]]:
    lock = _load_json(archive_root / "resolved-runs.json", "resolved-runs.json")
    raw_runs = lock.get("runs")
    if lock.get("schema_version") != "evidence_runs.resolved.v1" or not isinstance(
        raw_runs, list
    ):
        raise EvidenceError("resolved-runs.json tiene schema inválido")
    runs: list[ResolvedRun] = []
    for raw in raw_runs:
        if not isinstance(raw, dict) or not isinstance(raw.get("relations"), list):
            raise EvidenceError("resolved-runs.json contiene un run inválido")
        relations = tuple(Relation(**relation) for relation in raw["relations"])
        runs.append(
            ResolvedRun(
                RunKey(raw["plane"], raw["run_id"]),
                raw["status"],
                relations,
                reason=raw.get("reason"),
            )
        )

    file_manifest = _load_json(
        archive_root / "archive-files.json", "archive-files.json"
    )
    raw_files = file_manifest.get("files")
    if file_manifest.get(
        "schema_version"
    ) != "evidence_archive.files.v1" or not isinstance(raw_files, list):
        raise EvidenceError("archive-files.json tiene schema inválido")
    files: list[ArchivedFile] = []
    for raw in raw_files:
        if not isinstance(raw, dict):
            raise EvidenceError("archive-files.json contiene una fila inválida")
        files.append(
            ArchivedFile(
                RunKey(raw["plane"], raw["run_id"]),
                workspace_root / raw["source_path"],
                raw["source_sha256"],
                raw["source_size"],
                Path(raw["archive_path"]),
                raw["archive_sha256"],
                raw["archive_size"],
                raw["compression"],
                raw["redaction"],
            )
        )
    return runs, files


def _offline_check(repo_root: Path, manifest_path: Path) -> CheckReport:
    manifest = load_manifest(manifest_path)
    archive_root = repo_root / "results/evidence-runs"
    inventory = repo_root / "results/evidence-runs.md"
    if not archive_root.is_dir() or not inventory.is_file():
        return CheckReport(False, ("falta el archivo versionable",))
    policy = ArchivePolicy.from_manifest(manifest.archive_policy)
    try:
        validate_archive_tree(archive_root, policy)
        checksum_path = archive_root / "files.sha256"
        if checksum_path.read_bytes() != render_checksums(archive_root):
            return CheckReport(False, ("files.sha256 difiere",))
        runs, files = _offline_objects(archive_root, _workspace_root(repo_root))
    except (EvidenceError, OSError) as exc:
        return CheckReport(False, (str(exc),))

    expected_run_dirs = {
        _artifact_path
        for run in runs
        if (
            _artifact_path := (
                f"artifacts/{run.key.plane}/{run.key.run_id}"
                if run.status == "copied"
                else f"artifacts/archived-only/{run.key.plane}--{run.key.run_id}"
            )
        )
    }
    actual_run_dirs: set[str] = set()
    for plane in ("media-plane", "control-plane"):
        root = archive_root / "artifacts" / plane
        if root.is_dir():
            actual_run_dirs.update(
                f"artifacts/{plane}/{path.name}"
                for path in root.iterdir()
                if path.is_dir()
            )
    archived = archive_root / "artifacts/archived-only"
    if archived.is_dir():
        actual_run_dirs.update(
            f"artifacts/archived-only/{path.name}"
            for path in archived.iterdir()
            if path.is_dir()
        )
    if expected_run_dirs != actual_run_dirs:
        return CheckReport(False, ("sobran o faltan directorios de runs",))

    actual_artifacts = {
        path.relative_to(archive_root).as_posix()
        for path in (archive_root / "artifacts").rglob("*")
        if path.is_file()
    }
    expected_artifacts = {item.archive_path.as_posix() for item in files}
    if expected_artifacts != actual_artifacts:
        return CheckReport(False, ("sobran o faltan archivos de runs",))
    for item in files:
        path = archive_root / item.archive_path
        if (
            path.stat().st_size != item.archive_size
            or _hash(path) != item.archive_sha256
        ):
            return CheckReport(False, (f"difiere: {item.archive_path.as_posix()}",))

    for name, expected in render_collections(runs).items():
        path = archive_root / "collections" / name
        if not path.is_file() or path.read_bytes() != expected:
            return CheckReport(False, (f"difiere: collections/{name}",))
    if (archive_root / "README.md").read_bytes() != render_archive_readme(
        manifest.generated_date, runs
    ):
        return CheckReport(False, ("difiere: README.md",))
    if inventory.read_bytes() != render_inventory_markdown(
        manifest.generated_date, runs, files
    ):
        return CheckReport(False, ("difiere: evidence-runs.md",))
    return CheckReport(
        True,
        ("archivo válido; --archive-only no comparó contra los runs originales",),
        {"runs": len(runs), "files": len(files)},
    )


def check(
    repo_root: Path,
    manifest_path: Path | None = None,
    *,
    archive_only: bool = False,
) -> CheckReport:
    repo_root = repo_root.resolve()
    manifest_path = (
        manifest_path or repo_root / "results/evidence-runs.yaml"
    ).resolve()
    if archive_only:
        return _offline_check(repo_root, manifest_path)

    actual_tree = repo_root / "results/evidence-runs"
    actual_inventory = repo_root / "results/evidence-runs.md"
    with tempfile.TemporaryDirectory(prefix="evidence-runs-check-") as raw_temp:
        temp = Path(raw_temp)
        expected_tree = temp / "evidence-runs"
        expected_inventory = temp / "evidence-runs.md"
        try:
            expected_report = _build(
                repo_root,
                manifest_path,
                expected_tree,
                expected_inventory,
            )
        except EvidenceError as exc:
            return CheckReport(False, (str(exc),))
        messages = _compare_trees(expected_tree, actual_tree)
        if not actual_inventory.is_file():
            messages.append("falta: evidence-runs.md")
        elif actual_inventory.read_bytes() != expected_inventory.read_bytes():
            messages.append("difiere: evidence-runs.md")
        return CheckReport(not messages, tuple(messages), expected_report.counts)
