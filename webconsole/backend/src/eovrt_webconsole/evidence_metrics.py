"""Adaptadores de metrics.json. Los cuatro esquemas NO comparten forma.

El despacho es por `schema_version` cuando está declarado; sólo se recurre a una
sonda estructural para el único esquema que no lo declara (`nivel_a_gate`, sin
`schema_version`, identificado por las claves `gate` + `complementarity`, que
sólo él tiene). Una forma desconocida devuelve None: la pantalla muestra el
resultado sin cabecera leída antes que adivinar una métrica.

Contrato real de cada entrada de "cabecera" (documenta lo que el código produce, no
lo que proponía el brief original — no hay TypedDict, esto es la referencia para
quien consuma este módulo):
    {"label": str, "valor": float | None, "nota": str | None (opcional),
     "entero": bool (opcional, True si "valor" se muestra sin decimales)}
No existe una clave "texto": el brief la declaraba pero ningún adaptador la
produce; "nota" cumple esa función.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _cargar(path: Path) -> dict | None:
    """Ausente es NORMAL; ilegible es un problema. Se loguean distinto.

    18 de los 35 resultados no tienen `metrics.json` por diseño (son las cifras
    citadas, con artefacto fuera de este repositorio), así que la ausencia es el
    caso esperado y gritarla por cada request enterraba el único aviso que
    importa: un `metrics.json` que SÍ está y no se puede parsear.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.debug("sin metrics.json en %s (cifra citada, no leída)", path)
        return None
    except (OSError, ValueError) as exc:
        logger.warning("metrics.json ilegible en %s: %s", path, exc)
        return None


def campo_de(path: Path, campo: str) -> float | None:
    """Una métrica puntual, para las cifras `leer:` del recorrido."""
    data = _cargar(path)
    if not isinstance(data, dict):
        return None
    for contenedor in (data.get("positives"), data):
        if isinstance(contenedor, dict) and isinstance(contenedor.get(campo), (int, float)):
            return float(contenedor[campo])
    return None


def _clip_campaign(data: dict) -> dict:
    pos, neg = data.get("positives", {}), data.get("negatives", {})
    cabecera = [
        {"label": "F1 micro", "valor": pos.get("f1_micro")},
        {"label": "recall micro", "valor": pos.get("recall_micro")},
        {"label": "precision micro", "valor": pos.get("precision_micro")},
        {"label": "episodios evaluables", "valor": pos.get("episodes_evaluable"),
         "entero": True, "nota": f"de {pos.get('episodes_total')}"},
        {"label": "falsos positivos", "valor": pos.get("false_positives"), "entero": True},
    ]
    condicion = {
        "id": "condicion", "titulo": "Por condición de riesgo",
        "nota": "El t_alert está dominado por la persistencia del patrón, no por el transporte.",
        "columnas": ["Condición", "Episodios", "SDR", "t_alert"],
        "filas": [{"nombre": k, "episodios": v.get("episodes"), "sdr": v.get("sdr"),
                   "t_alert_ms": v.get("t_alert_system_ms"), "fp": v.get("false_positives"),
                   "no_aplica": None}
                  for k, v in sorted(data.get("by_condition", {}).items())],
    }
    escenario = {
        "id": "escenario", "titulo": "Por escenario",
        "nota": "Nunca sólo el agregado — limitación L5.",
        "columnas": ["Escenario", "Clips", "Episodios", "recall", "FP", "SDR"],
        "filas": [{"nombre": k, "clips": v.get("clips"),
                   "episodios": v.get("episodes_evaluable"), "recall": v.get("recall"),
                   "fp": v.get("false_positives"), "sdr": v.get("sdr"),
                   # Lo que no tiene dato se DECLARA, no se dibuja como cero.
                   "no_aplica": None if v.get("recall") is not None
                   else "sin episodios evaluables"}
                  for k, v in sorted(data.get("by_scenario", {}).items())],
    }
    clip = {
        "id": "clip", "titulo": "Por clip", "nota": None,
        "columnas": ["Clip", "Escenario", "Esperados", "Detectados", "recall", "t_alert"],
        "filas": [{"nombre": c.get("clip_id"), "escenario": c.get("scenario"),
                   "esperados": c.get("expected"), "detectados": c.get("matched"),
                   "recall": c.get("recall"), "t_alert_ms": c.get("t_alert_system_ms"),
                   "no_aplica": None if c.get("applicability") == "computed"
                   else c.get("applicability_cause")}
                  for c in data.get("by_clip", [])],
    }
    negativos = {
        "id": "negativos", "titulo": "Control de negativos",
        "nota": "Los negativos no entran a precision, recall ni F1: su métrica son los FP.",
        "columnas": ["Clips", "FP", "Tiempo observado"],
        "filas": [{"nombre": "negativos", "clips": neg.get("clips"),
                   "fp": neg.get("false_positives"),
                   "observado_ms": neg.get("observed_ms"), "no_aplica": None}],
    }
    return {"esquema": "clip_campaign_metrics.v1", "cabecera": cabecera,
            "desgloses": [condicion, escenario, clip, negativos]}


