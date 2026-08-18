"""Preflight de plataforma: estado agregado de media-plane + control-plane.

Compartido por GET /api/preflight (meta.py) y el gate de lanzamiento de
experimentos (experiments.py): una corrida en tiempo real no debe dispararse
si algún plano está caído o no listo — el fallo tiene que ser sincrónico y
explicable, no quedar enterrado en el task 202 del runner.

Los `blockers` son frases cortas en el idioma del operador: el frontend las
muestra tal cual, sin traducir códigos.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import socket
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import FastAPI

from eovrt_webconsole.experiment.manifest import ExperimentManifest
from eovrt_webconsole.experiment.runner import resolve_distribution_executable


async def _probe(http: httpx.AsyncClient) -> tuple[bool, bool]:
    """(healthy, ready) de un plano; servicio caído -> (False, False)."""
    healthy = ready = False
    try:
        healthy = (await http.get("/healthz")).status_code == 200
        ready = (await http.get("/readyz")).status_code == 200
    except httpx.HTTPError:
        pass
    return healthy, ready


def _load_distribution_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _distribution_transport_is_http() -> bool:
    """Mismo switch que `runner._resolve_distribution_caller` (ADR-020): HTTP
    es el default; `EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT=subprocess` (valor
    estricto) activa el fallback operativo por subproceso local en su lugar."""
    return os.environ.get("EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT") != "subprocess"


def _distribution_preflight_checks(manifest: ExperimentManifest, experiments_dir: Path) -> list[str]:
    blockers: list[str] = []
    distribution_run = manifest.runs.get("distribution")
    if distribution_run is None:
        return blockers

    # I3 (ADR-020): con transporte HTTP -- el default -- el distribuidor puede
    # vivir en otro host o contenedor; exigir el binario local aca tumbaria el
    # experimento antes de empezar. El chequeo equivalente para ese transporte
    # es el sondeo async a /healthz, hecho por `_distribution_http_transport_checks`
    # desde `platform_preflight`. El chequeo de binario local solo corre en el
    # fallback por subproceso (`EOVRT_CONSOLE_DISTRIBUTION_TRANSPORT=subprocess`).
    if not _distribution_transport_is_http():
        try:
            resolve_distribution_executable()
        except FileNotFoundError as exc:
            blockers.append(f"el binario eovrt-distribute no es resoluble: {exc}")
            return blockers

    config_path = Path(distribution_run.config)
    if not config_path.is_absolute():
        config_path = experiments_dir / config_path
    if not config_path.is_file():
        blockers.append(f"la configuración de distribución no existe: {config_path}")
        return blockers

    try:
        distribution_config = _load_distribution_config(config_path)
    except (OSError, yaml.YAMLError) as exc:
        blockers.append(f"error leyendo configuración de distribución: {exc}")
        return blockers

    channel = distribution_config.get("channel")
    if not isinstance(channel, dict):
        blockers.append("la configuración de distribución no tiene sección channel")
        return blockers

    mode = channel.get("mode")
    if mode != "live":
        return blockers

    host = channel.get("host")
    port = channel.get("port")
    if not isinstance(host, str) or not host:
        blockers.append("la configuración de distribución live no define channel.host")
        return blockers

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        blockers.append("la configuración de distribución live no define channel.port válido")
        return blockers

    try:
        with contextlib.closing(socket.create_connection((host, port_int), timeout=2.0)):
            pass
    except OSError as exc:
        blockers.append(f"broker MQTT inalcanzable ({host}:{port_int}): {exc}")

    return blockers


async def _distribution_http_transport_checks(distribution_service_url: str) -> list[str]:
    """Sustituto del chequeo de binario local (I3) cuando el transporte es HTTP:
    sondea `GET /healthz` contra el servicio de distribución en vez de exigir
    `eovrt-distribute` resoluble en este host."""
    blockers: list[str] = []
    try:
        async with httpx.AsyncClient(base_url=distribution_service_url, timeout=2.0) as client:
            response = await client.get("/healthz")
        if response.status_code != 200:
            blockers.append(
                "el servicio de distribución no respondió ok en /healthz "
                f"({distribution_service_url}): HTTP {response.status_code}"
            )
    except httpx.HTTPError as exc:
        blockers.append(
            f"el servicio de distribución no es alcanzable ({distribution_service_url}): {exc}"
        )
    return blockers


async def platform_preflight(app: FastAPI, manifest: ExperimentManifest | None = None) -> dict:
    settings = app.state.settings
    (media_healthy, media_ready), (control_healthy, control_ready) = await asyncio.gather(
        _probe(app.state.http), _probe(app.state.control_http)
    )

    media: dict = {
        "service_url": settings.service_url,
        "healthy": media_healthy,
        "ready": media_ready,
        "model": None,
    }
    if media_ready:
        try:
            media["model"] = (await app.state.http.get("/api/model")).json()
        except (httpx.HTTPError, ValueError):
            # ValueError cubre un body no-JSON de /api/model: el modelo es dato
            # decorativo del preflight, nunca debe convertir el gate en un 500.
            pass

    control: dict = {
        "service_url": settings.control_service_url,
        "healthy": control_healthy,
        "ready": control_ready,
    }

    blockers: list[str] = []
    if not media_healthy:
        blockers.append("el media-plane no responde")
    elif not media_ready:
        blockers.append("el media-plane no terminó de cargar el modelo")
    if not control_healthy:
        blockers.append("el control-plane no responde")
    elif not control_ready:
        blockers.append("el control-plane no está listo")

    if manifest is not None:
        blockers.extend(_distribution_preflight_checks(manifest, settings.experiments_dir))
        if manifest.runs.get("distribution") is not None and _distribution_transport_is_http():
            blockers.extend(
                await _distribution_http_transport_checks(settings.distribution_service_url)
            )

    return {"ready": not blockers, "blockers": blockers, "media": media, "control": control}
