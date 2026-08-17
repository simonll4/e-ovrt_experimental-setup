from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tools.evidence_archive.model import EvidenceError
from tools.evidence_archive.workflow import check, sync
from tools.evidence_runs import main


@dataclass(frozen=True)
class WorkspaceFixture:
    workspace: Path
    repo: Path
    manifest: Path
    media_root: Path

    def remove_source_repos(self) -> None:
        shutil.rmtree(self.media_root)


@pytest.fixture
def workspace_fixture(tmp_path: Path) -> WorkspaceFixture:
    repo = tmp_path / "e-ovrt_experimental-setup"
    results = repo / "results"
    results.mkdir(parents=True)
    media_root = tmp_path / "e-ovrt_media-plane/runs"
    run = media_root / "run_a"
    run.mkdir(parents=True)
    (run / "summary.json").write_text('{"status":"succeeded"}\n', encoding="utf-8")
    (run / "detections.jsonl").write_text('{"frame":1}\n', encoding="utf-8")
    docs = tmp_path / "docs/operacion/datos"
    docs.mkdir(parents=True)
    (docs / "runs.json").write_text(
        json.dumps({"rows": [{"run_id": "run_a"}]}) + "\n", encoding="utf-8"
    )
    manifest = results / "evidence-runs.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "evidence_runs.v1",
                "generated_date": "2026-08-13",
                "collections": {
                    "dbe_datasets": "DBE datasets",
                    "dbe_video": "DBE video",
                    "ebe_realtime": "EBE realtime",
                    "shared": "Shared",
                },
                "source_roots": {
                    "media-plane": ["../e-ovrt_media-plane/runs"],
                    "control-plane": ["../e-ovrt_control-plane/runs"],
                },
                "expected_campaigns": [],
                "structured_sources": [
                    {
                        "id": "fixture_runs",
                        "path": "../docs/operacion/datos/runs.json",
                        "selectors": ["rows.*.run_id"],
                        "expected_count": 1,
                        "plane": "media-plane",
                        "collection": "dbe_datasets",
                        "result_id": "bench_fixture",
                        "role": "benchmark",
                        "document": "../docs/operacion/fixture.md",
                    }
                ],
                "manual_groups": [],
                "archived_only": [],
                "source_dispositions": [],
                "archive_policy": {
                    "allowed_extensions": [
                        ".json",
                        ".jsonl",
                        ".csv",
                        ".yaml",
                        ".yml",
                        ".txt",
                        ".log",
                        ".md",
                    ],
                    "excluded_extensions": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".bmp",
                        ".gif",
                        ".tif",
                        ".tiff",
                        ".mp4",
                        ".avi",
                        ".mkv",
                        ".mov",
                        ".webm",
                        ".m4v",
                    ],
                    "excluded_directories": [
                        "previews",
                        "frames",
                        "images",
                        "annotated",
                        "videos",
                        "cameras",
                        "camera_presets",
                    ],
                    "max_archive_mib": 95,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return WorkspaceFixture(tmp_path, repo, manifest, media_root.parent)


def _mtimes(root: Path) -> dict[str, int]:
    return {
        path.relative_to(root).as_posix(): path.stat().st_mtime_ns
        for path in root.rglob("*")
        if path.is_file()
    }


def test_sync_then_full_check_is_clean(workspace_fixture: WorkspaceFixture) -> None:
    synced = sync(workspace_fixture.repo, workspace_fixture.manifest)
    checked = check(workspace_fixture.repo, workspace_fixture.manifest)

    assert synced.ok
    assert checked.ok
    assert (workspace_fixture.repo / "results/evidence-runs.md").is_file()
    archived = (
        workspace_fixture.repo
        / "results/evidence-runs/artifacts/media-plane/run_a/detections.jsonl.gz"
    )
    assert archived.is_file()


def test_sync_reports_every_run_per_plane(workspace_fixture: WorkspaceFixture) -> None:
    second = workspace_fixture.workspace / "e-ovrt_media-plane/runs/run_b"
    second.mkdir(parents=True)
    (second / "summary.json").write_text('{"status":"succeeded"}\n', encoding="utf-8")
    source = workspace_fixture.workspace / "docs/operacion/datos/runs.json"
    source.write_text(
        json.dumps({"rows": [{"run_id": "run_a"}, {"run_id": "run_b"}]}) + "\n",
        encoding="utf-8",
    )
    manifest_data = yaml.safe_load(
        workspace_fixture.manifest.read_text(encoding="utf-8")
    )
    manifest_data["structured_sources"][0]["expected_count"] = 2
    workspace_fixture.manifest.write_text(
        yaml.safe_dump(manifest_data, sort_keys=False), encoding="utf-8"
    )

    report = sync(workspace_fixture.repo, workspace_fixture.manifest)

    assert report.counts["plane:media-plane"] == 2


def test_check_does_not_modify_the_archive(workspace_fixture: WorkspaceFixture) -> None:
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    before = _mtimes(workspace_fixture.repo / "results")

    assert check(workspace_fixture.repo, workspace_fixture.manifest).ok

    assert _mtimes(workspace_fixture.repo / "results") == before


def test_check_detects_an_extra_empty_run_directory(
    workspace_fixture: WorkspaceFixture,
) -> None:
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    extra = (
        workspace_fixture.repo / "results/evidence-runs/artifacts/media-plane/run_extra"
    )
    extra.mkdir(parents=True)

    report = check(workspace_fixture.repo, workspace_fixture.manifest)

    assert not report.ok
    assert any("sobra" in message for message in report.messages)


def test_archive_only_check_works_without_source_repos(
    workspace_fixture: WorkspaceFixture,
) -> None:
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    workspace_fixture.remove_source_repos()

    report = check(
        workspace_fixture.repo,
        workspace_fixture.manifest,
        archive_only=True,
    )

    assert report.ok
    assert any("no comparó" in message for message in report.messages)


def test_failed_sync_preserves_the_previous_archive(
    workspace_fixture: WorkspaceFixture,
) -> None:
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    lock = workspace_fixture.repo / "results/evidence-runs/resolved-runs.json"
    before = lock.read_bytes()
    source_summary = (
        workspace_fixture.workspace / "e-ovrt_media-plane/runs/run_a/summary.json"
    )
    source_summary.write_text('{"api_key":"must-not-print"}\n', encoding="utf-8")

    with pytest.raises(EvidenceError) as raised:
        sync(workspace_fixture.repo, workspace_fixture.manifest)

    assert "must-not-print" not in str(raised.value)
    assert lock.read_bytes() == before


def test_cli_returns_success_for_a_clean_full_check(
    workspace_fixture: WorkspaceFixture,
) -> None:
    assert main(["--repo-root", str(workspace_fixture.repo), "sync"]) == 0

    assert main(["--repo-root", str(workspace_fixture.repo), "--check"]) == 0


def test_cli_file_entrypoint_works_outside_the_repository(
    workspace_fixture: WorkspaceFixture,
) -> None:
    script = Path(__file__).resolve().parents[1] / "tools/evidence_runs.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(workspace_fixture.repo),
            "sync",
        ],
        cwd=workspace_fixture.workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
