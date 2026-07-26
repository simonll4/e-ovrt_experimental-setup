"""
Lógica de generación de ventanas de recorte desde marcas del operador.

Convierte dos marcas (evento y fin) en una ventana de recorte con validación
y advertencias del guion de rodaje.
"""

from dataclasses import dataclass


class InvalidMarks(ValueError):
    """Excepción de validación: marcas inválidas o fuera del master."""

    pass


# Constantes del guion de rodaje (segundos)
PRE_ROLL_S = 3.5

# Cola por escenario (segundos). Default 3,0; los que necesitan cola larga
# están acá (doc operacion/72 §4.2 P2, §4.4 P4).
SCENARIO_TAIL_S: dict[str, float] = {
    "P2": 5.0,
    "P4": 10.0,
}
DEFAULT_TAIL_S = 3.0

# Condición de cada escenario de 1 episodio, o None si no hay episodio
# (P3 = transitorio sub-umbral, P5 = negativo). Usado para calcular el piso
# de censura (doc operacion/72 §1).
SCENARIO_CONDITION: dict[str, str | None] = {
    "P1": "CR-01",
    "P2": "CR-02",
    "P3": None,
    "P4": "CR-01",
    "P5": None,
    "P7": "CR-01",
    "P9": "CR-01",
}

# Espejo de DIMENSIONING_MS en
# e-ovrt_datasets/datasets/scripts/videogt/derive_clip_gt.py (verificado
# 2026-07-26). Si esos valores cambian ahí, tienen que cambiar acá — no hay
# import cross-repo posible entre los dos servicios en runtime.
DIMENSIONING_MS = {
    "CR-01": {"t_alert_upper_ms": 10000, "resolve_ms": 2000},
    "CR-02": {"t_alert_upper_ms": 20000, "resolve_ms": 3000},
}
DIMENSIONING_TAIL_S = 2.0

# Duraciones objetivo por escenario (segundos), o None si no está cuantificado
SCENARIO_TARGET_S = {
    "P1": 20.0,
    "P2": 30.0,
    "P3": 15.0,
    "P5": 15.0,
    "P9": 18.0,
}


@dataclass(frozen=True)
class EpisodeDraft:
    """Un episodio (onset, fin, condición) dentro del clip recortado."""

    onset_ms: int
    end_ms: int
    condition: str | None


@dataclass(frozen=True)
class TrimWindow:
    """Resultado de la computación de ventana de recorte.

    Attributes:
        ss: inicio del corte en el master (segundos)
        duration: duración del recorte (lo que se pasa como --to a prepare_clip.sh)
        episodes: episodios dentro del clip (1 para compute_window, 2 para
            compute_window_multi)
        warnings: lista de advertencias del guion de rodaje
    """

    ss: float
    duration: float
    episodes: list[EpisodeDraft]
    warnings: list[str]


def piso_s(scenario: str) -> float | None:
    """Piso A1 (segundos de duración mínima) para un escenario de 1 episodio.

    None si el escenario no tiene episodio (P3, P5) — no hay piso que censurar.
    Asume onset_rel == PRE_ROLL_S, válido para los 7 escenarios de 1 episodio
    (ss siempre se calcula como marca_evento - PRE_ROLL_S, salvo pre-roll
    degradado, que ya de por sí hace el clip más corto que el piso nominal).
    """
    condition = SCENARIO_CONDITION.get(scenario)
    if condition is None:
        return None
    dim = DIMENSIONING_MS[condition]
    return (
        PRE_ROLL_S
        + dim["t_alert_upper_ms"] / 1000
        + dim["resolve_ms"] / 1000
        + DIMENSIONING_TAIL_S
    )


def compute_window(
    t_event: float, t_end: float, master_duration: float, scenario: str
) -> TrimWindow:
    """Convierte marcas del operador en ventana de recorte.

    Recibe dos marcas en segundos sobre el master y retorna la ventana de recorte
    con pre-roll, cola y advertencias según el guion de rodaje.

    Args:
        t_event: instante del evento en el master (segundos)
        t_end: instante del fin en el master (segundos)
        master_duration: duración total del master (segundos)
        scenario: identificador del escenario (ej: "P1", "P2", ...)

    Returns:
        TrimWindow con ss, duration, episodes, warnings

    Raises:
        InvalidMarks: si fin <= evento, o marcas fuera del master
    """

    # Validación: fin tiene que ser posterior al evento
    if t_end <= t_event:
        raise InvalidMarks(
            f"el fin ({t_end:.1f} s) tiene que ser posterior al evento ({t_event:.1f} s)"
        )

    # Validación: ambas marcas dentro del master
    if t_event < 0 or t_end > master_duration:
        raise InvalidMarks(
            f"marcas fuera del master (evento={t_event:.1f} s, fin={t_end:.1f} s, "
            f"master de {master_duration:.1f} s)"
        )

    warnings: list[str] = []

    # Cálculo del inicio: evento menos pre-roll
    start = t_event - PRE_ROLL_S
    if start < 0:
        # No se puede retroceder más: el corte arranca en 0 y el onset queda
        # en t_evento (<3500 ms). Esa asimetría es la señal de TTFD degradado.
        warnings.append(
            f"solo {t_event:.1f} s de pre-roll, se necesitan {PRE_ROLL_S} — "
            "el TTFD va a salir degradado"
        )
        start = 0.0

    # Cálculo del fin: end más cola (por escenario, default 3,0 s)
    tail = SCENARIO_TAIL_S.get(scenario, DEFAULT_TAIL_S)
    end_clip = t_end + tail
    if end_clip > master_duration:
        cola = max(master_duration - t_end, 0.0)
        warnings.append(f"solo {cola:.1f} s de cola, se necesitan {tail:g}")
        end_clip = master_duration

    # Duración total del clip
    duration = end_clip - start

    # Validación de duración según escenario
    target = SCENARIO_TARGET_S.get(scenario)
    if target is not None and duration < target:
        warnings.append(
            f"clip de {duration:.1f} s, el guion pide ~{target:g} s para este escenario"
        )

    # Piso de censura (gate A1): universal para todo escenario con condición,
    # no solo los 5 que tenían objetivo de guion cargado.
    floor = piso_s(scenario)
    if floor is not None and duration < floor:
        warnings.append(
            f"clip de {duration:.1f} s, el piso de censura pide {floor:g} s "
            f"para este episodio — por debajo, t_alert-system/recall quedan "
            f"censurados (doc 57 §6.7)"
        )

    # Retorna la ventana con redondeo a 3 decimales
    return TrimWindow(
        ss=round(start, 3),
        duration=round(duration, 3),
        episodes=[
            EpisodeDraft(
                onset_ms=round((t_event - start) * 1000),
                end_ms=round((t_end - start) * 1000),
                condition=SCENARIO_CONDITION.get(scenario),
            )
        ],
        warnings=warnings,
    )
