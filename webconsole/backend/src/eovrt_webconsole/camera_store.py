"""Presets de cámara para la ventana de preview. Un YAML por preset en cameras/.

La consola no valida la config de fuente: el media-plane es el validador final
(mismo principio que el prompt store).
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

_ID_RE = re.compile(r"^[a-z0-9_-]+$")


class CameraStoreError(Exception):
    pass


class CameraNotFound(CameraStoreError):
    pass


class CameraExists(CameraStoreError):
    pass


class CameraInvalid(CameraStoreError):
    def __init__(self, errors: list) -> None:
        super().__init__("preset de cámara inválido")
        self.errors = errors


class CameraPresetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    plugin: str
    config: dict = {}

    @field_validator("id")
    @classmethod
    def _id_valido(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError("id debe matchear ^[a-z0-9_-]+$")
        return v


def _path(cameras_dir: Path, camera_id: str) -> Path:
    if not _ID_RE.match(camera_id):
        raise CameraNotFound(camera_id)
    return cameras_dir / f"{camera_id}.yaml"


def _validate(payload: dict) -> CameraPresetModel:
    try:
        return CameraPresetModel.model_validate(payload)
    except ValidationError as exc:
        raise CameraInvalid(exc.errors()) from exc


def _write(path: Path, preset: CameraPresetModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"camera": preset.model_dump()}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _read(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CameraInvalid([{"msg": f"YAML ilegible: {path.name}"}]) from exc
    return data.get("camera", {})


def list_cameras(cameras_dir: Path) -> list[dict]:
    if not cameras_dir.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(cameras_dir.glob("*.yaml")):
        try:
            out.append(_read(path))
        except CameraInvalid:
            continue  # archivo ilegible: se omite del listado
    return out


def get_camera(cameras_dir: Path, camera_id: str) -> dict:
    path = _path(cameras_dir, camera_id)
    if not path.exists():
        raise CameraNotFound(camera_id)
    return _read(path)


def create_camera(cameras_dir: Path, payload: dict) -> dict:
    preset = _validate(payload)
    path = _path(cameras_dir, preset.id)
    if path.exists():
        raise CameraExists(preset.id)
    _write(path, preset)
    return preset.model_dump()


def update_camera(cameras_dir: Path, camera_id: str, payload: dict) -> dict:
    if not _path(cameras_dir, camera_id).exists():
        raise CameraNotFound(camera_id)
    preset = _validate({**payload, "id": camera_id})
    _write(_path(cameras_dir, camera_id), preset)
    return preset.model_dump()


def delete_camera(cameras_dir: Path, camera_id: str) -> None:
    path = _path(cameras_dir, camera_id)
    if not path.exists():
        raise CameraNotFound(camera_id)
    path.unlink()
