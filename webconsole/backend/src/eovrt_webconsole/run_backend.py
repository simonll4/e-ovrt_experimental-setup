"""RunBackend: cliente del servicio media-plane (la costura de control plane, Spec B §5.5).

Fase 1: una instancia (SERVICE_URL). Fase 2: N instancias/nodos detrás de esta interfaz.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx


class ServiceUnavailable(Exception):
    """El servicio no responde o respondió 5xx/503."""


class RunBusy(Exception):
    def __init__(
        self, detail: str, active_run_id: str | None, reason: str | None = None
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.active_run_id = active_run_id
        self.reason = reason


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


class RunActive(Exception):
    """409 al borrar: el run sigue activo."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PreviewConflict(Exception):
    """409 del media-plane al iniciar preview; body completo del upstream."""

    def __init__(self, body: dict) -> None:
        super().__init__(body.get("detail", "slot ocupado"))
        self.body = body


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
            raise RunBusy(
                body.get("detail", "run activo"),
                body.get("active_run_id"),
                body.get("reason"),
            )
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

    async def dropped(self, run_id: str, page: int = 1, page_size: int = 100) -> dict:
        return await self._get_json(
            f"/api/runs/{run_id}/dropped", page=page, page_size=page_size
        )

    async def list_artifacts(self, run_id: str) -> dict:
        """Inventario de archivos de la corrida (nombre, tamaño, qué es)."""
        try:
            return await self._get_json(f"/api/runs/{run_id}/artifacts")
        except UnknownRun:
            # El servicio media-plane no expone índice de artefactos: ninguna
            # versión lo hace; sólo ofrece /artifacts/{artifact_path:path}.
            # El sondeo de abajo es la ruta primaria contra ese servicio,
            # no un fallback para versiones anteriores. Validar el run aparte.
            pass
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {307, 308}:
                raise
        await self.status(run_id)
        names = {
            "summary.json": "Métricas de la corrida",
            "run_manifest.json": "Manifiesto efectivo",
            "run_provenance.json": "Procedencia de la corrida",
            "detections.jsonl": "Detecciones por unidad",
            "metrics.jsonl": "Métricas por unidad",
            "errors.jsonl": "Errores de procesamiento",
            "dropped.jsonl": "Unidades descartadas",
            "eval_perception.json": "Evaluación BENCH",
            "annotated.mp4": "Video con detecciones",
        }
        limit = asyncio.Semaphore(4)

        async def probe(name: str, description: str) -> dict | None:
            async with limit:
                response = await self.open_artifact(run_id, name, range_header="bytes=0-0")
                try:
                    if response.status_code == 404:
                        return None
                    if response.status_code not in {200, 206, 416}:
                        raise ServiceUnavailable(f"artefacto {name}: HTTP {response.status_code}")
                    # Range evita descargar videos o JSONL completos. Un archivo
                    # vacío puede responder 416 con Content-Range: bytes */0.
                    raw_size = (
                        response.headers.get("content-range", "").rsplit("/", 1)[-1]
                        if response.status_code in {206, 416}
                        else response.headers.get("content-length", "")
                    )
                    if not raw_size.isdigit():
                        raise ServiceUnavailable(f"artefacto {name}: tamaño no disponible")
                    if response.status_code == 416 and raw_size != "0":
                        raise ServiceUnavailable(f"artefacto {name}: rango no disponible")
                    return {"path": name, "name": name, "size_bytes": int(raw_size),
                            "n_files": None, "description": description}
                finally:
                    await response.aclose()

        items = await asyncio.gather(*(probe(name, desc) for name, desc in names.items()))
        return {
            "run_id": run_id, "items": [item for item in items if item is not None],
            "complete": False,
            "notice": "El servicio no publica un inventario completo; se muestran los archivos "
                      "estándar disponibles. Las vistas previas se consultan en la traza.",
        }

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

    async def delete(self, run_id: str) -> None:
        try:
            response = await self._http.delete(f"/api/runs/{run_id}")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(run_id)
        if response.status_code == 409:
            raise RunActive(response.json().get("detail", "run activo"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(f"DELETE /api/runs/{run_id} -> {response.status_code}")
        response.raise_for_status()

    async def preview_start(self, body: dict) -> dict:
        try:
            response = await self._http.post("/api/preview", json=body)
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 409:
            raise PreviewConflict(response.json())
        if response.status_code == 422:
            raise ServiceRejected(response.json().get("detail", "config inválida"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(response.text)
        response.raise_for_status()
        return response.json()

    async def preview_status(self) -> dict:
        return await self._get_json("/api/preview")

    async def preview_stop(self) -> None:
        try:
            response = await self._http.delete("/api/preview")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code >= 500:
            raise ServiceUnavailable(response.text)
        response.raise_for_status()
