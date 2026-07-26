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


# Condición de cada episodio, en orden, para los escenarios de 2 episodios.
# Dato del guion (doc operacion/72 §4.6/§4.8), no derivable de las marcas.
# Definido acá arriba (y no junto a compute_window_multi) porque
# compute_window también lo necesita, para rechazar P6/P8 con solo 2 marcas.
MULTI_EPISODE_CONDITIONS: dict[str, list[str]] = {
    "P6": ["CR-01", "CR-02"],
    "P8": ["CR-01", "CR-01"],
}

# Qué par de marcas (índices 0-based en `marks`) delimita cada episodio.
# P6 ANIDA el episodio de chaleco (CR-02) dentro del de casco (CR-01):
# episodio 0 = [t1,t4] (casco fuera -> puesto), episodio 1 = [t2,t3]
# (chaleco fuera -> puesto), con t1<t2<t3<t4. P8 son dos tramos SECUENCIALES
# separados por una ausencia de cuadro: episodio 0 = [t1,t2] (casco fuera ->
# sale de cuadro), episodio 1 = [t3,t4] (vuelve a entrar -> casco puesto).
# Doc operacion/72 §4.6 (P6) / §4.8 (P8).
MULTI_EPISODE_MARK_INDICES: dict[str, list[tuple[int, int]]] = {
    "P6": [(0, 3), (1, 2)],
    "P8": [(0, 1), (2, 3)],
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
        InvalidMarks: si fin <= evento, o marcas fuera del master, o el
            escenario es P6/P8 (esos requieren 4 marcas, ver
            compute_window_multi)
    """

    # Validación: P6/P8 son de 2 episodios y necesitan 4 marcas — con solo 2
    # marcas acá, SCENARIO_CONDITION no tiene entrada para ellos y piso_s()
    # devolvería None, indistinguible del "sin episodio" legítimo de P3/P5.
    # Hay que cortar esto ANTES de cualquier otra validación.
    if scenario in MULTI_EPISODE_CONDITIONS:
        raise InvalidMarks(f"{scenario} requiere 4 marcas (2 episodios), recibidas 2")

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


def compute_window_multi(
    marks: list[float], master_duration: float, scenario: str
) -> TrimWindow:
    """Convierte 4 marcas (2 episodios) en ventana de recorte, para P6/P8.

    marks: [t1, t2, t3, t4] en segundos sobre el master, estrictamente
    crecientes. Ver doc operacion/72 §4.6 (P6) / §4.8 (P8) para el
    significado de cada marca — P6 anida sus dos episodios, P8 los separa
    en dos tramos secuenciales (ver `MULTI_EPISODE_MARK_INDICES`).

    Raises:
        InvalidMarks: si no son 4, no son estrictamente crecientes, quedan
            fuera del master, o el escenario no es de 2 episodios.
    """
    if len(marks) != 4:
        raise InvalidMarks(f"P6/P8 requieren 4 marcas, recibidas {len(marks)}")
    if list(marks) != sorted(marks) or len(set(marks)) != 4:
        raise InvalidMarks(f"las marcas tienen que ser estrictamente crecientes: {marks}")
    conditions = MULTI_EPISODE_CONDITIONS.get(scenario)
    mark_indices = MULTI_EPISODE_MARK_INDICES.get(scenario)
    if conditions is None or mark_indices is None:
        raise InvalidMarks(f"{scenario} no es un escenario de 2 episodios (P6/P8)")
    t1, t4 = marks[0], marks[-1]
    if t1 < 0 or t4 > master_duration:
        raise InvalidMarks(
            f"marcas fuera del master (primera={t1:.1f} s, última={t4:.1f} s, "
            f"master de {master_duration:.1f} s)"
        )

    warnings: list[str] = []

    start = t1 - PRE_ROLL_S
    if start < 0:
        warnings.append(
            f"solo {t1:.1f} s de pre-roll, se necesitan {PRE_ROLL_S} — "
            "el TTFD va a salir degradado"
        )
        start = 0.0

    # onset/end relativos a `start` (ya clampeado a 0 si hizo falta), no
    # asumiendo PRE_ROLL_S exacto — así el piso sigue siendo correcto incluso
    # con pre-roll degradado.
    onset_rel = [marks[i] - start for i, _ in mark_indices]
    end_rel = [marks[j] - start for _, j in mark_indices]

    cobertura = (t4 - start) + DEFAULT_TAIL_S
    floors = [
        onset_rel[i]
        + DIMENSIONING_MS[conditions[i]]["t_alert_upper_ms"] / 1000
        + DIMENSIONING_MS[conditions[i]]["resolve_ms"] / 1000
        + DIMENSIONING_TAIL_S
        + 1.0  # margen explícito (doc operacion/72 §4.6/§4.8)
        for i in range(2)
    ]
    duration = max(cobertura, *floors)

    if duration > master_duration - start:
        warnings.append(
            f"el master no tiene los {duration:.1f} s que pide el piso/cobertura "
            f"(quedan {master_duration - start:.1f} s) — clip corto, revisar toma"
        )
        duration = master_duration - start

    episodes = [
        EpisodeDraft(
            onset_ms=round(onset_rel[i] * 1000),
            end_ms=round(end_rel[i] * 1000),
            condition=conditions[i],
        )
        for i in range(2)
    ]
    return TrimWindow(
        ss=round(start, 3), duration=round(duration, 3),
        episodes=episodes, warnings=warnings,
    )
