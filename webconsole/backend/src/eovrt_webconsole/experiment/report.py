"""Generador del reporte consolidado (spec 40 SS6, spec 44 SS4 Tarea 3).

Agrega lo que ambos planos ya persistieron en el dir consolidado (ADR-014,
`consolidation.py`): NO recalcula metricas (ADR-006). La UNICA excepcion es el
join `t_capture->alert` (spec 40 SS5.2.4), que se recomputa aca invocando
`applicability.join_capture_to_alert`.

El diccionario de metricas de spec 40 SS5.1 se enumera SIEMPRE en
`resultados`: cada entrada figura con su `status` + `cause` de aplicabilidad
(ADR-006), aunque el insumo no este disponible ("figuran, no se omiten").

Nota sobre el borde `two_node` + `source_clock: none` (Tarea 1): no se trata
de forma especial aca -- `join_capture_to_alert` ya resuelve la precedencia
(`none` gana sobre `two_node`) y este modulo solo pasa el flag que lee de
`run_descriptor.topology` (heuristica minima, ver `_is_two_node`).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import fmean

import yaml

from eovrt_webconsole.experiment.applicability import MetricResult, join_capture_to_alert

# Vocabulario cerrado de causas que este modulo asigna por decision propia
# (las metricas del tramo plataforma sin GT, la excepcion del join, y las
# metricas sin trayecto de distribucion instrumentado). Los bloques que se
# copian tal cual de los summaries (p.ej. `g2a.causes`) conservan SU causa
# verbatim, que puede no pertenecer a este vocabulario.
NO_GROUND_TRUTH = "no_ground_truth"
DBE_MEDIA_TIME = "dbe_media_time"
CLOCK_SKEW = "clock_skew"
NON_TEMPORAL_SOURCE = "non_temporal_source"
MISSING_JOIN_KEY = "missing_join_key"
NO_DISTRIBUTION = "no_distribution"
# La distribucion corrio pero nada se entrego (todo suprimido/duplicado): no es
# lo mismo que no_distribution (el modulo si corrio, spec 45 / ADR-016).
NO_NOTIFICATIONS_DELIVERED = "no_notifications_delivered"
# Unica latencia disponible es wall-clock de un reproceso DBE, no la latencia
# operativa real (92b SS8, mismo tratamiento que DBE_MEDIA_TIME para
# t_capture->alert): nunca se reporta como si fuera la metrica real.
DISTRIBUTION_WALL_CLOCK_DBE_ONLY = "distribution_wall_clock_dbe_only"
# La latencia operativa exige un camino de broker real: modo "live".
DISTRIBUTION_CHANNEL_DRY_RUN = (
    "canal en dry_run: la latencia no atraviesa un broker MQTT real; "
    "la metrica operativa exige channel.mode=live (92b SS8)"
)
# Evaluacion temporal presente pero SIN los campos v2 A2/A3 (FAR/censura):
# JSON persistido por una version vieja de evaluate-alerts, o path v1 (el GT
# por frame no tiene ms). No se inventa un valor: applicable_not_computed.
EVAL_WITHOUT_V2_FIELDS = "evaluation_without_v2_fields"
EVAL_WITHOUT_TEMPORAL_FIELDS = "evaluation_without_temporal_fields"
EVAL_WITHOUT_PERCEPTION_FIELDS = "evaluation_without_perception_fields"
NO_MATCHED_ALERTS = "no_matched_alerts"


# ---------------------------------------------------------------------------
# Lectura tolerante de artefactos (agregar, no recalcular: si falta, {} / []).
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _find_effective_config(plane_dir: Path) -> dict | None:
    """Carga effective_config.yaml o .json de un plano, lo que exista."""
    for name in ("effective_config.yaml", "effective_config.json"):
        path = plane_dir / name
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return None


def _hash_dict(data: dict) -> str:
    """Hash determinista de un dict, independiente del orden de claves."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# t_capture->alert / t_compute-budget: la unica excepcion a "no recalcular".
# ---------------------------------------------------------------------------


def _is_two_node(media_summary: dict) -> bool:
    """Heuristica minima (ver docstring del modulo): topologia declarada por
    el media-plane en `run_descriptor.topology`. Sin sobre-ingenieria: si el
    campo no esta, se asume single-host (False)."""
    descriptor = media_summary.get("run_descriptor") or {}
    return descriptor.get("topology") == "two_node"


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _aggregate_t_capture_to_alert(
    join_results: list[dict], *, source_clock: str, two_node: bool
) -> MetricResult:
    if not join_results:
        if source_clock == "none":
            return MetricResult(
                name="t_capture->alert", unit="ms",
                status="not_applicable", cause=NON_TEMPORAL_SOURCE,
            )
        if source_clock == "media":
            return MetricResult(
                name="t_capture->alert", unit="ms",
                status="not_interpretable", cause=DBE_MEDIA_TIME,
            )
        if two_node:
            return MetricResult(
                name="t_capture->alert", unit="ms",
                status="not_interpretable", cause=CLOCK_SKEW,
            )
        return MetricResult(
            name="t_capture->alert", unit="ms",
            status="applicable_not_computed", cause=MISSING_JOIN_KEY,
        )

    statuses = {row["status"] for row in join_results}
    if statuses == {"computed"}:
        values = [row["t_capture_to_alert_ms"] for row in join_results
                  if row["t_capture_to_alert_ms"] is not None]
        return MetricResult(
            name="t_capture->alert", value=_mean(values), unit="ms",
            status="computed", cause=None,
        )
    if "not_applicable" in statuses:
        return MetricResult(
            name="t_capture->alert", unit="ms",
            status="not_applicable", cause=NON_TEMPORAL_SOURCE,
        )
    if "not_interpretable" in statuses:
        cause = CLOCK_SKEW if two_node else DBE_MEDIA_TIME
        return MetricResult(
            name="t_capture->alert", unit="ms",
            status="not_interpretable", cause=cause,
        )
    return MetricResult(
        name="t_capture->alert", unit="ms",
        status="applicable_not_computed", cause=MISSING_JOIN_KEY,
    )


