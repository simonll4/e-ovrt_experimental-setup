"""POST /api/manifests — guardar la composición como manifiesto declarativo in-repo."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from eovrt_webconsole.manifest_writer import (
    ManifestExistsError,
    ProtectedManifestError,
    write_manifest,
)
from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole.run_backend import ServiceUnavailable
from eovrt_webconsole.translation import Composition, composition_to_manifest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/manifests")


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    name: str
    group: str | None = None
    overwrite: bool = False
    composition: Composition


@router.post("", status_code=201)
async def save_manifest(body: ManifestRequest, request: Request) -> dict:
    settings = request.app.state.settings
    if get_prompt_set(settings.prompts_dir, body.composition.prompts.set_id) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt set desconocido: {body.composition.prompts.set_id!r}",
        )
    try:
        model = await request.app.state.backend.model()
    except ServiceUnavailable as exc:
        logger.warning("save_manifest: servicio inaccesible al resolver modelo: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        manifest = composition_to_manifest(body.composition, target_model_ref=model["ref"])
        path = write_manifest(
            settings.experiments_dir,
            body.name,
            body.group,
            manifest,
            overwrite=body.overwrite,
            protected_groups=settings.protected_groups,
        )
    except ProtectedManifestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManifestExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "save_manifest: escrito %s (group=%s, overwrite=%s)",
        path.relative_to(settings.experiments_dir).as_posix(),
        body.group,
        body.overwrite,
    )
    return {"path": path.relative_to(settings.experiments_dir).as_posix()}
