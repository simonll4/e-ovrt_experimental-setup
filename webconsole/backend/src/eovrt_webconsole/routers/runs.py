"""Runs: lanzar (compose→launch), listar hidratado, estado y stop (Spec B §5.5/§6)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from eovrt_webconsole.routers.compose import validate_composition
from eovrt_webconsole.run_backend import RunBusy, RunNotFinished, ServiceRejected, ServiceUnavailable, UnknownRun
from eovrt_webconsole.translation import Composition, composition_to_run_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs")

_FORWARD_HEADERS = {"content-type", "content-length", "content-range", "accept-ranges"}


def _row(info: dict) -> dict:
    summary = info.get("summary") or {}
    return {
        "run_id": info.get("run_id"),
        "status": info.get("status", "unknown"),
        "model": info.get("model") or summary.get("model_name"),
        "source_type": summary.get("source_type"),
        "prompt_set_id": summary.get("prompt_set_id"),
        "fps_effective": summary.get("fps_effective"),
        "total_detections": summary.get("total_detections"),
        "duration_seconds": summary.get("duration_seconds"),
        "started_at": info.get("started_at") or summary.get("started_at"),
        "bench_split": info.get("bench_split"),
        "evaluated": info.get("evaluated"),
        "live": info.get("live", False),
        "topology": (summary.get("run_descriptor") or {}).get("topology"),
    }


@router.post("", status_code=201)
async def launch(comp: Composition, request: Request):
    settings = request.app.state.settings
    backend = request.app.state.backend
    errors = await validate_composition(comp, settings, backend)
    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})
    run_request = composition_to_run_request(comp, settings.prompts_dir)
    try:
        run_id = await backend.launch(run_request)
    except RunBusy as exc:
        return JSONResponse(
            status_code=409, content={"detail": exc.detail, "active_run_id": exc.active_run_id}
        )
    except ServiceRejected as exc:
        logger.warning("launch: el servicio rechazó la composición: %s", exc.detail)
        return JSONResponse(
            status_code=422, content={"errors": [{"field": "_service", "message": str(exc.detail)}]}
        )
    except ServiceUnavailable as exc:
        logger.warning("launch: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info(
        "launch: plugin=%s dataset=%s prompt_set=%s -> run_id=%s",
        comp.ingest.plugin,
        comp.ingest.config.get("dataset"),
        comp.prompts.set_id,
        run_id,
    )
    return {"run_id": run_id}


@router.get("")
async def list_runs(request: Request) -> list[dict]:
    settings = request.app.state.settings
    backend = request.app.state.backend
    try:
        base = await backend.list_runs()
    except ServiceUnavailable as exc:
        logger.warning("list_runs: servicio inaccesible: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    rows: list[dict] = []
    for item in base[: settings.hydration_limit]:
        try:
            rows.append(_row(await backend.status(item["run_id"])))
        except (UnknownRun, ServiceUnavailable):
            rows.append(
                {
                    "run_id": item["run_id"],
                    "status": item["status"],
                    "bench_split": item.get("bench_split"),
                    "evaluated": item.get("evaluated"),
                    "live": item.get("live", False),
                }
            )
    rows.extend(
        {
            "run_id": item["run_id"],
            "status": item["status"],
            "bench_split": item.get("bench_split"),
            "evaluated": item.get("evaluated"),
            "live": item.get("live", False),
        }
        for item in base[settings.hydration_limit :]
    )
    return rows


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    try:
        return await request.app.state.backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("get_run(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{run_id}/stop", status_code=202)
async def stop_run(run_id: str, request: Request) -> dict:
    try:
        await request.app.state.backend.stop(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("stop_run(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info("stop_run: solicitado stop de run_id=%s", run_id)
    return {"run_id": run_id, "stopping": True}


@router.post("/{run_id}/evaluate")
async def evaluate_run(run_id: str, request: Request):
    try:
        return await request.app.state.backend.evaluate(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except RunNotFinished as exc:
        return JSONResponse(status_code=409, content={"detail": exc.detail})
    except ServiceRejected as exc:
        return JSONResponse(
            status_code=422,
            content={"errors": [{"field": "_service", "message": str(exc.detail)}]},
        )
    except ServiceUnavailable as exc:
        logger.warning("evaluate(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/evaluate")
async def get_evaluation(run_id: str, request: Request):
    try:
        return await request.app.state.backend.get_evaluation(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run no evaluado: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("get_evaluation(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/detections")
async def detections(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
) -> dict:
    try:
        return await request.app.state.backend.detections(run_id, page=page, page_size=page_size)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Sin detecciones para: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("detections(%s): servicio inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/artifacts/{artifact_path:path}")
async def artifact(run_id: str, artifact_path: str, request: Request):
    backend = request.app.state.backend
    try:
        upstream = await backend.open_artifact(
            run_id, artifact_path, range_header=request.headers.get("range")
        )
    except ServiceUnavailable as exc:
        logger.warning("artifact(%s, %s): servicio inaccesible: %s", run_id, artifact_path, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if upstream.status_code == 404:
        await upstream.aclose()
        raise HTTPException(status_code=404, detail="Artefacto no encontrado")
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in _FORWARD_HEADERS}
    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,  # 200 o 206 (Range) del servicio
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )
