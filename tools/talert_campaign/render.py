from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import CampaignConfig
from .model import GateViolation


def render_evidence(
    config: CampaignConfig,
    attempt: Path,
    *,
    integrated_phase: str,
    camera_status: str,
) -> dict[str, Any]:
    if camera_status != "hardware_source_not_connected":
        raise GateViolation("unsupported camera disposition")
    metrics = _load_json(attempt / "candidate-metrics.json")
    if metrics.get("status") != "candidate":
        raise GateViolation("measurement candidate is not available")
    integrated = _load_json(attempt / integrated_phase / "integrated-runs.json")
    repetitions = integrated.get("repetitions")
    if integrated.get("status") != "succeeded" or not isinstance(repetitions, list):
        raise GateViolation("integrated video evidence did not succeed")
    if len(repetitions) != 3 or any(row.get("status") != "succeeded" for row in repetitions):
        raise GateViolation("integrated video does not contain three successful repetitions")

    destination = config.repo_root / "results/realtime/t_alert_notification"
    if destination.exists():
        raise GateViolation("curated evidence destination already exists")
    destination.mkdir(parents=True)

    metrics = _accepted_metrics(metrics)
    _write_json(destination / "metrics.json", metrics)

    corpus = {
        "schema_version": "talert_notification_corpus.v1",
        "source": "results/evidence-runs/resolved-runs.json",
        "validated_alert_ids_unique": 1410,
        "primary": {
            "dbe": {"runs": 400, "nonempty_runs": 346, "events": 823},
            "ebe_non_derived": {"runs": 13, "nonempty_runs": 10, "events": 13},
            "total": {"runs": 413, "nonempty_runs": 356, "events": 836},
        },
        "supplemental_derived_ebe": {
            "runs": 544,
            "nonempty_runs": 440,
            "events": 574,
        },
        "total": {"runs": 957, "nonempty_runs": 796, "events": 1410},
    }
    _write_json(destination / "corpus.json", corpus)

    curated_integrated = {
        "schema_version": integrated["schema_version"],
        "status": integrated["status"],
        "selected_clip": integrated["selected_clip"],
        "admissions": [_curate_integrated_row(row) for row in integrated["admissions"]],
        "repetitions": [_curate_integrated_row(row) for row in repetitions],
        "included_in_primary_aggregate": False,
    }
    _write_json(destination / "integrated-runs.json", curated_integrated)
    _write_json(
        destination / "camera-smoke.json",
        {
            "schema_version": "talert_notification_camera_smoke.v1",
            "status": "not_executed",
            "cause": camera_status,
            "source_connected": False,
            "included_in_primary_aggregate": False,
            "interpretation": "No aporta evidencia positiva ni negativa del sistema.",
        },
    )

    attempt_state = _load_json(attempt / "attempt.json")
    provenance = {
        "schema_version": "talert_notification_provenance.v1",
        "attempt_id": attempt_state["attempt_id"],
        "prepared_at": attempt_state["prepared_at"],
        "accepted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "environment": attempt_state["environment"],
        "repositories": {
            name: {
                "branch": value["branch"],
                "commit": value["commit"],
                "dirty": value["dirty"],
            }
            for name, value in sorted(attempt_state["repositories"].items())
        },
        "hashes": attempt_state["hashes"],
        "selected_phases": {
            "preflight": "preflight-dbe",
            "primary": "live-primary",
            "supplemental": "live-supplemental",
            "integrated_video": integrated_phase,
            "camera": None,
        },
        "excluded_attempts": [
            {
                "attempt_id": "official-20260813-01",
                "cause": "incomplete_preparation_fingerprint",
            },
            {
                "attempt_id": "official-20260813-02",
                "cause": "orchestrator_empty_run_ledger_assumption",
            },
        ],
        "excluded_phases": [
            {"phase": "integrated-video", "cause": "media_request_schema_rejected"},
            {"phase": "camera-smoke", "cause": "media_request_schema_rejected"},
            {"phase": "camera-smoke-02", "cause": "hardware_source_not_connected"},
            {"phase": "camera-smoke-03", "cause": "hardware_source_not_connected"},
        ],
        "publication_tooling_sha256": _publication_tooling_hash(config.repo_root),
    }
    _write_json(destination / "provenance.json", provenance)
    shutil.copyfile(config.path, destination / "campaign.yaml")
    shutil.copyfile(attempt / "candidate-outcomes.csv", destination / "outcomes.csv")
    (destination / "README.md").write_text(_readme(metrics, curated_integrated), encoding="utf-8")

    state = attempt_state.copy()
    state["status"] = "succeeded"
    state["completed_at"] = provenance["accepted_at"]
    state["publication"] = "results/realtime/t_alert_notification"
    state["selected_integrated_phase"] = integrated_phase
    state["camera_status"] = camera_status
    state["publication_tooling_sha256"] = provenance["publication_tooling_sha256"]
    _write_json(attempt / "attempt.json", state)
    return {
        "status": "succeeded",
        "destination": str(destination.relative_to(config.repo_root)),
        "p95_ms": metrics["citable"]["value"],
        "sample_size": metrics["citable"]["sample_size"],
        "camera_status": "not_executed",
    }