def _aggregate_t_compute_budget(join_results: list[dict]) -> MetricResult:
    # t_compute-budget es monotonico e independiente de la fuente (spec 40
    # SS5.2.1): se computa siempre que haya al menos un valor derivable, sin
    # importar el estado de t_capture->alert.
    values = [row["t_compute_budget_ms"] for row in join_results
              if row.get("t_compute_budget_ms") is not None]
    if values:
        return MetricResult(
            name="t_compute-budget", value=_mean(values), unit="ms",
            status="computed", cause=None,
        )
    return MetricResult(
        name="t_compute-budget", unit="ms",
        status="applicable_not_computed", cause=MISSING_JOIN_KEY,
    )


# ---------------------------------------------------------------------------
# Resto del diccionario SS5.1: agregado directo de los summaries persistidos.
# ---------------------------------------------------------------------------


def _g2a_metric(media_summary: dict) -> MetricResult:
    g2a = media_summary.get("g2a") or {}
    state = g2a.get("state")
    if state == "computed":
        return MetricResult(name="G2A", value=g2a.get("p95_ms"), unit="ms",
                             status="computed", cause=None)
    if state:
        causes = g2a.get("causes") or []
        return MetricResult(name="G2A", unit="ms", status=state,
                             cause=causes[0] if causes else None)
    return MetricResult(name="G2A", unit="ms", status="applicable_not_computed", cause=None)


def _ttfa_interna_metric(control_summary: dict, source_clock: str) -> MetricResult:
    if source_clock == "none":
        return MetricResult(name="TTFA interna", unit="ms",
                             status="not_applicable", cause=NON_TEMPORAL_SOURCE)
    percentiles = control_summary.get("ttfa_internal_ms_percentiles")
    if percentiles:
        value = percentiles.get("p50")
        return MetricResult(name="TTFA interna", value=value, unit="ms",
                             status="computed", cause=None)
    return MetricResult(name="TTFA interna", unit="ms",
                         status="applicable_not_computed", cause=None)


def _simple_numeric_metric(name: str, value, unit: str) -> MetricResult:
    """Metrica de passthrough directo de un summary (latencias, FPS, drops)."""
    if value is None:
        return MetricResult(name=name, unit=unit, status="applicable_not_computed", cause=None)
    return MetricResult(name=name, value=float(value), unit=unit, status="computed", cause=None)


def _substage_metrics(media_summary: dict, control_summary: dict) -> list[MetricResult]:
    metrics = [
        _simple_numeric_metric("latencia_media_p50_ms", media_summary.get("p50_latency_ms"), "ms"),
        _simple_numeric_metric("latencia_media_p95_ms", media_summary.get("p95_latency_ms"), "ms"),
        _simple_numeric_metric("latencia_media_p99_ms", media_summary.get("p99_latency_ms"), "ms"),
        _simple_numeric_metric("fps_efectivo", media_summary.get("fps_effective"), "fps"),
        _simple_numeric_metric("drops_media", media_summary.get("units_dropped"), "count"),
        _simple_numeric_metric(
            "latencia_control_avg_ms", control_summary.get("avg_processing_ms"), "ms"
        ),
        _simple_numeric_metric(
            "bus_dropped_events", control_summary.get("bus_dropped_events"), "count"
        ),
    ]
    control_percentiles = control_summary.get("processing_ms_percentiles") or {}
    for pct in ("p50", "p95", "p99"):
        metrics.append(
            _simple_numeric_metric(
                f"latencia_control_{pct}_ms", control_percentiles.get(pct), "ms"
            )
        )
    return metrics


def _eval_perception(consolidated_dir: Path, media_summary: dict) -> dict | None:
    """Busca una evaluacion de percepcion con GT, si existe (extension
    forward-compatible: ninguna tarea previa la produce todavia -- spec 43,
    diferido). Se busca embebida en el summary o en un archivo dedicado."""
    embedded = media_summary.get("eval_perception")
    if embedded:
        return embedded
    path = consolidated_dir / "media" / "eval_perception.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _temporal_evaluation(consolidated_dir: Path, control_summary: dict) -> dict | None:
    """Busca la evaluacion temporal contra ground truth (spec 43 SS6), si el
    runner la corrio (`runner._run_temporal_evaluation`). Mismo patron que
    `_eval_perception`: embebida en el summary o en un archivo dedicado."""
    embedded = control_summary.get("temporal_evaluation")
    if embedded:
        return embedded
    path = consolidated_dir / "control" / "temporal_evaluation.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _distribution_detail(consolidated_dir: Path) -> dict:
    """Busca `distribution_summary.json` del modulo de distribucion de alertas
    (spec 45 / ADR-016), si el runner lo corrio -- cuarto hermano de
    media/control/report en el layout de corrida (ADR-014). Passthrough
    verbatim, sin recalcular (ADR-006): {} si no existe."""
    path = consolidated_dir / "distribution" / "distribution_summary.json"
    if not path.is_file():
        return {}
    try:
        detail = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return detail if isinstance(detail, dict) else {}


