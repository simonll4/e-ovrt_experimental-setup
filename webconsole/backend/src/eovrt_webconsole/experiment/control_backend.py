"""ControlPlaneBackend: cliente del servicio control-plane (:8081, spec 41 SS5, doc 38).

Espejo de RunBackend (media-plane, run_backend.py) para los endpoints del
control-plane: POST /api/runs (mode: live|replay), GET /api/runs/{id},
GET /api/runs/current, GET /api/runs/{id}/alerts, GET /api/config.
"""
from __future__ import annotations

from typing import Any

import httpx


class ServiceUnavailable(Exception):
    """El servicio no responde o respondio 5xx/503."""


class RunBusy(Exception):
    def __init__(self, detail: str, active_run_id: str | None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.active_run_id = active_run_id


class ServiceRejected(Exception):
    """422 del servicio (config invalida, mode que no matchea input.type, etc.)."""

    def __init__(self, detail: Any) -> None:
        super().__init__(str(detail))
        self.detail = detail


class UnknownRun(Exception):
    pass


class ControlPlaneBackend:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def _get_json(self, path: str, **params: Any) -> Any:
        try:
            response = await self._http.get(path, params=params or None)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(path)
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(f"{path} -> {response.status_code}")
        response.raise_for_status()
        return response.json()

    async def launch(self, config: dict, mode: str, experiment_id: str | None) -> str:
        body = {"mode": mode, "config": config, "experiment_id": experiment_id}
        try:
            response = await self._http.post("/api/runs", json=body)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 409:
            resp_body = response.json()
            raise RunBusy(resp_body.get("detail", "run activo"), resp_body.get("active_run_id"))
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(f"POST /api/runs -> {response.status_code}")
        response.raise_for_status()
        return response.json()["control_run_id"]

    async def status(self, control_run_id: str) -> dict:
        return await self._get_json(f"/api/runs/{control_run_id}")

    async def current(self) -> dict:
        return await self._get_json("/api/runs/current")

    async def alerts(self, control_run_id: str) -> list[dict]:
        return await self._get_json(f"/api/runs/{control_run_id}/alerts")

    async def config(self) -> dict:
        return await self._get_json("/api/config")

    async def list_runs(self, media_run_id: str | None = None) -> list[dict]:
        params = {"media_run_id": media_run_id} if media_run_id else {}
        return await self._get_json("/api/runs", **params)

    async def pattern_progress(self, control_run_id: str) -> list[dict]:
        return await self._get_json(f"/api/runs/{control_run_id}/pattern-progress")

    async def received_units(self, control_run_id: str) -> list[dict]:
        return await self._get_json(f"/api/runs/{control_run_id}/received-units")
