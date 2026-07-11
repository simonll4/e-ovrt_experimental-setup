"""Tests del generador de reporte consolidado (spec 40 SS6, spec 44 Tarea 3).

El generador agrega lo persistido por ambos planos (ADR-006): no recalcula, salvo
la unica excepcion del join t_capture->alert (spec 40 SS5.2.4). Los dirs
consolidados se arman a mano con tmp_path (mismo layout que produce
`consolidation.consolidate_experiment`, Tarea 2), sin pasar por esa funcion.
"""
from __future__ import annotations

import json

import yaml

from eovrt_webconsole.experiment.report import generate_report, render_markdown, write_report


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
                     encoding="utf-8")


def _write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _build_video_experiment(tmp_path):
    """Corrida DBE sobre video: source_clock=media -> t_capture->alert no interpretable."""
    root = tmp_path / "exp_video"

    media_effective_config = {"model_ref": "gdino-tiny", "prompt_set_id": "eind_v1"}
    _write_yaml(root / "media" / "effective_config.yaml", media_effective_config)
    _write_json(
        root / "media" / "summary.json",
        {
            "run_id": "media-run-1",
            "scenario": "video_x",
            "model_name": "gdino-tiny",
            "prompt_set_id": "eind_v1",
            "source_type": "video",
            "source_count": 1,
            "units_processed": 50,
            "units_failed": 0,
            "avg_latency_ms": 120.0,
            "p50_latency_ms": 110.0,
            "p95_latency_ms": 180.0,
            "p99_latency_ms": 200.0,
            "fps_effective": 8.5,
            "device": "cuda:0",
            "gpu_memory_peak_mb": 2048.0,
            "duration_seconds": 12.3,
            "started_at": "2026-07-11T00:00:00Z",
            "finished_at": "2026-07-11T00:00:12Z",
            "units_dropped": 2,
            "source_clock": "media",
            "run_descriptor": {
                "scenario": "video_x",
                "topology": "single_host",
                "transport": {},
                "rate_control": {},
                "source_kind": "video_file",
                "model": "gdino-tiny",
            },
            "g2a": {
                "state": "computed",
                "causes": [],
                "count": 50,
                "warmup_units": 5,
                "avg_ms": 90.0,
                "p50_ms": 85.0,
                "p95_ms": 140.0,
                "p99_ms": 160.0,
                "budget_min_ms": 50.0,
                "budget_max_ms": 250.0,
                "p95_within_budget": True,
            },
        },
    )
    _write_jsonl(
        root / "media" / "metrics.jsonl",
        [
            {"unit_id": "u1", "capture_monotonic_ns": 1_000_000_000},
            {"unit_id": "u2", "capture_monotonic_ns": 1_100_000_000},
        ],
    )

    control_effective_config = {"pattern_set_id": "cr01_cr02_v2"}
    _write_yaml(root / "control" / "effective_config.yaml", control_effective_config)
    _write_json(
        root / "control" / "summary.json",
        {
            "control_run_id": "control-run-1",
            "media_run_ids": ["media-run-1"],
            "scenario": "video_x",
            "pattern_set_id": "cr01_cr02_v2",
            "active_pattern_ids": ["cr01"],
            "units_processed": 50,
            "units_failed": 0,
            "pattern_events_count": 3,
            "alerts_count": 1,
            "errors_count": 0,
            "avg_processing_ms": 5.0,
            "processing_ms_percentiles": {"p50": 4.0, "p95": 9.0, "p99": 12.0},
            "ttfa_internal_ms_percentiles": {"p50": 20.0, "p95": 40.0, "p99": 60.0},
            "media_run_id": "media-run-1",
            "experiment_id": "exp_video",
            "source": "jsonl",
            "bus_dropped_events": 0,
        },
    )
    _write_jsonl(
        root / "control" / "alerts.jsonl",
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
    _write_jsonl(root / "control" / "metrics.jsonl", [{"unit_id": "u1", "alerts_count": 1}])
    _write_jsonl(root / "control" / "pattern_events.jsonl", [{"event": "cr01_confirmed"}])

    manifest_effective = {
        "schema_version": "experiment.manifest.v1",
        "slug": "video-smoke",
        "experiment_id": "exp_video",
        "runs": {
            "media": {"service": "media", "config": "media.yaml", "mode": "run"},
            "control": {"service": "control", "config": "control.yaml", "mode": "replay"},
        },
        "frozen": {
            "prompt_set": "eind_v1",
            "pattern_set": "cr01_cr02_v2",
            "model_ref": "gdino-tiny",
        },
        # Config "enviada" congelada al armar el manifiesto -- ver el
        # comentario de anti-drift en report.py sobre esta clave opcional.
        "sent_config": {
            "media": media_effective_config,
            # Deliberadamente distinta de control/effective_config.yaml para
            # ejercitar la deteccion de drift.
            "control": {"pattern_set_id": "cr01_cr02_v1_DRIFTED"},
        },
    }
    _write_yaml(root / "manifest.effective.yaml", manifest_effective)

    (root / "report").mkdir(parents=True, exist_ok=True)
    return root


def _build_images_experiment(tmp_path):
    """Corrida sobre dataset de imagenes: source_clock=none -> fuente no temporal."""
    root = tmp_path / "exp_images"

    _write_json(
        root / "media" / "summary.json",
        {
            "run_id": "media-run-2",
            "scenario": "images_x",
            "model_name": "gdino-tiny",
            "source_type": "image",
            "source_count": 200,
            "units_processed": 200,
            "units_failed": 0,
            "source_clock": "none",
            "g2a": {"state": "computed", "causes": [], "count": 200, "warmup_units": 0,
                    "avg_ms": 40.0, "p50_ms": 38.0, "p95_ms": 60.0, "p99_ms": 70.0,
                    "budget_min_ms": 50.0, "budget_max_ms": 250.0, "p95_within_budget": True},
        },
    )
    _write_jsonl(
        root / "media" / "metrics.jsonl",
        [{"unit_id": "u1", "capture_monotonic_ns": 500_000_000}],
    )

    _write_json(
        root / "control" / "summary.json",
        {
            "control_run_id": "control-run-2",
            "scenario": "images_x",
            "pattern_set_id": "cr01_cr02_v2",
            "active_pattern_ids": ["cr01"],
            "units_processed": 200,
            "units_failed": 0,
            "pattern_events_count": 0,
            "alerts_count": 1,
            "errors_count": 0,
            "avg_processing_ms": 2.0,
        },
    )
    _write_jsonl(
        root / "control" / "alerts.jsonl",
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

    _write_yaml(
        root / "manifest.effective.yaml",
        {
            "schema_version": "experiment.manifest.v1",
            "slug": "images-smoke",
            "experiment_id": "exp_images",
            "runs": {
                "media": {"service": "media", "config": "media.yaml", "mode": "run"},
                "control": {"service": "control", "config": "control.yaml", "mode": "replay"},
            },
            "frozen": {},
        },
    )
    (root / "report").mkdir(parents=True, exist_ok=True)
    return root


def test_video_run_t_capture_to_alert_not_interpretable_and_compute_budget_computed(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)

    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_capture = resultados_by_name["t_capture->alert"]
    assert t_capture["status"] == "not_interpretable"
    assert t_capture["cause"] == "dbe_media_time"

    t_budget = resultados_by_name["t_compute-budget"]
    assert t_budget["status"] == "computed"
    assert t_budget["value"] is not None


def test_ground_truth_metrics_figuran_not_applicable_no_ground_truth(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    for name in ("t_alert-system", "TTFD", "SDR", "mAP", "recall CR-01"):
        assert name in resultados_by_name, f"{name} debe figurar en resultados, no omitirse"
        assert resultados_by_name[name]["status"] == "not_applicable"
        assert resultados_by_name[name]["cause"] == "no_ground_truth"


def test_todas_las_metricas_del_diccionario_figuran(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    nombres = {m["name"] for m in report["resultados"]}

    for name in (
        "G2A",
        "t_alert-system",
        "t_capture->alert",
        "t_compute-budget",
        "t_alert-notification",
        "TTFD",
        "SDR",
        "TTFA interna",
        "ΔFP_tracker",
        "re_alerts",
    ):
        assert name in nombres, f"{name} falta en resultados (ADR-006: deben figurar todas)"


def test_g2a_computed_desde_summary_de_media(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    g2a = resultados_by_name["G2A"]
    assert g2a["status"] == "computed"
    assert g2a["value"] == 140.0  # p95_ms del bloque g2a del summary


def test_re_alerts_toma_el_conteo_del_summary_de_control_si_esta(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    # Agrega el conteo de re_alerts al summary de control (no requiere GT completo).
    control_summary_path = consolidated_dir / "control" / "summary.json"
    control_summary = json.loads(control_summary_path.read_text(encoding="utf-8"))
    control_summary["re_alerts_count"] = 2
    control_summary_path.write_text(json.dumps(control_summary), encoding="utf-8")

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    re_alerts = resultados_by_name["re_alerts"]
    assert re_alerts["status"] == "computed"
    assert re_alerts["value"] == 2.0


def test_re_alerts_no_temporal_source_cuando_source_clock_none(tmp_path):
    # source_clock: none (imagenes) -- re_alerts es metrica de patron/temporal
    # (spec 40 SS5.2.3.3): su causa de no-aplicabilidad debe ser
    # non_temporal_source, no no_ground_truth (finding de revision).
    consolidated_dir = _build_images_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    re_alerts = resultados_by_name["re_alerts"]
    assert re_alerts["status"] == "not_applicable"
    assert re_alerts["cause"] == "non_temporal_source"


def test_anti_drift_marca_diferencia_entre_config_enviada_y_efectiva(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    anti_drift = report["anti_drift"]

    # media: la config "enviada" (sent_config.media) es igual a la persistida -> sin drift.
    assert anti_drift["media"]["checked"] is True
    assert anti_drift["media"]["drift_detected"] is False

    # control: la config "enviada" difiere deliberadamente de la persistida -> drift.
    assert anti_drift["control"]["checked"] is True
    assert anti_drift["control"]["drift_detected"] is True


def test_anti_drift_no_rompe_si_no_hay_config_enviada(tmp_path):
    consolidated_dir = _build_images_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    anti_drift = report["anti_drift"]

    # exp_images no tiene "sent_config" en el manifiesto ni effective_config
    # persistido: el chequeo queda "no verificable", no rompe.
    assert anti_drift["media"]["checked"] is False
    assert anti_drift["control"]["checked"] is False


def test_images_run_source_no_temporal(tmp_path):
    consolidated_dir = _build_images_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_capture = resultados_by_name["t_capture->alert"]
    assert t_capture["status"] == "not_applicable"
    assert t_capture["cause"] == "non_temporal_source"

    t_budget = resultados_by_name["t_compute-budget"]
    assert t_budget["status"] == "computed"
    assert t_budget["value"] is not None

    observaciones = " ".join(report["observaciones"])
    assert "diagnostico espacial" in observaciones or "smoke de contrato" in observaciones


def test_render_markdown_no_vacio_con_secciones(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    report = generate_report(consolidated_dir)

    markdown = render_markdown(report)

    assert markdown.strip() != ""
    for header in (
        "Identificacion",
        "Modelo",
        "Entrada",
        "Parametros",
        "Hardware",
        "Temporalidad",
        "Eventos",
        "Resultados",
        "Anti-drift",
        "Observaciones",
    ):
        assert header in markdown


def test_write_report_escribe_json_y_markdown(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    json_path, md_path = write_report(consolidated_dir)

    assert json_path == consolidated_dir / "report" / "report.json"
    assert md_path == consolidated_dir / "report" / "report.md"
    assert json_path.is_file()
    assert md_path.is_file()

    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted["identificacion"]["experiment_id"] == "exp_video"
