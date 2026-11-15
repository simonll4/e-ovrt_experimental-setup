"""La plataforma (plan de la consola, §7.1): estado de los trece servicios, orquestación y registro."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.orchestrator import ComposeError, PlatformBusy, SwitchFailed, UnknownInstance
from eovrt_webconsole.plataforma import AccionInvalida, ConsolaPropia, EnCurso

router = APIRouter(prefix="/api/plataforma")


def _error(exc: Exception) -> JSONResponse:
    if isinstance(exc, ConsolaPropia):
        return JSONResponse(status_code=409, content={
            "detail": "La consola no se detiene a sí misma: hacelo desde una terminal.", "comando": exc.comando})
    if isinstance(exc, EnCurso):
        return JSONResponse(status_code=409, content={"detail": str(exc), "confirmar": True})
    if isinstance(exc, PlatformBusy):
        return JSONResponse(status_code=409, content={
            "detail": f"El motor de detección tiene una corrida en curso ({exc.run_id}): no se cambia hasta que termine."})
    if isinstance(exc, (AccionInvalida, UnknownInstance)):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    if isinstance(exc, SwitchFailed):
        return JSONResponse(status_code=504 if exc.step == "readyz" else 502, content={"detail": exc.detail})
    if isinstance(exc, ComposeError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    raise exc


@router.get("")
async def estado(request: Request) -> dict:
    plataforma = request.app.state.plataforma
    try:
        datos = await plataforma.estado()
    except ComposeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {**datos, "acciones": plataforma.acciones()}


@router.post("/servicios/{servicio}/{verbo}")
async def accion(servicio: str, verbo: str, request: Request, body: dict | None = None):
    try:
        return await request.app.state.plataforma.accion(servicio, verbo, bool((body or {}).get("confirmar")))
    except Exception as exc:  # noqa: BLE001 -- `_error` traduce las conocidas y relanza el resto
        return _error(exc)


@router.post("/lista")
async def dejar_lista(request: Request):
    try:
        return await request.app.state.plataforma.dejar_lista()
    except Exception as exc:  # noqa: BLE001
        return _error(exc)
