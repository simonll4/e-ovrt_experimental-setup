"""Runner reproducible del experimento (ADR-004, spec 44 SS3).

Lee el manifiesto paraguas, genera/toma el experiment_id, y dispara los dos
planos por HTTP en el orden correcto. Cubre las dos ramas:
- DBE-replay (`runs.control.mode == "replay"`): media-plane primero, esperar
  a que termine, control-plane despues en modo replay sobre el
  detections.jsonl del run de media.
- live (`runs.control.mode == "live"`): control-plane primero -- su 201
  implica que el BusSource ya esta suscripto (PUB/SUB pierde lo publicado
  antes de la suscripcion) -- recien despues se dispara el media-plane con
  el bus habilitado.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml
from pydantic import BaseModel

from eovrt_webconsole.experiment.consolidation import consolidate_experiment
from eovrt_webconsole.experiment.manifest import ExperimentManifest, generate_experiment_id
from eovrt_webconsole.experiment.report import write_report

logger = logging.getLogger(__name__)

# Estados terminales de un run en cualquiera de los dos planos.
TERMINAL_STATUSES = frozenset({"succeeded", "failed", "error"})

LoadConfig = Callable[[str], dict]
# Resuelve el directorio runs/<run_id>/ de un plano ("media" | "control") a
# partir del run_id devuelto por ese plano. Inyectable para tests (dirs
# sinteticos); el default de produccion es la convencion de workspace hermano
# (ver CLAUDE.md raiz: los planos son repos hermanos de este).
ResolveRunDir = Callable[[str, str], Path]


class ExperimentTimeout(Exception):
    """El polling de un run supero timeout_s sin llegar a un estado terminal."""


class MediaBackendProtocol(Protocol):
    async def launch(self, run_request: dict) -> str: ...
    async def status(self, run_id: str) -> dict: ...


class ControlBackendProtocol(Protocol):
    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str: ...
    async def status(self, control_run_id: str) -> dict: ...
    async def current(self) -> dict: ...


class ExperimentResult(BaseModel):
    """Resultado consolidado de las dos corridas (media + control)."""

    experiment_id: str
    media_run_id: str | None
    control_run_id: str | None
    media_status: str | None
    control_status: str | None
    ok: bool
    # Paso final post-run (Tarea 4): set solo si ambas corridas terminaron OK
    # y la consolidacion + el reporte se generaron sin error.
    consolidated_dir: str | None = None
    report_path: str | None = None


def _default_load_config(config_path: str) -> dict:
    """Carga por defecto: yaml.safe_load del path tal cual viene del manifiesto.

    Para uso real (manifiesto en disco) el llamador puede inyectar un
    load_config que resuelva rutas relativas al directorio del manifiesto.
    """
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


def _repo_root() -> Path:
    """Raiz de e-ovrt_experimental-setup, derivada de la ubicacion de este archivo."""
    # runner.py -> experiment -> eovrt_webconsole -> src -> backend -> webconsole -> repo_root
    return Path(__file__).resolve().parents[5]


def _default_resolve_run_dir(plane: str, run_id: str) -> Path:
    """Convencion por defecto de layout de workspace (ver CLAUDE.md raiz):
    los planos son repos hermanos de e-ovrt_experimental-setup, y cada uno
    persiste sus corridas en `runs/<run_id>/` dentro de su propio repo."""
    return _repo_root().parent / f"e-ovrt_{plane}-plane" / "runs" / run_id


def _default_dest_root() -> Path:
    """dest_root por defecto para la consolidacion: `<repo_root>/runs`."""
    return _repo_root() / "runs"


async def _poll_until_terminal(
    get_status: Callable[[str], Any],
    run_id: str,
    *,
    poll_interval_s: float,
    timeout_s: float,
) -> dict:
    """Poll de un run hasta que su status sea terminal, con timeout."""
    deadline = time.monotonic() + timeout_s
    while True:
        summary = await get_status(run_id)
        if summary.get("status") in TERMINAL_STATUSES:
            return summary
        if time.monotonic() > deadline:
            raise ExperimentTimeout(
                f"run {run_id} no llego a un estado terminal en {timeout_s}s "
                f"(ultimo status={summary.get('status')!r})"
            )
        if poll_interval_s > 0:
            await asyncio.sleep(poll_interval_s)


# Regla de reconciliacion entre `sequencing` y `runs.control.mode` (nota de
# revision de la Tarea 3): la fuente de verdad OPERATIVA para el dispatch es
# `runs.control.mode` -- es el campo que decide que llamadas HTTP hace el
# runner y en que orden (ver run_experiment). `sequencing` es un campo
# declarativo del manifiesto que debe coincidir con esa decision; no se
# resuelve en silencio a favor de uno de los dos si difieren, se rechaza el
# manifiesto con un error claro.
_SEQUENCING_FOR_CONTROL_MODE = {"live": "control_first", "replay": "media_first"}


def _validate_sequencing(sequencing: str, control_mode: str) -> None:
    """Valida que `sequencing` no contradiga `runs.control.mode`."""
    expected = _SEQUENCING_FOR_CONTROL_MODE.get(control_mode)
    if expected is not None and sequencing != expected:
        raise ValueError(
            f"sequencing '{sequencing}' contradice runs.control.mode '{control_mode}' "
            f"(se esperaba '{expected}')"
        )


def _validate_planes_present(runs: dict[str, Any]) -> None:
    """Valida que `manifest.runs` tenga las dos claves de plano requeridas.

    Sin este chequeo, indexar `runs["media"]` / `runs["control"]` cuando falta
    una clave levanta un `KeyError` crudo antes de cualquier llamada HTTP. Se
    valida antes de tocar ningun backend para dar un error claro (que plano
    falta) en vez de un traceback opaco.
    """
    faltantes = [plano for plano in ("media", "control") if plano not in runs]
    if faltantes:
        raise ValueError(
            f"manifiesto invalido: falta(n) el/los plano(s) {faltantes} en manifest.runs"
        )


def _detections_path_for(media_run_id: str, media_summary: dict) -> str:
    """Deriva la ruta del detections.jsonl del run de media.

    Preferencia: si el summary del media-plane declara detections_path lo
    usamos tal cual; si no, aplicamos la convencion runs/<run_id>/detections.jsonl.
    """
    nested = media_summary.get("summary") or {}
    return (
        media_summary.get("detections_path")
        or nested.get("detections_path")
        or f"runs/{media_run_id}/detections.jsonl"
    )


async def run_experiment(
    manifest: ExperimentManifest,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    now: datetime,
    poll_interval_s: float = 0.0,
    timeout_s: float = 300.0,
    load_config: LoadConfig | None = None,
    resolve_run_dir: ResolveRunDir | None = None,
    dest_root: Path | str | None = None,
) -> ExperimentResult:
    """Orquesta el experimento paraguas segun el modo del control-plane.

    DBE-replay (`runs.control.mode == "replay"`): media-plane primero, se
    espera a que termine, y recien entonces se dispara el control-plane en
    modo replay apuntando al detections.jsonl del run de media.

    live (`runs.control.mode == "live"`): control-plane primero -- su 201
    implica que el BusSource ya esta suscripto -- y recien entonces se
    dispara el media-plane con el bus habilitado. Ver `_run_live`.

    `manifest.sequencing` se valida contra `runs.control.mode` antes de
    dispatchear (regla en `_validate_sequencing`): si contradicen se rechaza
    el manifiesto en vez de arrancar una secuencia ambigua.

    Paso final (Tarea 4, post-run): si ambas corridas terminan OK se invoca
    `consolidate_experiment` + `write_report` (`manifest.report` es siempre
    un dict presente en el manifiesto -- default `{}` -- asi que su sola
    presencia se interpreta como opt-in y el paso corre siempre que el
    resultado sea exitoso; no hay hoy un flag para desactivarlo). Es un paso
    protegido (`_consolidate_and_report`): si falla no tumba la corrida.
    """
    experiment_id = manifest.experiment_id or generate_experiment_id(manifest.slug, now)
    loader = load_config or _default_load_config
    resolver = resolve_run_dir or _default_resolve_run_dir
    resolved_dest_root = Path(dest_root) if dest_root is not None else _default_dest_root()

    _validate_planes_present(manifest.runs)
    control_run = manifest.runs["control"]
    _validate_sequencing(manifest.sequencing, control_run.mode)

    if control_run.mode == "replay":
        result = await _run_dbe_replay(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    elif control_run.mode == "live":
        result = await _run_live(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    else:
        raise NotImplementedError(f"modo de control '{control_run.mode}' no soportado")

    if not result.ok:
        # Si cualquiera de las dos corridas fallo, no hay artefactos
        # completos que consolidar: se deja consolidated_dir/report_path en None.
        return result

    manifest_effective = manifest.model_dump(mode="json")
    manifest_effective["experiment_id"] = experiment_id

    return await _consolidate_and_report(
        result,
        manifest_effective=manifest_effective,
        resolve_run_dir=resolver,
        dest_root=resolved_dest_root,
    )


async def _consolidate_and_report(
    result: ExperimentResult,
    *,
    manifest_effective: dict,
    resolve_run_dir: ResolveRunDir,
    dest_root: Path,
) -> ExperimentResult:
    """Paso final protegido: consolida + reporta un experimento ya exitoso.

    No debe tumbar la corrida si la consolidacion o el reporte fallan (dirs
    no resolubles, IO rota, etc.): se logea una advertencia y se devuelve el
    `result` original (con consolidated_dir/report_path en None), preservando
    `result.ok` tal cual refleja la corrida real.
    """
    try:
        media_run_dir = resolve_run_dir("media", result.media_run_id)
        control_run_dir = resolve_run_dir("control", result.control_run_id)
        consolidated_dir = consolidate_experiment(
            result.experiment_id,
            media_run_dir=media_run_dir,
            control_run_dir=control_run_dir,
            manifest_effective=manifest_effective,
            dest_root=dest_root,
        )
        report_json_path, _report_md_path = write_report(consolidated_dir)
    except Exception:
        logger.warning(
            "post-run: fallo la consolidacion/reporte del experimento %s "
            "(no afecta el resultado de la corrida)",
            result.experiment_id,
            exc_info=True,
        )
        return result

    return result.model_copy(
        update={
            "consolidated_dir": str(consolidated_dir),
            "report_path": str(report_json_path),
        }
    )


async def _run_dbe_replay(
    manifest: ExperimentManifest,
    experiment_id: str,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    poll_interval_s: float,
    timeout_s: float,
    loader: LoadConfig,
) -> ExperimentResult:
    media_run = manifest.runs["media"]
    control_run = manifest.runs["control"]

    media_config = dict(loader(media_run.config))
    media_config["experiment_id"] = experiment_id

    media_run_id = await media_backend.launch(media_config)
    media_summary = await _poll_until_terminal(
        media_backend.status, media_run_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s
    )
    media_status = media_summary.get("status")

    if media_status != "succeeded":
        # Falla temprana: nunca se dispara el control-plane.
        return ExperimentResult(
            experiment_id=experiment_id,
            media_run_id=media_run_id,
            control_run_id=None,
            media_status=media_status,
            control_status=None,
            ok=False,
        )

    detections_path = _detections_path_for(media_run_id, media_summary)
    control_config = dict(loader(control_run.config))
    control_config["experiment_id"] = experiment_id
    control_config["input"] = {"type": "replay", "path": detections_path}

    control_run_id = await control_backend.launch(
        control_config, mode="replay", experiment_id=experiment_id
    )
    control_summary = await _poll_until_terminal(
        control_backend.status,
        control_run_id,
        poll_interval_s=poll_interval_s,
        timeout_s=timeout_s,
    )
    control_status = control_summary.get("status")

    return ExperimentResult(
        experiment_id=experiment_id,
        media_run_id=media_run_id,
        control_run_id=control_run_id,
        media_status=media_status,
        control_status=control_status,
        ok=media_status == "succeeded" and control_status == "succeeded",
    )


class SubscriptionNotConfirmed(Exception):
    """El control-plane no confirmo subscribed=True tras el 201 de live.

    Invariante no negociable (doc 50 SS5.1): PUB/SUB pierde lo publicado
    antes de la suscripcion, asi que el runner NO debe disparar el media
    si esto no se puede confirmar.
    """


async def _run_live(
    manifest: ExperimentManifest,
    experiment_id: str,
    *,
    media_backend: MediaBackendProtocol,
    control_backend: ControlBackendProtocol,
    poll_interval_s: float,
    timeout_s: float,
    loader: LoadConfig,
) -> ExperimentResult:
    """Rama live: control-plane primero, media-plane recien despues.

    Orden no negociable (spec 40 SS3.2 / doc 50 SS5.1): POST al control-plane
    en mode=live primero -- su 201 implica que el BusSource ya esta
    suscripto -- y solo entonces POST al media-plane con bus.enabled=true.
    El control cierra 1:1 con el media (run_finished); se hace poll de
    ambos hasta un estado terminal.
    """
    media_run = manifest.runs["media"]
    control_run = manifest.runs["control"]

    control_config = dict(loader(control_run.config))
    control_config["experiment_id"] = experiment_id
    control_config["input"] = {"type": "bus"}

    control_run_id = await control_backend.launch(
        control_config, mode="live", experiment_id=experiment_id
    )

    # Confirmacion explicita de la invariante antes de tocar el media: el
    # 201 ya implica suscripto, pero lo verificamos con current() en vez de
    # confiar ciegamente en el codigo de estado.
    current = await control_backend.current()
    if not current.get("subscribed"):
        raise SubscriptionNotConfirmed(
            f"control-plane run {control_run_id} no reporta subscribed=True tras el 201; "
            "se aborta el disparo del media (invariante de orden violada)"
        )

    media_config = dict(loader(media_run.config))
    media_config["experiment_id"] = experiment_id
    media_config["bus"] = {"enabled": True}

    media_run_id = await media_backend.launch(media_config)

    media_summary = await _poll_until_terminal(
        media_backend.status, media_run_id, poll_interval_s=poll_interval_s, timeout_s=timeout_s
    )
    control_summary = await _poll_until_terminal(
        control_backend.status,
        control_run_id,
        poll_interval_s=poll_interval_s,
        timeout_s=timeout_s,
    )
    media_status = media_summary.get("status")
    control_status = control_summary.get("status")

    return ExperimentResult(
        experiment_id=experiment_id,
        media_run_id=media_run_id,
        control_run_id=control_run_id,
        media_status=media_status,
        control_status=control_status,
        ok=media_status == "succeeded" and control_status == "succeeded",
    )
