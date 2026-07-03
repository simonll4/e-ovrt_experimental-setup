"""Validación de composiciones contra el target y el repo (Spec B §5.2)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole.run_backend import RunBackend, ServiceUnavailable
from eovrt_webconsole.settings import ConsoleSettings
from eovrt_webconsole.translation import Composition

router = APIRouter(prefix="/api/compose")


async def validate_composition(
    comp: Composition, settings: ConsoleSettings, backend: RunBackend
) -> list[dict]:
    errors: list[dict] = []

    if comp.ingest.plugin not in settings.mvp_plugins:
        errors.append({
            "field": "ingest.plugin",
            "message": f"Plugin '{comp.ingest.plugin}' fuera del MVP "
                       f"(permitidos: {sorted(settings.mvp_plugins)})",
        })

    try:
        plugins = {p["id"]: p for p in await backend.ingest_plugins()}
        datasets = {d["id"]: d for d in await backend.datasets()}
        model = await backend.model()
    except ServiceUnavailable as exc:
        errors.append({"field": "_target", "message": f"Servicio media-plane inaccesible: {exc}"})
        return errors

    plugin_entry = plugins.get(comp.ingest.plugin)
    if plugin_entry is not None and not plugin_entry.get("available", False):
        errors.append({"field": "ingest.plugin",
                       "message": f"Plugin '{comp.ingest.plugin}' no disponible en el target"})

    dataset = comp.ingest.config.get("dataset")
    if dataset:
        entry = datasets.get(dataset)
        if entry is None:
            errors.append({"field": "ingest.config.dataset",
                           "message": f"Dataset '{dataset}' no existe en el catálogo del target"})
        elif not entry.get("available", False):
            errors.append({"field": "ingest.config.dataset",
                           "message": f"Dataset '{dataset}' no disponible (path no montado)"})
    elif not comp.ingest.config.get("path"):
        errors.append({"field": "ingest.config.path",
                       "message": "Se requiere 'dataset' (catálogo) o 'path' explícito"})

    prompt_set = get_prompt_set(settings.prompts_dir, comp.prompts.set_id)
    if prompt_set is None:
        errors.append({"field": "prompts.set_id",
                       "message": f"Prompt set '{comp.prompts.set_id}' no existe en prompts/"})
    elif comp.prompts.active_ids:
        known = {c.get("id") for c in prompt_set.get("classes", [])}
        unknown = [i for i in comp.prompts.active_ids if i not in known]
        if unknown:
            errors.append({"field": "prompts.active_ids",
                           "message": f"Clases desconocidas en el set: {unknown}"})

    if comp.run.stride is not None and comp.run.stride < 1:
        errors.append({"field": "run.stride", "message": "stride debe ser >= 1"})
    if comp.run.max_units is not None and comp.run.max_units < 1:
        errors.append({"field": "run.max_units", "message": "max_units debe ser >= 1"})

    # Policy §5.4: manifiesto con model.ref ≠ modelo del target bloquea sin confirmación.
    if (
        comp.manifest_model_ref
        and comp.manifest_model_ref != model["ref"]
        and not comp.confirm_target_model
    ):
        errors.append({
            "field": "model",
            "message": f"El manifiesto declara '{comp.manifest_model_ref}' pero el target tiene "
                       f"'{model['ref']}'. Confirmá «usar el modelo del target» para lanzar.",
        })
    return errors


@router.post("/validate")
async def validate(comp: Composition, request: Request) -> dict:
    errors = await validate_composition(
        comp, request.app.state.settings, request.app.state.backend
    )
    return {"valid": not errors, "errors": errors}
