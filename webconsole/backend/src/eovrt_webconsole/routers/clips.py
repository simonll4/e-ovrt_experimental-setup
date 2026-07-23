"""Generación de clips desde la consola (spec 2026-07-21): listas, recorte
y servido de video con HTTP Range para poder arrastrar la línea de tiempo."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from eovrt_webconsole.clips import inventory
from eovrt_webconsole.clips.generate import InvalidRequest, generate_clip
from eovrt_webconsole.clips.naming import InvalidScenario
from eovrt_webconsole.clips.trim import TrimFailed
from eovrt_webconsole.clips.window import InvalidMarks
from eovrt_webconsole.recording.probe import ProbeError

router = APIRouter(prefix="/api/clips")


class GenerateClipBody(BaseModel):
    master: str
    t_event_s: float
    t_end_s: float
    scenario: str | None = None
    clip_id: str | None = None


def _settings(request: Request):
    return request.app.state.settings


@router.get("/masters")
def masters(request: Request) -> dict:
    settings = _settings(request)
    return {"masters": inventory.list_masters(settings.raw_dir, settings.videos_dir)}


@router.get("")
def clips(request: Request) -> dict:
    return {"clips": inventory.list_clips(_settings(request).videos_dir)}


@router.post("", status_code=201)
def create_clip(request: Request, body: GenerateClipBody) -> dict:
    settings = _settings(request)
    try:
        return generate_clip(
            raw_dir=settings.raw_dir,
            videos_dir=settings.videos_dir,
            script=settings.prepare_clip_script,
            master_name=body.master,
            t_event=body.t_event_s,
            t_end=body.t_end_s,
            scenario=body.scenario,
            clip_id=body.clip_id,
        )
    except (InvalidRequest, InvalidMarks, InvalidScenario) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProbeError as exc:
        raise HTTPException(
            status_code=422, detail=f"el master no se puede leer: {exc}"
        ) from exc
    except TrimFailed as exc:
        # La salida REAL de prepare_clip.sh, no un error genérico (spec §7).
        # El master queda intacto: recortar solo lo lee.
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _serve(base: Path, filename: str) -> FileResponse:
    # El nombre no puede traer separadores: cualquier intento de salirse del
    # directorio es un 404, igual que un archivo inexistente.
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="no encontrado")
    path = base / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="no encontrado")
    # FileResponse (Starlette >=1.x) responde 206 a Range por sí solo: es lo
    # que permite arrastrar la línea de tiempo sin bajar el master entero.
    return FileResponse(path, media_type="video/mp4")


@router.get("/media/master/{name}")
def media_master(request: Request, name: str) -> FileResponse:
    return _serve(_settings(request).raw_dir, name)


@router.get("/media/clip/{clip_id}")
def media_clip(request: Request, clip_id: str) -> FileResponse:
    return _serve(_settings(request).clips_dir, f"{clip_id}.mp4")
