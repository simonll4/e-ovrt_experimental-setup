"""«Correr un clip» (plan de la consola, §7.2): tres clips del rodaje por la cadena completa. No es evidencia."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.demo.config import ConfigDemoError
from eovrt_webconsole.demostracion import ClipDesconocido, ClipNoListo, ClipOcupado
from eovrt_webconsole.experiment.run_manager import ExperimentBusy

router = APIRouter(prefix="/api/demostracion/clip")


@router.get("")
def clips(request: Request) -> dict:
    correr = request.app.state.correr_clip
    return {"clips": correr.clips(), "cadencia": correr.cadencia(), "actual": correr.actual()}


@router.get("/preparacion")
async def preparacion(request: Request) -> dict:
    return await request.app.state.correr_clip.preparacion()


@router.post("/{clip_id}/correr", status_code=202)
async def correr(clip_id: str, request: Request):
    try:
        return await request.app.state.correr_clip.correr(clip_id)
    except ClipDesconocido as exc:
        raise HTTPException(status_code=404, detail=f"Ese clip no se puede correr: {exc.args[0]}") from exc
    except (ClipOcupado, ExperimentBusy) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except ClipNoListo as exc:
        return JSONResponse(status_code=503, content={"detail": str(exc), "preparacion": exc.preparacion})
    except ConfigDemoError as exc:
        return JSONResponse(status_code=503, content={"detail": f"La configuración del informe no se pudo armar: {exc}"})


@router.get("/corridas/{corrida_id}")
def corrida(corrida_id: str, request: Request) -> dict:
    datos = request.app.state.correr_clip.corrida(corrida_id)
    if datos is None:
        raise HTTPException(status_code=404, detail="Esa corrida no existe")
    return datos