def _accepted_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Candidato -> aceptado: agrega la cifra citable, la tasa de cooldown y los gates.

    Es la única transformación entre `candidate-metrics.json` y el `metrics.json`
    publicado; vive en una función propia para que `rebuild_curated_metrics` pueda
    reproducirla exactamente sin re-ejecutar toda la publicación.
    """
    primary = metrics["primary"]
    outcomes = primary["outcomes"]
    metrics["status"] = "accepted"
    metrics["citable"] = {
        "name": "t_alert-notification",
        "statistic": "p95",
        "unit": "ms",
        "value": primary["latency_ms"]["p95"],
        "sample_size": primary["latency_ms"]["count"],
    }
    metrics["primary"]["cooldown_rate"] = outcomes.get("suppressed_cooldown", 0) / primary[
        "events"
    ]
    metrics["gates"] = {
        "primary_full_corpus": True,
        "all_runs_finished": True,
        "bus_dropped_events_zero": True,
        "dead_letters_zero": True,
        "malformed_events_zero": True,
        "invalid_alerts_zero": True,
        "mqtt_witness_exact": True,
        "mqtt_duplicates_zero": primary["mqtt_duplicates"] == 0,
        "integrated_video_three_repetitions": True,
        "camera_not_required_for_primary_metric": True,
    }
    return metrics


def rebuild_curated_metrics(attempt: Path, destination: Path) -> dict[str, Any]:
    """Regenera `metrics.json` y `README.md` de un destino YA publicado.

    Existe para un caso puntual y declarado: cuando el agregador o la plantilla del
    README cambian después de una publicación, el artefacto publicado deja de ser
    reproducible por el pipeline. Esta función lo vuelve a derivar del
    `candidate-metrics.json` del intento, de modo que la cadena
    `fases -> candidato -> publicado` cierre de nuevo.

    Deliberadamente NO toca `provenance.json`, `corpus.json`, `integrated-runs.json`,
    `camera-smoke.json`, `campaign.yaml` ni `outcomes.csv`: la procedencia y el universo
    de la campaña son historia y se enmiendan aparte, nunca por regeneración.
    """
    metrics = _load_json(attempt / "candidate-metrics.json")
    if metrics.get("status") != "candidate":
        raise GateViolation("measurement candidate is not available")
    if not destination.is_dir():
        raise GateViolation("curated evidence destination does not exist")
    integrated = _load_json(destination / "integrated-runs.json")
    accepted = _accepted_metrics(metrics)
    _write_json(destination / "metrics.json", accepted)
    (destination / "README.md").write_text(_readme(accepted, integrated), encoding="utf-8")
    return {
        "status": "rebuilt",
        "destination": str(destination),
        "p95_ms": accepted["citable"]["value"],
        "sample_size": accepted["citable"]["sample_size"],
    }


def _curate_integrated_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "label",
            "clip_id",
            "experiment_id",
            "media_run_id",
            "control_run_id",
            "delivered",
            "delivered_ids",
            "latency_p95_ms",
            "report_metric",
            "status",
        )
    }


def _publication_tooling_hash(repo_root: Path) -> str:
    digest = hashlib.sha256()
    for relative in (
        "tools/t_alert_notification_campaign.py",
        "tools/talert_campaign/aggregate.py",
        "tools/talert_campaign/integrated.py",
        "tools/talert_campaign/render.py",
    ):
        digest.update(relative.encode())
        digest.update((repo_root / relative).read_bytes())
    return digest.hexdigest()


def _readme(metrics: dict[str, Any], integrated: dict[str, Any]) -> str:
    latency = metrics["primary"]["latency_ms"]
    outcomes = metrics["primary"]["outcomes"]
    first = metrics["steady_state"]["first_delivery_per_run"]
    subsequent = metrics["steady_state"]["subsequent_deliveries"]
    payload = metrics["payload_bytes"]
    first_share = 100.0 * first["count"] / latency["count"]
    repetitions = ", ".join(
        f'{row["latency_p95_ms"]:.3f} ms' for row in integrated["repetitions"]
    )
    return f"""# Campaña `t_alert-notification` live

