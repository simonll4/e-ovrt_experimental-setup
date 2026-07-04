"""Compare: agrega las evaluaciones BENCH de N runs para la vista comparativa."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from eovrt_webconsole.run_backend import ServiceUnavailable, UnknownRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MAX_COMPARE_RUNS = 8


@router.get("/compare")
async def compare(request: Request, runs: str = Query(...)):
    # dedupe preservando orden; ids vacíos (",," o espacios) se descartan
    ids = [rid for rid in dict.fromkeys(part.strip() for part in runs.split(",")) if rid]
    if not ids:
        raise HTTPException(status_code=422, detail="Parámetro runs vacío")
    if len(ids) > MAX_COMPARE_RUNS:
        raise HTTPException(
            status_code=422, detail=f"Máximo {MAX_COMPARE_RUNS} runs a comparar"
        )
    backend = request.app.state.backend
    evals: list[tuple[str, dict]] = []
    skipped: list[str] = []
    for run_id in ids:
        try:
            evals.append((run_id, await backend.get_evaluation(run_id)))
        except UnknownRun:
            skipped.append(run_id)
        except ServiceUnavailable as exc:
            logger.warning("compare(%s): servicio inaccesible: %s", run_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    # El set/orden de clases es idéntico entre runs (mismo BENCH COCO): se toma
    # del primer eval resuelto.
    classes: list[str] = (
        [item.get("class_name") for item in evals[0][1].get("per_class") or []]
        if evals
        else []
    )
    rows: list[dict] = []
    ap_by_class: dict[str, list[float | None]] = {name: [] for name in classes}
    for run_id, ev in evals:
        model = ev.get("model")
        bench_split = ev.get("bench_split")
        rows.append(
            {
                "run_id": run_id,
                "label": f"{model or run_id} · {bench_split or '?'}",
                "model": model,
                "bench_split": bench_split,
                "mAP50": ev.get("mAP50"),
                "cr01_detection_recall": ev.get("cr01_detection_recall"),
            }
        )
        ap50_by_name = {
            item.get("class_name"): item.get("AP50") for item in ev.get("per_class") or []
        }
        for name in classes:
            ap_by_class[name].append(ap50_by_name.get(name))
    return {"runs": rows, "classes": classes, "ap_by_class": ap_by_class, "skipped": skipped}
