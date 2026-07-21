"""Grabación de tomas de rodaje: una activa por consola (spec 2026-07-21)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole import camera_store as cs
from eovrt_webconsole.recording.guards import GateError
from eovrt_webconsole.recording.manager import BasenameTaken, RecordingBusy
from eovrt_webconsole.recording.naming import InvalidTakeId, next_basename
from eovrt_webconsole.recording.occupancy import check_media_plane_free
from eovrt_webconsole.recording.types import RecordingSpec
from eovrt_webconsole.redact import redact_rtsp_credentials

router = APIRouter(prefix="/api/recordings")


def _manager(request: Request):
    return request.app.state.recording_manager


@router.get("/next")
def next_take(request: Request, scenario: str, variant: str) -> dict:
    try:
        basename = next_basename(
            request.app.state.settings.raw_dir, scenario, variant
        )
    except InvalidTakeId as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"basename": basename}


@router.get("")
def recording_status(request: Request) -> dict:
    return _manager(request).status()


@router.post("", status_code=201)
async def start_recording(request: Request, payload: dict) -> dict:
    settings = request.app.state.settings
    body = dict(payload)

    camera_id = body.pop("camera_id", None)
    if camera_id is not None:
        try:
            preset = cs.get_camera(settings.cameras_dir, camera_id)
        except cs.CameraNotFound as exc:
            raise HTTPException(status_code=404, detail=f"cámara desconocida: {camera_id}") from exc
        body.setdefault("plugin", preset.get("plugin"))
        body.setdefault("config", preset.get("config", {}))
        body.setdefault("label", camera_id)

    scenario = body.pop("scenario", None)
    variant = body.pop("variant", None)
    if scenario is not None and variant is not None:
        try:
            body["basename"] = next_basename(settings.raw_dir, scenario, variant)
        except InvalidTakeId as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        spec = RecordingSpec(**body)
    except Exception as exc:  # noqa: BLE001 - ValidationError de pydantic y kwargs sobrantes
        # pydantic incluye el valor recibido en el mensaje de error (p. ej. si
        # `config` llega como string en vez de objeto, "input_value=" repite la
        # URL completa). Si esa URL es rtsp://user:pass@host, la contraseña sale
        # en claro en el detail del 422. redact_rtsp_credentials es la misma
        # función que ya protege el sidecar y el stderr de ffmpeg.
        raise HTTPException(
            status_code=422, detail=redact_rtsp_credentials(str(exc))
        ) from exc

    ocupante = await check_media_plane_free(request.app.state.backend)
    if ocupante is not None:
        raise HTTPException(
            status_code=409,
            detail=f"el media-plane está ocupado por {ocupante}: grabar y correr son secuenciales",
        )

    try:
        return _manager(request).start(spec)
    except RecordingBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BasenameTaken as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("")
def stop_recording(request: Request) -> dict:
    try:
        return _manager(request).stop()
    except RecordingBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
