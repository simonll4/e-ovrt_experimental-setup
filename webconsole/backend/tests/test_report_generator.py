"""Tests del generador de reporte consolidado (spec 40 SS6, spec 44 Tarea 3).

El generador agrega lo persistido por ambos planos (ADR-006): no recalcula, salvo
la unica excepcion del join t_capture->alert (spec 40 SS5.2.4). Los dirs
consolidados se arman a mano con tmp_path (mismo layout que produce
`consolidation.consolidate_experiment`, Tarea 2), sin pasar por esa funcion.
"""
from __future__ import annotations

import json

import yaml

from eovrt_webconsole.experiment.report import (
    DISTRIBUTION_WALL_CLOCK_DBE_ONLY,
    generate_report,
    render_markdown,
    write_report,
)


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


def test_distribution_metric_not_applicable_sin_distribution_summary(tmp_path):
    """Sin runs/exp_<id>/distribution/ (mayoria de las corridas hoy): comportamiento
    sin cambios, mismo que antes de cablear la distribucion (spec 45 / ADR-016)."""
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_notif = resultados_by_name["t_alert-notification"]
    assert t_notif["status"] == "not_applicable"
    assert t_notif["cause"] == "no_distribution"
    assert report["distribucion"] == {}


def test_distribution_metric_computed_desde_latencia_live(tmp_path):
    """Con modo 'live' presente (EBE, publisher real): es la latencia operativa,
    se reporta como computed con el p95 de ESE modo (nunca mezclado con DBE)."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "distribution_summary.json",
        {
            "schema_version": "control.distribution_summary.v1",
            "channel": "mqtt",
            "mode": "live",
            "counts": {"delivered": 23, "suppressed_cooldown": 170},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": {
                "live": {"count": 23, "min": 0.7, "mean": 1.2, "p95": 1.8},
            },
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_notif = resultados_by_name["t_alert-notification"]
    assert t_notif["status"] == "computed"
    assert t_notif["value"] == 1.8
    assert t_notif["cause"] is None
    assert report["distribucion"]["counts"]["delivered"] == 23


def test_distribution_metric_not_interpretable_solo_wall_clock_dbe(tmp_path):
    """Replay DBE con `mode='dry_run'`: la causa es canal no operativo.

    La causa `distribution_wall_clock_dbe_only` ya no aplica si el canal no fue
    `live`.
    """
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "distribution_summary.json",
        {
            "schema_version": "control.distribution_summary.v1",
            "channel": "mqtt",
            "mode": "dry_run",
            "counts": {"delivered": 23, "suppressed_cooldown": 170},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": {
                "wall_clock_dbe": {"count": 23, "min": 0.02, "mean": 0.03, "p95": 0.05},
            },
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_notif = resultados_by_name["t_alert-notification"]
    assert t_notif["status"] == "applicable_not_computed"
    assert t_notif["cause"] == "canal en dry_run: la latencia no atraviesa un broker MQTT real; " \
        "la metrica operativa exige channel.mode=live (92b SS8)"
    assert t_notif["value"] is None


def test_distribution_metric_not_interpretable_canal_live_solo_wall_clock_dbe(tmp_path):
    """Canal MQTT live real, pero la latencia agregada SOLO tiene base
    `wall_clock_dbe` (reproceso DBE publicado contra un broker de verdad): no es
    la latencia operativa, y tampoco es un caveat escondido detras de un numero
    -> `not_interpretable`.

    Es la unica combinacion que alcanza la rama
    `DISTRIBUTION_WALL_CLOCK_DBE_ONLY`: con `mode != live` el guard de dry_run
    corta antes, asi que sin `mode: live` esta rama queda muerta y sin cubrir.
    """
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "distribution_summary.json",
        {
            "schema_version": "control.distribution_summary.v1",
            "channel": "mqtt",
            "mode": "live",
            "counts": {"delivered": 23, "suppressed_cooldown": 170},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": {
                "wall_clock_dbe": {"count": 23, "min": 0.02, "mean": 0.03, "p95": 0.05},
            },
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_notif = resultados_by_name["t_alert-notification"]
    assert t_notif["status"] == "not_interpretable"
    assert t_notif["cause"] == DISTRIBUTION_WALL_CLOCK_DBE_ONLY
    assert t_notif["cause"] == "distribution_wall_clock_dbe_only"
    assert t_notif["value"] is None


def test_distribution_metric_dry_run_channel_never_computed():
    detail = {
        "schema_version": "control.distribution_summary.v1",
        "channel": "mqtt",
        "mode": "dry_run",
        "counts": {"delivered": 3},
        "talert_notification_ms": {"live": {"count": 3, "min": 1.0, "mean": 2.0, "p95": 7.8}},
    }
    from eovrt_webconsole.experiment.report import _distribution_metric

    metric = _distribution_metric(detail)

    assert metric.status == "applicable_not_computed"
    assert metric.cause == (
        "canal en dry_run: la latencia no atraviesa un broker MQTT real; "
        "la metrica operativa exige channel.mode=live (92b SS8)"
    )
    assert metric.value is None


def test_distribution_metric_live_channel_still_computed():
    detail = {
        "schema_version": "control.distribution_summary.v1",
        "mode": "live",
        "counts": {"delivered": 3},
        "talert_notification_ms": {"live": {"count": 3, "min": 1.0, "mean": 2.0, "p95": 7.8}},
    }
    from eovrt_webconsole.experiment.report import _distribution_metric

    metric = _distribution_metric(detail)
    assert metric.status == "computed"


def test_distribution_outcomes_by_alert_toma_ultimo_por_alert_id(tmp_path):
    """Ante reintentos, se conserva el último outcome por alert_id.

    `distribution/notifications.jsonl` es append-only: una misma alerta puede
    aparecer varias veces (reintento), y el registro terminal real es la última
    línea de ese alert_id. Cualquier UI que mire la primera pierde el estado final.
    """
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "notifications.jsonl",
        {
            "not_json": "ignored",
        },
    )
    # notifications en realidad es JSONL; escribo explícitamente para no
    # mezclar formatos al generar con _write_json.
    (consolidated_dir / "distribution" / "notifications.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"alert_id": "a-1", "outcome": "failed", "notification_id": "n1"}),
                json.dumps({"alert_id": "a-1", "outcome": "delivered", "notification_id": "n2"}),
                json.dumps({"alert_id": "a-2", "outcome": "failed", "notification_id": "n3"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = generate_report(consolidated_dir)
    outcomes = report["distribucion_por_alerta"]

    assert outcomes == {
        "a-1": {"alert_id": "a-1", "outcome": "delivered", "notification_id": "n2"},
        "a-2": {"alert_id": "a-2", "outcome": "failed", "notification_id": "n3"},
    }


def test_distribution_outcomes_by_alert_ignora_lineas_no_json(tmp_path):
    """Una línea corrupta no rompe el parser: se omite y se siguen procesando
    los registros válidos siguientes.

    En campo real esto se ve cuando un proceso se cae y deja trazas parciales:
    robustez en lectura evita que se pierda el reporte entero.
    """
    consolidated_dir = _build_video_experiment(tmp_path)
    notifications_path = consolidated_dir / "distribution" / "notifications.jsonl"
    notifications_path.parent.mkdir(parents=True, exist_ok=True)
    notifications_path.write_text(
        "\n".join(
            [
                "no-json",
                json.dumps({"alert_id": "a-1", "outcome": "failed"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = generate_report(consolidated_dir)
    outcomes = report["distribucion_por_alerta"]

    assert outcomes == {"a-1": {"alert_id": "a-1", "outcome": "failed"}}


def test_distribution_outcomes_by_alert_ignora_json_que_no_es_objeto(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    notifications_path = consolidated_dir / "distribution" / "notifications.jsonl"
    notifications_path.parent.mkdir(parents=True, exist_ok=True)
    notifications_path.write_text(
        "[]\nnull\n42\n" + json.dumps({"alert_id": "a-1", "outcome": "delivered"}) + "\n",
        encoding="utf-8",
    )

    report = generate_report(consolidated_dir)

    assert report["distribucion_por_alerta"] == {
        "a-1": {"alert_id": "a-1", "outcome": "delivered"}
    }


def test_distribution_summary_corrupto_se_trata_como_ausente(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    summary_path = consolidated_dir / "distribution" / "distribution_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("{truncado", encoding="utf-8")

    report = generate_report(consolidated_dir)
    metric = next(row for row in report["resultados"] if row["name"] == "t_alert-notification")

    assert report["distribucion"] == {}
    assert metric["status"] == "not_applicable"
    assert metric["cause"] == "no_distribution"


def test_distribution_summary_json_no_objeto_se_trata_como_ausente(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    summary_path = consolidated_dir / "distribution" / "distribution_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("[]", encoding="utf-8")

    report = generate_report(consolidated_dir)

    assert report["distribucion"] == {}


def test_distribution_artifacts_invalid_utf8_do_not_break_report(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    distribution_dir = consolidated_dir / "distribution"
    distribution_dir.mkdir()
    (distribution_dir / "distribution_summary.json").write_bytes(b"\xff")
    (distribution_dir / "notifications.jsonl").write_bytes(b"\xff")

    report = generate_report(consolidated_dir)

    assert report["distribucion"] == {}
    assert report["distribucion_por_alerta"] == {}


def test_distribution_outcomes_by_alert_vacio_sin_directorio_distribucion(tmp_path):
    """Corridas históricas sin distribución no rompen: `{}` como contrato
    tolerante de lectura (ADR-006: sin dato no hay excepción).
    """
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)

    assert report["distribucion_por_alerta"] == {}


def test_distribution_metric_applicable_not_computed_sin_entregas(tmp_path):
    """Distribucion corrio pero nada se entrego (todo suprimido/duplicado):
    no hay latencia que promediar, y no es lo mismo que 'no_distribution'
    (el modulo si corrio)."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "distribution_summary.json",
        {
            "schema_version": "control.distribution_summary.v1",
            "channel": "mqtt",
            "mode": "dry_run",
            "counts": {"suppressed_cooldown": 5},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": None,
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    t_notif = resultados_by_name["t_alert-notification"]
    assert t_notif["status"] == "applicable_not_computed"
    assert t_notif["cause"] == "no_notifications_delivered"


def test_hito_notificacion_entregada_refleja_delivered_del_summary(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "distribution" / "distribution_summary.json",
        {
            "schema_version": "control.distribution_summary.v1",
            "channel": "mqtt",
            "mode": "live",
            "counts": {"delivered": 1},
            "skipped_invalid_alerts": 0,
            "talert_notification_ms": {"live": {"count": 1, "min": 1.0, "mean": 1.0, "p95": 1.0}},
        },
    )

    report = generate_report(consolidated_dir)

    assert report["eventos"]["hitos"]["notificacion_entregada"] is True


def test_hito_notificacion_entregada_false_sin_distribucion(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)

    assert report["eventos"]["hitos"]["notificacion_entregada"] is False


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


def test_re_alerts_toma_el_conteo_de_la_evaluacion_temporal_dedicada(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_0007",
            "re_alerts_count": 3,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "applicability_state": "computed",
        },
    )

    report = generate_report(consolidated_dir)
    re_alerts = next(m for m in report["resultados"] if m["name"] == "re_alerts")

    assert re_alerts["status"] == "computed"
    assert re_alerts["value"] == 3.0


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


