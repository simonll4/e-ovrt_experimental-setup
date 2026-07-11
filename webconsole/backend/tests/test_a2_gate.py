"""Gate A2: e2e consolidacion + reporte + verificacion por mutacion (spec 44 SS4 Tarea 5).

Prueba de punta a punta sobre artefactos sinteticos "crudos" de ambos planos
(como los dejarian media-plane y control-plane en `runs/<run_id>/`): arma los
run dirs, corre `consolidate_experiment` (ADR-014, Tarea 2) sobre ellos y
despues `generate_report` (spec 40 SS6, Tarea 3) sobre el consolidado
resultante.

Dos escenarios, los dos bordes de aplicabilidad que importan al gate:
- video (`source_clock: media`): `t_capture->alert` no interpretable
  (dbe_media_time), `t_compute-budget` si se computa.
- imagenes (`source_clock: none`): fuente no temporal, `t_capture->alert` y
  `re_alerts` no aplican (non_temporal_source), `t_compute-budget` igual se
  computa (spec 40 SS5.2.1: independiente de la fuente).

Ademas verifica el layout ADR-014: los artefactos livianos se copian, pero
`detections.jsonl` (el crudo pesado del media-plane) NUNCA se copia dentro
del consolidado -- solo se referencia via `detections.ref.json`.

Este archivo es el gate del plan A2 (Tarea 5): su significancia se verifica
por mutacion (ver `.superpowers/sdd/a2/task-5-report.md` para la corrida de
las dos mutaciones obligatorias), no se repite aca.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from eovrt_webconsole.experiment.consolidation import consolidate_experiment
from eovrt_webconsole.experiment.report import generate_report


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row) for row in rows)
    path.write_text(content + ("\n" if rows else ""), encoding="utf-8")


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Escenario video: source_clock=media (reloj del medio, DBE).
# ---------------------------------------------------------------------------


def _build_video_media_run_dir(tmp_path: Path) -> Path:
    """Run dir crudo del media-plane para una corrida sobre video."""
    run_dir = tmp_path / "media_runs" / "media-run-video"
    _write_yaml(run_dir / "effective_config.yaml", {"model_ref": "gdino-tiny"})
    _write_json(
        run_dir / "summary.json",
        {
            "run_id": "media-run-video",
            "scenario": "video_gate",
            "model_name": "gdino-tiny",
            "source_type": "video",
            "source_count": 1,
            "units_processed": 50,
            "source_clock": "media",
            "run_descriptor": {"topology": "single_host"},
            "g2a": {"state": "computed", "causes": [], "p95_ms": 130.0, "warmup_units": 5},
        },
    )
    _write_jsonl(
        run_dir / "metrics.jsonl",
        [{"unit_id": "u1", "capture_monotonic_ns": 1_000_000_000}],
    )
    # Crudo pesado: simula un run real (miles de lineas). ADR-014: nunca debe
    # terminar copiado dentro del consolidado, solo referenciado.
    _write_jsonl(run_dir / "detections.jsonl", [{"unit_id": "u1", "boxes": []}] * 5000)
    return run_dir


def _build_control_run_dir_video(tmp_path: Path) -> Path:
    run_dir = tmp_path / "control_runs" / "control-run-video"
    _write_yaml(run_dir / "effective_config.yaml", {"pattern_set_id": "cr01_cr02_v2"})
    _write_json(
        run_dir / "summary.json",
        {
            "control_run_id": "control-run-video",
            "pattern_set_id": "cr01_cr02_v2",
            "active_pattern_ids": ["cr01"],
            "alerts_count": 1,
        },
    )
    _write_jsonl(
        run_dir / "alerts.jsonl",
        [
            {
                "alert_id": "al-1",
                "first_evidence_unit_id": "u1",
                "first_evidence_ms": 1000.0,
                "alert_registered_ms": 1300.0,
                "confirmed_at_ms": 1250.0,
            }
        ],
    )
    _write_jsonl(run_dir / "metrics.jsonl", [{"unit_id": "u1", "alerts_count": 1}])
    _write_jsonl(run_dir / "pattern_events.jsonl", [{"event": "cr01_confirmed"}])
    return run_dir


def test_gate_video_layout_adr014_y_aplicabilidad(tmp_path):
    media_run_dir = _build_video_media_run_dir(tmp_path)
    control_run_dir = _build_control_run_dir_video(tmp_path)
    dest_root = tmp_path / "runs"

    consolidated_dir = consolidate_experiment(
        "exp_gate_video",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective={
            "schema_version": "experiment.manifest.v1",
            "experiment_id": "exp_gate_video",
        },
        dest_root=dest_root,
    )

    # ADR-014: los livianos de ambos planos se copian dentro del consolidado.
    assert (consolidated_dir / "media" / "summary.json").is_file()
    assert (consolidated_dir / "media" / "metrics.jsonl").is_file()
    assert (consolidated_dir / "media" / "effective_config.yaml").is_file()
    assert (consolidated_dir / "control" / "summary.json").is_file()
    assert (consolidated_dir / "control" / "alerts.jsonl").is_file()
    assert (consolidated_dir / "control" / "pattern_events.jsonl").is_file()

    # ADR-014: detections.jsonl (crudo pesado) NUNCA se copia -- se referencia.
    assert not (consolidated_dir / "media" / "detections.jsonl").exists()
    ref_path = consolidated_dir / "media" / "detections.ref.json"
    assert ref_path.is_file()
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    assert ref["run_id"] == "media-run-video"
    assert ref["path"] == str(media_run_dir / "detections.jsonl")

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_capture = resultados_by_name["t_capture->alert"]
    assert t_capture["status"] == "not_interpretable"
    assert t_capture["cause"] == "dbe_media_time"

    t_budget = resultados_by_name["t_compute-budget"]
    assert t_budget["status"] == "computed"
    assert t_budget["value"] is not None


# ---------------------------------------------------------------------------
# Escenario imagenes: source_clock=none (fuente no temporal, ADR-013).
# ---------------------------------------------------------------------------


def _build_images_media_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "media_runs" / "media-run-images"
    _write_json(
        run_dir / "summary.json",
        {
            "run_id": "media-run-images",
            "scenario": "images_gate",
            "source_type": "image",
            "source_count": 200,
            "units_processed": 200,
            "source_clock": "none",
            "g2a": {"state": "computed", "causes": [], "p95_ms": 60.0, "warmup_units": 0},
        },
    )
    _write_jsonl(
        run_dir / "metrics.jsonl",
        [{"unit_id": "u1", "capture_monotonic_ns": 500_000_000}],
    )
    _write_jsonl(run_dir / "detections.jsonl", [{"unit_id": "u1", "boxes": []}] * 3000)
    return run_dir


def _build_control_run_dir_images(tmp_path: Path) -> Path:
    run_dir = tmp_path / "control_runs" / "control-run-images"
    _write_json(
        run_dir / "summary.json",
        {
            "control_run_id": "control-run-images",
            "pattern_set_id": "cr01_cr02_v2",
            "active_pattern_ids": ["cr01"],
            "alerts_count": 1,
            # Sin re_alerts_count: no hay GT (tramo plataforma, spec 43 diferido).
        },
    )
    _write_jsonl(
        run_dir / "alerts.jsonl",
        [
            {
                "alert_id": "al-2",
                "first_evidence_unit_id": "u1",
                "first_evidence_ms": 100.0,
                "alert_registered_ms": 250.0,
                "confirmed_at_ms": 200.0,
            }
        ],
    )
    return run_dir


def test_gate_images_layout_adr014_y_aplicabilidad(tmp_path):
    media_run_dir = _build_images_media_run_dir(tmp_path)
    control_run_dir = _build_control_run_dir_images(tmp_path)
    dest_root = tmp_path / "runs"

    consolidated_dir = consolidate_experiment(
        "exp_gate_images",
        media_run_dir=media_run_dir,
        control_run_dir=control_run_dir,
        manifest_effective={
            "schema_version": "experiment.manifest.v1",
            "experiment_id": "exp_gate_images",
        },
        dest_root=dest_root,
    )

    # ADR-014: idem video, el crudo pesado nunca se copia.
    assert not (consolidated_dir / "media" / "detections.jsonl").exists()
    assert (consolidated_dir / "media" / "detections.ref.json").is_file()

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_capture = resultados_by_name["t_capture->alert"]
    assert t_capture["status"] == "not_applicable"
    assert t_capture["cause"] == "non_temporal_source"

    # t_compute-budget es independiente de la fuente (spec 40 SS5.2.1): se
    # computa igual, aunque t_capture->alert no aplique.
    t_budget = resultados_by_name["t_compute-budget"]
    assert t_budget["status"] == "computed"
    assert t_budget["value"] is not None

    # re_alerts es metrica de patron/temporal: en fuente no temporal su causa
    # es non_temporal_source, no no_ground_truth (fix del finding de revision).
    re_alerts = resultados_by_name["re_alerts"]
    assert re_alerts["status"] == "not_applicable"
    assert re_alerts["cause"] == "non_temporal_source"

    # GT del tramo plataforma: figura, no se omite (ADR-006).
    mAP = resultados_by_name["mAP"]
    assert mAP["status"] == "not_applicable"
    assert mAP["cause"] == "no_ground_truth"
