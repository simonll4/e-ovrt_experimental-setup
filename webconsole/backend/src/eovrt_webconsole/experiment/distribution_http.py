"""Cliente HTTP del servicio de distribucion (ADR-019).

Implementacion alternativa del protocolo `RunDistribution` del runner. La
implementacion por subproceso (`run_distribution`, spec 44 §B4) se CONSERVA:
ADR-018 sigue vigente y este camino se suma, no la reemplaza.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TERMINALES = {"succeeded", "failed", "cancelled"}


async def _cancel_best_effort(client: httpx.AsyncClient, run_id: str | None) -> None:
    """Avisa al servicio que abandone la corrida remota (timeout local o
    cancelacion de la task del runner). Best-effort: si el POST /cancel
    falla, se loguea y NO se propaga -- la excepcion original (timeout o
    `asyncio.CancelledError`) es la que importa y no debe taparse ni
    reemplazarse por un error de esta limpieza.

    Sin esto, el camino HTTP diverge del gemelo por subproceso
    (`_cancel_distribution_task` en runner.py, que mata el proceso hijo):
    abandonar la task local no detiene al servicio, que sigue corriendo y
    publicando MQTT de un experimento ya dado por fallado, y deja el
    `POST /api/runs` siguiente respondiendo 409 mientras tanto.
    """
    if run_id is None:
        return
    try:
        await client.post(f"/api/runs/{run_id}/cancel")
    except Exception:
        logger.warning(
            "distribution http: fallo el POST /cancel best-effort (run_id=%s)",
            run_id,
            exc_info=True,
        )


def _status_error_message(exc: httpx.HTTPStatusError) -> str:
    """Enriquece el mensaje de `raise_for_status()` (status code + URL, sin
    body) con el detalle que manda el servicio: `detail` siempre, y cualquier
    otro campo del body (p.ej. `active_run_id` en el 409 de "ya hay una
    corrida activa") -- justo lo que se necesita para distinguir "corrida
    activa" de "config invalida" sin adivinar. El body puede no ser JSON
    (proxy, 5xx generico, etc.): en ese caso el fallback es el mensaje
    original de httpx, sin intentar parsear nada mas.
    """
    message = str(exc)
    try:
        payload = exc.response.json()
    except ValueError:
        return message
    if isinstance(payload, dict) and payload:
        return f"{message} — body: {payload}"
    return message


async def run_distribution_http(
    *,
    mode: str,
    alerts_path: Path | None,
    out_dir: Path,
    config_path: str | None,
    endpoint: str | None,
    control_run_id: str | None,
    backfill_path: Path | None,
    idle_timeout_ms: float | None,
    timeout_s: float,
    base_url: str,
    poll_interval_s: float = 0.5,
) -> dict[str, Any]:
    if mode not in {"replay", "live"}:
        raise ValueError(f"modo de distribucion invalido: {mode}")
    if mode == "replay" and not alerts_path:
        raise ValueError("distribucion en replay sin alerts_path")
    if mode == "live" and not endpoint:
        raise ValueError("distribucion en live sin endpoint")

    body: dict[str, Any] = {"mode": mode, "out_dir": str(out_dir)}
    if mode == "replay":
        body["alerts_path"] = str(alerts_path)
    else:
        body["endpoint"] = endpoint
        if control_run_id:
            body["control_run_id"] = control_run_id
        if backfill_path is not None:
            body["backfill"] = str(backfill_path)
        if idle_timeout_ms is not None:
            body["idle_timeout_ms"] = idle_timeout_ms
    if config_path:
        body["config_path"] = config_path

    run_id: str | None = None
    last_status: str | None = None

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout_s) as client:
        created = await client.post("/api/runs", json=body)
        try:
            created.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # 409 (ya hay una corrida activa, con `active_run_id`) y 422
            # (config/rutas invalidas) son justo los casos donde el body
            # importa: sin el detalle, quien depure solo ve "409 Conflict".
            raise RuntimeError(_status_error_message(exc)) from exc
        run_id = created.json()["distribution_run_id"]

        async def _poll() -> dict[str, Any]:
            nonlocal last_status
            while True:
                response = await client.get(f"/api/runs/{run_id}")
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise RuntimeError(_status_error_message(exc)) from exc
                info = response.json()
                last_status = info.get("status")
                if last_status in _TERMINALES:
                    return info
                await asyncio.sleep(poll_interval_s)

        try:
            info = await asyncio.wait_for(_poll(), timeout=timeout_s)
        except (TimeoutError, asyncio.CancelledError) as exc:
            # No reusamos `_poll_until_terminal`/`ExperimentTimeout` de
            # runner.py: su vocabulario de estados terminales
            # (TERMINAL_STATUSES = succeeded/failed/error/stopped) no incluye
            # "cancelled", que es un terminal propio de este servicio. Si lo
            # reusaramos tal cual, una corrida ya "cancelled" se clasificaria
            # como "todavia corriendo" y el poll seguiria hasta agotar
            # timeout_s de nuevo, con un diagnostico enganoso (parece que
            # nunca goteo estado, cuando en realidad sí llego a un terminal,
            # solo que uno que esa funcion no reconoce). Se mantiene el loop
            # propio, pero con el mismo estandar de diagnosticabilidad que el
            # camino por subproceso (`_default_run_distribution`): log +
            # mensaje con run_id/timeout_s/ultimo status visto.
            #
            # `asyncio.CancelledError` llega aca cuando el runner abandona
            # la task local (p.ej. `_cancel_distribution_task` en runner.py,
            # invocada en 4 puntos del camino live). El gemelo por subproceso
            # mata al hijo en ese mismo teardown; el HTTP necesita el aviso
            # explicito via /cancel porque cancelar la task local no toca al
            # servicio remoto (I2).
            is_cancelled = isinstance(exc, asyncio.CancelledError)
            logger.warning(
                "distribution http %s run_id=%s %s (%ss); ultimo status=%r",
                mode,
                run_id,
                "cancelado" if is_cancelled else "timeout",
                timeout_s,
                last_status,
            )
            await _cancel_best_effort(client, run_id)
            if is_cancelled:
                raise
            raise TimeoutError(
                f"distribucion http {mode} (run_id={run_id}) no llego a un estado "
                f"terminal en {timeout_s}s (ultimo status={last_status!r})"
            ) from None

    # Sólo "succeeded" es éxito: "cancelled" NO es sinónimo de éxito, y tanto
    # "failed" como "cancelled" deben propagarse como error con el detalle de
    # `error` si el servicio lo provee.
    if info["status"] != "succeeded":
        raise RuntimeError(
            f"distribucion {info['status']}: {info.get('error') or 'sin detalle'}"
        )
    return info["summary"]
