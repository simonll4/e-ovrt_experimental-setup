"""Las cifras de desempeño que muestra la demo, leídas de la generación 2.

La demo NO es evidencia de desempeño (spec §3.2): la tarjeta «Qué muestra y qué no»
remite a las cifras medidas. Esas cifras son las de la generación 2 (doc
`operacion/134`), que se generan en la Victus: acá se leen en el momento de mostrarlas
de `results/gen2/<ID>/resultado.json` y, si todavía no existen, la pantalla dice
«cifra pendiente (generación 2)». Ningún número del informe v0.1 se escribe a mano acá.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# (prueba, clave del resumen, qué es) — las que la pantalla de la demo cita.
CIFRAS = (
    ("ALR-01", "f1", "F1 de alertas por episodio, granularidad escena (la de esta demo), rodaje guionado"),
    ("ALR-07", "falsas_alarmas", "Falsas alarmas en obra real, granularidad escena"),
    ("ALR-08", "falsas_alarmas", "Falsas alarmas en obra real, granularidad por sujeto"),
    ("RT-03", "fps_efectivos", "Cuadros por segundo efectivos en vivo (config de la demo)"),
    ("RT-03", "g2a_p95_ms", "G2A p95 en vivo (config de la demo)"),
    ("RT-03", "capture_to_host_p50_ms", "Captura → host p50 en vivo (config de la demo)"),
)
PENDIENTE = "cifra pendiente (generación 2)"


def _resultado(results_dir: Path, prueba: str) -> dict | None:
    path = results_dir / "gen2" / prueba / "resultado.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def leer_cifras(results_dir: Path) -> list[dict[str, Any]]:
    salida: list[dict[str, Any]] = []
    for prueba, clave, que_es in CIFRAS:
        data = _resultado(results_dir, prueba)
        fila: dict[str, Any] = {
            "prueba": prueba, "clave": clave, "que_es": que_es,
            "valor": None, "unidad": None, "estado": None, "pendiente": True, "texto": PENDIENTE,
        }
        if data is not None:
            item = next(
                (r for r in data.get("resumen") or [] if isinstance(r, dict) and r.get("clave") == clave),
                None,
            )
            if item is not None and item.get("valor") is not None:
                fila.update(
                    valor=item.get("valor"),
                    unidad=item.get("unidad"),
                    estado=data.get("estado"),
                    pendiente=False,
                    texto=None,
                    fuente=f"results/gen2/{prueba}/resultado.json",
                )
        salida.append(fila)
    return salida
