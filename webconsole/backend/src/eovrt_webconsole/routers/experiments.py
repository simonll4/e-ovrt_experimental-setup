"""CRUD del manifiesto paraguas experiment.manifest.v1 (Spec 44 B, tarea 2) +
disparo orquestado en background (Tarea 3) + vista de alertas y lectura del
reporte consolidado (Tarea 4)."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from eovrt_webconsole.experiment.control_backend import ServiceUnavailable, UnknownRun
from eovrt_webconsole.experiment.manifest import ExperimentManifest, load_manifest
from eovrt_webconsole.experiment.run_manager import ExperimentBusy
from eovrt_webconsole.preflight import platform_preflight
from eovrt_webconsole.manifest_writer import (
    ManifestExistsError,
    ProtectedManifestError,
    write_manifest,
    write_manifest_dir,
)
from eovrt_webconsole.experiment_deriver import DeriveError, derive_payloads
from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole import camera_store as cs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/experiments")


@router.post("/manifests", status_code=201)
async def create_manifest(
    body: dict, request: Request, overwrite: bool = Query(False)
) -> dict:
    settings = request.app.state.settings
    try:
        manifest = ExperimentManifest.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    try:
        write_manifest(
            settings.experiments_dir,
            name=manifest.slug,
            group=None,
            manifest=manifest.model_dump(mode="json"),
            overwrite=overwrite,
            protected_groups=settings.protected_groups,
        )
    except ProtectedManifestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManifestExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("create_manifest: escrito slug=%s (overwrite=%s)", manifest.slug, overwrite)
    return {"slug": manifest.slug}


def _iter_umbrella_manifests(experiments_dir):
    """Recorre los YAML de experiments_dir y devuelve solo los manifiestos paraguas
    validos (schema_version: experiment.manifest.v1); tolera/salta los single-plane
    viejos y cualquier YAML que no parsee o no valide."""
    if not experiments_dir.is_dir():
        return
    for path in sorted(experiments_dir.rglob("*.yaml")):
        try:
            manifest = load_manifest(path)
        except (ValidationError, ValueError, OSError, yaml.YAMLError):
            continue
        yield manifest


@router.get("/manifests")
async def list_manifests(request: Request) -> list[dict]:
    settings = request.app.state.settings
    return [
        {
            "slug": manifest.slug,
            "experiment_id": manifest.experiment_id,
            "sequencing": manifest.sequencing,
            "runs": sorted(manifest.runs.keys()),
        }
        for manifest in _iter_umbrella_manifests(settings.experiments_dir)
    ]


@router.get("/manifests/{slug}")
async def get_manifest(slug: str, request: Request) -> dict:
    settings = request.app.state.settings
    for manifest in _iter_umbrella_manifests(settings.experiments_dir):
        if manifest.slug == slug:
            return manifest.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Manifiesto paraguas desconocido: {slug}")


def _load_source_payloads(slug: str, settings) -> tuple[ExperimentManifest, dict, dict]:
    """Resuelve el manifiesto paraguas `slug` y lee sus payloads media/control.

    Compartido por `derive` y `derive-defaults`: los dos parten exactamente del
    mismo estado del fuente, así que el formulario precarga lo que el derive va
    a leer — no dos lecturas que puedan desincronizarse.
    """
    source = None
    for manifest in _iter_umbrella_manifests(settings.experiments_dir):
        if manifest.slug == slug:
            source = manifest
            break
    if source is None:
        raise HTTPException(status_code=404, detail=f"Manifiesto paraguas desconocido: {slug}")

    for plane in ("media", "control"):
        if plane not in source.runs:
            raise HTTPException(
                status_code=422, detail=f"El manifiesto {slug!r} no declara runs.{plane}"
            )

    try:
        source_media = yaml.safe_load(Path(source.runs["media"].config).read_text(encoding="utf-8"))
        source_control = yaml.safe_load(
            Path(source.runs["control"].config).read_text(encoding="utf-8")
        )
    except OSError as exc:
        raise HTTPException(
            status_code=422, detail=f"No se pudieron leer los payloads de {slug!r}: {exc}"
        ) from exc
    return source, source_media or {}, source_control or {}


@router.get("/manifests/{slug}/derive-defaults")
async def get_derive_defaults(slug: str, request: Request) -> dict:
    """Valores del manifiesto fuente para precargar el formulario de derivación.

    Devuelve exactamente las claves que el formulario ofrece como `overrides`
    (mapeo 1:1, sin traducción que se pueda desincronizar con el endpoint de
    derive).

    NUNCA devuelve la url de la fuente: este payload va al browser y los presets
    RTSP llevan credenciales en claro (`cameras/` está gitignoreado justamente
    por eso). `camera_id` se resuelve matcheando plugin+url contra el catálogo de
    /api/cameras y, si no matchea, sale `null` — la url cruda no se expone en
    ningún caso.
    """
    settings = request.app.state.settings
    _, media, control = _load_source_payloads(slug, settings)

    ingest = media.get("ingest") or {}
    config = ingest.get("config") or {}
    run = media.get("run") or {}
    patterns = control.get("patterns") or {}

    camera_id = None
    for camera in cs.list_cameras(settings.cameras_dir):
        if camera.get("plugin") == ingest.get("plugin") and (
            (camera.get("config") or {}).get("url") == config.get("url")
        ):
            camera_id = camera.get("id")
            break

    return {
        "warmup_frames": config.get("warmup_frames"),
        "fps": config.get("fps"),
        "camera_id": camera_id,
        "prompt_set_id": ((media.get("prompts") or {}).get("set_inline") or {}).get("id"),
        "stride": run.get("stride"),
        "max_units": run.get("max_units"),
        "pattern_set_file": patterns.get("file"),
        "pattern_active_ids": patterns.get("active_ids"),
    }


@router.post("/manifests/{slug}/derive", status_code=201)
async def derive_manifest(slug: str, body: dict, request: Request) -> dict:
    """Crea un manifiesto paraguas nuevo a partir de otro, con overrides.

    El manifiesto fuente no se toca: el slug sigue siendo la unidad reproducible
    (spec 2026-07-25 §Decisión de fondo).
    """
    settings = request.app.state.settings
    source, source_media, source_control = _load_source_payloads(slug, settings)

    new_slug = (body.get("new_slug") or "").strip()
    overrides = body.get("overrides") or {}
    changes = body.get("changes")

    camera = None
    if "camera_id" in overrides:
        try:
            camera = cs.get_camera(settings.cameras_dir, overrides["camera_id"])
        except cs.CameraStoreError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt_set = None
    if "prompt_set_id" in overrides:
        prompt_set = get_prompt_set(settings.prompts_dir, overrides["prompt_set_id"])
        if prompt_set is None:
            raise HTTPException(
                status_code=400,
                detail=f"Prompt set desconocido: {overrides['prompt_set_id']!r}",
            )

    pattern_file = overrides.get("pattern_set_file")
    if pattern_file:
        # Absoluta ANTES que existente (spec §Validación 6, ADR-009): una ruta
        # relativa que existe respecto del cwd del BFF pasaría el is_file() y se
        # escribiría relativa en control.yaml, pero la resuelve el CONTROL-PLANE
        # contra su propio cwd — otro proceso, otro directorio de trabajo:
        # termina cargando otro pattern set o fallando al lanzar.
        if not Path(pattern_file).is_absolute():
            raise HTTPException(
                status_code=400,
                detail=f"pattern_set_file debe ser una ruta absoluta (ADR-009): {pattern_file}",
            )
        if not Path(pattern_file).is_file():
            raise HTTPException(
                status_code=400, detail=f"pattern_set_file no existe: {pattern_file}"
            )

    try:
        manifest_doc, media_doc, control_doc = derive_payloads(
            source_manifest=source.model_dump(mode="json"),
            source_media=source_media,
            source_control=source_control,
            new_slug=new_slug,
            changes=changes,
            overrides=overrides,
            target_dir=settings.experiments_dir / new_slug,
            camera=camera,
            prompt_set=prompt_set,
        )
    except DeriveError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        ExperimentManifest.model_validate(manifest_doc)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        write_manifest_dir(
            settings.experiments_dir,
            new_slug,
            {
                "manifest.yaml": manifest_doc,
                "media.yaml": media_doc,
                "control.yaml": control_doc,
            },
            protected_groups=settings.protected_groups,
        )
    except ProtectedManifestError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ManifestExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("derive_manifest: %s -> %s (overrides=%s)", slug, new_slug, sorted(overrides))
    return {"slug": new_slug}


def _resolve_manifest_from_body(body: dict, experiments_dir: Path) -> ExperimentManifest:
    """Resuelve el manifiesto paraguas a disparar desde el body de POST /run.

    Acepta un manifiesto inline (`{"manifest": {...}}`) o, el caso comun, un
    `{"slug": "..."}` que se busca entre los manifiestos paraguas ya escritos
    en `experiments_dir` (reusa `_iter_umbrella_manifests`, la misma lectura
    tolerante que usan las rutas de listado/get de la Tarea 2)."""
    inline = body.get("manifest")
    if inline is not None:
        try:
            return ExperimentManifest.model_validate(inline)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

    slug = body.get("slug")
    if not slug:
        raise HTTPException(status_code=422, detail="body debe incluir 'slug' o 'manifest'")
    for manifest in _iter_umbrella_manifests(experiments_dir):
        if manifest.slug == slug:
            return manifest
    raise HTTPException(status_code=422, detail=f"Manifiesto paraguas desconocido: {slug}")


@router.post("/run", status_code=202)
async def run_experiment_route(body: dict, request: Request) -> dict:
    settings = request.app.state.settings
    manager = request.app.state.experiment_manager

    manifest = _resolve_manifest_from_body(body, settings.experiments_dir)

    # Gate de preflight (sincrónico, antes del task 202): todo experimento usa
    # ambos planos — live los necesita a la vez (control se suscribe al bus
    # ANTES de disparar media), y replay los encadena. Si algo falta, el
    # operador se entera ACA con un 503 explicable, no polleando un
    # experimento que nació muerto dentro del runner en background.
    status = await platform_preflight(request.app)
    if not status["ready"]:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Plataforma no lista: " + "; ".join(status["blockers"]),
                "preflight": status,
            },
        )

    try:
        experiment_id = manager.start(
            manifest,
            media_backend=request.app.state.backend,
            control_backend=request.app.state.control_backend,
            now=datetime.now(timezone.utc),
        )
    except ExperimentBusy as exc:
        # Mismo shape que RunBusy en routers/runs.py: detail + el id activo como
        # clave hermana (no anidado bajo detail).
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc), "active_experiment_id": exc.active_experiment_id},
        )
    logger.info("run_experiment_route: disparado experiment_id=%s", experiment_id)
    return {"experiment_id": experiment_id}


@router.get("/current")
async def get_current_experiment(request: Request) -> dict:
    manager = request.app.state.experiment_manager
    state = manager.current()
    if state is None:
        raise HTTPException(status_code=404, detail="No hay experimento activo")
    return state


# Guarda contra path traversal (hallazgo de seguridad, Tarea 4 revision): el
# experiment_id viaja como segmento de URL y _resolve_consolidated_dir lo usa
# para armar un path de filesystem. Un cliente no-browser puede mandar ".."
# percent-encoded (%2e%2e); el server ASGI lo decodifica ANTES de que
# Starlette matchee la ruta, asi que ".." llega tal cual al handler y
# "runs/<experiment_id>" se resuelve un nivel afuera de runs/. No exigimos el
# formato exacto de generate_experiment_id (exp_<ts>_<slug>) porque
# ExperimentManifest.experiment_id permite inyectar un id a mano y varios
# tests usan ids simples ("no_existe"); en cambio exigimos que sea un
# componente de path de un solo nivel, sin ".." ni separadores.
_SAFE_EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _is_safe_experiment_id(experiment_id: str) -> bool:
    if not experiment_id or experiment_id.startswith(".") or ".." in experiment_id:
        return False
    return bool(_SAFE_EXPERIMENT_ID_RE.fullmatch(experiment_id))


@router.get("/{experiment_id}/alerts")
async def get_experiment_alerts(experiment_id: str, request: Request) -> list[dict]:
    """Proxya GET /api/runs/{control_run_id}/alerts del control-plane.

    Resuelve el control_run_id desde el resultado guardado en el manager
    (ExperimentResult.control_run_id, vacio si el media fallo antes de
    disparar el control). Sin control_run_id no hay nada que proxyar: 404
    (no se distingue de "experimento desconocido", mismo shape de error).

    Esta ruta solo usa experiment_id como clave de dict (manager.get), nunca
    para armar un path, pero se valida igual por consistencia con /report."""
    if not _is_safe_experiment_id(experiment_id):
        raise HTTPException(status_code=404, detail=f"Experimento desconocido: {experiment_id}")
    manager = request.app.state.experiment_manager
    state = manager.get(experiment_id)
    control_run_id = state.get("control_run_id") if state else None
    if not control_run_id:
        raise HTTPException(
            status_code=404,
            detail=f"Sin control_run_id para el experimento: {experiment_id}",
        )
    try:
        return await request.app.state.control_backend.alerts(control_run_id)
    except UnknownRun as exc:
        raise HTTPException(
            status_code=404, detail=f"Run de control desconocido: {control_run_id}"
        ) from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _resolve_consolidated_dir(experiment_id: str, request: Request) -> Path:
    """Resuelve el dir consolidado de un experimento (ADR-014 layout).

    Preferencia: el `consolidated_dir` que dejo `run_experiment` en el estado
    del manager (post-run exitoso). Si el manager no tiene ese estado (p.ej.
    el proceso se reinicio, o el consolidado se armo fuera del disparo
    orquestado de esta tarea), cae a la convencion `<repo_root>/runs/<id>`
    (mismo layout que `_default_dest_root` en runner.py).

    Path traversal (hallazgo de seguridad): `experiment_id` es input crudo de
    cliente. Dos guardas antes de devolver un path:
    1. formato: `_is_safe_experiment_id` rechaza ".." / separadores / id vacio
       ANTES de tocar el filesystem (404, mismo shape que "desconocido").
    2. contencion: el path final -- venga de la convencion o del manager --
       debe quedar dentro de `<repo_root>/runs` una vez resuelto
       (`Path.resolve()` + `is_relative_to`); si no, 404. Defensa en
       profundidad por si la guarda 1 tuviera un hueco."""
    if not _is_safe_experiment_id(experiment_id):
        raise HTTPException(status_code=404, detail=f"Experimento desconocido: {experiment_id}")

    manager = request.app.state.experiment_manager
    settings = request.app.state.settings
    state = manager.get(experiment_id)
    if state and state.get("consolidated_dir"):
        candidate = Path(state["consolidated_dir"])
    else:
        candidate = settings.repo_root / "runs" / experiment_id

    base = (settings.repo_root / "runs").resolve()
    if not candidate.resolve().is_relative_to(base):
        raise HTTPException(status_code=404, detail=f"Experimento desconocido: {experiment_id}")
    return candidate


def _is_non_temporal(report: dict[str, Any]) -> bool:
    """Deteccion ADR-013 de fuente no temporal (dataset de imagenes).

    Chequeo primario: `temporalidad.source_clock == "none"`. Fallback (por si
    la seccion `temporalidad` no esta presente): buscar la causa
    `non_temporal_source` en la metrica `t_capture->alert` de `resultados`."""
    temporalidad = report.get("temporalidad") or {}
    if temporalidad.get("source_clock") == "none":
        return True
    for metric in report.get("resultados") or []:
        if metric.get("name") == "t_capture->alert" and metric.get("cause") == "non_temporal_source":
            return True
    return False


@router.get("/{experiment_id}/report")
async def get_experiment_report(experiment_id: str, request: Request) -> dict:
    """Lee `<consolidated_dir>/report/report.json` (ver consolidation.py/report.py).

    404 si no hay dir consolidado resoluble o si el report.json todavia no se
    genero (p.ej. la corrida no termino, o el paso post-run protegido fallo)."""
    consolidated_dir = _resolve_consolidated_dir(experiment_id, request)
    report_path = consolidated_dir / "report" / "report.json"
    if not report_path.is_file():
        raise HTTPException(
            status_code=404, detail=f"Reporte consolidado no encontrado para: {experiment_id}"
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["non_temporal"] = _is_non_temporal(report)
    return report


# Ruta parametrica generica: DEBE quedar registrada al final del router. Con el
# mismo prefix ("/api/experiments") y metodo (GET) que "/manifests" y
# "/current", Starlette matchea las rutas en el orden en que se registraron
# (no por especificidad); si "/{experiment_id}" se registrara antes, un GET a
# /api/experiments/manifests o /api/experiments/current seria capturado aca
# como si "manifests"/"current" fueran un experiment_id, en vez de llegar a
# las rutas especificas de arriba.
@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str, request: Request) -> dict:
    manager = request.app.state.experiment_manager
    state = manager.get(experiment_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Experimento desconocido: {experiment_id}")
    return state