def test_sdr_ttfd_computed_desde_temporal_evaluation_json(tmp_path):
    """Cuando el runner corrio la evaluacion temporal (spec 43 SS6) y dejo
    `control/temporal_evaluation.json`, SDR/TTFD dejan de ser not_applicable."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_0007",
            "recall": 0.75,
            "precision": 0.9,
            "f1": 0.81,
            "avg_latency_ms_from_episode_start": 2500.0,
            # Campos NATIVOS de evaluate-alerts con --detections (spec 43 SS10).
            # SDR/TTFD salen SOLO de estos: recall y la latencia de alerta miden
            # otras metricas del diccionario y usarlas como proxy seria mentir.
            "avg_sdr": 0.68,
            "avg_ttfd_ms": 1200.0,
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    sdr = resultados_by_name["SDR"]
    assert sdr["status"] == "computed"
    assert sdr["value"] == 0.68  # avg_sdr nativo, NO recall (0.75)

    ttfd = resultados_by_name["TTFD"]
    assert ttfd["status"] == "computed"
    assert ttfd["value"] == 1.2  # avg_ttfd_ms/1000, NO la latencia de alerta (2.5)


def test_t_alert_system_y_clasificacion_se_proyectan_desde_evaluacion_temporal(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_0007",
            "matched_alerts_count": 2,
            "precision": 0.9,
            "recall": 0.75,
            "f1": 0.81,
            "avg_latency_ms_from_episode_start": 2500.0,
            "applicability_state": "computed",
            "applicability_cause": None,
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    assert resultados_by_name["t_alert-system"] == {
        "name": "t_alert-system",
        "value": 2.5,
        "unit": "s",
        "status": "computed",
        "cause": None,
        "passed": None,
        "threshold": None,
        "threshold_direction": None,
    }
    assert resultados_by_name["precision_alertas"]["value"] == 0.9
    assert resultados_by_name["recall_alertas"]["value"] == 0.75
    assert resultados_by_name["F1_alertas"]["value"] == 0.81
    for name in ("precision_alertas", "recall_alertas", "F1_alertas"):
        assert resultados_by_name[name]["status"] == "computed"


def test_metricas_temporales_honran_no_aplicabilidad_del_evaluador(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_negativo",
            "matched_alerts_count": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "avg_latency_ms_from_episode_start": None,
            "applicability_state": "not_applicable",
            "applicability_cause": "negative_clip_no_episodes",
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    for name in ("t_alert-system", "precision_alertas", "recall_alertas", "F1_alertas"):
        assert resultados_by_name[name]["status"] == "not_applicable"
        assert resultados_by_name[name]["value"] is None
        assert resultados_by_name[name]["cause"] == "negative_clip_no_episodes"


def test_t_alert_system_sin_matches_es_aplicable_no_computado(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_sin_match",
            "matched_alerts_count": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "avg_latency_ms_from_episode_start": None,
            "applicability_state": "computed",
            "applicability_cause": None,
        },
    )

    report = generate_report(consolidated_dir)
    metric = next(m for m in report["resultados"] if m["name"] == "t_alert-system")

    assert metric["status"] == "applicable_not_computed"
    assert metric["value"] is None
    assert metric["cause"] == "no_matched_alerts"


def test_percepcion_consume_el_contrato_canonico_del_media_plane(tmp_path):
    consolidated_dir = _build_images_experiment(tmp_path)
    _write_json(
        consolidated_dir / "media" / "eval_perception.json",
        {
            "type": "perception",
            "run_id": "media-run-2",
            "benchmark": "construction_site_safety_bench",
            "iou_threshold": 0.5,
            "mAP50": 0.7,
            "per_class": [
                {"class_name": "person", "AP50": 0.8, "n_gt": 10, "n_det": 11},
                {"class_name": "helmet", "AP50": 0.6, "n_gt": 5, "n_det": 6},
            ],
            "cr01_detection_recall": 0.75,
            "evaluated_at": "2026-08-13T00:00:00Z",
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    assert resultados_by_name["mAP"]["value"] == 0.7
    assert resultados_by_name["AP person"]["value"] == 0.8
    assert resultados_by_name["AP helmet"]["value"] == 0.6
    assert resultados_by_name["recall CR-01"]["value"] == 0.75
    for name in ("mAP", "AP person", "AP helmet", "recall CR-01"):
        assert resultados_by_name[name]["status"] == "computed"


def test_percepcion_antigua_sin_agregado_no_declara_map_computado_nulo(tmp_path):
    consolidated_dir = _build_images_experiment(tmp_path)
    _write_json(
        consolidated_dir / "media" / "eval_perception.json",
        {
            "type": "perception",
            "run_id": "media-run-2",
            "benchmark": "construction_site_safety_bench",
            "iou_threshold": 0.5,
            "per_class": [
                {"class_name": "person", "AP50": 0.8, "n_gt": 10, "n_det": 11},
            ],
            "cr01_detection_recall": 0.75,
            "evaluated_at": "2026-08-12T00:00:00Z",
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    assert resultados_by_name["mAP"]["status"] == "applicable_not_computed"
    assert resultados_by_name["mAP"]["value"] is None
    assert resultados_by_name["mAP"]["cause"] == "evaluation_without_perception_fields"
    assert resultados_by_name["AP person"]["value"] == 0.8
    assert resultados_by_name["recall CR-01"]["value"] == 0.75


def _write_temporal_eval_v2(consolidated_dir, **overrides):
    """Evaluacion temporal v2 con los campos A2/A3 (doc 57): FAR/hora + censura."""
    data = {
        "schema_version": "control.eval.temporal.v1",
        "scenario_id": "clip_0007",
        "recall": 1.0,
        "precision": 0.5,
        "f1": 0.66,
        "unexpected_alerts_count": 1,
        # Campos NATIVOS de _evaluate_v2 (deuda docs 51/58, doc 75 SS1.6):
        # far_per_hour = unexpected / (observed_duration_ms / 3.6e6);
        # observed_duration_ms se propaga ademas del cociente porque la
        # agregacion entre clips soak es Sigma FP / Sigma duracion.
        "observed_duration_ms": 600000.0,
        "far_per_hour": 6.0,
        "censored_episodes_count": 1,
        "censored_episodes": [
            {
                "episode_id": "e2",
                "condition_id": "CR-01",
                "cause": "clip_too_short_for_t_alert_window",
                "duration_ms": 12000.0,
                "required_ms": 23000.0,
            }
        ],
    }
    data.update(overrides)
    _write_json(consolidated_dir / "control" / "temporal_evaluation.json", data)
    return data


def test_far_y_censura_computed_desde_temporal_evaluation_v2(tmp_path):
    """far_per_hour / observed_duration_ms / censored_episodes salen de los
    campos v2 NATIVOS de evaluate-alerts (item 6 de doc 75 SS1): passthrough,
    sin recalcular (ADR-006)."""
    consolidated_dir = _build_video_experiment(tmp_path)
    eval_data = _write_temporal_eval_v2(consolidated_dir)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    far = resultados_by_name["far_per_hour"]
    assert far["status"] == "computed"
    assert far["value"] == 6.0
    assert far["unit"] == "alerts/hour"

    duration = resultados_by_name["observed_duration_ms"]
    assert duration["status"] == "computed"
    assert duration["value"] == 600000.0
    assert duration["unit"] == "ms"

    censored = resultados_by_name["censored_episodes"]
    assert censored["status"] == "computed"
    assert censored["value"] == 1.0
    assert censored["unit"] == "count"

    # Detalle de censurados (A2): verbatim de la evaluacion, para auditar el
    # margen faltante (duration_ms vs required_ms) sin abrir el JSON crudo.
    assert report["censored_episodes"] == eval_data["censored_episodes"]


def test_far_per_hour_cero_y_censura_cero_son_computed(tmp_path):
    """0.0 FP/hora (clip soak negativo limpio, Fase P) y 0 censurados son
    valores REALES, no ausencia: computed, no applicable_not_computed."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_temporal_eval_v2(
        consolidated_dir,
        unexpected_alerts_count=0,
        far_per_hour=0.0,
        censored_episodes_count=0,
        censored_episodes=[],
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    assert resultados_by_name["far_per_hour"]["status"] == "computed"
    assert resultados_by_name["far_per_hour"]["value"] == 0.0
    assert resultados_by_name["censored_episodes"]["status"] == "computed"
    assert resultados_by_name["censored_episodes"]["value"] == 0.0
    assert report["censored_episodes"] == []


