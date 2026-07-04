"""RunBackend: cliente del servicio media-plane (la costura de control plane, Spec B §5.5).

Fase 1: una instancia (SERVICE_URL). Fase 2: N instancias/nodos detrás de esta interfaz.
"""
from __future__ import annotations

from typing import Any

import httpx


class ServiceUnavailable(Exception):
    """El servicio no responde o respondió 5xx/503."""


class RunBusy(Exception):
    def __init__(self, detail: str, active_run_id: str | None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.active_run_id = active_run_id


class RunNotFinished(Exception):
    """409 al evaluar: el run sigue en curso (sin active_run_id, a diferencia
    de RunBusy que es el 409 de lanzamiento)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ServiceRejected(Exception):
    """422 del servicio (config inválida, plugin no disponible, etc.)."""

    def __init__(self, detail: Any) -> None:
        super().__init__(str(detail))
        self.detail = detail


class UnknownRun(Exception):
    pass


class RunBackend:
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

    async def model(self) -> dict:
        return await self._get_json("/api/model")

    async def ingest_plugins(self) -> list[dict]:
        return await self._get_json("/api/catalog/ingest-plugins")

    async def datasets(self) -> list[dict]:
        return await self._get_json("/api/catalog/datasets")

    async def launch(self, run_request: dict) -> str:
        try:
            response = await self._http.post("/api/runs", json=run_request)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 409:
            body = response.json()
            raise RunBusy(body.get("detail", "run activo"), body.get("active_run_id"))
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(f"POST /api/runs -> {response.status_code}")
        response.raise_for_status()
        return response.json()["run_id"]

    async def list_runs(self) -> list[dict]:
        return await self._get_json("/api/runs")

    async def status(self, run_id: str) -> dict:
        return await self._get_json(f"/api/runs/{run_id}")

    async def stop(self, run_id: str) -> None:
        try:
            response = await self._http.post(f"/api/runs/{run_id}/stop")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(run_id)
        if response.status_code >= 500:
            raise ServiceUnavailable(f"POST /api/runs/{run_id}/stop -> {response.status_code}")
        response.raise_for_status()

    async def evaluate(self, run_id: str) -> dict:
        try:
            response = await self._http.post(f"/api/runs/{run_id}/evaluate")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(run_id)
        if response.status_code == 409:
            raise RunNotFinished(response.json().get("detail", "run en curso"))
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(
                f"POST /api/runs/{run_id}/evaluate -> {response.status_code}"
            )
        response.raise_for_status()
        return response.json()

    async def get_evaluation(self, run_id: str) -> dict:
        return await self._get_json(f"/api/runs/{run_id}/evaluate")

    async def detections(self, run_id: str, page: int = 1, page_size: int = 100) -> dict:
        return await self._get_json(
            f"/api/runs/{run_id}/detections", page=page, page_size=page_size
        )

    async def open_artifact(
        self, run_id: str, artifact_path: str, range_header: str | None = None
    ) -> httpx.Response:
        """Respuesta en streaming (el caller es responsable de aclose())."""
        headers = {"range": range_header} if range_header else None
        request = self._http.build_request(
            "GET", f"/api/runs/{run_id}/artifacts/{artifact_path}", headers=headers
        )
        try:
            return await self._http.send(request, stream=True)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
