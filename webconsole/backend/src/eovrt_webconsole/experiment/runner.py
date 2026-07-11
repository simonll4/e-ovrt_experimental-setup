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
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml
from pydantic import BaseModel

from eovrt_webconsole.experiment.manifest import ExperimentManifest, generate_experiment_id

# Estados terminales de un run en cualquiera de los dos planos.
TERMINAL_STATUSES = frozenset({"succeeded", "failed", "error"})

LoadConfig = Callable[[str], dict]


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


def _default_load_config(config_path: str) -> dict:
    """Carga por defecto: yaml.safe_load del path tal cual viene del manifiesto.

    Para uso real (manifiesto en disco) el llamador puede inyectar un
    load_config que resuelva rutas relativas al directorio del manifiesto.
    """
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))


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
    """
    experiment_id = manifest.experiment_id or generate_experiment_id(manifest.slug, now)
    loader = load_config or _default_load_config

    _validate_planes_present(manifest.runs)
    control_run = manifest.runs["control"]
    _validate_sequencing(manifest.sequencing, control_run.mode)

    if control_run.mode == "replay":
        return await _run_dbe_replay(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    if control_run.mode == "live":
        return await _run_live(
            manifest,
            experiment_id,
            media_backend=media_backend,
            control_backend=control_backend,
            poll_interval_s=poll_interval_s,
            timeout_s=timeout_s,
            loader=loader,
        )
    raise NotImplementedError(f"modo de control '{control_run.mode}' no soportado")


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
