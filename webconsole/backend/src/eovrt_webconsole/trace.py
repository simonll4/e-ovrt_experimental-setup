"""Composición pura del trace media<->control (Spec B Tarea 3, spec §4).

`compose_trace` no hace I/O: recibe listas ya traídas por el router (todas las
páginas de detections/dropped del media-plane, y pattern-progress/alerts/
received-units del control-plane) y produce el eje unificado por
`unit_id` (la clave de join canónica del proyecto, presente en las cuatro
fuentes), con `totals`. `frame_index` es solo el orden preferido cuando
existe (video); en corridas `image_folder` es `None` en las cuatro fuentes y
el eje se ordena por `unit_id`. La paginación de `frames` la hace el
endpoint.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


def _index_by_unit(rows: list[dict]) -> dict[str, list[dict]]:
    by_unit: dict[str, list[dict]] = {}
    for row in rows:
        unit_id = row.get("unit_id")
        if unit_id is None:
            # Fail-safe: progress/alerts reales siempre traen unit_id (D5);
            # sin esto, una fila sin identidad quedaría huérfana del join.
            continue
        by_unit.setdefault(unit_id, []).append(row)
    return by_unit


def _sort_key(row: dict) -> tuple:
    frame_index = row["frame_index"]
    if frame_index is not None:
        # Video: orden por frame_index (con unit_id de desempate estable).
        return (0, frame_index, row["unit_id"])
    # image_folder: frame_index es None en las 4 fuentes -> orden lexicográfico
    # por unit_id (= orden de emisión, ej. img_000000...).
    return (1, row["unit_id"])


def compose_trace(
    *,
    detections: list[dict],
    dropped: list[dict],
    progress: list[dict],
    alerts: list[dict],
    received_unit_ids: set[str] | None,
    control_run_id: str | None,
    topology: str | None,
    pattern_events: list[dict] = (),
) -> dict[str, Any]:
    progress_by_unit = _index_by_unit(progress)
    alerts_by_unit = _index_by_unit(alerts)
    pattern_events_by_unit = _index_by_unit(list(pattern_events))

    rows: dict[str, dict] = {}
    dropped_by_reason: Counter[str] = Counter()

    for det in detections:
        source = det.get("source") or {}
        unit_id = det.get("unit_id")
        if unit_id is None:
            # Fail-safe: el DetectionEvent real siempre trae unit_id; sin
            # esto, sorted(rows) con clave None mezclada con str explota (M3).
            continue
        if received_unit_ids is None:
            control = "n/d"
        elif unit_id in received_unit_ids:
            control = "received"
        else:
            control = "not_received"
        raw_detections = det.get("detections")
        rows[unit_id] = {
            "frame_index": source.get("frame_index"),
            "unit_id": unit_id,
            "timestamp_ms": source.get("timestamp_ms"),
            "detections": None if raw_detections is None else [
                {
                    "label": d.get("label"),
                    "confidence": d.get("confidence"),
                    "bbox_norm_xyxy": d.get("bbox_norm_xyxy"),
                }
                for d in raw_detections
            ],
            "control": control,
        }

    for drop in dropped:
        unit_id = drop.get("unit_id")
        if unit_id is None:
            # Mismo criterio fail-safe que arriba (D5 garantiza unit_id incluso
            # en rate_gate, pero no confiamos ciegamente en la fuente).
            continue
        reason = drop.get("reason")
        dropped_by_reason[reason] += 1
        rows[unit_id] = {
            "frame_index": drop.get("frame_index"),
            "unit_id": unit_id,
            "timestamp_ms": None,
            "detections": None,
            "control": f"dropped:{reason}",
        }

    # active_patterns: reconstruye el intervalo confirmed/sustained->resolved
    # que ni alerts.jsonl (solo el flanco de subida) ni pattern_progress.jsonl
    # (solo "candidate") pueden mostrar -- pattern_events.jsonl es la unica
    # fuente con el ciclo completo. Se plegua hacia adelante sobre el eje de
    # frames YA ordenado: por (pattern_id, subject_key), confirmed/sustained
    # abre el episodio (incluido el propio frame del evento), resolved lo
    # cierra (el propio frame del resolved YA no cuenta como activo).
    # candidate se ignora -- todavia no es un riesgo confirmado (mismo
    # criterio que PatternEngine.snapshot_active() del motor en vivo).
    open_episodes: dict[tuple[str, str], dict] = {}
    frames = []
    for row in sorted(rows.values(), key=_sort_key):
        row["progress"] = progress_by_unit.get(row["unit_id"], [])
        row["alert"] = alerts_by_unit.get(row["unit_id"], [])
        for ev in pattern_events_by_unit.get(row["unit_id"], []):
            key = (ev.get("pattern_id"), ev.get("subject_key"))
            state = ev.get("state")
            if state in ("confirmed", "sustained"):
                open_episodes[key] = {
                    "pattern_id": ev.get("pattern_id"),
                    "condition_id": ev.get("condition_id"),
                    "severity": ev.get("severity"),
                    "subject_key": ev.get("subject_key"),
                }
            elif state == "resolved":
                open_episodes.pop(key, None)
        row["active_patterns"] = list(open_episodes.values())
        frames.append(row)

    totals = {
        "frames": len(frames),
        "detections": len(detections),
        "dropped_by_reason": dict(dropped_by_reason),
        "alerts": len(alerts),
        "received": None if received_unit_ids is None else sum(
            1 for f in frames if f["control"] == "received"
        ),
        "not_received": None if received_unit_ids is None else sum(
            1 for f in frames if f["control"] == "not_received"
        ),
    }

    return {
        "control_run_id": control_run_id,
        "topology": topology,
        "totals": totals,
        "frames": frames,
    }
