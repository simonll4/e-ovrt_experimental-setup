"""Lo que muestra cada tarjeta de la demo, derivado de los episodios del control-plane.

Fuente: `episodes[]` de `GET :8081/api/runs/current` (un episodio por condición y
sujeto en `candidate`, `confirmed` o `sustained`, con su avance; ver
`PatternEngine.snapshot_episodes` del control-plane). Acá no se decide nada: el motor
confirma y resuelve; esto solo traduce su estado a las cinco caras de la tarjeta.

| Episodio del motor                                   | Tarjeta      |
|------------------------------------------------------|--------------|
| ninguno                                              | ok           |
| candidate                                            | confirmando  |
| confirmed / sustained, sin cobertura en curso        | alerta       |
| confirmed / sustained, con cobertura en curso        | resolviendo  |
| desapareció después de alerta o resolviendo          | resuelta (5 s) |

Con granularidad escena hay a lo sumo un episodio por condición; si hubiera varios
(sujeto), se muestra el más avanzado, igual que el banner de `defensa/overlay_render.py`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CONDICIONES = {"CR-01": "Casco", "CR-02": "Chaleco"}
HOLD_RESUELTA_S = 5.0
_ORDEN = {"ok": 0, "resuelta": 0, "confirmando": 1, "resolviendo": 2, "alerta": 3}


def _cara(episodio: dict[str, Any]) -> tuple[str, float | None, float | None]:
    """(estado, transcurrido_ms, umbral_ms) de un episodio del motor."""
    estado = episodio.get("state")
    if estado == "candidate":
        return "confirmando", episodio.get("elapsed_ms"), episodio.get("confirm_after_ms")
    if estado in {"confirmed", "sustained"}:
        if episodio.get("clear_elapsed_ms") is not None:
            return "resolviendo", episodio.get("clear_elapsed_ms"), episodio.get("resolve_after_ms")
        return "alerta", episodio.get("elapsed_ms"), None
    return "ok", None, None


@dataclass
class _Condicion:
    codigo: str
    estado: str = "ok"
    desde: float | None = None
    alertas: int = 0
    alerta_desde: float | None = None
    severidad: str | None = None
    transcurrido_ms: float | None = None
    umbral_ms: float | None = None


@dataclass
class Derivador:
    """Mantiene la cara de cada tarjeta entre consultas (el "resuelta" dura 5 s)."""

    condiciones: dict[str, _Condicion] = field(
        default_factory=lambda: {c: _Condicion(c) for c in CONDICIONES}
    )

    def actualizar(self, episodios: list[dict[str, Any]], ahora: float) -> list[dict[str, Any]]:
        """Aplica una foto de episodios. Devuelve las transiciones (para el log)."""
        transiciones: list[dict[str, Any]] = []
        for codigo, cond in self.condiciones.items():
            propios = [e for e in episodios if e.get("condition_id") == codigo]
            caras = [(_cara(e), e) for e in propios]
            if caras:
                (estado, transcurrido, umbral), episodio = max(caras, key=lambda c: _ORDEN[c[0][0]])
                cond.severidad = episodio.get("severity") or cond.severidad
            elif cond.estado in {"alerta", "resolviendo"}:
                estado, transcurrido, umbral = "resuelta", None, None
            elif cond.estado == "resuelta" and cond.desde is not None and ahora - cond.desde < HOLD_RESUELTA_S:
                estado, transcurrido, umbral = "resuelta", None, None
            else:
                estado, transcurrido, umbral = "ok", None, None

            if estado != cond.estado:
                # Una alerta NUEVA es entrar a "alerta" desde algo que no era el mismo
                # episodio (ok, confirmando, resuelta). Volver de "resolviendo" a
                # "alerta" es el mismo episodio: la histéresis no re-alerta.
                if estado == "alerta" and cond.estado != "resolviendo":
                    cond.alertas += 1
                    cond.alerta_desde = ahora
                transiciones.append({"condicion": codigo, "de": cond.estado, "a": estado})
                cond.estado = estado
                cond.desde = ahora
            cond.transcurrido_ms = transcurrido
            cond.umbral_ms = umbral
        return transiciones

    def foto(self) -> list[dict[str, Any]]:
        return [
            {
                "condicion": c.codigo,
                "nombre": CONDICIONES[c.codigo],
                "estado": c.estado,
                "transcurrido_ms": c.transcurrido_ms,
                "umbral_ms": c.umbral_ms,
                "severidad": c.severidad,
                "alertas": c.alertas,
                "alerta_desde": c.alerta_desde,
            }
            for c in self.condiciones.values()
        ]
