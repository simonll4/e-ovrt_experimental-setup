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
TAIL_S = 3.0

# Duraciones objetivo por escenario (segundos), o None si no está cuantificado
SCENARIO_TARGET_S = {
    "P1": 20.0,
    "P2": 30.0,
    "P3": 15.0,
    "P5": 15.0,
    "P9": 18.0,
}


@dataclass(frozen=True)
class TrimWindow:
    """Resultado de la computación de ventana de recorte.

    Attributes:
        ss: inicio del corte en el master (segundos)
        duration: duración del recorte (lo que se pasa como --to a prepare_clip.sh)
        onset_ms: evento relativo al clip (milisegundos)
        end_ms: fin relativo al clip (milisegundos)
        warnings: lista de advertencias del guion de rodaje
    """

    ss: float
    duration: float
    onset_ms: int
    end_ms: int
    warnings: list[str]


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
        TrimWindow con ss, duration, onset_ms, end_ms, warnings

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

    # Cálculo del fin: end más tail
    end_clip = t_end + TAIL_S
    if end_clip > master_duration:
        cola = max(master_duration - t_end, 0.0)
        warnings.append(f"solo {cola:.1f} s de cola, se necesitan {TAIL_S:g}")
        end_clip = master_duration

    # Duración total del clip
    duration = end_clip - start

    # Validación de duración según escenario
    target = SCENARIO_TARGET_S.get(scenario)
    if target is not None and duration < target:
        warnings.append(
            f"clip de {duration:.1f} s, el guion pide ~{target:g} s para este escenario"
        )

    # Retorna la ventana con redondeo a 3 decimales
    return TrimWindow(
        ss=round(start, 3),
        duration=round(duration, 3),
        onset_ms=round((t_event - start) * 1000),
        end_ms=round((t_end - start) * 1000),
        warnings=warnings,
    )
