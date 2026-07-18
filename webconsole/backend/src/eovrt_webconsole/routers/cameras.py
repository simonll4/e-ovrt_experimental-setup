"""CRUD de presets de cámara (cameras/*.yaml)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder

from eovrt_webconsole import camera_store as cs

router = APIRouter(prefix="/api/cameras")


def _cameras_dir(request: Request):
    return request.app.state.settings.cameras_dir


def _raise(exc: cs.CameraStoreError) -> None:
    if isinstance(exc, cs.CameraNotFound):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, cs.CameraExists):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, cs.CameraInvalid):
        raise HTTPException(
            status_code=422, detail=jsonable_encoder(exc.errors, custom_encoder={Exception: str})
        ) from exc
    raise exc


@router.get("")
def list_cameras(request: Request) -> list[dict]:
    return cs.list_cameras(_cameras_dir(request))


@router.get("/{camera_id}")
def get_camera(request: Request, camera_id: str) -> dict:
    try:
        return cs.get_camera(_cameras_dir(request), camera_id)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.post("", status_code=201)
def create_camera(request: Request, payload: dict) -> dict:
    try:
        return cs.create_camera(_cameras_dir(request), payload)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.put("/{camera_id}")
def update_camera(request: Request, camera_id: str, payload: dict) -> dict:
    try:
        return cs.update_camera(_cameras_dir(request), camera_id, payload)
    except cs.CameraStoreError as exc:
        _raise(exc)


@router.delete("/{camera_id}", status_code=204)
def delete_camera(request: Request, camera_id: str) -> None:
    try:
        cs.delete_camera(_cameras_dir(request), camera_id)
    except cs.CameraStoreError as exc:
        _raise(exc)
