"""Traducción manifiesto ↔ composición ↔ run request (dueño único, Spec B §5.3/§5.4).

La composición es el contrato form/BFF. El run request es el contrato del servicio
(Spec A §3.1 implementada): {ingest:{plugin,config}, prompts:{set_inline,active_ids},
run:{stride,max_units,save_annotated_video,save_previews,name}} — sin sección model.
La ref de dataset viaja como ingest.config.dataset (el servicio la retraduce a source.ref).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eovrt_webconsole.repo_catalog import get_prompt_set

_SOURCE_TYPE_TO_PLUGIN = {"image_folder": "image_folder", "video_file": "video_file",
                          "video": "video_file", "video_frame": "video_file"}
_PLUGIN_TO_SOURCE_TYPE = {"image_folder": "image_folder", "video_file": "video_file"}


class UnknownPromptSetError(ValueError):
    """El set_id no existe en prompts/ del repo."""


class IngestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plugin: str
    config: dict[str, Any] = Field(default_factory=dict)
    # Tipo `source.type` original del manifiesto (video/video_frame/video_file, …).
    # Varios tipos mapean a un mismo plugin, así que sin esto el round-trip
    # manifiesto→composición→manifiesto colapsa el string. Interno del BFF: NO
    # viaja al servicio (composition_to_run_request solo manda plugin+config).
    source_type: str | None = None


class PromptsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    set_id: str
    active_ids: list[str] | None = None


class RunParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stride: int | None = None
    max_units: int | None = None
    save_annotated_video: bool = False
    save_previews: bool = True
    name: str | None = None


class Composition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingest: IngestSpec
    prompts: PromptsSpec
    run: RunParams = Field(default_factory=RunParams)
    manifest_model_ref: str | None = None  # policy §5.4: bloqueo si ≠ modelo del target
    confirm_target_model: bool = False


def composition_to_run_request(comp: Composition, prompts_dir: Path) -> dict[str, Any]:
    prompt_set = get_prompt_set(prompts_dir, comp.prompts.set_id)
    if prompt_set is None:
        raise UnknownPromptSetError(f"Prompt set desconocido: {comp.prompts.set_id!r}")
    run: dict[str, Any] = {
        "save_annotated_video": comp.run.save_annotated_video,
        "save_previews": comp.run.save_previews,
    }
    if comp.run.stride is not None:
        run["stride"] = comp.run.stride
    if comp.run.max_units is not None:
        run["max_units"] = comp.run.max_units
    if comp.run.name:
        run["name"] = comp.run.name
    return {
        "ingest": {"plugin": comp.ingest.plugin, "config": dict(comp.ingest.config)},
        "prompts": {"set_inline": prompt_set, "active_ids": comp.prompts.active_ids},
        "run": run,
    }


def manifest_to_composition(manifest: dict) -> Composition:
    source = manifest.get("source") or {}
    if source.get("ref"):
        # El plugin es nominal cuando viaja una ref: el servicio resuelve el tipo real
        # desde su catálogo de datasets (run_request.py:to_raw_run_config).
        ingest = {"plugin": "image_folder", "config": {"dataset": source["ref"]}}
    elif source.get("type"):
        source_type = source["type"]
        plugin = _SOURCE_TYPE_TO_PLUGIN.get(source_type)
        if plugin is None:
            raise ValueError(f"source.type fuera del MVP: {source_type!r}")
        ingest = {
            "plugin": plugin,
            "config": {k: v for k, v in source.items() if k != "type"},
            "source_type": source_type,  # preserva el string exacto para el round-trip
        }
    else:
        raise ValueError("Manifiesto sin source.ref ni source.type")
    prompts = manifest.get("prompts") or {}
    if not prompts.get("ref"):
        raise ValueError("Manifiesto sin prompts.ref")
    run_section = manifest.get("run") or {}
    outputs = manifest.get("outputs") or {}
    return Composition(
        ingest=ingest,
        prompts={"set_id": prompts["ref"], "active_ids": prompts.get("active_ids")},
        run={
            "stride": (manifest.get("rate_control") or {}).get("stride"),
            "max_units": run_section.get("max_units"),
            "save_annotated_video": bool(outputs.get("save_annotated_video", False)),
            "save_previews": bool(outputs.get("save_previews", True)),
            "name": run_section.get("name"),
        },
        manifest_model_ref=(manifest.get("model") or {}).get("ref"),
    )


def composition_to_manifest(comp: Composition, target_model_ref: str) -> dict[str, Any]:
    """Formato declarativo actual (source.ref / rate_control / model.ref / prompts.ref)."""
    run_block: dict[str, Any] = {"scenario": "DBE"}
    if comp.run.name:
        run_block["name"] = comp.run.name
    if comp.run.max_units is not None:
        run_block["max_units"] = comp.run.max_units
    dataset = comp.ingest.config.get("dataset")
    if dataset:
        source: dict[str, Any] = {"ref": dataset}
    else:
        # Preferir el source.type original (round-trip sin pérdida); si la
        # composición viene del formulario (sin source_type), derivarlo del plugin.
        plugin_type = comp.ingest.source_type or _PLUGIN_TO_SOURCE_TYPE.get(comp.ingest.plugin)
        if plugin_type is None:
            raise ValueError(
                f"Plugin no soportado para guardar manifiesto: {comp.ingest.plugin!r} "
                f"(soportados: {sorted(_PLUGIN_TO_SOURCE_TYPE)})"
            )
        source = {"type": plugin_type, **{k: v for k, v in comp.ingest.config.items()}}
    manifest: dict[str, Any] = {"run": run_block, "source": source}
    if comp.run.stride is not None:
        manifest["rate_control"] = {"stride": comp.run.stride}
    manifest["model"] = {"ref": comp.manifest_model_ref or target_model_ref}
    manifest["prompts"] = {"ref": comp.prompts.set_id}
    if comp.prompts.active_ids is not None:
        manifest["prompts"]["active_ids"] = comp.prompts.active_ids
    outputs: dict[str, Any] = {}
    if comp.run.save_annotated_video:
        outputs["save_annotated_video"] = True
    if comp.run.save_previews is False:
        outputs["save_previews"] = False
    if outputs:
        manifest["outputs"] = outputs
    return manifest
