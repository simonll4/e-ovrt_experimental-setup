"""Catálogos: in-repo (prompts/experiments) y proxy del servicio (Task 4)."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole.repo_catalog import list_experiments, list_prompt_sets

router = APIRouter(prefix="/api/catalog")


@router.get("/prompt-sets")
def prompt_sets(request: Request) -> list[dict]:
    settings = request.app.state.settings
    return list_prompt_sets(settings.prompts_dir, settings.frozen_set_ids)


@router.get("/experiments")
def experiments(request: Request) -> list[dict]:
    return list_experiments(request.app.state.settings.experiments_dir)


async def _service_get(request: Request, path: str) -> list[dict]:
    http: httpx.AsyncClient = request.app.state.http
    try:
        response = await http.get(path)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Servicio media-plane inaccesible: {exc}") from exc
    return response.json()


@router.get("/ingest-plugins")
async def ingest_plugins(request: Request) -> list[dict]:
    settings = request.app.state.settings
    plugins = await _service_get(request, "/api/catalog/ingest-plugins")
    # mvp_enabled es policy de la CONSOLA (Spec B §6): el catálogo del servicio marca
    # rtsp como disponible, pero el MVP solo lanza fuentes acotadas.
    return [
        {**p, "mvp_enabled": p["id"] in settings.mvp_plugins and p.get("available", False)}
        for p in plugins
    ]


@router.get("/datasets")
async def datasets_proxy(request: Request) -> list[dict]:
    return await _service_get(request, "/api/catalog/datasets")
