from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.evidence_archive.archive import ArchivedFile
from tools.evidence_archive.model import Relation, ResolvedRun, RunKey
from tools.evidence_archive.render import (
    render_archive_files,
    render_archive_readme,
    render_checksums,
    render_collections,
    render_inventory_markdown,
    render_resolved_runs,
)


def _runs(workspace: Path) -> list[ResolvedRun]:
    shared_relations = (
        Relation(
            "dbe_video",
            "clip_bench/t1_gdinotiny560_v2short_scene",
            "campaign_media",
            "results/t1.json",
        ),
        Relation("ebe_realtime", "doc101", "live_distribution", "../docs/101.json"),
    )
    return [
        ResolvedRun(
            RunKey("media-plane", "run_shared"),
            "copied",
            shared_relations,
            source_dirs=(workspace / "e-ovrt_media-plane/runs/run_shared",),
        ),
        ResolvedRun(
            RunKey("control-plane", "control_t1"),
            "archived_only",
            (
                Relation(
                    "dbe_video",
                    "clip_bench/t1_gdinotiny560_v2short_scene",
                    "campaign_control",
                    "results/t1/evals/eval_a.json",
                ),
            ),
            archived_substitutes=(
                workspace
                / "e-ovrt_experimental-setup/results/clip_bench/t1/evals/eval_a.json",
            ),
            reason="scratchpad ausente",
        ),
    ]


def _archived_file(workspace: Path) -> ArchivedFile:
    payload = b'{"frame":1}\n'
    digest = hashlib.sha256(payload).hexdigest()
    return ArchivedFile(
        run_key=RunKey("media-plane", "run_shared"),
        source_path=workspace / "e-ovrt_media-plane/runs/run_shared/detections.jsonl",
        source_sha256=digest,
        source_size=len(payload),
        archive_path=Path("artifacts/media-plane/run_shared/detections.jsonl.gz"),
        archive_sha256="0" * 64,
        archive_size=31,
        compression="gzip",
        redaction=False,
    )


def test_render_resolved_runs_is_stable_and_uses_relative_paths(tmp_path: Path) -> None:
    runs = _runs(tmp_path)

    first = render_resolved_runs(runs, tmp_path)
    second = render_resolved_runs(list(reversed(runs)), tmp_path)
    decoded = json.loads(first)

    assert first == second
    assert b"/tmp/" not in first
    assert decoded["runs"][0]["run_id"] == "control_t1"
    assert decoded["runs"][1]["source_dirs"] == ["e-ovrt_media-plane/runs/run_shared"]


def test_collections_include_shared_run_without_duplicate_artifact(
    tmp_path: Path,
) -> None:
    csvs = render_collections(_runs(tmp_path))

    assert b"run_shared" in csvs["dbe-video.csv"]
    assert b"run_shared" in csvs["ebe-realtime.csv"]
    shared_lines = csvs["shared.csv"].decode("utf-8").splitlines()
    assert len(shared_lines) == 3
    assert all("run_shared" in line for line in shared_lines[1:])


def test_archive_files_manifest_never_persists_absolute_source_paths(
    tmp_path: Path,
) -> None:
    rendered = render_archive_files([_archived_file(tmp_path)], tmp_path)
    decoded = json.loads(rendered)

    assert b"/tmp/" not in rendered
    assert decoded["files"][0]["source_path"] == (
        "e-ovrt_media-plane/runs/run_shared/detections.jsonl"
    )
    assert decoded["files"][0]["compression"] == "gzip"


def test_inventory_links_every_run_to_its_artifact(tmp_path: Path) -> None:
    rendered = render_inventory_markdown(
        "2026-08-13", _runs(tmp_path), [_archived_file(tmp_path)]
    ).decode("utf-8")

    assert "2 runs únicos" in rendered
    assert "evidence-runs/artifacts/media-plane/run_shared/" in rendered
    assert (
        "evidence-runs/artifacts/archived-only/control-plane--control_t1/" in rendered
    )
    assert "Controles T1 en estado `archived_only`: **1**" in rendered
    assert "## Cobertura por resultado" in rendered
    assert (
        "| dbe_video | `clip_bench/t1_gdinotiny560_v2short_scene` | 2 | 1 | 1 | 1 |"
        in rendered
    )
    assert "dbe_video=2" in rendered
    assert "ebe_realtime=1" in rendered
    assert "compartidos=1" in rendered


def test_inventory_campaign_count_excludes_structured_result_groups(
    tmp_path: Path,
) -> None:
    runs = [
        *_runs(tmp_path),
        ResolvedRun(
            RunKey("media-plane", "run_nivel_a_replica"),
            "copied",
            (
                Relation(
                    "dbe_datasets",
                    "bench_nivel_a/replica_base560",
                    "nivel_a_replica",
                    "../docs/84/runs.json",
                ),
            ),
            source_dirs=(tmp_path / "e-ovrt_media-plane/runs/run_nivel_a_replica",),
        ),
    ]

    rendered = render_inventory_markdown("2026-08-13", runs, []).decode("utf-8")

    assert "Campañas con artefactos: **1**" in rendered


def test_archive_readme_documents_both_check_modes(tmp_path: Path) -> None:
    rendered = render_archive_readme("2026-08-13", _runs(tmp_path)).decode("utf-8")

    assert "python3 tools/evidence_runs.py --check" in rendered
    assert "--archive-only" in rendered
    assert "imágenes" in rendered
    assert "videos" in rendered


def test_checksums_are_sorted_and_exclude_themselves(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "files.sha256").write_text("stale", encoding="utf-8")

    lines = render_checksums(tmp_path).decode("utf-8").splitlines()

    assert lines == [
        "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb  a.txt",
        "594e519ae499312b29433b7dd8a97ff068defcba9755b6d5d00e84c524d67b06  z.txt",
    ]
    assert all("files.sha256" not in line for line in lines)
