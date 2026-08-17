from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evidence_archive.catalog import manual_requests
from tools.evidence_archive.manifest import (
    campaign_requests,
    discover_campaigns,
    extract_values,
    load_manifest,
    structured_requests,
)
from tools.evidence_archive.model import EvidenceError, Manifest, RunKey


COLLECTIONS = {
    "dbe_datasets": "Resultados DBE sobre datasets",
    "dbe_video": "Resultados DBE sobre video",
    "ebe_realtime": "Resultados EBE realtime",
    "shared": "Runs compartidos",
}


def _write_manifest(repo: Path, expected_campaigns: list[str]) -> Path:
    manifest = repo / "results/evidence-runs.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "\n".join(
            [
                "schema_version: evidence_runs.v1",
                "generated_date: 2026-08-13",
                "collections:",
                *[f"  {key}: {value}" for key, value in COLLECTIONS.items()],
                "source_roots:",
                "  media-plane: [../e-ovrt_media-plane/runs]",
                "  control-plane: [../e-ovrt_control-plane/runs]",
                "expected_campaigns:",
                *[f"  - {campaign}" for campaign in expected_campaigns],
                "structured_sources: []",
                "manual_groups: []",
                "archived_only: []",
                "archive_policy:",
                "  allowed_extensions: [.json, .jsonl, .yaml]",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def _write_campaign(
    repo: Path,
    campaign_key: str,
    provenance: object,
    *,
    eval_alerts_path: str | None = None,
) -> Path:
    campaign = repo / "results" / campaign_key
    campaign.mkdir(parents=True)
    (campaign / "metrics.json").write_text("{}\n", encoding="utf-8")
    (campaign / "campaign.yaml").write_text(
        f"campaign_id: {campaign.name}\n", encoding="utf-8"
    )
    (campaign / "provenance.json").write_text(
        json.dumps(provenance) + "\n", encoding="utf-8"
    )
    if eval_alerts_path is not None:
        evals = campaign / "evals"
        evals.mkdir()
        (evals / "eval_clip_a.json").write_text(
            json.dumps({"alerts_path": eval_alerts_path}) + "\n",
            encoding="utf-8",
        )
    return campaign


def test_extract_values_walks_lists_and_object_values() -> None:
    data = {
        "rows": [{"run_id": "run_a"}, {"run_id": "run_b"}],
        "nested": {"left": {"run_id": "run_c"}},
    }

    assert extract_values(data, "rows.*.run_id") == ["run_a", "run_b"]
    assert extract_values(data, "nested.*.run_id") == ["run_c"]


def test_extract_values_rejects_a_missing_token() -> None:
    with pytest.raises(EvidenceError, match="selector"):
        extract_values({"rows": []}, "missing.*.run_id")


def test_discover_campaigns_requires_provenance(tmp_path: Path) -> None:
    campaign = tmp_path / "results/clip_bench/t1"
    campaign.mkdir(parents=True)
    (campaign / "metrics.json").write_text("{}\n", encoding="utf-8")
    (campaign / "campaign.yaml").write_text("campaign_id: t1\n", encoding="utf-8")

    with pytest.raises(EvidenceError, match="provenance"):
        discover_campaigns(tmp_path)


def test_campaign_requests_extracts_media_and_control_runs(tmp_path: Path) -> None:
    campaign_key = "clip_bench/t1"
    _write_campaign(
        tmp_path,
        campaign_key,
        [
            {
                "clip_id": "clip_a",
                "media_run_id": "run_media",
                "nested": {
                    "eind_run_id": "run_eind",
                    "edir_run_id": "run_edir",
                    "detections_from": "run_reused",
                },
            }
        ],
        eval_alerts_path=(
            "/old/work/docs/operacion/datos/campaign/control_runs/"
            "control_eval_20260803T000000Z/alerts.jsonl"
        ),
    )
    manifest = load_manifest(_write_manifest(tmp_path, [campaign_key]))

    requests = campaign_requests(manifest, tmp_path)
    keys = {item.key for item in requests}

    assert RunKey("media-plane", "run_media") in keys
    assert RunKey("media-plane", "run_eind") in keys
    assert RunKey("media-plane", "run_edir") in keys
    assert RunKey("media-plane", "run_reused") in keys
    assert RunKey("control-plane", "control_eval_20260803T000000Z") in keys


def test_campaign_requests_rejects_manifest_coverage_drift(tmp_path: Path) -> None:
    _write_campaign(tmp_path, "clip_bench/t1", [{"media_run_id": "run_media"}])
    manifest = load_manifest(_write_manifest(tmp_path, ["clip_bench/t2"]))

    with pytest.raises(EvidenceError, match="campañas"):
        campaign_requests(manifest, tmp_path)


def test_structured_eval_source_extracts_control_runs_from_alert_paths(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "e-ovrt_experimental-setup"
    manifest_path = repo / "results/evidence-runs.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("schema_version: evidence_runs.v1\n", encoding="utf-8")
    source_dir = tmp_path / "docs/operacion/datos/variant"
    control_dir = source_dir / "control_runs/control_variant_a"
    control_dir.mkdir(parents=True)
    (control_dir / "alerts.jsonl").write_text("", encoding="utf-8")
    (source_dir / "eval_a.json").write_text(
        json.dumps(
            {
                "alerts_path": (
                    "/old/projects/docs/operacion/datos/variant/control_runs/"
                    "control_variant_a/alerts.jsonl"
                )
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = Manifest(
        path=manifest_path,
        generated_date="2026-08-13",
        collections=tuple(sorted(COLLECTIONS)),
        source_roots={
            "media-plane": ("../e-ovrt_media-plane/runs",),
            "control-plane": ("../e-ovrt_control-plane/runs",),
        },
        expected_campaigns=(),
        structured_sources=(
            {
                "id": "empirical_controls",
                "kind": "eval_control_runs",
                "paths": ["../docs/operacion/datos/variant"],
                "expected_count": 1,
                "collection": "ebe_realtime",
                "result_id": "realtime/decimado_empirico",
                "role": "empirical_control",
            },
        ),
        manual_groups=(),
        archived_only=(),
        archive_policy={"allowed_extensions": [".json", ".jsonl"]},
    )

    [request] = structured_requests(manifest, repo)

    assert request.key == RunKey("control-plane", "control_variant_a")
    assert request.source_hints[0].endswith("control_variant_a/alerts.jsonl")
    assert request.relations[0].source_ref == (
        "../docs/operacion/datos/variant/eval_a.json"
    )


REAL_REPO = Path(__file__).resolve().parents[1]


def test_real_manifest_covers_every_current_campaign() -> None:
    manifest = load_manifest(REAL_REPO / "results/evidence-runs.yaml")

    discovered = set(discover_campaigns(REAL_REPO))

    assert discovered == set(manifest.expected_campaigns)
    assert len(discovered) == 16


def test_real_campaign_baseline_has_every_media_and_control_run() -> None:
    manifest = load_manifest(REAL_REPO / "results/evidence-runs.yaml")

    requests = campaign_requests(manifest, REAL_REPO)

    assert (
        len({item.key for item in requests if item.key.plane == "media-plane"}) == 273
    )
    assert (
        len({item.key for item in requests if item.key.plane == "control-plane"}) == 434
    )


def test_real_manifest_resolves_all_structured_and_manual_sources() -> None:
    manifest = load_manifest(REAL_REPO / "results/evidence-runs.yaml")

    structured = structured_requests(manifest, REAL_REPO)
    manual = manual_requests(manifest)

    assert len(structured) == 721
    assert (
        len({item.key for item in structured if item.key.plane == "control-plane"})
        == 544
    )
    # 53 manuales históricas + 6 nuevas del doc 118 con requests explícitas a doc 118.
    assert len(manual) == 59
    assert len(manifest.archived_only) == 6