def _clip_person_state(data: dict) -> dict:
    # Forma real: cada entrada de `por_clip` NO trae "f1" plano — trae
    # "por_condicion": {"CR-01": {...}, "CR-02": {...}}, y dentro de cada condición
    # "recall" puede venir null (sin person-frames GT positivas para esa condición
    # en ese clip). El desglose declarado es por clip Y condición.
    agregado = data.get("agregado", {})
    cabecera = [{"label": f"{cond} F1", "valor": v.get("f1")}
                for cond, v in sorted(agregado.items())]
    filas = [
        {"nombre": str(c.get("clip_id")), "condicion": condicion,
         # Lo que no tiene dato se DECLARA, no se dibuja como cero: la fuente
         # codifica "sin person-frames GT positivas" como f1=0.0 con recall=null.
         # El adaptador no repite ese 0.0 — lo vacía junto con no_aplica, porque
         # "F1" es la única columna de métrica del desglose: un 0.0 ahí es
         # indistinguible de un resultado medido malo.
         "f1": v.get("f1") if v.get("recall") is not None else None,
         "no_aplica": None if v.get("recall") is not None
         else "sin person-frames GT positivas"}
        for c in data.get("por_clip", [])
        for condicion, v in sorted(c.get("por_condicion", {}).items())
    ]
    return {
        "esquema": "clip_person_state.v1", "cabecera": cabecera,
        "desgloses": [{
            "id": "clip", "titulo": "Por clip y condición",
            "nota": "person-frames con atributo unknown excluidas del denominador.",
            "columnas": ["Clip", "Condición", "F1"],
            "filas": filas,
        }],
    }


def _nivel_a_gate(data: dict) -> dict:
    # Forma real de cada entrada de "gate": f1_eind, best_edir_variant, f1_edir,
    # ratio, edir_below_half. No existe "delta": el campo de comparación es "ratio"
    # (F1 de E-DIR sobre F1 de E-IND).
    gate = data.get("gate", {})
    cabecera = [
        {"label": k, "valor": v.get("ratio"),
         "nota": "ratio F1 E-DIR/E-IND" + (" — bajo la mitad" if v.get("edir_below_half") else "")}
        for k, v in sorted(gate.items())
    ]
    return {
        "esquema": "nivel_a_gate", "cabecera": cabecera,
        "desgloses": [{
            "id": "estrato", "titulo": "Por estrato",
            "nota": "Comparación pre-registrada entre formulaciones. "
                    "«Rescatadas» son las que E-IND falla y la mejor variante E-DIR acierta.",
            # Columnas REALES, no el dict crudo: antes la fila viajaba como
            # `{"valores": v}` y la pantalla la imprimía como JSON bajo un
            # encabezado que prometía columnas. El desglose no es opcional
            # (limitación L5), así que tiene que ser legible.
            "columnas": ["Estrato / condición", "Variante E-DIR", "Faltantes E-IND",
                         "Faltantes E-DIR", "Rescatadas por E-DIR", "Fracción rescatada"],
            "filas": [{"nombre": k, "variante": v.get("best_edir_variant"),
                       "eind_misses": v.get("eind_misses"),
                       "edir_misses": v.get("edir_misses"),
                       "recuperadas": v.get("recovered_by_edir"),
                       "fraccion": v.get("fraction_recovered"), "no_aplica": None}
                      for k, v in sorted(data.get("complementarity", {}).items())],
        }],
    }


def _fila_latencia(nombre: str, v: dict) -> dict:
    return {"nombre": nombre, "n": v.get("count"), "p50": v.get("p50"),
            "p95": v.get("p95"), "p99": v.get("p99"), "no_aplica": None}


def _talert_notification(data: dict) -> dict:
    # Forma real: declara schema_version ("talert_notification_metrics.v1"), así
    # que no hace falta sonda. NO tiene clave "fases" en ningún nivel; la latencia
    # primaria vive en primary.latency_ms y primary.by_origin, y la comparación
    # primera-entrega-vs-reenvío en steady_state.
    primary = data.get("primary", {})
    latencia = primary.get("latency_ms", {})
    citable = data.get("citable", {})
    steady = data.get("steady_state", {})
    cabecera = [
        {"label": "p95 control→MQTT", "valor": citable.get("value"), "nota": citable.get("unit")},
        {"label": "p50", "valor": latencia.get("p50"), "nota": "ms"},
        {"label": "p99", "valor": latencia.get("p99"), "nota": "ms"},
        {"label": "muestras", "valor": citable.get("sample_size"), "entero": True},
        {"label": "duplicados MQTT", "valor": primary.get("mqtt_duplicates"), "entero": True},
    ]
    origen = {
        "id": "origen", "titulo": "Por origen del evento",
        "nota": "dbe/ebe: procedencia del evento de control que originó la alerta.",
        "columnas": ["Origen", "n", "p50", "p95", "p99"],
        "filas": [_fila_latencia(nombre, v)
                  for nombre, v in sorted(primary.get("by_origin", {}).items())],
    }
    entrega = {
        "id": "entrega", "titulo": "Primera entrega vs reenvíos por cooldown",
        "nota": "steady_state distingue la primera entrega de un run de los reenvíos "
                "posteriores al cooldown.",
        "columnas": ["Tipo", "n", "p50", "p95", "p99"],
        "filas": [
            _fila_latencia("primera entrega por run", steady.get("first_delivery_per_run", {})),
            _fila_latencia("reenvíos (cooldown)", steady.get("subsequent_deliveries", {})),
        ],
    }
    return {"esquema": "talert_notification_metrics.v1", "cabecera": cabecera,
            "desgloses": [origen, entrega]}


def leer_metricas(path: Path) -> dict | None:
    data = _cargar(path)
    if not isinstance(data, dict):
        return None
    esquema = data.get("schema_version")
    if esquema == "clip_campaign_metrics.v1":
        return _clip_campaign(data)
    if esquema == "clip_person_state.v1":
        return _clip_person_state(data)
    if esquema == "talert_notification_metrics.v1":
        return _talert_notification(data)
    # Sonda de forma: bench_nivel_a/d1 es el único de los 17 que no declara
    # schema_version. No adivinamos por nombre de archivo: exigimos las dos
    # claves que sólo tiene ese esquema.
    if esquema is None and "gate" in data and "complementarity" in data:
        return _nivel_a_gate(data)
    logger.warning("esquema de métricas no reconocido en %s: %r", path, esquema)
    return None
