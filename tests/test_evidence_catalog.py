from __future__ import annotations

from pathlib import Path

import pytest

from tools.evidence_archive.catalog import (
    manual_requests,
    merge_requests,
    portable_docs_path,
    resolve_catalog,
)
from tools.evidence_archive.model import (
    EvidenceError,
    Manifest,
    Relation,
    RunKey,
    RunRequest,
)


def _manifest(
    workspace: Path,
    *,
    media_roots: tuple[str, ...] = ("../media-a", "../media-b"),
    manual_groups: tuple[dict[str, object], ...] = (),
    archived_only: tuple[dict[str, object], ...] = (),
) -> Manifest:
    manifest_path = workspace / "experimental/results/evidence-runs.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("schema_version: evidence_runs.v1\n", encoding="utf-8")
    return Manifest(
        path=manifest_path,
        generated_date="2026-08-13",
        collections=("dbe_datasets", "dbe_video", "ebe_realtime", "shared"),
        source_roots={
            "media-plane": media_roots,
            "control-plane": ("../control",),
        },
        expected_campaigns=(),
        structured_sources=(),
        manual_groups=manual_groups,
        archived_only=archived_only,
        archive_policy={
            "allowed_extensions": [".json", ".jsonl", ".yaml", ".csv", ".txt"]
        },
    )


def _relation(collection: str, result_id: str = "result") -> Relation:
    return Relation(collection, result_id, "evidence", "source.json")


def _request(
    run_id: str,
    collection: str,
    *,
    source_hints: tuple[str, ...] = (),
    substitutes: tuple[str, ...] = (),
) -> RunRequest:
    return RunRequest(
        RunKey("media-plane", run_id),
        (_relation(collection),),
        source_hints=source_hints,
        archived_substitutes=substitutes,
    )


def _make_run(path: Path, summary: str = "same") -> None:
    path.mkdir(parents=True)
    (path / "summary.json").write_text(f'{{"value":"{summary}"}}\n', encoding="utf-8")
    (path / "detections.jsonl").write_text('{"frame":1}\n', encoding="utf-8")


def test_merge_requests_keeps_one_run_and_all_relations() -> None:
    first = _request("run_x", "dbe_video", source_hints=("one",))
    second = _request("run_x", "ebe_realtime", source_hints=("two",))

    merged = merge_requests([first, second])

    request = merged[RunKey("media-plane", "run_x")]
    assert {relation.collection for relation in request.relations} == {
        "dbe_video",
        "ebe_realtime",
    }
    assert request.source_hints == ("one", "two")


def test_portable_docs_path_reanchors_old_absolute_path(tmp_path: Path) -> None:
    actual = portable_docs_path(
        "/old/machine/projects/docs/operacion/datos/x/control_runs/"
        "control_a/alerts.jsonl",
        tmp_path,
    )

    assert actual == tmp_path / "docs/operacion/datos/x/control_runs/control_a"


def test_resolve_catalog_accepts_identical_duplicate_sources(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    _make_run(tmp_path / "media-a/run_x")
    _make_run(tmp_path / "media-b/run_x")

    [result] = resolve_catalog(manifest, [_request("run_x", "dbe_video")], tmp_path)

    assert result.status == "copied"
    assert len(result.source_dirs) == 2


def test_resolve_catalog_marks_non_identical_duplicate_as_conflict(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path)
    _make_run(tmp_path / "media-a/run_x", summary="a")
    _make_run(tmp_path / "media-b/run_x", summary="b")

    [result] = resolve_catalog(manifest, [_request("run_x", "dbe_video")], tmp_path)

    assert result.status == "conflict"
    assert "divergentes" in (result.reason or "")


def test_resolve_catalog_uses_declared_campaign_substitute(tmp_path: Path) -> None:
    eval_path = tmp_path / "experimental/results/clip_bench/t1/evals/eval_a.json"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text("{}\n", encoding="utf-8")
    manifest = _manifest(
        tmp_path,
        media_roots=("../media-a",),
        archived_only=(
            {
                "id": "t1_controls",
                "request_source": "campaign:clip_bench/t1",
                "substitute_from": "matching_eval",
                "reason": "scratchpad ausente",
            },
        ),
    )
    request = RunRequest(
        RunKey("control-plane", "control_t1"),
        (_relation("dbe_video", "clip_bench/t1"),),
        source_hints=("/deleted/control_t1/alerts.jsonl",),
        archived_substitutes=("results/clip_bench/t1/evals/eval_a.json",),
    )

    [result] = resolve_catalog(manifest, [request], tmp_path)

    assert result.status == "archived_only"
    assert result.archived_substitutes == (eval_path,)


def test_resolve_catalog_uses_declared_result_substitute(tmp_path: Path) -> None:
    data_path = tmp_path / "docs/operacion/datos/bench.json"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("{}\n", encoding="utf-8")
    manifest = _manifest(
        tmp_path,
        media_roots=("../media-a",),
        archived_only=(
            {
                "id": "bench_original_missing",
                "relation_result_id": "bench_imagenes/modelos_crudos",
                "substitutes": ["../docs/operacion/datos/bench.json"],
                "reason": "el JSON crudo conserva el resultado",
            },
        ),
    )
    request = RunRequest(
        RunKey("media-plane", "run_missing"),
        (_relation("dbe_datasets", "bench_imagenes/modelos_crudos"),),
    )

    [result] = resolve_catalog(manifest, [request], tmp_path)

    assert result.status == "archived_only"
    assert result.archived_substitutes == (data_path,)


def test_resolve_catalog_does_not_downgrade_an_undeclared_missing_run(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path, media_roots=("../media-a",))

    [result] = resolve_catalog(
        manifest, [_request("run_missing", "dbe_video")], tmp_path
    )

    assert result.status == "missing"


def test_manual_requests_rejects_an_incomplete_required_pair(tmp_path: Path) -> None:
    manifest = _manifest(
        tmp_path,
        manual_groups=(
            {
                "id": "ebe_pair",
                "collection": "ebe_realtime",
                "result_id": "doc65",
                "role": "l0",
                "document": "../docs/operacion/65.md",
                "requires_pair": True,
                "pairs": [{"pair_id": "p1", "media_run_id": "run_media"}],
            },
        ),
    )

    with pytest.raises(EvidenceError, match="media_run_id.*control_run_id"):
        manual_requests(manifest)