def _distribution_outcomes_by_alert(consolidated_dir: Path) -> dict:
    """Último DeliveryRecord por alert_id en `distribution/notifications.jsonl`.

    Un mismo alert_id puede aparecer varias veces por reintentos; la última línea
    escrita para ese alert_id es su outcome terminal.
    """
    path = consolidated_dir / "distribution" / "notifications.jsonl"
    if not path.is_file():
        return {}

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return {}

    by_alert: dict = {}
    for line in lines:
        row = line.strip()
        if not row:
            continue
        try:
            record = json.loads(row)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        alert_id = record.get("alert_id")
        if alert_id:
            by_alert[str(alert_id)] = record
    return by_alert


def _distribution_metric(distribution_detail: dict) -> MetricResult:
    """t_alert-notification (spec 40 SS5, spec 45 SS6). El summary agrega la
    latencia por `latency_mode` (nunca mezclada, 92b SS8): si hay 'live', es la
    latencia operativa real y se reporta `computed`; el summary además declara el
    modo del canal ('mode'): dry_run nunca produce una metrica computed, aunque
    latency_mode sea 'live'. Si SOLO hay 'wall_clock_dbe', es reloj de pared de
    un reproceso, no la metrica real -- mismo criterio que `t_capture->alert`
    con reloj de medio
    (`DBE_MEDIA_TIME`): `not_interpretable`, nunca un caveat escondido detras
    de un numero."""
    if not distribution_detail:
        return MetricResult(name="t_alert-notification", unit="ms",
                             status="not_applicable", cause=NO_DISTRIBUTION)
    latency_by_mode = distribution_detail.get("talert_notification_ms")
    if not latency_by_mode:
        return MetricResult(name="t_alert-notification", unit="ms",
                             status="applicable_not_computed",
                             cause=NO_NOTIFICATIONS_DELIVERED)
    if distribution_detail.get("mode") != "live":
        return MetricResult(name="t_alert-notification", unit="ms",
                             status="applicable_not_computed", cause=DISTRIBUTION_CHANNEL_DRY_RUN)
    live = latency_by_mode.get("live")
    if live is not None:
        return MetricResult(name="t_alert-notification", value=live["p95"],
                             unit="ms", status="computed", cause=None)
    return MetricResult(name="t_alert-notification", unit="ms",
                         status="not_interpretable",
                         cause=DISTRIBUTION_WALL_CLOCK_DBE_ONLY)


def _sdr_metric(temporal_eval: dict | None) -> MetricResult:
    """SDR (spec 43 SS10 / spec 40 SS17.1.7): proporcion del intervalo anotado
    con deteccion sostenida. Campo nativo del control-plane: `avg_sdr`
    (evaluate-alerts con --detections). Sin el campo (evaluacion sin
    detecciones), no hay proxy honesto: recall mide otra cosa (episodios
    alertados, no cobertura de deteccion) y usarlo inflaria/deprimiria SDR
    en silencio."""
    if temporal_eval is None:
        return MetricResult(name="SDR", unit="ratio", status="not_applicable", cause=NO_GROUND_TRUTH)
    sdr = temporal_eval.get("avg_sdr")
    if sdr is None:
        cause = temporal_eval.get("ttfd_sdr_applicability")
        return MetricResult(name="SDR", unit="ratio", status="applicable_not_computed",
                            cause=cause)
    return MetricResult(name="SDR", value=float(sdr), unit="ratio", status="computed", cause=None)


def _ttfd_metric(temporal_eval: dict | None) -> MetricResult:
    """TTFD (spec 43 SS10): t0 = start_ms del episodio, t1 = primera deteccion
    positiva valida. Campo nativo del control-plane: `avg_ttfd_ms` (ms -> s;
    evaluate-alerts con --detections). Sin el campo no se estima: la latencia
    de ALERTA (avg_latency_ms_from_episode_start) es t_alert-system, otra
    metrica del diccionario -- usarla como TTFD la sobreestimaria siempre."""
    if temporal_eval is None:
        return MetricResult(name="TTFD", unit="s", status="not_applicable", cause=NO_GROUND_TRUTH)
    ttfd_ms = temporal_eval.get("avg_ttfd_ms")
    if ttfd_ms is None:
        cause = temporal_eval.get("ttfd_sdr_applicability")
        return MetricResult(name="TTFD", unit="s", status="applicable_not_computed",
                            cause=cause)
    return MetricResult(name="TTFD", value=float(ttfd_ms) / 1000.0, unit="s",
                        status="computed", cause=None)