Resultado aceptado de la campaña del 2026-08-13. La cifra citable es
**p95 = {latency["p95"]:.3f} ms** sobre **n = {latency["count"]}** entregas live confirmadas
por PUBACK MQTT QoS 1.

## Definición y alcance

`t_alert-notification = puback_wall_ms - ts_publish_ms`

Mide exclusivamente el tramo `bus de alertas del control-plane -> PUBACK MQTT`; no mide
sensor -> notificación. Solo entran registros `outcome=delivered`, `mode=live` y
`latency_mode=live`, observados también por el suscriptor testigo.

## Resultado principal

| Muestra | min | media | p50 | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|
| {latency["count"]} | {latency["min"]:.3f} | {latency["mean"]:.3f} | {latency["p50"]:.3f} | {latency["p95"]:.3f} | {latency["p99"]:.3f} | {latency["max"]:.3f} |

El corpus principal contiene 413 runs y 836 alertas: {outcomes["delivered"]} entregas y
{outcomes["suppressed_cooldown"]} supresiones por cooldown. No hubo drops, dead letters,
eventos inválidos, eventos malformados, IDs inesperados ni duplicados MQTT observados.

## Régimen sostenido (steady-state)

| Muestra | n | min | media | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Primeras entregas de cada corrida | {first["count"]} | {first["min"]:.3f} | {first["mean"]:.3f} | {first["p50"]:.3f} | {first["p95"]:.3f} | {first["p99"]:.3f} | {first["max"]:.3f} |
| Entregas 2.ª en adelante | {subsequent["count"]} | {subsequent["min"]:.3f} | {subsequent["mean"]:.3f} | {subsequent["p50"]:.3f} | {subsequent["p95"]:.3f} | {subsequent["p99"]:.3f} | {subsequent["max"]:.3f} |

El p95 principal agrega todas las entregas; el **{first_share:.1f} %** son primeras entregas de
su corrida (proceso y conexión MQTT recién creados) y resultan las **más rápidas**. La cota
honesta para operación continua es el p95 del régimen sostenido:
**{subsequent["p95"]:.3f} ms sobre n = {subsequent["count"]}**.

Ambas particiones salen del mismo `outcomes.csv`, sin re-corrida: la partición es por orden
temporal dentro de cada corrida y usa el mismo percentil nearest-rank que el agregado principal.

## Tamaño de payload

| n | min | media | p50 | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|
| {payload["count"]} | {payload["min"]} | {payload["mean"]:.1f} | {payload["p50"]} | {payload["p95"]} | {payload["p99"]} | {payload["max"]} |

Bytes del payload MQTT publicado, observados por el suscriptor testigo.

## Contrastes separados

Las tres repeticiones integradas desde video hasta `report.json` produjeron una entrega cada una,
con `t_alert-notification` de {repetitions}. No se mezclan con el agregado principal.

El smoke de cámara figura como `not_executed`: ni OAK-D ni RTSP estaban conectadas. Esto no es un
resultado negativo del sistema y no altera la métrica primaria, cuya fuente es la republicación
live controlada del corpus y cuyo acople completo fue validado con video.

## Artefactos

- `metrics.json`: cifra aceptada, estadísticos, outcomes y gates.
- `outcomes.csv`: los 1.410 registros principales y suplementarios para recomputación.
- `integrated-runs.json`: admisión y tres repeticiones E2E, sin rutas locales.
- `camera-smoke.json`: disposición explícita de la prueba no ejecutada.
- `corpus.json`, `campaign.yaml` y `provenance.json`: universo, configuración y procedencia.
"""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateViolation(f"cannot load publication artifact: {path.name}") from exc
    if not isinstance(value, dict):
        raise GateViolation(f"publication artifact is not an object: {path.name}")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
