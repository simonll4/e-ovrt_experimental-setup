"""Chequeo de ocupación del media-plane antes de grabar (doble toma, doc 59 §7)."""

from __future__ import annotations

import json
import logging

from eovrt_webconsole.run_backend import ServiceUnavailable, UnknownRun

logger = logging.getLogger(__name__)

# El media-plane hoy solo emite "running" como estado activo (run_manager.py);
# terminales reales: succeeded / failed / stopped. "starting"/"pending" se
# mantienen a propósito: sobre-incluir es seguro (a lo sumo bloquea de más y el
# operador reintenta), sub-incluir dejaría grabar sobre una corrida viva.
_RUN_ACTIVO = {"running", "starting", "pending"}


async def check_media_plane_free(backend) -> str | None:
    """None = libre. Un id de ocupante = ocupado. No se pudo preguntar = libre + warning.

    Grabar no necesita el media-plane: si está caído, o responde algo que no se
    puede interpretar (404 por una versión sin este endpoint, 200 con un cuerpo
    no-JSON), el chequeo se degrada a advertencia en vez de costar una toma. La
    exclusividad física de la OAK-D es el backstop real si alguien saltea la
    consola.
    """
    try:
        preview = await backend.preview_status()
        if preview.get("status") == "streaming":
            return f"preview:{preview.get('preview_id')}"
        for run in await backend.list_runs():
            if str(run.get("status")) in _RUN_ACTIVO:
                return f"run:{run.get('run_id')}"
    except (ServiceUnavailable, UnknownRun, json.JSONDecodeError) as exc:
        logger.warning(
            "No se pudo consultar el media-plane (%s): se graba igual, sin chequeo "
            "de doble toma",
            exc,
        )
        return None
    return None