def _t_alert_system_metric(temporal_eval: dict | None) -> MetricResult:
    """Latencia desde el inicio anotado del episodio hasta la alerta registrada.

    Es passthrough de `avg_latency_ms_from_episode_start`; el evaluador temporal
    ya hizo el matching contra GT. Un clip negativo o totalmente censurado
    conserva la no-aplicabilidad declarada por ese evaluador.
    """
    if temporal_eval is None:
        return MetricResult(
            name="t_alert-system",
            unit="s",
            status="not_applicable",
            cause=NO_GROUND_TRUTH,
        )

    if temporal_eval.get("applicability_state") == "not_applicable":
        return MetricResult(
            name="t_alert-system",
            unit="s",
            status="not_applicable",
            cause=temporal_eval.get("applicability_cause"),
        )

    latency_ms = temporal_eval.get("avg_latency_ms_from_episode_start")
    if latency_ms is not None:
        return MetricResult(
            name="t_alert-system",
            value=float(latency_ms) / 1000.0,
            unit="s",
            status="computed",
            cause=None,
        )

    cause = (
        NO_MATCHED_ALERTS
        if temporal_eval.get("matched_alerts_count") == 0
        else EVAL_WITHOUT_TEMPORAL_FIELDS
    )
    return MetricResult(
        name="t_alert-system",
        unit="s",
        status="applicable_not_computed",
        cause=cause,
    )


def _temporal_classification_metrics(temporal_eval: dict | None) -> list[MetricResult]:
    specs = (
        ("precision_alertas", "precision"),
        ("recall_alertas", "recall"),
        ("F1_alertas", "f1"),
    )
    if temporal_eval is None:
        return [
            MetricResult(
                name=name,
                unit="ratio",
                status="not_applicable",
                cause=NO_GROUND_TRUTH,
            )
            for name, _field in specs
        ]

    if temporal_eval.get("applicability_state") == "not_applicable":
        cause = temporal_eval.get("applicability_cause")
        return [
            MetricResult(
                name=name,
                unit="ratio",
                status="not_applicable",
                cause=cause,
            )
            for name, _field in specs
        ]

    metrics: list[MetricResult] = []
    for name, field in specs:
        value = temporal_eval.get(field)
        if value is None:
            metrics.append(
                MetricResult(
                    name=name,
                    unit="ratio",
                    status="applicable_not_computed",
                    cause=EVAL_WITHOUT_TEMPORAL_FIELDS,
                )
            )
        else:
            metrics.append(
                MetricResult(
                    name=name,
                    value=float(value),
                    unit="ratio",
                    status="computed",
                    cause=None,
                )
            )
    return metrics


def _censura_evaluada(temporal_eval: dict) -> bool:
    """Discriminador del path v2 para la censura A2 (finding H1): el control-plane
    serializa con `model_dump_json` SIN excludes, asi que el path `_evaluate_v1`
    emite los DEFAULTS de Pydantic (`censored_episodes_count: 0`,
    `censored_episodes: []`) aunque JAMAS evaluo censura — ese 0 no es un 0
    medido. La senal es `observed_duration_ms`: `_evaluate_v1` nunca lo setea
    (queda null), `_evaluate_v2` lo setea en sus DOS retornos, y ademas es la
    precondicion literal de la metrica (`_episode_metric_censored` devuelve None
    si `duration_ms is None`: sin duracion observada no hay censura evaluable).

    Se descartaron dos candidatos: `ttfd_sdr_applicability ==
    "not_applicable:non_v2_ground_truth"` solo aparece si se pasaron
    detecciones — un v1 sin --detections (el caso comun del runner) emite
    `no_detections_provided`, indistinguible de un v2 sin detecciones — y
    `effective_matching_windows` queda `{}` en clips v2 negativos (sin
    episodios), justo el escenario soak/FAR donde el 0 censurados es real."""
    return temporal_eval.get("observed_duration_ms") is not None


def _temporal_eval_v2_metrics(temporal_eval: dict | None) -> list[MetricResult]:
    """FAR/hora + censura (doc 57 A2/A3; deuda docs 51/58, doc 75 SS1.6):
    passthrough de los campos v2 NATIVOS de evaluate-alerts (`far_per_hour`,
    `observed_duration_ms`, `censored_episodes_count`). `observed_duration_ms`
    se expone ademas del cociente por clip porque la agregacion entre clips
    soak es Sigma FP / Sigma duracion, NO promedio de tasas (comentario A3 del
    control-plane). Sin evaluacion -> not_applicable/no_ground_truth; con
    evaluacion pero sin los campos (JSON viejo) o por el path v1 (defaults
    serializados, ver `_censura_evaluada`) -> applicable_not_computed, jamas un
    valor inventado (ADR-006). 0.0 y 0 son valores reales (soak negativo
    limpio / sin censura), pero SOLO en el path v2: computed."""
    specs = (
        ("far_per_hour", "alerts/hour", "far_per_hour"),
        ("observed_duration_ms", "ms", "observed_duration_ms"),
        ("censored_episodes", "count", "censored_episodes_count"),
    )
    metrics: list[MetricResult] = []
    for name, unit, field in specs:
        if temporal_eval is None:
            metrics.append(MetricResult(name=name, unit=unit,
                                        status="not_applicable", cause=NO_GROUND_TRUTH))
            continue
        value = temporal_eval.get(field)
        if field == "censored_episodes_count" and not _censura_evaluada(temporal_eval):
            # El 0 default del path v1 no es un 0 medido: mismo estado que
            # far_per_hour/observed_duration_ms (coherencia entre las tres).
            value = None
        if value is None:
            metrics.append(MetricResult(name=name, unit=unit,
                                        status="applicable_not_computed",
                                        cause=EVAL_WITHOUT_V2_FIELDS))
        else:
            metrics.append(MetricResult(name=name, value=float(value), unit=unit,
                                        status="computed", cause=None))
    return metrics


