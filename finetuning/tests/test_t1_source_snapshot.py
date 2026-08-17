from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
snapshot = importlib.import_module("create_t1_source_snapshot")


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _make_repositories(tmp_path: Path) -> tuple[dict[str, Path], dict[str, list[str]]]:
    roots: dict[str, Path] = {}
    inventories: dict[str, list[str]] = {}
    selected = {
        "experimental": "finetuning/config.yaml",
        "docs": "operacion/plan.md",
        "media": "src/adapter.py",
    }
    for index, name in enumerate(snapshot.REPOSITORY_NAMES):
        root = tmp_path / name
        root.mkdir()
        _git(root, "init", "-q")
        _git(root, "config", "user.name", "Snapshot Test")
        _git(root, "config", "user.email", "snapshot@example.invalid")
        relative = selected[name]
        source = root / relative
        source.parent.mkdir(parents=True)
        source.write_text(f"{name}-source-{index}\n", encoding="utf-8")
        if name == "media":
            source.chmod(0o755)
        unrelated = root / "unrelated.txt"
        unrelated.write_text("clean unrelated\n", encoding="utf-8")
        _git(root, "add", relative, "unrelated.txt")
        _git(root, "commit", "-qm", f"seed {name}")
        roots[name] = root
        inventories[name] = [relative]
    return roots, inventories


def _write_inventory(tmp_path: Path, repositories: dict[str, list[str]]) -> Path:
    path = tmp_path / "inventory.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": snapshot.INVENTORY_SCHEMA,
                "repositories": repositories,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_snapshot_is_deterministic_and_git_status_is_inventory_scoped(tmp_path: Path) -> None:
    roots, inventories = _make_repositories(tmp_path)
    inventory = _write_inventory(tmp_path, inventories)
    selected = roots["experimental"] / inventories["experimental"][0]
    selected.write_text("dirty selected source\n", encoding="utf-8")
    (roots["experimental"] / "unrelated.txt").write_text("dirty but excluded\n", encoding="utf-8")

    first_tar = tmp_path / "first.tar"
    first_manifest = tmp_path / "first.json"
    first = snapshot.create_snapshot(
        roots=roots,
        inventory_path=inventory,
        output_tar=first_tar,
        output_manifest=first_manifest,
    )
    second_tar = tmp_path / "second.tar"
    second_manifest = tmp_path / "second.json"
    second = snapshot.create_snapshot(
        roots=roots,
        inventory_path=inventory,
        output_tar=second_tar,
        output_manifest=second_manifest,
    )

    assert first == second
    assert first_tar.read_bytes() == second_tar.read_bytes()
    assert first_manifest.read_bytes() == second_manifest.read_bytes()
    assert first["archive"]["sha256"] == snapshot.sha256_file(first_tar)
    assert first["repositories"]["experimental"]["dirty_scoped"] is True
    status = first["repositories"]["experimental"]["status_porcelain_v1"]
    assert status == [f" M {inventories['experimental'][0]}"]
    assert "unrelated.txt" not in "\n".join(status)
    assert first["repositories"]["docs"]["dirty_scoped"] is False
    assert first["repositories"]["media"]["dirty_scoped"] is False

    with tarfile.open(first_tar, mode="r:") as archive:
        members = archive.getmembers()
        assert [member.name for member in members] == sorted(member.name for member in members)
        assert all(member.uid == member.gid == member.mtime == 0 for member in members)
        assert all(member.uname == member.gname == "" for member in members)
        assert {member.mode for member in members} == {0o644, 0o755}
        archived = archive.extractfile(
            f"{snapshot.ARCHIVE_ROOT}/experimental/{inventories['experimental'][0]}"
        )
        assert archived is not None
        assert archived.read() == b"dirty selected source\n"