def test_far_y_censura_figuran_not_applicable_sin_ground_truth(tmp_path):
    """Sin evaluacion temporal, las metricas nuevas figuran igual (ADR-006:
    'figuran, no se omiten') como not_applicable/no_ground_truth."""
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    for name in ("far_per_hour", "observed_duration_ms", "censored_episodes"):
        assert name in resultados_by_name, f"{name} debe figurar en resultados"
        assert resultados_by_name[name]["status"] == "not_applicable"
        assert resultados_by_name[name]["cause"] == "no_ground_truth"
        assert resultados_by_name[name]["value"] is None
    assert report["censored_episodes"] == []


def test_far_y_censura_evaluacion_vieja_sin_campos_no_inventa_valores(tmp_path):
    """Evaluacion persistida por una version vieja de evaluate-alerts (o path
    v1, sin ms): los campos no estan -> applicable_not_computed con causa
    explicita, jamas un valor inventado (ADR-006)."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "clip_0007",
            "recall": 0.75,
            "precision": 0.9,
            "f1": 0.81,
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    for name in ("far_per_hour", "observed_duration_ms", "censored_episodes"):
        assert resultados_by_name[name]["status"] == "applicable_not_computed"
        assert resultados_by_name[name]["value"] is None
        assert resultados_by_name[name]["cause"] == "evaluation_without_v2_fields"
    assert report["censored_episodes"] == []


def test_far_y_censura_evaluacion_v1_real_no_confunde_defaults_con_ceros(tmp_path):
    """Evaluacion v1 REAL de hoy (H1): el control-plane serializa con
    `model_dump_json` SIN excludes, asi que el path `_evaluate_v1` emite los
    DEFAULTS de Pydantic: `censored_episodes_count: 0` y `censored_episodes: []`
    PRESENTES junto a `far_per_hour: null` / `observed_duration_ms: null`.
    Ese 0 no es un 0 medido (la censura A2 se define contra `duration_ms`, que
    el GT v1 por frames no tiene): las TRES metricas deben salir coherentes
    como applicable_not_computed/evaluation_without_v2_fields, jamas un
    `computed = 0` que conflada "no se evaluo censura" con "se evaluo y no
    hubo" (docstring del modulo: path v1 -> applicable_not_computed).

    Shape verificado ejecutando `evaluate_temporal_alerts` contra un GT v1
    (frame-based) sin --detections: notese `ttfd_sdr_applicability =
    not_applicable:no_detections_provided` (NO `non_v2_ground_truth`, que solo
    aparece si se pasaron detecciones) — por eso el discriminador es
    `observed_duration_ms`, no ese campo."""
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_json(
        consolidated_dir / "control" / "temporal_evaluation.json",
        {
            "schema_version": "control.eval.temporal.v1",
            "scenario_id": "esc_v1",
            "alerts_path": "runs/control-run-1/alerts.jsonl",
            "ground_truth_path": "gt/esc_v1.json",
            "expected_alerts_count": 1,
            "observed_alerts_count": 0,
            "matched_alerts_count": 0,
            "missed_alerts_count": 1,
            "unexpected_alerts_count": 0,
            "duplicate_alerts_count": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "avg_latency_frames_from_first_evidence": None,
            "avg_latency_ms_from_first_evidence": None,
            "re_alerts_count": 0,
            "sub_threshold_count": 0,
            "censored_episodes_count": 0,
            "observed_duration_ms": None,
            "far_per_hour": None,
            "applicability_state": "computed",
            "applicability_cause": None,
            "avg_latency_ms_from_episode_start": None,
            "effective_matching_windows": {},
            "warnings": [],
            "matches": [],
            "missed_alerts": [
                {
                    "expected_id": "e1",
                    "condition_id": "CR-01",
                    "subject_key": None,
                    "source_id": "cam0",
                    "expected_alert_frame_index": 20,
                    "max_alert_frame_index": None,
                }
            ],
            "unexpected_alerts": [],
            "censored_episodes": [],
            "avg_ttfd_ms": None,
            "avg_sdr": None,
            "ttfd_by_episode": [],
            "sdr_by_episode": [],
            "ttfd_sdr_applicability": "not_applicable:no_detections_provided",
            "positive_criterion": None,
            "detections_path": None,
        },
    )

    report = generate_report(consolidated_dir)
    resultados_by_name = {m["name"]: m for m in report["resultados"]}

    for name in ("far_per_hour", "observed_duration_ms", "censored_episodes"):
        assert resultados_by_name[name]["status"] == "applicable_not_computed", (
            f"{name}: una evaluacion v1 no computa campos v2 (estado coherente entre las tres)"
        )
        assert resultados_by_name[name]["cause"] == "evaluation_without_v2_fields"
        assert resultados_by_name[name]["value"] is None
    assert report["censored_episodes"] == []


def test_render_markdown_muestra_far_y_detalle_de_censurados(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    _write_temporal_eval_v2(consolidated_dir)

    report = generate_report(consolidated_dir)
    markdown = render_markdown(report)

    # Las tres metricas nuevas aparecen en la tabla de Resultados.
    for name in ("far_per_hour", "observed_duration_ms", "censored_episodes"):
        assert name in markdown
    # Y el detalle de censurados tiene su seccion propia, auditable.
    assert "Episodios censurados" in markdown
    assert "e2" in markdown
    assert "clip_too_short_for_t_alert_window" in markdown


def test_render_markdown_sin_censurados_omite_la_seccion_de_detalle(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)
    markdown = render_markdown(report)

    # Sin detalle no hay seccion (la METRICA censored_episodes figura igual
    # en Resultados, con su estado ADR-006).
    assert "Episodios censurados" not in markdown
    assert "censored_episodes" in markdown


def test_render_markdown_tolera_report_viejo_sin_clave_censored(tmp_path):
    """Un report.json persistido antes de este cableado no tiene la clave
    `censored_episodes`: re-renderizarlo no debe explotar."""
    consolidated_dir = _build_video_experiment(tmp_path)
    report = generate_report(consolidated_dir)
    report.pop("censored_episodes", None)

    markdown = render_markdown(report)

    assert markdown.strip() != ""
    assert "Episodios censurados" not in markdown


def test_identificacion_liga_clip_id_y_ground_truth_path(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)
    manifest_path = consolidated_dir / "manifest.effective.yaml"
    manifest_effective = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest_effective["clip_id"] = "clip_0007"
    manifest_effective["ground_truth"] = "gt/clip_0007.gt.json"
    _write_yaml(manifest_path, manifest_effective)

    report = generate_report(consolidated_dir)

    assert report["identificacion"]["clip_id"] == "clip_0007"
    assert report["identificacion"]["ground_truth_path"] == "gt/clip_0007.gt.json"


def test_identificacion_clip_id_none_sin_video_gt_lab(tmp_path):
    consolidated_dir = _build_video_experiment(tmp_path)

    report = generate_report(consolidated_dir)

    assert report["identificacion"]["clip_id"] is None
    assert report["identificacion"]["ground_truth_path"] is None


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