def _censored_episodes_detail(temporal_eval: dict | None) -> list[dict]:
    """Detalle de episodios censurados (A2), verbatim de la evaluacion:
    episode_id/condition_id/cause + duration_ms/required_ms para auditar el
    margen faltante sin abrir el JSON crudo. [] si no hay evaluacion o campos."""
    if not temporal_eval:
        return []
    return list(temporal_eval.get("censored_episodes") or [])


def _perception_metrics(
    consolidated_dir: Path,
    media_summary: dict,
    control_summary: dict,
    source_clock: str,
    temporal_eval: dict | None,
) -> list[MetricResult]:
    eval_perception = _eval_perception(consolidated_dir, media_summary)
    metrics: list[MetricResult] = []

    if eval_perception:
        map_key = next((key for key in ("mAP50", "map") if key in eval_perception), None)
        map_value = eval_perception.get(map_key) if map_key else None
        if map_key is None:
            metrics.append(
                MetricResult(
                    name="mAP",
                    unit="ratio",
                    status="applicable_not_computed",
                    cause=EVAL_WITHOUT_PERCEPTION_FIELDS,
                )
            )
        elif map_value is None:
            metrics.append(
                MetricResult(
                    name="mAP",
                    unit="ratio",
                    status="not_applicable",
                    cause=NO_GROUND_TRUTH,
                )
            )
        else:
            metrics.append(
                MetricResult(
                    name="mAP",
                    value=float(map_value),
                    unit="ratio",
                    status="computed",
                    cause=None,
                )
            )

        class_metrics: list[MetricResult] = []
        if "per_class" in eval_perception:
            for item in eval_perception.get("per_class") or []:
                class_name = item.get("class_name")
                if not class_name:
                    continue
                ap_value = item.get("AP50")
                if ap_value is None:
                    class_metrics.append(
                        MetricResult(
                            name=f"AP {class_name}",
                            unit="ratio",
                            status="not_applicable",
                            cause=NO_GROUND_TRUTH,
                        )
                    )
                else:
                    class_metrics.append(
                        MetricResult(
                            name=f"AP {class_name}",
                            value=float(ap_value),
                            unit="ratio",
                            status="computed",
                            cause=None,
                        )
                    )
            if not class_metrics:
                class_metrics.append(
                    MetricResult(
                        name="AP por clase",
                        unit="ratio",
                        status="not_applicable",
                        cause=NO_GROUND_TRUTH,
                    )
                )
        elif "ap_by_class" in eval_perception:
            for class_name, ap_value in (eval_perception.get("ap_by_class") or {}).items():
                class_metrics.append(
                    MetricResult(
                        name=f"AP {class_name}",
                        value=float(ap_value),
                        unit="ratio",
                        status="computed",
                        cause=None,
                    )
                )
            if not class_metrics:
                class_metrics.append(
                    MetricResult(
                        name="AP por clase",
                        unit="ratio",
                        status="not_applicable",
                        cause=NO_GROUND_TRUTH,
                    )
                )
        else:
            class_metrics.append(
                MetricResult(
                    name="AP por clase",
                    unit="ratio",
                    status="applicable_not_computed",
                    cause=EVAL_WITHOUT_PERCEPTION_FIELDS,
                )
            )
        metrics.extend(class_metrics)

        recall_key = next(
            (
                key
                for key in ("cr01_detection_recall", "recall_cr01")
                if key in eval_perception
            ),
            None,
        )
        recall_value = eval_perception.get(recall_key) if recall_key else None
        if recall_key is None:
            metrics.append(
                MetricResult(
                    name="recall CR-01",
                    unit="ratio",
                    status="applicable_not_computed",
                    cause=EVAL_WITHOUT_PERCEPTION_FIELDS,
                )
            )
        elif recall_value is None:
            metrics.append(
                MetricResult(
                    name="recall CR-01",
                    unit="ratio",
                    status="not_applicable",
                    cause=NO_GROUND_TRUTH,
                )
            )
        else:
            metrics.append(
                MetricResult(
                    name="recall CR-01",
                    value=float(recall_value),
                    unit="ratio",
                    status="computed",
                    cause=None,
                )
            )
    else:
        metrics.append(MetricResult(name="mAP", unit="ratio",
                                     status="not_applicable", cause=NO_GROUND_TRUTH))
        metrics.append(MetricResult(name="AP por clase", unit="ratio",
                                     status="not_applicable", cause=NO_GROUND_TRUTH))
        metrics.append(MetricResult(name="recall CR-01", unit="ratio",
                                     status="not_applicable", cause=NO_GROUND_TRUTH))

    re_alerts = control_summary.get("re_alerts_count")
    if re_alerts is None:
        re_alerts = (temporal_eval or {}).get("re_alerts_count")
    if re_alerts is not None:
        metrics.append(MetricResult(name="re_alerts", value=float(re_alerts), unit="count",
                                     status="computed", cause=None))
    else:
        # re_alerts es metrica de patron/temporal (spec 40 SS5.2.3.3): en fuente
        # no temporal (source_clock=none) toda evaluacion de patrones es
        # non_temporal_source, no no_ground_truth (finding de revision).
        cause = NON_TEMPORAL_SOURCE if source_clock == "none" else NO_GROUND_TRUTH
        metrics.append(MetricResult(name="re_alerts", unit="count",
                                     status="not_applicable", cause=cause))

    return metrics