def test_rejects_symlink_inventory_source(tmp_path: Path) -> None:
    roots, inventories = _make_repositories(tmp_path)
    relative = inventories["experimental"][0]
    source = roots["experimental"] / relative
    source.unlink()
    source.symlink_to(roots["experimental"] / "unrelated.txt")
    inventory = _write_inventory(tmp_path, inventories)

    with pytest.raises(snapshot.SnapshotError, match="symlink inventory path"):
        snapshot.create_snapshot(
            roots=roots,
            inventory_path=inventory,
            output_tar=tmp_path / "snapshot.tar",
            output_manifest=tmp_path / "snapshot.json",
        )


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("../outside.txt", "canonical and repository-relative"),
        ("missing.py", "source is missing"),
    ],
)
def test_rejects_unsafe_or_missing_inventory_path(
    tmp_path: Path, replacement: str, message: str
) -> None:
    roots, inventories = _make_repositories(tmp_path)
    inventories["experimental"] = [replacement]
    inventory = _write_inventory(tmp_path, inventories)

    with pytest.raises(snapshot.SnapshotError, match=message):
        snapshot.create_snapshot(
            roots=roots,
            inventory_path=inventory,
            output_tar=tmp_path / "snapshot.tar",
            output_manifest=tmp_path / "snapshot.json",
        )


def test_rejects_duplicate_inventory_path(tmp_path: Path) -> None:
    roots, inventories = _make_repositories(tmp_path)
    selected = inventories["docs"][0]
    inventories["docs"] = [selected, selected]
    inventory = _write_inventory(tmp_path, inventories)

    with pytest.raises(snapshot.SnapshotError, match="duplicate inventory paths"):
        snapshot.create_snapshot(
            roots=roots,
            inventory_path=inventory,
            output_tar=tmp_path / "snapshot.tar",
            output_manifest=tmp_path / "snapshot.json",
        )


@pytest.mark.parametrize("kind", ["ignored", "weight", "credential"])
def test_rejects_ignored_heavy_or_credential_source(tmp_path: Path, kind: str) -> None:
    roots, inventories = _make_repositories(tmp_path)
    root = roots["media"]
    if kind == "ignored":
        relative = "ignored-source.py"
        (root / ".gitignore").write_text(f"{relative}\n", encoding="utf-8")
        (root / relative).write_text("print('ignored')\n", encoding="utf-8")
        expected = "Git-ignored source"
    elif kind == "weight":
        relative = "model.pt"
        (root / relative).write_bytes(b"not a real weight")
        expected = "artifact suffix"
    else:
        relative = "credentials.txt"
        private_key_fixture = "-----BEGIN OPENSSH " + "PRIVATE KEY-----\nsecret\n"
        (root / relative).write_text(
            private_key_fixture, encoding="utf-8"
        )
        expected = "credential-like filename"
    inventories["media"] = [relative]
    inventory = _write_inventory(tmp_path, inventories)

    with pytest.raises(snapshot.SnapshotError, match=expected):
        snapshot.create_snapshot(
            roots=roots,
            inventory_path=inventory,
            output_tar=tmp_path / "snapshot.tar",
            output_manifest=tmp_path / "snapshot.json",
        )


@pytest.mark.parametrize("which", ["tar", "manifest"])
def test_rejects_output_that_is_in_the_inventory(tmp_path: Path, which: str) -> None:
    roots, inventories = _make_repositories(tmp_path)
    inventory = _write_inventory(tmp_path, inventories)
    selected = roots["docs"] / inventories["docs"][0]
    output_tar = selected if which == "tar" else tmp_path / "snapshot.tar"
    output_manifest = selected if which == "manifest" else tmp_path / "snapshot.json"

    with pytest.raises(snapshot.SnapshotError, match="output cannot be one"):
        snapshot.create_snapshot(
            roots=roots,
            inventory_path=inventory,
            output_tar=output_tar,
            output_manifest=output_manifest,
        )
    assert selected.read_text(encoding="utf-8") == "docs-source-1\n"
