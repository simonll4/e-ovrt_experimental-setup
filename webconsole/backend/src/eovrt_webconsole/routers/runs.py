"""Runs: lanzar (compose→launch), listar hidratado, estado y stop (Spec B §5.5/§6)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from eovrt_webconsole.experiment.control_backend import (
    RunActive as ControlRunActive,
    ServiceUnavailable as ControlServiceUnavailable,
    UnknownRun as ControlUnknownRun,
)
from eovrt_webconsole.routers.compose import validate_composition
from eovrt_webconsole.run_backend import (
    RunActive, RunBusy, RunNotFinished, ServiceRejected, ServiceUnavailable, UnknownRun,
)
from eovrt_webconsole.trace import compose_trace
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


@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: str, request: Request):
    backend = request.app.state.backend
    control = request.app.state.control_backend

    media_gone = False
    try:
        media_status = await backend.status(run_id)
    except UnknownRun:
        media_gone = True
    except ServiceUnavailable as exc:
        logger.warning("delete_run(%s): servicio media inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        if media_status.get("status") == "running":
            raise HTTPException(status_code=409, detail="No se puede borrar un run activo")

    try:
        candidates = await control.list_runs(media_run_id=run_id)
    except ControlServiceUnavailable as exc:
        logger.warning(
            "delete_run(%s): control-plane inaccesible al resolver correlación: %s", run_id, exc
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    control_run_ids = [item["control_run_id"] for item in candidates]

    if media_gone and not control_run_ids:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}")

    for control_run_id in control_run_ids:
        try:
            control_status = await control.status(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlServiceUnavailable as exc:
            logger.warning("delete_run(%s): control-plane inaccesible: %s", run_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if control_status.get("status") == "running":
            raise HTTPException(
                status_code=409, detail=f"No se puede borrar: {control_run_id} sigue activo"
            )

    # Orden de borrado (finding de la revisión final): control-plane PRIMERO,
    # media-plane AL FINAL — y el borrado de media SOLO se intenta si el lado
    # control terminó sin errores. La visibilidad de la UI (RunsPage/
    # RunDetailPage) se nutre enteramente del media-plane, así que dejar media
    # como lo último en tocarse, y condicionado al éxito de control, garantiza
    # que ante CUALQUIER falla parcial el run siga visible para reintentar:
    # si control falla, media NI SE INTENTA (sigue existiendo, visible); si
    # control tiene éxito pero media falla, el borrado quedó incompleto y el
    # run también sigue visible (no se borró). Solo cuando ambos lados
    # terminan bien el run desaparece de la UI, que es lo correcto. Con el
    # orden inverso (media primero, sin gating), una falla del lado control
    # (el endpoint más nuevo, menos probado) dejaba el run invisible en la UI
    # sin forma de reintentar, pese a que control seguía huérfano.
    errors: dict[str, str] = {}
    control_errors: list[str] = []
    for control_run_id in control_run_ids:
        try:
            await control.delete(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlRunActive as exc:
            control_errors.append(exc.detail)
        except ControlServiceUnavailable as exc:
            control_errors.append(str(exc))
    if control_errors:
        errors["control"] = "; ".join(control_errors)

    if not control_errors and not media_gone:
        try:
            await backend.delete(run_id)
        except UnknownRun:
            pass
        except RunActive as exc:
            errors["media"] = exc.detail
        except ServiceUnavailable as exc:
            errors["media"] = str(exc)

    if errors:
        logger.warning("delete_run(%s): borrado parcial: %s", run_id, errors)
        return JSONResponse(status_code=207, content={"detail": "borrado parcial", "errors": errors})
    logger.info("delete_run: run_id=%s borrado en ambos planos", run_id)
    return Response(status_code=204)


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


async def _fetch_all(fetch, run_id: str) -> list[dict]:
    """Pagina un endpoint del media-plane (detections/dropped) hasta traer
    todas las filas (trampa de volumen del spec §7: sin esto, el trace solo
    vería la primera página)."""
    items: list[dict] = []
    page = 1
    page_size = 1000
    while True:
        result = await fetch(run_id, page=page, page_size=page_size)
        if not result["items"]:
            break
        items.extend(result["items"])
        if len(items) >= result["total"]:
            break
        page += 1
    return items


@router.get("/{run_id}/trace")
async def trace(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    control_run_id: str | None = Query(default=None),
) -> dict:
    backend = request.app.state.backend
    control = request.app.state.control_backend
    try:
        summary = await backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Trae TODAS las paginas de detections y dropped (page_size=1000, loop hasta total).
    # UnknownRun en cualquiera de las dos lecturas se tolera como lista vacia: el
    # run ya fue validado por status() arriba, asi que un 404 puntual de detections
    # o dropped no debe tumbar el trace (I2 del review).
    try:
        detections_rows = await _fetch_all(backend.detections, run_id)
    except UnknownRun:
        detections_rows = []
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible (detections): %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        dropped_rows = await _fetch_all(backend.dropped, run_id)
    except UnknownRun:
        dropped_rows = []
    except ServiceUnavailable as exc:
        logger.warning("trace(%s): servicio media inaccesible (dropped): %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Lado control: best-effort (degradacion del spec §6). ControlUnknownRun en
    # el lookup o en las lecturas se trata como "sin control run" (no 404 del
    # trace); ControlServiceUnavailable puebla control_error y deja todo en n/d.
    progress, alerts, received, control_error = [], [], None, None
    try:
        if control_run_id is None:
            candidates = await control.list_runs(media_run_id=run_id)
            control_run_id = candidates[0]["control_run_id"] if candidates else None
        if control_run_id is not None:
            progress = await control.pattern_progress(control_run_id)
            alerts = await control.alerts(control_run_id)
            received = {u["unit_id"] for u in await control.received_units(control_run_id)}
    except ControlServiceUnavailable as exc:
        logger.warning("trace(%s): servicio control inaccesible: %s", run_id, exc)
        control_error = str(exc)
        control_run_id, progress, alerts, received = None, [], [], None
    except ControlUnknownRun:
        control_run_id, progress, alerts, received = None, [], [], None
    topology = ((summary.get("summary") or {}).get("run_descriptor") or {}).get("topology")
    composed = compose_trace(
        detections=detections_rows, dropped=dropped_rows, progress=progress, alerts=alerts,
        received_unit_ids=received, control_run_id=control_run_id,
        topology=topology,
    )
    frames = composed.pop("frames")
    start = (page - 1) * page_size
    return {
        "media_run_id": run_id,
        **composed,
        "control_error": control_error,
        "page": page,
        "page_size": page_size,
        "total": len(frames),
        "frames": frames[start : start + page_size],
    }


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