def _build_resultados(
    consolidated_dir: Path, media_summary: dict, control_summary: dict,
    join_results: list[dict], *, source_clock: str, two_node: bool,
    temporal_eval: dict | None, distribution_detail: dict,
) -> list[MetricResult]:
    resultados = [
        _g2a_metric(media_summary),
        _t_alert_system_metric(temporal_eval),
        _aggregate_t_capture_to_alert(join_results, source_clock=source_clock,
                                       two_node=two_node),
        _aggregate_t_compute_budget(join_results),
        _distribution_metric(distribution_detail),
        _ttfd_metric(temporal_eval),
        _sdr_metric(temporal_eval),
        *_temporal_classification_metrics(temporal_eval),
        *_temporal_eval_v2_metrics(temporal_eval),
        _ttfa_interna_metric(control_summary, source_clock),
        MetricResult(name="ΔFP_tracker", unit="count",
                     status="not_applicable", cause=None),
    ]
    resultados.extend(_substage_metrics(media_summary, control_summary))
    resultados.extend(
        _perception_metrics(
            consolidated_dir,
            media_summary,
            control_summary,
            source_clock,
            temporal_eval,
        )
    )
    return resultados


# ---------------------------------------------------------------------------
# Anti-drift: hash de la config "enviada" (congelada en el manifiesto
# efectivo, clave opcional `sent_config.<plano>`) vs la effective_config que
# cada plano persistio. Si cualquiera de las dos no esta disponible (por
# ejemplo, el cableado del runner -- Tarea 4 -- todavia no persiste
# `sent_config`), el chequeo queda "no verificable" y NO rompe el reporte.
# ---------------------------------------------------------------------------


def _anti_drift_for_plane(sent_config: dict | None, persisted_config: dict | None) -> dict:
    if sent_config is None or persisted_config is None:
        return {
            "checked": False,
            "reason": "sent_config o effective_config no disponibles en el consolidado",
        }
    hash_sent = _hash_dict(sent_config)
    hash_effective = _hash_dict(persisted_config)
    return {
        "checked": True,
        "hash_sent": hash_sent,
        "hash_effective": hash_effective,
        "drift_detected": hash_sent != hash_effective,
    }


def _build_anti_drift(manifest_effective: dict, media_dir: Path, control_dir: Path) -> dict:
    sent_config = manifest_effective.get("sent_config") or {}
    return {
        "media": _anti_drift_for_plane(sent_config.get("media"), _find_effective_config(media_dir)),
        "control": _anti_drift_for_plane(
            sent_config.get("control"), _find_effective_config(control_dir)
        ),
    }


# ---------------------------------------------------------------------------
# Secciones descriptivas (identidad, entrada, temporalidad, eventos, ...).
# ---------------------------------------------------------------------------


def _clock_criterion_text(source_clock: str | None) -> str:
    if source_clock == "wallclock":
        return "reloj de pared local (single-host); latencias intra-nodo monotonicas."
    if source_clock == "media":
        return ("reloj de medio (tiempo de video, no de pared): t_capture->alert no "
                "interpretable (dbe_media_time); t_compute-budget si es valido.")
    if source_clock == "none":
        return ("fuente no temporal (dataset de imagenes, ADR-013): no hay episodio en "
                "el tiempo; t_capture->alert no aplica (non_temporal_source).")
    return "source_clock no declarado en el summary del media-plane."


def _hitos(alerts: list[dict], pattern_events: list[dict], distribution_detail: dict) -> dict:
    return {
        "primera_evidencia": any(a.get("first_evidence_unit_id") for a in alerts),
        "patron_confirmado": bool(pattern_events),
        "alerta_registrada": any(a.get("alert_registered_ms") is not None for a in alerts),
        # Hito de spec 45 / ADR-016: refleja distribution_summary.json si el
        # runner corrio el modulo; False si no corrio (sin cambios).
        "notificacion_entregada": bool(
            (distribution_detail.get("counts") or {}).get("delivered")
        ),
    }


def _observaciones(source_clock: str, anti_drift: dict) -> list[str]:
    notas = [
        (
            "Reporte agregado (ADR-006): no recalcula metricas persistidas; la unica "
            "excepcion es el join t_capture->alert (spec 40 SS5.2.4)."
        ),
    ]
    if source_clock == "none":
        notas.append(
            "Corrida rotulada como diagnostico espacial / smoke de contrato: fuente no "
            "temporal (source_clock=none), la evaluacion de patrones es "
            "not_applicable/non_temporal_source."
        )
    for plano, entry in anti_drift.items():
        if entry.get("checked") and entry.get("drift_detected"):
            notas.append(
                f"anti-drift: la config enviada del plano '{plano}' difiere de la "
                "effective_config persistida."
            )
    return notas


