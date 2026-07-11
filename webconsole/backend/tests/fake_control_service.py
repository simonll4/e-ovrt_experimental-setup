"""Replica minima de la API del control-plane (:8081) para tests del BFF.

Shapes copiados de la implementacion real (e-ovrt_control-plane, service/):
run_request.py, routers/runs.py, routers/config.py, run_manager.py.
"""
from __future__ import annotations

import itertools

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

EFFECTIVE_CONFIG = {
    "run": {"scenario": "EBE", "experiment_id": "exp-1"},
    "input": {"type": "bus"},
}


class FakeControlState:
    def __init__(self) -> None:
        self.ready = True
        self.active_run_id: str | None = None
        self.subscribed: bool = False
        self.reject_launch: bool = False
        # Fuerza subscribed=False incluso en un launch live (default False:
        # preserva el comportamiento previo subscribed = mode == "live").
        # Sirve para ejercitar el guard SubscriptionNotConfirmed del runner
        # sin tocar el codigo de estado HTTP (201 se devuelve igual).
        self.force_unsubscribed: bool = False
        self.launched: list[dict] = []
        self.received_mode: str | None = None
        self.received_experiment_id: str | None = None
        self.alerts: dict[str, list[dict]] = {}
        self._run_ids = itertools.count(1)
        # Si se setea (p.ej. "succeeded"/"failed"), GET /api/runs/{id} para el
        # run activo reporta ese status terminal en lugar de "running". Sirve
        # para que el runner (poller) pueda ejercitarse sin un fake que
        # simule el paso del tiempo. Default None: comportamiento previo
        # (siempre "running" mientras sea el run activo).
        self.finish_status: str | None = None


def make_fake_control_service(state: FakeControlState) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        if state.ready:
            return {"status": "ready"}
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    @app.post("/api/runs", status_code=201)
    async def create_run(body: dict):
        mode = body.get("mode")
        if state.active_run_id:
            return JSONResponse(
                status_code=409,
                content={"detail": "run activo", "active_run_id": state.active_run_id},
            )
        if state.reject_launch or mode not in ("live", "replay"):
            return JSONResponse(status_code=422, content={"detail": "config rechazada"})
        control_run_id = f"control_run_{next(state._run_ids)}"
        state.launched.append(body)
        state.received_mode = mode
        state.received_experiment_id = body.get("experiment_id")
        state.active_run_id = control_run_id
        # ADR/spec: en `live`, al devolver 201 el BusSource ya existe (ya suscripto).
        state.subscribed = mode == "live" and not state.force_unsubscribed
        state.alerts[control_run_id] = []
        return {"control_run_id": control_run_id}

    @app.get("/api/runs/current")
    def get_current_run():
        if not state.active_run_id:
            return JSONResponse(status_code=404, content={"detail": "No hay run activo"})
        return {
            "control_run_id": state.active_run_id,
            "status": "running",
            "live": True,
            "subscribed": state.subscribed,
            "progress": {
                "units_processed": 0,
                "units_failed": 0,
                "errors_count": 0,
                "pattern_events_count": 0,
                "alerts_count": 0,
                "bus_dropped_events": 0,
            },
        }

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        if run_id == state.active_run_id:
            if state.finish_status is not None:
                return {
                    "control_run_id": run_id,
                    "status": state.finish_status,
                    "live": False,
                    "summary": {"schema_version": "control.summary.v1"},
                    "degraded": False,
                    "degradation_causes": [],
                }
            return {
                "control_run_id": run_id,
                "status": "running",
                "live": True,
                "subscribed": state.subscribed,
                "progress": {
                    "units_processed": 0,
                    "units_failed": 0,
                    "errors_count": 0,
                    "pattern_events_count": 0,
                    "alerts_count": 0,
                    "bus_dropped_events": 0,
                },
            }
        if run_id in state.alerts:
            return {
                "control_run_id": run_id,
                "status": "succeeded",
                "live": False,
                "summary": {"schema_version": "control.summary.v1"},
                "degraded": False,
                "degradation_causes": [],
            }
        return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})

    @app.get("/api/runs/{run_id}/alerts")
    def get_run_alerts(run_id: str, limit: int | None = Query(default=None, ge=0)):
        if run_id not in state.alerts:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        rows = state.alerts[run_id]
        if limit is not None:
            rows = rows[: max(limit, 0)]
        return rows

    @app.get("/api/config")
    def get_effective_config():
        return {"effective_config": EFFECTIVE_CONFIG}

    return app
