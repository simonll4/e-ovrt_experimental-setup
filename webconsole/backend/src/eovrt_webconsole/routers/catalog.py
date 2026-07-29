"""Catálogos: in-repo (prompts/experiments) y proxy del servicio (Task 4)."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request

from eovrt_webconsole.repo_catalog import list_experiments, list_prompt_sets

logger = logging.getLogger(__name__)

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


def _disabled_reason(plugin: dict, supported: frozenset[str]) -> str | None:
    """Por qué este origen no se puede elegir, o None si sí se puede.

    La interfaz muestra este texto en la columna "Por qué" de Catálogos y debajo
    de la fuente deshabilitada en Nueva corrida. Antes solo se podía decir "no
    soportado", que no distingue "la consola no lo ofrece" de "falta instalar un
    SDK en el motor de detección" — que es lo único accionable de los dos.
    """
    if plugin["id"] not in supported:
        return "La consola no ofrece este origen"
    if not plugin.get("available", False):
        return plugin.get("unavailable_reason") or "No disponible en el motor de detección"
    return None


@router.get("/ingest-plugins")
async def ingest_plugins(request: Request) -> list[dict]:
    settings = request.app.state.settings
    plugins = await _service_get(request, "/api/catalog/ingest-plugins")
    # `enabled` es policy de la CONSOLA: un plugin se ofrece si está soportado por la
    # consola Y disponible en el servicio (decisión 2026-07-07, rtsp habilitado).
    return [
        {
            **p,
            "enabled": p["id"] in settings.supported_plugins and p.get("available", False),
            "disabled_reason": _disabled_reason(p, settings.supported_plugins),
        }
        for p in plugins
    ]


@router.get("/datasets")
async def datasets_proxy(request: Request) -> list[dict]:
    return await _service_get(request, "/api/catalog/datasets")


@router.get("/conditions")
async def conditions(request: Request) -> list[dict]:
    """Nombres legibles de las condiciones de riesgo (CR-01, CR-02, ...).

    Viene del motor de reglas, que es donde están definidas. La consola lo usa
    para no tener que mostrar el código crudo ni mantener su propio glosario
    paralelo, que se desactualizaba en silencio.

    Si el motor de reglas no responde se devuelve vacío en vez de 502: es un
    catálogo de adorno para las etiquetas, y la pantalla degrada mostrando el
    código. Tumbar la vista entera por esto sería peor.
    """
    control = request.app.state.control_backend
    try:
        return await control.conditions()
    except Exception as exc:  # noqa: BLE001 - degradación deliberada
        logger.warning("conditions: motor de reglas inaccesible: %s", exc)
        return []