def apply_thresholds(
    resultados: list[MetricResult], criterios: dict | None
) -> list[MetricResult]:
    """Adjunta a cada métrica el criterio de aceptación del manifiesto.

    Se hace en una sola pasada al final y no en cada sitio que arma un
    `MetricResult` (son quince) por dos razones: no hay que enhebrar el
    manifiesto por toda la construcción del reporte, y el umbral queda declarado
    en un solo lugar del YAML en vez de repetido.

    Forma esperada en el manifiesto, bajo `report.criterios`:

        report:
          criterios:
            far_per_hour:   {max: 2.0}
            "recall CR-01": {min: 0.85}

    Una métrica sin criterio queda con `threshold=None`, que la interfaz muestra
    como "—": declarar el umbral es opcional y su ausencia no es un fallo.
    """
    if not criterios:
        return resultados
    salida = []
    for metrica in resultados:
        criterio = criterios.get(metrica.name)
        if not isinstance(criterio, dict):
            salida.append(metrica)
            continue
        if "max" in criterio:
            umbral, direccion = criterio["max"], "max"
        elif "min" in criterio:
            umbral, direccion = criterio["min"], "min"
        else:
            salida.append(metrica)
            continue
        # Se revalida (en vez de model_copy) para que el validador vuelva a
        # correr y derive `passed`: con el umbral recién puesto, en el original
        # todavía no existía.
        salida.append(
            MetricResult.model_validate(
                {
                    **metrica.model_dump(),
                    "threshold": float(umbral),
                    "threshold_direction": direccion,
                    "passed": None,
                }
            )
        )
    return salida


def generate_report(consolidated_dir: str | Path) -> dict:
    """Arma el `report.json` (dict) de un experimento consolidado (ADR-014).

    Lee `media/summary.json`, `media/metrics.jsonl`, `control/summary.json`,
    `control/alerts.jsonl`, `control/pattern_events.jsonl` y
    `manifest.effective.yaml` del dir consolidado; no recalcula nada salvo el
    join `t_capture->alert` / `t_compute-budget` (unica excepcion, ADR-006).
    """
    consolidated_dir = Path(consolidated_dir)
    media_dir = consolidated_dir / "media"
    control_dir = consolidated_dir / "control"

    media_summary = _read_json(media_dir / "summary.json")
    media_metrics = _read_jsonl(media_dir / "metrics.jsonl")
    control_summary = _read_json(control_dir / "summary.json")
    alerts = _read_jsonl(control_dir / "alerts.jsonl")
    pattern_events = _read_jsonl(control_dir / "pattern_events.jsonl")
    manifest_effective = _read_yaml(consolidated_dir / "manifest.effective.yaml")

    source_clock = media_summary.get("source_clock") or "none"
    two_node = _is_two_node(media_summary)

    media_metrics_by_unit = {
        row["unit_id"]: row for row in media_metrics if row.get("unit_id")
    }
    join_results = join_capture_to_alert(
        alerts, media_metrics_by_unit, source_clock=source_clock, two_node=two_node
    )

    anti_drift = _build_anti_drift(manifest_effective, media_dir, control_dir)
    temporal_eval = _temporal_evaluation(consolidated_dir, control_summary)
    distribution_detail = _distribution_detail(consolidated_dir)

    experiment_id = manifest_effective.get("experiment_id") or consolidated_dir.name

    identificacion = {
        "experiment_id": experiment_id,
        "media_run_id": media_summary.get("run_id"),
        "control_run_id": control_summary.get("control_run_id"),
        "fecha_inicio": media_summary.get("started_at"),
        "fecha_fin": media_summary.get("finished_at"),
        # Trazabilidad spec 43 SS6 (experiment_id -> clip_id -> gt/*.json):
        # None cuando la corrida no declaro clip_id/ground_truth en el
        # manifiesto (comportamiento actual intacto, campo aditivo).
        "clip_id": manifest_effective.get("clip_id"),
        "ground_truth_path": manifest_effective.get("ground_truth"),
    }
    modelo = {
        "model_name": media_summary.get("model_name"),
        "prompt_set_id": media_summary.get("prompt_set_id"),
        "pattern_set_id": control_summary.get("pattern_set_id"),
        "active_pattern_ids": control_summary.get("active_pattern_ids"),
    }
    entrada = {
        "source_type": media_summary.get("source_type"),
        "source_count": media_summary.get("source_count"),
        "scenario": media_summary.get("scenario"),
    }
    parametros = {
        "frozen": manifest_effective.get("frozen", {}),
        "warmup_units": (media_summary.get("g2a") or {}).get("warmup_units"),
        "active_pattern_ids": control_summary.get("active_pattern_ids"),
    }
    hardware_entorno = {
        "device": media_summary.get("device"),
        "gpu_memory_peak_mb": media_summary.get("gpu_memory_peak_mb"),
        "topology": (media_summary.get("run_descriptor") or {}).get("topology"),
    }
    temporalidad = {
        "source_clock": source_clock,
        "two_node": two_node,
        "warmup_units": (media_summary.get("g2a") or {}).get("warmup_units"),
        "criterio_relojes": _clock_criterion_text(source_clock),
    }
    eventos = {
        "pattern_events_count": control_summary.get("pattern_events_count"),
        "alerts_count": control_summary.get("alerts_count"),
        "errors_count": control_summary.get("errors_count"),
        "units_processed_media": media_summary.get("units_processed"),
        "units_processed_control": control_summary.get("units_processed"),
        "hitos": _hitos(alerts, pattern_events, distribution_detail),
    }

    resultados = _build_resultados(
        consolidated_dir, media_summary, control_summary, join_results,
        source_clock=source_clock, two_node=two_node, temporal_eval=temporal_eval,
        distribution_detail=distribution_detail,
    )
    # Criterios de aceptación del manifiesto: sin esto el reporte dice cuánto
    # midió cada métrica pero no contra qué, que es lo que decide si el
    # experimento pasa.
    resultados = apply_thresholds(
        resultados, (manifest_effective.get("report") or {}).get("criterios")
    )

    return {
        "identificacion": identificacion,
        "modelo": modelo,
        "entrada": entrada,
        "parametros": parametros,
        "hardware_entorno": hardware_entorno,
        "temporalidad": temporalidad,
        "eventos": eventos,
        "resultados": [m.model_dump() for m in resultados],
        # Detalle A2 (aditivo): la METRICA censored_episodes figura arriba con
        # su estado ADR-006; esto es el rastro auditable por episodio.
        "censored_episodes": _censored_episodes_detail(temporal_eval),
        # Detalle aditivo (spec 45 / ADR-016): la METRICA t_alert-notification
        # figura arriba con su estado ADR-006; esto es el distribution_summary.json
        # verbatim, para auditar counts/skipped_invalid_alerts sin abrir el JSON crudo.
        "distribucion": distribution_detail,
        "distribucion_por_alerta": _distribution_outcomes_by_alert(consolidated_dir),
        "anti_drift": anti_drift,
        "observaciones": _observaciones(source_clock, anti_drift),
    }


