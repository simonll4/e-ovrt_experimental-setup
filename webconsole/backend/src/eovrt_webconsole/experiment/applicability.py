"""Modelo de aplicabilidad (ADR-006) + join t_capture->alert (spec 40 SS5.2.4).

El reporte del experimento NO recalcula metricas (ADR-006): agrega lo persistido
por cada plano. La UNICA excepcion es este join: por cada alerta, unir su
`first_evidence_unit_id` con la fila de metricas del media-plane que tiene ese
`unit_id`, para obtener `t_capture_to_alert_ms` y el `t_compute_budget_ms`
derivado (extension propia del experimental-setup sobre el join del
control-plane; ver `e-ovrt_control-plane/src/eovrt_control/metrics/latency.py`
como referencia de disenio, reimplementado aca sin importar el paquete).
"""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, model_validator

ApplicabilityStatus = Literal[
    "computed",
    "applicable_not_computed",
    "not_applicable",
    "not_interpretable",
]

# Enum exacto de estados de aplicabilidad (ADR-006). Derivado del Literal de
# arriba para que ambos no puedan desincronizarse.
APPLICABILITY_STATES: tuple[str, ...] = get_args(ApplicabilityStatus)


class MetricResult(BaseModel):
    """Resultado de una metrica del diccionario spec 40 SS5.1, con su estado
    de aplicabilidad y causa (cuando no esta `computed`)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: float | None = None
    unit: str | None = None
    status: ApplicabilityStatus
    cause: str | None = None

    # Criterio de aceptación de la métrica, cuando el manifiesto lo declara.
    #
    # Sin esto, el reporte decía cuánto midió pero no contra qué: la consola
    # mostraba "4,2 falsos positivos por hora" sin poder decir si eso pasa o no
    # pasa, que es lo único que se le pregunta a un experimento. El prototipo lo
    # muestra en su propia columna, al lado del valor medido.
    #
    # `threshold_direction` dice de qué lado está el aprobado: `max` es "no debe
    # superar" (falsos positivos, latencia) y `min` es "debe alcanzar"
    # (exhaustividad, precisión). Sin esa dirección el número solo no alcanza
    # para decidir.
    threshold: float | None = None
    threshold_direction: Literal["max", "min"] | None = None
    # None cuando no hay umbral declarado o la métrica no se pudo medir: no es
    # lo mismo que "no cumple".
    passed: bool | None = None

    @model_validator(mode="after")
    def _evaluar_umbral(self) -> "MetricResult":
        """Deriva `passed` del valor y el umbral.

        Se calcula acá y no en cada sitio que arma un MetricResult para que la
        comparación exista una sola vez: repartida, es cuestión de tiempo que
        alguien invierta el signo en uno de los quince lugares.
        """
        if self.passed is not None:
            return self
        if self.value is None or self.threshold is None or self.status != "computed":
            return self
        cumple = (
            self.value <= self.threshold
            if self.threshold_direction == "max"
            else self.value >= self.threshold
            if self.threshold_direction == "min"
            else None
        )
        if cumple is not None:
            object.__setattr__(self, "passed", cumple)
        return self


def _get(alert: dict, key: str):
    """Lee una clave de la alerta (dict); ausente -> None."""
    return alert.get(key)


def join_capture_to_alert(
    alerts: list[dict],
    media_metrics_by_unit: dict[str, dict],
    *,
    source_clock: str,
    two_node: bool = False,
) -> list[dict]:
    """Une cada alerta con la captura del media-plane (por `first_evidence_unit_id`)
    y declara el estado de aplicabilidad de `t_capture_to_alert` (ADR-006).

    Precedencia (spec 40 SS5.2.4 / Global Constraints del plan A2):
    1. `source_clock == "none"` (fuente no temporal, ej. imagenes) ->
       `not_applicable/non_temporal_source`. `t_compute_budget_ms` sigue
       siendo `computed` si los insumos monotonicos estan disponibles.
    2. `source_clock == "media"` (reloj del video, DBE) ->
       `not_interpretable/dbe_media_time`. Idem: `t_compute_budget_ms`
       sigue `computed` desde los monotonicos si estan.
    3. `two_node` (dos hosts sin sync de reloj) ->
       `not_interpretable/clock_skew`. Aca el skew invalida tambien el
       valor crudo (viene de dos hosts distintos): `t_compute_budget_ms`
       no se computa.
    4. Resto (`wallclock` single-host): si falta la unidad en
       `media_metrics_by_unit` o `alert_registered_ms` es None ->
       `applicable_not_computed/missing_join_key`. Si no, `computed` con
       `t_capture_to_alert_ms = alert_registered_ms - capture_monotonic_ns/1e6`.

    `t_compute_budget_ms = t_capture_to_alert_ms(crudo) - T_persistencia_efectiva`
    cuando ambos son derivables, donde `T_persistencia_efectiva =
    confirmed_at_ms - first_evidence_ms` (si esos dos campos estan en la
    alerta). El "crudo" se calcula siempre que capture_monotonic_ns y
    alert_registered_ms esten disponibles, independientemente de si el
    valor reportado de `t_capture_to_alert_ms` es None por no aplicar/no
    ser interpretable.
    """
    results: list[dict] = []
    for alert in alerts:
        alert_id = _get(alert, "alert_id")
        unit_id = _get(alert, "first_evidence_unit_id")
        registered = _get(alert, "alert_registered_ms")
        first_evidence_ms = _get(alert, "first_evidence_ms")
        confirmed_at_ms = _get(alert, "confirmed_at_ms")

        media_row = media_metrics_by_unit.get(unit_id) if unit_id is not None else None
        capture_ns = media_row.get("capture_monotonic_ns") if media_row else None

        # Valor crudo del join (independiente del estado de aplicabilidad
        # reportado): se usa para derivar t_compute_budget cuando aplica.
        raw_t_capture_to_alert_ms = None
        if capture_ns is not None and registered is not None:
            raw_t_capture_to_alert_ms = registered - (capture_ns / 1e6)

        t_persistencia_efectiva = None
        if confirmed_at_ms is not None and first_evidence_ms is not None:
            t_persistencia_efectiva = confirmed_at_ms - first_evidence_ms

        raw_t_compute_budget_ms = None
        if raw_t_capture_to_alert_ms is not None and t_persistencia_efectiva is not None:
            raw_t_compute_budget_ms = raw_t_capture_to_alert_ms - t_persistencia_efectiva

        if source_clock == "none":
            status, cause = "not_applicable", "non_temporal_source"
            t_capture_to_alert_ms = None
            t_compute_budget_ms = raw_t_compute_budget_ms
        elif source_clock == "media":
            status, cause = "not_interpretable", "dbe_media_time"
            t_capture_to_alert_ms = None
            t_compute_budget_ms = raw_t_compute_budget_ms
        elif two_node:
            status, cause = "not_interpretable", "clock_skew"
            t_capture_to_alert_ms = None
            t_compute_budget_ms = None
        else:
            # wallclock single-host
            if capture_ns is None or registered is None:
                status, cause = "applicable_not_computed", "missing_join_key"
                t_capture_to_alert_ms = None
                t_compute_budget_ms = None
            else:
                status, cause = "computed", None
                t_capture_to_alert_ms = raw_t_capture_to_alert_ms
                t_compute_budget_ms = raw_t_compute_budget_ms

        results.append(
            {
                "alert_id": alert_id,
                "first_evidence_unit_id": unit_id,
                "status": status,
                "cause": cause,
                "t_capture_to_alert_ms": t_capture_to_alert_ms,
                "t_compute_budget_ms": t_compute_budget_ms,
            }
        )
    return results