# ---------------------------------------------------------------------------
# report.md
# ---------------------------------------------------------------------------


def _render_dict_section(title: str, data: dict) -> str:
    lines = [f"## {title}", ""]
    if not data:
        lines.append("(sin datos)")
    for key, value in data.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    return "\n".join(lines)


def _render_resultados_section(resultados: list[dict]) -> str:
    lines = ["## Resultados", "", "| Metrica | Valor | Unidad | Estado | Causa |",
              "|---|---|---|---|---|"]
    for metric in resultados:
        lines.append(
            f"| {metric['name']} | {metric['value']} | {metric['unit']} | "
            f"{metric['status']} | {metric['cause']} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_censored_section(censored: list[dict]) -> str:
    """Detalle de episodios censurados (A2). Solo se emite si hay alguno: la
    metrica `censored_episodes` figura siempre en Resultados igualmente."""
    if not censored:
        return ""
    lines = ["## Episodios censurados", "",
             "| Episodio | Condicion | Causa | duration_ms | required_ms |",
             "|---|---|---|---|---|"]
    for episode in censored:
        lines.append(
            f"| {episode.get('episode_id')} | {episode.get('condition_id')} | "
            f"{episode.get('cause')} | {episode.get('duration_ms')} | "
            f"{episode.get('required_ms')} |"
        )
    lines.append("")
    return "\n".join(lines)


def _render_anti_drift_section(anti_drift: dict) -> str:
    lines = ["## Anti-drift", ""]
    for plano, entry in anti_drift.items():
        if not entry.get("checked"):
            lines.append(f"- **{plano}**: no verificable ({entry.get('reason')})")
            continue
        estado = "DRIFT DETECTADO" if entry.get("drift_detected") else "sin diferencias"
        lines.append(f"- **{plano}**: {estado} (sent={entry['hash_sent'][:12]}..., "
                     f"effective={entry['hash_effective'][:12]}...)")
    lines.append("")
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    """Renderiza el `report.json` a un `report.md` legible por humanos.

    Mapea las mismas secciones que `generate_report` (spec 40 SS6 / Tabla D.6).
    """
    experiment_id = report["identificacion"].get("experiment_id", "?")
    parts = [
        f"# Reporte del experimento {experiment_id}",
        "",
        _render_dict_section("Identificacion", report["identificacion"]),
        _render_dict_section("Modelo", report["modelo"]),
        _render_dict_section("Entrada", report["entrada"]),
        _render_dict_section("Parametros", report["parametros"]),
        _render_dict_section("Hardware y entorno", report["hardware_entorno"]),
        _render_dict_section("Temporalidad", report["temporalidad"]),
        _render_dict_section("Eventos", report["eventos"]),
        _render_resultados_section(report["resultados"]),
    ]
    # `.get`: un report.json persistido antes de este cableado no trae la clave.
    censored_section = _render_censored_section(report.get("censored_episodes") or [])
    if censored_section:
        parts.append(censored_section)
    parts += [
        _render_anti_drift_section(report["anti_drift"]),
        "## Observaciones",
        "",
    ]
    parts.extend(f"- {nota}" for nota in report["observaciones"])
    parts.append("")
    return "\n".join(parts)


def write_report(consolidated_dir: str | Path) -> tuple[Path, Path]:
    """Genera y persiste `report/report.json` + `report/report.md`."""
    consolidated_dir = Path(consolidated_dir)
    report = generate_report(consolidated_dir)
    markdown = render_markdown(report)

    report_dir = consolidated_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "report.json"
    md_path = report_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")

    return json_path, md_path
