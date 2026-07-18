> **SUPERSEDED por `2026-07-03-webconsole-mvp.md` — no refleja lo implementado.** Este plan
> nombra el paquete `eovrt_console` (el real es `eovrt_webconsole`) y describe `RunBackend`
> como cliente HTTP síncrono vía `httpx.Client` (lo implementado usa `httpx.AsyncClient`,
> async). Se conserva solo como referencia histórica del diseño inicial.

# Webconsole Backend (BFF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el BFF (`webconsole/backend`, paquete `eovrt_console`) de la consola web: un servicio FastAPI que compone runs, los lanza contra una instancia del servicio media-plane (Spec A) vía HTTP/WebSocket, y expone catálogos y resultados a la futura SPA. No ejecuta el pipeline — es puro cliente/proxy.

**Architecture:** `RunBackend` es la única costura de red: encapsula todas las llamadas HTTP (síncronas, vía `httpx.Client`) hacia el servicio media-plane, y expone la URL del WebSocket de telemetría para que la ruta de streaming (la única parte async del BFF) la reexponga a la SPA. Los prompt sets y manifiestos se leen/escriben directamente del propio repo (`prompts/`, `experiments/`, en la raíz de `e-ovrt_experimental-setup`) — sin red. Toda la suite de tests corre contra un **servicio media-plane falso** (una segunda app FastAPI mínima, servida en un puerto real vía `uvicorn.Server` en un hilo) que imita el contrato exacto de Spec A — nunca contra el servicio real ni contra GPU.

**Tech Stack:** Python 3.11, FastAPI, `httpx` (cliente síncrono), `websockets` (cliente async, solo para el proxy de streaming), Pydantic, pytest + `fastapi.testclient.TestClient`, `uvicorn` (para servir el fake y, más adelante, el propio BFF).

## Global Constraints

- El BFF vive en `webconsole/backend/` dentro de `e-ovrt_experimental-setup` (monorepo). `prompts/` y `experiments/` permanecen en la raíz del repo — el BFF los lee con una ruta relativa calculada, nunca los mueve.
- El BFF **nunca ejecuta el pipeline ni importa el paquete Python `eovrt_media`** — es cliente HTTP/WS puro del servicio media-plane (arquitecturalmente son procesos/servicios separados, potencialmente en hosts distintos en Fase 2).
- Fase 1: **un solo target** (`SERVICE_URL`, una instancia local del servicio). El parámetro `node` de Spec B se omite en las firmas por ahora — `RunBackend` representa una única instancia; una futura Fase 2 mapea `{node_id: RunBackend}` sin cambiar la forma de esta clase.
- Los prompts se resuelven **en el BFF** (lee `prompts/<id>.yaml`) y se envían **inline** al servicio — el servicio media-plane nunca ve `experimental-setup`.
- El proxy de artefactos reenvía el header `Range` y transmite bytes en streaming (no bufferiza el archivo completo en memoria).
- Todos los tests corren contra el fake service (Task 1) — nunca requieren GPU ni el servicio media-plane real corriendo.
- No se toca `e-ovrt_media-plane` en este plan — ya tiene su propio plan (`2026-07-01-media-plane-service.md`).

---

## File Structure

```
webconsole/
└── backend/
    ├── pyproject.toml
    ├── src/eovrt_console/
    │   ├── __init__.py
    │   ├── settings.py            # ConsoleSettings, load_settings()
    │   ├── schemas.py             # Modelos Pydantic de la API del BFF
    │   ├── prompts_repo.py        # list_prompt_sets(), load_prompt_set()
    │   ├── manifests_repo.py      # list_manifests(), save_manifest()
    │   ├── compose.py             # validate_compose(), build_service_run_request()
    │   ├── run_backend.py         # RunBackend + excepciones (única costura de red)
    │   ├── app.py                 # create_app(), lifespan, instancia `app`
    │   └── routers/
    │       ├── __init__.py
    │       ├── catalog.py          # GET /api/catalog/{ingest-plugins,datasets,prompt-sets,manifests}, GET /api/model
    │       ├── compose.py          # POST /api/compose/validate
    │       ├── runs.py             # POST/GET /api/runs, .../stop
    │       ├── manifests.py        # POST /api/manifests
    │       ├── stream.py           # WS /api/runs/{id}/stream (proxy async)
    │       └── artifacts.py        # GET /api/runs/{id}/detections, /artifacts/{path}
    └── tests/
        ├── __init__.py
        ├── conftest.py             # fixture `fake_service`
        ├── fake_service.py         # FakeServiceState, FakeServiceHandle (servidor real en un hilo)
        ├── test_run_backend.py
        ├── test_prompts_repo.py
        ├── test_manifests_repo.py
        ├── test_compose.py
        ├── test_app_catalog_routes.py
        ├── test_compose_routes.py
        ├── test_runs_routes.py
        ├── test_manifests_routes.py
        ├── test_stream_route.py
        ├── test_artifacts_routes.py
        └── test_end_to_end.py
```

---

### Task 1: Bootstrap del paquete + servicio media-plane falso para tests

**Files:**
- Create: `webconsole/backend/pyproject.toml`
- Create: `webconsole/backend/src/eovrt_console/__init__.py`
- Create: `webconsole/backend/tests/__init__.py`
- Create: `webconsole/backend/tests/fake_service.py`
- Create: `webconsole/backend/tests/conftest.py`
- Test: `webconsole/backend/tests/test_fake_service.py`

**Interfaces:**
- Produces: `FakeServiceState` (dataclass mutable, ver campos abajo), `FakeServiceHandle(port, state)` con `.start()`/`.stop()`/`.base_url`, fixture pytest `fake_service` (yields un `FakeServiceHandle` ya arrancado, con `.state` reseteado por test).

Esta es la pieza de infraestructura de la que dependen todos los tasks siguientes: un servicio HTTP+WS real (no mockeado a nivel de transporte) que imita el contrato exacto de Spec A (`GET /api/model`, `GET /api/catalog/{ingest-plugins,datasets}`, `POST /api/runs`, `POST /api/runs/{id}/stop`, `GET /api/runs/{id}`, `GET /api/runs`, `WS /api/runs/{id}/stream`, `GET /api/runs/{id}/detections`, `GET /api/runs/{id}/artifacts/{path}`).

- [ ] **Step 1: Crear el paquete**

Create `webconsole/backend/pyproject.toml`:

```toml
[project]
name = "eovrt-console-backend"
version = "0.1.0"
description = "BFF de la consola web experimental E-OVRT — cliente del servicio media-plane"
requires-python = ">=3.11"
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "httpx",
    "websockets",
    "pyyaml",
    "pydantic",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Create `webconsole/backend/src/eovrt_console/__init__.py`:

```python
```

Create `webconsole/backend/tests/__init__.py`:

```python
```

Run:
```bash
cd webconsole/backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```
Expected: instala sin errores.

- [ ] **Step 2: Escribir el test que falla**

Create `webconsole/backend/tests/test_fake_service.py`:

```python
import httpx

from tests.fake_service import FakeServiceHandle, FakeServiceState


def test_fake_service_starts_and_answers_healthz():
    state = FakeServiceState()
    handle = FakeServiceHandle(port=8931, state=state)
    handle.start()
    try:
        response = httpx.get(f"{handle.base_url}/healthz")
        assert response.status_code == 200
    finally:
        handle.stop()


def test_fake_service_reports_model_info():
    state = FakeServiceState()
    handle = FakeServiceHandle(port=8932, state=state)
    handle.start()
    try:
        response = httpx.get(f"{handle.base_url}/api/model")
        assert response.json()["ref"] == "mock"
    finally:
        handle.stop()


def test_fake_service_create_run_returns_id_then_busy_on_second():
    state = FakeServiceState()
    handle = FakeServiceHandle(port=8933, state=state)
    handle.start()
    try:
        first = httpx.post(f"{handle.base_url}/api/runs", json={})
        assert first.status_code == 201
        run_id = first.json()["run_id"]

        state.busy = True
        second = httpx.post(f"{handle.base_url}/api/runs", json={})
        assert second.status_code == 409

        assert state.created_run_ids == [run_id]
    finally:
        handle.stop()
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `pytest tests/test_fake_service.py -v`
Expected: `ModuleNotFoundError: No module named 'tests.fake_service'`

- [ ] **Step 4: Implementar el fake service**

Create `webconsole/backend/tests/fake_service.py`:

```python
"""Fake del servicio media-plane (Spec A) para testear el BFF sin GPU ni red real
más allá de localhost. Sirve el contrato exacto vía un servidor uvicorn real en un
hilo — necesario para poder testear tanto el proxy HTTP como el proxy WebSocket."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response


@dataclass
class FakeServiceState:
    model_info: dict = field(
        default_factory=lambda: {
            "ref": "mock",
            "adapter": "mock",
            "device": "cpu",
            "prompt_backend": "default",
        }
    )
    ingest_plugins: list = field(
        default_factory=lambda: [
            {"id": "image_folder", "kind": "bounded", "available": True, "reason": None},
            {"id": "video_file", "kind": "bounded", "available": True, "reason": None},
            {"id": "rtsp", "kind": "live", "available": True, "reason": None},
            {"id": "oak_d", "kind": "live", "available": False, "reason": "sin hardware"},
        ]
    )
    datasets: list = field(default_factory=list)
    runs: dict[str, dict] = field(default_factory=dict)
    stream_events: dict[str, list[dict]] = field(default_factory=dict)
    artifacts: dict[str, bytes] = field(default_factory=dict)
    busy: bool = False
    next_run_id: str = "run_fake_001"
    created_run_ids: list[str] = field(default_factory=list)
    stopped_run_ids: list[str] = field(default_factory=list)
    last_create_payload: dict | None = None
    last_artifact_range_header: str | None = None


def build_fake_service_app(state: FakeServiceState) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/api/model")
    def get_model() -> dict:
        return state.model_info

    @app.get("/api/catalog/ingest-plugins")
    def get_ingest_plugins() -> list:
        return state.ingest_plugins

    @app.get("/api/catalog/datasets")
    def get_datasets() -> list:
        return state.datasets

    @app.post("/api/runs", status_code=201)
    def create_run(payload: dict) -> JSONResponse:
        state.last_create_payload = payload
        if state.busy:
            return JSONResponse(status_code=409, content={"detail": "busy"})
        run_id = state.next_run_id
        state.runs[run_id] = {
            "run_id": run_id,
            "status": "succeeded",
            "error": None,
            "summary": {"units_processed": 3},
        }
        state.created_run_ids.append(run_id)
        return JSONResponse(status_code=201, content={"run_id": run_id})

    @app.post("/api/runs/{run_id}/stop")
    def stop_run(run_id: str) -> Response:
        if run_id not in state.runs:
            return JSONResponse(status_code=404, content={"detail": "not found"})
        state.stopped_run_ids.append(run_id)
        return Response(status_code=204)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        if run_id not in state.runs:
            return JSONResponse(status_code=404, content={"detail": "not found"})
        return JSONResponse(status_code=200, content=state.runs[run_id])

    @app.get("/api/runs")
    def list_runs() -> list:
        return list(state.runs.values())

    @app.get("/api/runs/{run_id}/detections")
    def get_detections(run_id: str, page: int = 1, page_size: int = 50) -> dict:
        return {"run_id": run_id, "page": page, "page_size": page_size, "total": 0, "items": []}

    @app.get("/api/runs/{run_id}/artifacts/{artifact_path:path}")
    def get_artifact(run_id: str, artifact_path: str, request: Request) -> Response:
        state.last_artifact_range_header = request.headers.get("range")
        if artifact_path not in state.artifacts:
            return JSONResponse(status_code=404, content={"detail": "not found"})
        return Response(content=state.artifacts[artifact_path], media_type="application/octet-stream")

    @app.websocket("/api/runs/{run_id}/stream")
    async def stream(websocket: WebSocket, run_id: str) -> None:
        await websocket.accept()
        for event in state.stream_events.get(run_id, []):
            await websocket.send_json(event)
        await websocket.close()

    return app


class FakeServiceHandle:
    def __init__(self, port: int, state: FakeServiceState) -> None:
        self.port = port
        self.state = state
        self.base_url = f"http://127.0.0.1:{port}"
        app = build_fake_service_app(state)
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self) -> None:
        self._thread.start()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                httpx.get(f"{self.base_url}/healthz", timeout=0.2)
                return
            except httpx.HTTPError:
                time.sleep(0.05)
        raise RuntimeError("fake service no arrancó a tiempo")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5.0)
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `pytest tests/test_fake_service.py -v`
Expected: 3 passed

- [ ] **Step 6: Agregar la fixture reusable de pytest**

Create `webconsole/backend/tests/conftest.py`:

```python
import pytest

from tests.fake_service import FakeServiceHandle, FakeServiceState

_NEXT_PORT = [8940]


@pytest.fixture
def fake_service():
    port = _NEXT_PORT[0]
    _NEXT_PORT[0] += 1
    state = FakeServiceState()
    handle = FakeServiceHandle(port=port, state=state)
    handle.start()
    yield handle
    handle.stop()
```

(El contador de puertos evita colisiones entre tests que usan la fixture en la misma sesión de pytest.)

- [ ] **Step 7: Verificar que la fixture funciona**

Run: `pytest tests/test_fake_service.py -v`
Expected: sigue en 3 passed (no se rompió nada; la fixture se usará recién en el próximo task).

- [ ] **Step 8: Commit**

```bash
git add webconsole/backend/pyproject.toml webconsole/backend/src webconsole/backend/tests
git commit -m "test(webconsole-backend): bootstrap del paquete + fake del servicio media-plane"
```

---

### Task 2: `ConsoleSettings`

**Files:**
- Create: `webconsole/backend/src/eovrt_console/settings.py`
- Test: Create `webconsole/backend/tests/test_settings.py`

**Interfaces:**
- Produces: `ConsoleSettings` (dataclass: `service_url: str`, `repo_root: Path`, propiedades `prompts_dir`/`experiments_dir`), `load_settings() -> ConsoleSettings`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_settings.py`:

```python
from pathlib import Path

import pytest

from eovrt_console.settings import load_settings


def test_load_settings_reads_service_url_and_repo_root(monkeypatch, tmp_path):
    monkeypatch.setenv("SERVICE_URL", "http://localhost:8000")
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))

    settings = load_settings()

    assert settings.service_url == "http://localhost:8000"
    assert settings.repo_root == tmp_path
    assert settings.prompts_dir == tmp_path / "prompts"
    assert settings.experiments_dir == tmp_path / "experiments"


def test_load_settings_missing_service_url_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("SERVICE_URL", raising=False)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))

    with pytest.raises(RuntimeError, match="SERVICE_URL"):
        load_settings()
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_settings.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.settings'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/settings.py`:

```python
"""Configuración del BFF leída de variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConsoleSettings:
    service_url: str
    repo_root: Path

    @property
    def prompts_dir(self) -> Path:
        return self.repo_root / "prompts"

    @property
    def experiments_dir(self) -> Path:
        return self.repo_root / "experiments"


def _default_repo_root() -> Path:
    # webconsole/backend/src/eovrt_console/settings.py -> raíz del repo es 4 niveles arriba
    return Path(__file__).resolve().parents[4]


def load_settings() -> ConsoleSettings:
    service_url = os.environ.get("SERVICE_URL")
    if not service_url:
        raise RuntimeError(
            "SERVICE_URL es obligatorio (URL del servicio media-plane, ej. http://localhost:8000)."
        )
    repo_root_env = os.environ.get("EOVRT_CONSOLE_REPO_ROOT")
    repo_root = Path(repo_root_env) if repo_root_env else _default_repo_root()
    return ConsoleSettings(service_url=service_url, repo_root=repo_root)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_settings.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/settings.py webconsole/backend/tests/test_settings.py
git commit -m "feat(webconsole-backend): ConsoleSettings"
```

---

### Task 3: `RunBackend` — la costura de red hacia el servicio media-plane

**Files:**
- Create: `webconsole/backend/src/eovrt_console/run_backend.py`
- Test: Create `webconsole/backend/tests/test_run_backend.py`

**Interfaces:**
- Consumes: `FakeServiceHandle`/fixture `fake_service` (Task 1).
- Produces: `RunBusyError`, `RunNotFoundError`, `ArtifactNotFoundError` (excepciones); `RunBackend(base_url: str, client: httpx.Client)` con métodos `launch(run_request: dict) -> str`, `stop(run_id: str) -> None`, `status(run_id: str) -> dict`, `list_runs() -> list[dict]`, `get_model() -> dict`, `get_ingest_plugins() -> list[dict]`, `get_datasets() -> list[dict]`, `get_detections(run_id: str, page: int, page_size: int) -> dict`, `stream_artifact(run_id: str, artifact_path: str, range_header: str | None) -> httpx.Response`, `stream_ws_url(run_id: str) -> str`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_run_backend.py`:

```python
import httpx
import pytest

from eovrt_console.run_backend import ArtifactNotFoundError, RunBackend, RunBusyError, RunNotFoundError


def _backend(fake_service) -> RunBackend:
    return RunBackend(base_url=fake_service.base_url, client=httpx.Client(timeout=5.0))


def test_launch_returns_run_id(fake_service):
    backend = _backend(fake_service)
    run_id = backend.launch({"ingest": {}, "prompts": {}, "run": {}})
    assert run_id == fake_service.state.next_run_id


def test_launch_raises_busy_on_409(fake_service):
    fake_service.state.busy = True
    backend = _backend(fake_service)
    with pytest.raises(RunBusyError):
        backend.launch({})


def test_status_returns_run_dict(fake_service):
    backend = _backend(fake_service)
    run_id = backend.launch({})
    body = backend.status(run_id)
    assert body["status"] == "succeeded"


def test_status_unknown_run_raises_not_found(fake_service):
    backend = _backend(fake_service)
    with pytest.raises(RunNotFoundError):
        backend.status("does-not-exist")


def test_stop_unknown_run_raises_not_found(fake_service):
    backend = _backend(fake_service)
    with pytest.raises(RunNotFoundError):
        backend.stop("does-not-exist")


def test_stop_known_run_records_it(fake_service):
    backend = _backend(fake_service)
    run_id = backend.launch({})
    backend.stop(run_id)
    assert fake_service.state.stopped_run_ids == [run_id]


def test_list_runs_returns_list(fake_service):
    backend = _backend(fake_service)
    backend.launch({})
    runs = backend.list_runs()
    assert len(runs) == 1


def test_get_model_returns_model_info(fake_service):
    backend = _backend(fake_service)
    assert backend.get_model()["ref"] == "mock"


def test_get_ingest_plugins_returns_four(fake_service):
    backend = _backend(fake_service)
    assert len(backend.get_ingest_plugins()) == 4


def test_get_datasets_returns_list(fake_service):
    backend = _backend(fake_service)
    assert backend.get_datasets() == []


def test_get_detections_forwards_pagination(fake_service):
    backend = _backend(fake_service)
    body = backend.get_detections("run_x", page=2, page_size=10)
    assert body["page"] == 2
    assert body["page_size"] == 10


def test_stream_artifact_returns_bytes_and_forwards_range(fake_service):
    fake_service.state.artifacts["annotated.mp4"] = b"fake-video-bytes"
    backend = _backend(fake_service)

    response = backend.stream_artifact("run_x", "annotated.mp4", range_header="bytes=0-3")

    assert b"".join(response.iter_bytes()) == b"fake-video-bytes"
    response.close()
    assert fake_service.state.last_artifact_range_header == "bytes=0-3"


def test_stream_artifact_missing_raises_not_found(fake_service):
    backend = _backend(fake_service)
    with pytest.raises(ArtifactNotFoundError):
        backend.stream_artifact("run_x", "missing.mp4", range_header=None)


def test_stream_ws_url_converts_http_to_ws(fake_service):
    backend = _backend(fake_service)
    url = backend.stream_ws_url("run_x")
    assert url == fake_service.base_url.replace("http://", "ws://") + "/api/runs/run_x/stream"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_run_backend.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.run_backend'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/run_backend.py`:

```python
"""Única costura de red del BFF: todas las llamadas HTTP hacia el servicio
media-plane (Spec A) pasan por acá. Una instancia = un target/nodo."""

from __future__ import annotations

import httpx


class RunBusyError(RuntimeError):
    pass


class RunNotFoundError(RuntimeError):
    pass


class ArtifactNotFoundError(RuntimeError):
    pass


class RunBackend:
    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client

    def launch(self, run_request: dict) -> str:
        response = self._client.post(f"{self.base_url}/api/runs", json=run_request)
        if response.status_code == 409:
            raise RunBusyError(response.json().get("detail", "servicio ocupado"))
        response.raise_for_status()
        return response.json()["run_id"]

    def stop(self, run_id: str) -> None:
        response = self._client.post(f"{self.base_url}/api/runs/{run_id}/stop")
        if response.status_code == 404:
            raise RunNotFoundError(run_id)
        response.raise_for_status()

    def status(self, run_id: str) -> dict:
        response = self._client.get(f"{self.base_url}/api/runs/{run_id}")
        if response.status_code == 404:
            raise RunNotFoundError(run_id)
        response.raise_for_status()
        return response.json()

    def list_runs(self) -> list[dict]:
        response = self._client.get(f"{self.base_url}/api/runs")
        response.raise_for_status()
        return response.json()

    def get_model(self) -> dict:
        response = self._client.get(f"{self.base_url}/api/model")
        response.raise_for_status()
        return response.json()

    def get_ingest_plugins(self) -> list[dict]:
        response = self._client.get(f"{self.base_url}/api/catalog/ingest-plugins")
        response.raise_for_status()
        return response.json()

    def get_datasets(self) -> list[dict]:
        response = self._client.get(f"{self.base_url}/api/catalog/datasets")
        response.raise_for_status()
        return response.json()

    def get_detections(self, run_id: str, page: int, page_size: int) -> dict:
        response = self._client.get(
            f"{self.base_url}/api/runs/{run_id}/detections",
            params={"page": page, "page_size": page_size},
        )
        response.raise_for_status()
        return response.json()

    def stream_artifact(
        self, run_id: str, artifact_path: str, range_header: str | None
    ) -> httpx.Response:
        headers = {"Range": range_header} if range_header else {}
        request = self._client.build_request(
            "GET",
            f"{self.base_url}/api/runs/{run_id}/artifacts/{artifact_path}",
            headers=headers,
        )
        response = self._client.send(request, stream=True)
        if response.status_code == 404:
            response.close()
            raise ArtifactNotFoundError(artifact_path)
        return response

    def stream_ws_url(self, run_id: str) -> str:
        ws_base = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{ws_base}/api/runs/{run_id}/stream"
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_run_backend.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/run_backend.py webconsole/backend/tests/test_run_backend.py
git commit -m "feat(webconsole-backend): RunBackend, cliente HTTP del servicio media-plane"
```

---

### Task 4: Repositorio de prompt sets (lectura in-repo)

**Files:**
- Create: `webconsole/backend/src/eovrt_console/prompts_repo.py`
- Test: Create `webconsole/backend/tests/test_prompts_repo.py`

**Interfaces:**
- Produces: `PromptSetSummary` (dataclass: `id`, `description`, `classes: list[str]`, `frozen: bool`), `list_prompt_sets(prompts_dir: Path) -> list[PromptSetSummary]`, `load_prompt_set(prompts_dir: Path, prompt_set_id: str) -> dict`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_prompts_repo.py`:

```python
from pathlib import Path

import pytest

from eovrt_console.prompts_repo import list_prompt_sets, load_prompt_set

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  description: "Set corto v2"
  language: en
  classes:
    - id: person
      role: entity
      phrasings: { default: ["person"] }
    - id: helmet
      role: ppe
      phrasings: { default: ["helmet"] }
"""


def test_list_prompt_sets_reads_repo(tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)

    summaries = list_prompt_sets(prompts_dir)

    assert len(summaries) == 1
    assert summaries[0].id == "cr01_cr02_v2_short"
    assert summaries[0].description == "Set corto v2"
    assert summaries[0].classes == ["person", "helmet"]
    assert summaries[0].frozen is False


def test_list_prompt_sets_missing_dir_returns_empty(tmp_path: Path):
    assert list_prompt_sets(tmp_path / "prompts") == []


def test_load_prompt_set_returns_raw_dict(tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)

    prompt_set = load_prompt_set(prompts_dir, "cr01_cr02_v2_short")

    assert prompt_set["id"] == "cr01_cr02_v2_short"
    assert len(prompt_set["classes"]) == 2


def test_load_prompt_set_missing_raises(tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_prompt_set(prompts_dir, "does-not-exist")
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_prompts_repo.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.prompts_repo'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/prompts_repo.py`:

```python
"""Lectura de los prompt sets declarados en la raíz del repo (``prompts/*.yaml``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PromptSetSummary:
    id: str
    description: str | None
    classes: list[str]
    frozen: bool


def list_prompt_sets(prompts_dir: Path) -> list[PromptSetSummary]:
    if not prompts_dir.is_dir():
        return []
    summaries: list[PromptSetSummary] = []
    for path in sorted(prompts_dir.glob("*.yaml")):
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        prompt_set = raw.get("prompt_set", {})
        summaries.append(
            PromptSetSummary(
                id=prompt_set.get("id", path.stem),
                description=prompt_set.get("description"),
                classes=[c["id"] for c in prompt_set.get("classes", [])],
                frozen=bool(prompt_set.get("frozen", False)),
            )
        )
    return summaries


def load_prompt_set(prompts_dir: Path, prompt_set_id: str) -> dict[str, Any]:
    path = prompts_dir / f"{prompt_set_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt set '{prompt_set_id}' no encontrado en {prompts_dir}")
    with open(path) as f:
        raw = yaml.safe_load(f)
    return raw["prompt_set"]
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_prompts_repo.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/prompts_repo.py webconsole/backend/tests/test_prompts_repo.py
git commit -m "feat(webconsole-backend): lectura de prompt sets in-repo"
```

---

### Task 5: Repositorio de manifiestos (lectura + escritura in-repo)

**Files:**
- Create: `webconsole/backend/src/eovrt_console/manifests_repo.py`
- Test: Create `webconsole/backend/tests/test_manifests_repo.py`

**Interfaces:**
- Consumes: `ComposeRequest`-shaped dict (definido formalmente en Task 6; este task recibe los campos que necesita como parámetros sueltos para no crear una dependencia circular).
- Produces: `ManifestSummary` (dataclass: `id`, `name`, `description`), `list_manifests(experiments_dir: Path) -> list[ManifestSummary]`, `save_manifest(experiments_dir: Path, name: str, ingest_plugin: str, ingest_ref: str | None, ingest_config: dict, model_ref: str, prompt_set_id: str, active_ids: list[str] | None, description: str | None) -> Path`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_manifests_repo.py`:

```python
from pathlib import Path

import pytest
import yaml

from eovrt_console.manifests_repo import list_manifests, save_manifest


def test_list_manifests_reads_run_metadata(tmp_path: Path):
    experiments_dir = tmp_path / "experiments"
    experiments_dir.mkdir()
    (experiments_dir / "gdino.yaml").write_text(
        "run:\n  name: dbe_gdino\n  description: Corrida de muestra\n"
    )

    summaries = list_manifests(experiments_dir)

    assert len(summaries) == 1
    assert summaries[0].id == "gdino"
    assert summaries[0].name == "dbe_gdino"
    assert summaries[0].description == "Corrida de muestra"


def test_list_manifests_missing_dir_returns_empty(tmp_path: Path):
    assert list_manifests(tmp_path / "experiments") == []


def test_save_manifest_with_ref_ingest(tmp_path: Path):
    experiments_dir = tmp_path / "experiments"
    experiments_dir.mkdir()

    path = save_manifest(
        experiments_dir,
        name="from_console",
        ingest_plugin="image_folder",
        ingest_ref="demo_v2",
        ingest_config={},
        model_ref="mock",
        prompt_set_id="cr01_cr02_v2_short",
        active_ids=["person", "helmet"],
        description="Generado desde la consola",
    )

    assert path == experiments_dir / "from_console.yaml"
    data = yaml.safe_load(path.read_text())
    assert data["run"]["name"] == "from_console"
    assert data["source"] == {"ref": "demo_v2"}
    assert data["model"] == {"ref": "mock"}
    assert data["prompts"] == {"ref": "cr01_cr02_v2_short", "active_ids": ["person", "helmet"]}


def test_save_manifest_with_inline_ingest(tmp_path: Path):
    experiments_dir = tmp_path / "experiments"
    experiments_dir.mkdir()

    path = save_manifest(
        experiments_dir,
        name="from_console_video",
        ingest_plugin="video_file",
        ingest_ref=None,
        ingest_config={"path": "data/sample.mp4"},
        model_ref="mock",
        prompt_set_id="cr01_cr02_v2_short",
        active_ids=None,
        description=None,
    )

    data = yaml.safe_load(path.read_text())
    assert data["source"] == {"type": "video_file", "path": "data/sample.mp4"}


def test_save_manifest_existing_name_raises(tmp_path: Path):
    experiments_dir = tmp_path / "experiments"
    experiments_dir.mkdir()
    (experiments_dir / "dup.yaml").write_text("run:\n  name: dup\n")

    with pytest.raises(FileExistsError):
        save_manifest(
            experiments_dir,
            name="dup",
            ingest_plugin="image_folder",
            ingest_ref="demo_v2",
            ingest_config={},
            model_ref="mock",
            prompt_set_id="cr01_cr02_v2_short",
            active_ids=None,
            description=None,
        )
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_manifests_repo.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.manifests_repo'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/manifests_repo.py`:

```python
"""Lectura y escritura de manifiestos de experimento (``experiments/*.yaml``).

No recorre subdirectorios (p.ej. ``experiments/bench_v2/``) — la matriz BENCH
queda fuera del alcance del compositor ad-hoc de la consola en esta fase.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ManifestSummary:
    id: str
    name: str | None
    description: str | None


def list_manifests(experiments_dir: Path) -> list[ManifestSummary]:
    if not experiments_dir.is_dir():
        return []
    summaries: list[ManifestSummary] = []
    for path in sorted(experiments_dir.glob("*.yaml")):
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        run = raw.get("run", {})
        summaries.append(
            ManifestSummary(id=path.stem, name=run.get("name"), description=run.get("description"))
        )
    return summaries


def save_manifest(
    experiments_dir: Path,
    name: str,
    ingest_plugin: str,
    ingest_ref: str | None,
    ingest_config: dict[str, Any],
    model_ref: str,
    prompt_set_id: str,
    active_ids: list[str] | None,
    description: str | None,
) -> Path:
    experiments_dir.mkdir(parents=True, exist_ok=True)
    path = experiments_dir / f"{name}.yaml"
    if path.exists():
        raise FileExistsError(f"Ya existe un manifiesto '{name}.yaml' en {experiments_dir}")

    source = {"ref": ingest_ref} if ingest_ref else {"type": ingest_plugin, **ingest_config}
    manifest = {
        "run": {
            "scenario": "DBE",
            "name": name,
            "description": description or f"Manifiesto generado desde la consola ({name})",
        },
        "source": source,
        "model": {"ref": model_ref},
        "prompts": {"ref": prompt_set_id, "active_ids": active_ids},
    }
    with open(path, "w") as f:
        yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)
    return path
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_manifests_repo.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/manifests_repo.py webconsole/backend/tests/test_manifests_repo.py
git commit -m "feat(webconsole-backend): lectura y escritura de manifiestos in-repo"
```

---

### Task 6: Schemas de la API del BFF

**Files:**
- Create: `webconsole/backend/src/eovrt_console/schemas.py`
- Test: Create `webconsole/backend/tests/test_schemas.py`

**Interfaces:**
- Produces: `ComposeIngestRequest`, `ComposePromptsRequest`, `ComposeRunParams`, `ComposeRequest`, `ComposeValidationResponse`, `SaveManifestRequest`, `RunStatusResponse`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from eovrt_console.schemas import ComposeRequest, SaveManifestRequest


def _compose_payload() -> dict:
    return {
        "ingest": {"plugin": "image_folder", "config": {"path": "/tmp/imgs"}},
        "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
    }


def test_compose_request_accepts_minimal_payload():
    request = ComposeRequest(**_compose_payload())
    assert request.ingest.plugin == "image_folder"
    assert request.prompts.prompt_set_id == "cr01_cr02_v2_short"
    assert request.run.stride == 1


def test_compose_request_rejects_missing_prompts():
    payload = _compose_payload()
    del payload["prompts"]
    with pytest.raises(ValidationError):
        ComposeRequest(**payload)


def test_save_manifest_request_wraps_compose():
    request = SaveManifestRequest(name="from_console", compose=_compose_payload())
    assert request.name == "from_console"
    assert request.compose.ingest.plugin == "image_folder"
    assert request.description is None
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.schemas'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/schemas.py`:

```python
"""Modelos Pydantic de la API HTTP del BFF."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComposeIngestRequest(BaseModel):
    plugin: str
    ref: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ComposePromptsRequest(BaseModel):
    prompt_set_id: str
    active_ids: list[str] | None = None


class ComposeRunParams(BaseModel):
    stride: int = 1
    max_units: int | None = None
    save_annotated_video: bool = False
    min_confidence: float = 0.25


class ComposeRequest(BaseModel):
    ingest: ComposeIngestRequest
    prompts: ComposePromptsRequest
    run: ComposeRunParams = Field(default_factory=ComposeRunParams)


class ComposeValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class SaveManifestRequest(BaseModel):
    name: str
    description: str | None = None
    compose: ComposeRequest


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    error: str | None = None
    summary: dict[str, Any] | None = None
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_schemas.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/schemas.py webconsole/backend/tests/test_schemas.py
git commit -m "feat(webconsole-backend): schemas Pydantic de la API del BFF"
```

---

### Task 7: `compose.py` — validación y construcción del request al servicio

**Files:**
- Create: `webconsole/backend/src/eovrt_console/compose.py`
- Test: Create `webconsole/backend/tests/test_compose.py`

**Interfaces:**
- Consumes: `ComposeRequest` (Task 6), `load_prompt_set` (Task 4).
- Produces: `validate_compose(request: ComposeRequest, prompts_dir: Path) -> list[str]`, `build_service_run_request(request: ComposeRequest, prompts_dir: Path) -> dict`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_compose.py`:

```python
from pathlib import Path

from eovrt_console.compose import build_service_run_request, validate_compose
from eovrt_console.schemas import ComposeRequest

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  description: "Set corto"
  classes:
    - id: person
      phrasings: { default: ["person"] }
    - id: helmet
      phrasings: { default: ["helmet"] }
"""


def _prompts_dir(tmp_path: Path) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)
    return prompts_dir


def _request(**overrides) -> ComposeRequest:
    payload = {
        "ingest": {"plugin": "image_folder", "config": {"path": "/tmp/imgs"}},
        "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
    }
    payload.update(overrides)
    return ComposeRequest(**payload)


def test_validate_compose_accepts_valid_request(tmp_path: Path):
    errors = validate_compose(_request(), _prompts_dir(tmp_path))
    assert errors == []


def test_validate_compose_rejects_unknown_prompt_set(tmp_path: Path):
    errors = validate_compose(
        _request(prompts={"prompt_set_id": "does-not-exist", "active_ids": ["person"]}),
        _prompts_dir(tmp_path),
    )
    assert len(errors) == 1
    assert "does-not-exist" in errors[0]


def test_validate_compose_rejects_unknown_active_id(tmp_path: Path):
    errors = validate_compose(
        _request(prompts={"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["nope"]}),
        _prompts_dir(tmp_path),
    )
    assert any("nope" in e for e in errors)


def test_validate_compose_requires_path_for_image_folder(tmp_path: Path):
    errors = validate_compose(
        _request(ingest={"plugin": "image_folder", "config": {}}),
        _prompts_dir(tmp_path),
    )
    assert any("path" in e for e in errors)


def test_validate_compose_ok_with_ref_instead_of_path(tmp_path: Path):
    errors = validate_compose(
        _request(ingest={"plugin": "image_folder", "ref": "demo_v2", "config": {}}),
        _prompts_dir(tmp_path),
    )
    assert errors == []


def test_validate_compose_requires_url_for_rtsp(tmp_path: Path):
    errors = validate_compose(
        _request(ingest={"plugin": "rtsp", "config": {}}),
        _prompts_dir(tmp_path),
    )
    assert any("url" in e for e in errors)


def test_build_service_run_request_shape(tmp_path: Path):
    body = build_service_run_request(_request(), _prompts_dir(tmp_path))

    assert body["ingest"] == {"plugin": "image_folder", "ref": None, "config": {"path": "/tmp/imgs"}}
    assert body["prompts"]["prompt_set"]["id"] == "cr01_cr02_v2_short"
    assert body["prompts"]["active_ids"] == ["person"]
    assert body["run"]["stride"] == 1
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_compose.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.compose'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/compose.py`:

```python
"""Validación de una composición y construcción del body exacto que espera
``POST /api/runs`` del servicio media-plane (Spec A)."""

from __future__ import annotations

from pathlib import Path

from eovrt_console.prompts_repo import load_prompt_set
from eovrt_console.schemas import ComposeRequest

_PATH_REQUIRED_PLUGINS = {"image_folder", "video_file"}


def validate_compose(request: ComposeRequest, prompts_dir: Path) -> list[str]:
    errors: list[str] = []

    try:
        prompt_set = load_prompt_set(prompts_dir, request.prompts.prompt_set_id)
    except FileNotFoundError as exc:
        return [str(exc)]

    known_ids = {c["id"] for c in prompt_set.get("classes", [])}
    for active_id in request.prompts.active_ids or []:
        if active_id not in known_ids:
            errors.append(
                f"active_id '{active_id}' no existe en el prompt set "
                f"'{request.prompts.prompt_set_id}'"
            )

    if (
        request.ingest.plugin in _PATH_REQUIRED_PLUGINS
        and not request.ingest.ref
        and "path" not in request.ingest.config
    ):
        errors.append("ingest.config.path (o ingest.ref) es requerido para este plugin")

    if request.ingest.plugin == "rtsp" and "url" not in request.ingest.config:
        errors.append("ingest.config.url es requerido para el plugin rtsp")

    return errors


def build_service_run_request(request: ComposeRequest, prompts_dir: Path) -> dict:
    prompt_set = load_prompt_set(prompts_dir, request.prompts.prompt_set_id)
    return {
        "ingest": {
            "plugin": request.ingest.plugin,
            "ref": request.ingest.ref,
            "config": request.ingest.config,
        },
        "prompts": {
            "prompt_set": prompt_set,
            "active_ids": request.prompts.active_ids,
        },
        "run": request.run.model_dump(),
    }
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_compose.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/compose.py webconsole/backend/tests/test_compose.py
git commit -m "feat(webconsole-backend): validación de composición y construcción del request al servicio"
```

---

### Task 8: App FastAPI + rutas de catálogo

**Files:**
- Create: `webconsole/backend/src/eovrt_console/app.py`
- Create: `webconsole/backend/src/eovrt_console/routers/__init__.py`
- Create: `webconsole/backend/src/eovrt_console/routers/catalog.py`
- Test: Create `webconsole/backend/tests/test_app_catalog_routes.py`

**Interfaces:**
- Consumes: `RunBackend` (Task 3), `load_settings` (Task 2), `list_prompt_sets` (Task 4), `list_manifests` (Task 5).
- Produces: `create_app() -> FastAPI`, `app` (instancia module-level), `app.state.settings`/`app.state.run_backend`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_app_catalog_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    with TestClient(create_app()) as c:
        yield c, fake_service


def test_healthz_ok(client):
    c, _ = client
    assert c.get("/healthz").status_code == 200


def test_get_model_proxies_service(client):
    c, _ = client
    response = c.get("/api/model")
    assert response.status_code == 200
    assert response.json()["ref"] == "mock"


def test_get_ingest_plugins_proxies_service(client):
    c, _ = client
    response = c.get("/api/catalog/ingest-plugins")
    assert len(response.json()) == 4


def test_get_datasets_proxies_service(client):
    c, fake = client
    fake.state.datasets = [{"id": "demo_v2", "type": "image_folder", "description": None}]
    response = c.get("/api/catalog/datasets")
    assert response.json() == [{"id": "demo_v2", "type": "image_folder", "description": None}]


def test_get_prompt_sets_reads_repo(client, tmp_path):
    c, _ = client
    (tmp_path / "prompts" / "adhoc.yaml").write_text(
        "prompt_set:\n  id: adhoc\n  classes:\n    - id: person\n      phrasings: {default: [person]}\n"
    )
    response = c.get("/api/catalog/prompt-sets")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "adhoc"


def test_get_manifests_reads_repo(client, tmp_path):
    c, _ = client
    (tmp_path / "experiments" / "sample.yaml").write_text("run:\n  name: sample\n")
    response = c.get("/api/catalog/manifests")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "sample"
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_app_catalog_routes.py -v`
Expected: `ModuleNotFoundError: No module named 'eovrt_console.app'`

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/__init__.py`:

```python
```

Create `webconsole/backend/src/eovrt_console/routers/catalog.py`:

```python
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request

from eovrt_console.manifests_repo import list_manifests
from eovrt_console.prompts_repo import list_prompt_sets

router = APIRouter()


@router.get("/api/model")
def get_model(request: Request) -> dict:
    return request.app.state.run_backend.get_model()


@router.get("/api/catalog/ingest-plugins")
def get_ingest_plugins(request: Request) -> list[dict]:
    return request.app.state.run_backend.get_ingest_plugins()


@router.get("/api/catalog/datasets")
def get_datasets(request: Request) -> list[dict]:
    return request.app.state.run_backend.get_datasets()


@router.get("/api/catalog/prompt-sets")
def get_prompt_sets(request: Request) -> list[dict]:
    settings = request.app.state.settings
    return [asdict(p) for p in list_prompt_sets(settings.prompts_dir)]


@router.get("/api/catalog/manifests")
def get_manifests(request: Request) -> list[dict]:
    settings = request.app.state.settings
    return [asdict(m) for m in list_manifests(settings.experiments_dir)]
```

Create `webconsole/backend/src/eovrt_console/app.py`:

```python
"""App FastAPI del BFF de la consola — cliente del servicio media-plane."""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from eovrt_console.routers import catalog
from eovrt_console.run_backend import RunBackend
from eovrt_console.settings import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    http_client = httpx.Client(timeout=10.0)
    run_backend = RunBackend(base_url=settings.service_url, client=http_client)

    app.state.settings = settings
    app.state.run_backend = run_backend

    yield

    http_client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="E-OVRT Webconsole Backend", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    app.include_router(catalog.router)
    return app


app = create_app()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_app_catalog_routes.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/app.py webconsole/backend/src/eovrt_console/routers webconsole/backend/tests/test_app_catalog_routes.py
git commit -m "feat(webconsole-backend): app FastAPI con healthz y rutas de catálogo"
```

---

### Task 9: `POST /api/compose/validate`

**Files:**
- Create: `webconsole/backend/src/eovrt_console/routers/compose.py`
- Modify: `webconsole/backend/src/eovrt_console/app.py` (registrar router)
- Test: Create `webconsole/backend/tests/test_compose_routes.py`

**Interfaces:**
- Consumes: `validate_compose` (Task 7), `ComposeRequest`/`ComposeValidationResponse` (Task 6).
- Produces: ruta `POST /api/compose/validate`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_compose_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  classes:
    - id: person
      phrasings: { default: ["person"] }
"""


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "prompts" / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)
    with TestClient(create_app()) as c:
        yield c


def _payload(**overrides) -> dict:
    payload = {
        "ingest": {"plugin": "image_folder", "config": {"path": "/tmp/imgs"}},
        "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
    }
    payload.update(overrides)
    return payload


def test_validate_valid_payload_returns_valid_true(client):
    response = client.post("/api/compose/validate", json=_payload())
    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": []}


def test_validate_unknown_active_id_returns_valid_false(client):
    response = client.post(
        "/api/compose/validate",
        json=_payload(prompts={"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["nope"]}),
    )
    body = response.json()
    assert body["valid"] is False
    assert len(body["errors"]) == 1


def test_validate_malformed_payload_returns_422(client):
    response = client.post("/api/compose/validate", json={"ingest": {"plugin": "image_folder"}})
    assert response.status_code == 422
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_compose_routes.py -v`
Expected: `404 Not Found` (ruta no registrada)

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/compose.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Request

from eovrt_console.compose import validate_compose
from eovrt_console.schemas import ComposeRequest, ComposeValidationResponse

router = APIRouter()


@router.post("/api/compose/validate", response_model=ComposeValidationResponse)
def validate(payload: ComposeRequest, request: Request) -> ComposeValidationResponse:
    settings = request.app.state.settings
    errors = validate_compose(payload, settings.prompts_dir)
    return ComposeValidationResponse(valid=not errors, errors=errors)
```

Modificar `webconsole/backend/src/eovrt_console/app.py`:

```python
from eovrt_console.routers import catalog, compose
```

```python
    app.include_router(catalog.router)
    app.include_router(compose.router)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_compose_routes.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/routers/compose.py webconsole/backend/src/eovrt_console/app.py webconsole/backend/tests/test_compose_routes.py
git commit -m "feat(webconsole-backend): ruta de validación de composición"
```

---

### Task 10: Rutas de runs — crear, consultar, listar, detener

**Files:**
- Create: `webconsole/backend/src/eovrt_console/routers/runs.py`
- Modify: `webconsole/backend/src/eovrt_console/app.py` (registrar router + exception handlers)
- Test: Create `webconsole/backend/tests/test_runs_routes.py`

**Interfaces:**
- Consumes: `RunBackend`/`RunBusyError`/`RunNotFoundError` (Task 3), `validate_compose`/`build_service_run_request` (Task 7), `RunStatusResponse` (Task 6).
- Produces: `POST /api/runs`, `POST /api/runs/{run_id}/stop`, `GET /api/runs/{run_id}`, `GET /api/runs`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_runs_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  classes:
    - id: person
      phrasings: { default: ["person"] }
"""


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "prompts" / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)
    with TestClient(create_app()) as c:
        yield c, fake_service


def _payload() -> dict:
    return {
        "ingest": {"plugin": "image_folder", "config": {"path": "/tmp/imgs"}},
        "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
    }


def test_create_run_returns_run_id(client):
    c, fake = client
    response = c.post("/api/runs", json=_payload())
    assert response.status_code == 201
    assert response.json()["run_id"] == fake.state.next_run_id
    assert fake.state.last_create_payload["prompts"]["prompt_set"]["id"] == "cr01_cr02_v2_short"


def test_create_run_invalid_compose_returns_422(client):
    c, _ = client
    response = c.post(
        "/api/runs",
        json={
            "ingest": {"plugin": "image_folder", "config": {"path": "/tmp/imgs"}},
            "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["nope"]},
        },
    )
    assert response.status_code == 422


def test_create_run_busy_service_returns_409(client):
    c, fake = client
    fake.state.busy = True
    response = c.post("/api/runs", json=_payload())
    assert response.status_code == 409


def test_get_run_proxies_status(client):
    c, fake = client
    run_id = c.post("/api/runs", json=_payload()).json()["run_id"]
    response = c.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"


def test_get_unknown_run_returns_404(client):
    c, _ = client
    assert c.get("/api/runs/does-not-exist").status_code == 404


def test_stop_run_proxies_to_service(client):
    c, fake = client
    run_id = c.post("/api/runs", json=_payload()).json()["run_id"]
    response = c.post(f"/api/runs/{run_id}/stop")
    assert response.status_code == 204
    assert fake.state.stopped_run_ids == [run_id]


def test_list_runs_proxies_service(client):
    c, _ = client
    c.post("/api/runs", json=_payload())
    response = c.get("/api/runs")
    assert len(response.json()) == 1
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_runs_routes.py -v`
Expected: `404 Not Found` (rutas no registradas)

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/runs.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from eovrt_console.compose import build_service_run_request, validate_compose
from eovrt_console.run_backend import RunBusyError, RunNotFoundError
from eovrt_console.schemas import ComposeRequest, RunStatusResponse

router = APIRouter()


@router.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(payload: ComposeRequest, request: Request) -> dict:
    settings = request.app.state.settings
    run_backend = request.app.state.run_backend

    errors = validate_compose(payload, settings.prompts_dir)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    service_request = build_service_run_request(payload, settings.prompts_dir)
    try:
        run_id = run_backend.launch(service_request)
    except RunBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"run_id": run_id}


@router.post("/api/runs/{run_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
def stop_run(run_id: str, request: Request) -> Response:
    run_backend = request.app.state.run_backend
    try:
        run_backend.stop(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str, request: Request) -> RunStatusResponse:
    run_backend = request.app.state.run_backend
    try:
        body = run_backend.status(run_id)
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatusResponse(**body)


@router.get("/api/runs", response_model=list[RunStatusResponse])
def list_runs(request: Request) -> list[RunStatusResponse]:
    run_backend = request.app.state.run_backend
    return [RunStatusResponse(**r) for r in run_backend.list_runs()]
```

Modificar `webconsole/backend/src/eovrt_console/app.py`:

```python
from eovrt_console.routers import catalog, compose, runs
```

```python
    app.include_router(compose.router)
    app.include_router(runs.router)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_runs_routes.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/routers/runs.py webconsole/backend/src/eovrt_console/app.py webconsole/backend/tests/test_runs_routes.py
git commit -m "feat(webconsole-backend): rutas de creación/consulta/detención de runs"
```

---

### Task 11: `POST /api/manifests`

**Files:**
- Create: `webconsole/backend/src/eovrt_console/routers/manifests.py`
- Modify: `webconsole/backend/src/eovrt_console/app.py` (registrar router)
- Test: Create `webconsole/backend/tests/test_manifests_routes.py`

**Interfaces:**
- Consumes: `validate_compose` (Task 7), `save_manifest` (Task 5), `SaveManifestRequest` (Task 6), `RunBackend.get_model` (Task 3).
- Produces: `POST /api/manifests`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_manifests_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  classes:
    - id: person
      phrasings: { default: ["person"] }
"""


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "prompts" / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)
    with TestClient(create_app()) as c:
        yield c, tmp_path


def _payload(name: str) -> dict:
    return {
        "name": name,
        "compose": {
            "ingest": {"plugin": "image_folder", "ref": "demo_v2", "config": {}},
            "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
        },
    }


def test_create_manifest_writes_file(client):
    c, tmp_path = client
    response = c.post("/api/manifests", json=_payload("from_console"))

    assert response.status_code == 201
    manifest_path = tmp_path / "experiments" / "from_console.yaml"
    assert manifest_path.exists()
    assert response.json()["path"] == "experiments/from_console.yaml"


def test_create_manifest_uses_service_model_ref(client):
    c, tmp_path = client
    c.post("/api/manifests", json=_payload("from_console"))

    import yaml

    data = yaml.safe_load((tmp_path / "experiments" / "from_console.yaml").read_text())
    assert data["model"] == {"ref": "mock"}


def test_create_manifest_invalid_compose_returns_422(client):
    c, _ = client
    payload = _payload("bad")
    payload["compose"]["prompts"]["active_ids"] = ["nope"]
    response = c.post("/api/manifests", json=payload)
    assert response.status_code == 422


def test_create_manifest_duplicate_name_returns_409(client):
    c, _ = client
    c.post("/api/manifests", json=_payload("dup"))
    response = c.post("/api/manifests", json=_payload("dup"))
    assert response.status_code == 409
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_manifests_routes.py -v`
Expected: `404 Not Found` (ruta no registrada)

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/manifests.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from eovrt_console.compose import validate_compose
from eovrt_console.manifests_repo import save_manifest
from eovrt_console.schemas import SaveManifestRequest

router = APIRouter()


@router.post("/api/manifests", status_code=status.HTTP_201_CREATED)
def create_manifest(payload: SaveManifestRequest, request: Request) -> dict:
    settings = request.app.state.settings
    run_backend = request.app.state.run_backend

    errors = validate_compose(payload.compose, settings.prompts_dir)
    if errors:
        raise HTTPException(status_code=422, detail=errors)

    model_info = run_backend.get_model()
    try:
        path = save_manifest(
            settings.experiments_dir,
            name=payload.name,
            ingest_plugin=payload.compose.ingest.plugin,
            ingest_ref=payload.compose.ingest.ref,
            ingest_config=payload.compose.ingest.config,
            model_ref=model_info["ref"],
            prompt_set_id=payload.compose.prompts.prompt_set_id,
            active_ids=payload.compose.prompts.active_ids,
            description=payload.description,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"path": str(path.relative_to(settings.repo_root))}
```

Modificar `webconsole/backend/src/eovrt_console/app.py`:

```python
from eovrt_console.routers import catalog, compose, manifests, runs
```

```python
    app.include_router(runs.router)
    app.include_router(manifests.router)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_manifests_routes.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/routers/manifests.py webconsole/backend/src/eovrt_console/app.py webconsole/backend/tests/test_manifests_routes.py
git commit -m "feat(webconsole-backend): ruta para guardar manifiestos in-repo"
```

---

### Task 12: WebSocket de telemetría (proxy)

**Files:**
- Create: `webconsole/backend/src/eovrt_console/routers/stream.py`
- Modify: `webconsole/backend/src/eovrt_console/app.py` (registrar router)
- Test: Create `webconsole/backend/tests/test_stream_route.py`

**Interfaces:**
- Consumes: `RunBackend.stream_ws_url` (Task 3).
- Produces: `WS /api/runs/{run_id}/stream` — abre una conexión saliente al WS del servicio y reenvía cada mensaje tal cual a la SPA.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_stream_route.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    with TestClient(create_app()) as c:
        yield c, fake_service


def test_stream_relays_events_from_service(client):
    c, fake = client
    fake.state.stream_events["run_fake_001"] = [
        {"type": "started", "run_id": "run_fake_001"},
        {"type": "progress", "units_processed": 1},
        {"type": "finished", "status": "succeeded"},
    ]

    events = []
    with c.websocket_connect("/api/runs/run_fake_001/stream") as ws:
        for _ in range(3):
            events.append(ws.receive_json())

    assert [e["type"] for e in events] == ["started", "progress", "finished"]
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_stream_route.py -v`
Expected: falla al conectar (ruta WS no registrada)

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/stream.py`:

```python
from __future__ import annotations

import websockets
from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/api/runs/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: str) -> None:
    run_backend = websocket.app.state.run_backend
    upstream_url = run_backend.stream_ws_url(run_id)

    await websocket.accept()
    try:
        async with websockets.connect(upstream_url) as upstream:
            async for message in upstream:
                await websocket.send_text(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await websocket.close()
```

Modificar `webconsole/backend/src/eovrt_console/app.py`:

```python
from eovrt_console.routers import catalog, compose, manifests, runs, stream
```

```python
    app.include_router(manifests.router)
    app.include_router(stream.router)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_stream_route.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/routers/stream.py webconsole/backend/src/eovrt_console/app.py webconsole/backend/tests/test_stream_route.py
git commit -m "feat(webconsole-backend): proxy de WebSocket de telemetría"
```

---

### Task 13: Detecciones paginadas y artefactos (proxy con Range)

**Files:**
- Create: `webconsole/backend/src/eovrt_console/routers/artifacts.py`
- Modify: `webconsole/backend/src/eovrt_console/app.py` (registrar router)
- Test: Create `webconsole/backend/tests/test_artifacts_routes.py`

**Interfaces:**
- Consumes: `RunBackend.get_detections`/`stream_artifact` (Task 3).
- Produces: `GET /api/runs/{run_id}/detections`, `GET /api/runs/{run_id}/artifacts/{artifact_path:path}`.

- [ ] **Step 1: Escribir el test que falla**

Create `webconsole/backend/tests/test_artifacts_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient

from eovrt_console.app import create_app


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    with TestClient(create_app()) as c:
        yield c, fake_service


def test_get_detections_proxies_pagination(client):
    c, _ = client
    response = c.get("/api/runs/run_x/detections?page=2&page_size=10")
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 10


def test_get_artifact_returns_bytes(client):
    c, fake = client
    fake.state.artifacts["previews/0001.jpg"] = b"fake-jpeg"

    response = c.get("/api/runs/run_x/artifacts/previews/0001.jpg")

    assert response.status_code == 200
    assert response.content == b"fake-jpeg"


def test_get_artifact_forwards_range_header(client):
    c, fake = client
    fake.state.artifacts["annotated.mp4"] = b"fake-video-bytes"

    response = c.get(
        "/api/runs/run_x/artifacts/annotated.mp4", headers={"Range": "bytes=0-3"}
    )

    assert response.status_code == 200
    assert fake.state.last_artifact_range_header == "bytes=0-3"


def test_get_artifact_missing_returns_404(client):
    c, _ = client
    response = c.get("/api/runs/run_x/artifacts/does-not-exist.jpg")
    assert response.status_code == 404
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `pytest tests/test_artifacts_routes.py -v`
Expected: `404 Not Found` en todas (rutas no registradas)

- [ ] **Step 3: Implementar**

Create `webconsole/backend/src/eovrt_console/routers/artifacts.py`:

```python
from __future__ import annotations

from typing import Iterator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from eovrt_console.run_backend import ArtifactNotFoundError

router = APIRouter()


@router.get("/api/runs/{run_id}/detections")
def get_detections(run_id: str, request: Request, page: int = 1, page_size: int = 50) -> dict:
    run_backend = request.app.state.run_backend
    return run_backend.get_detections(run_id, page, page_size)


def _iter_and_close(response: httpx.Response) -> Iterator[bytes]:
    try:
        yield from response.iter_bytes()
    finally:
        response.close()


@router.get("/api/runs/{run_id}/artifacts/{artifact_path:path}")
def get_artifact(run_id: str, artifact_path: str, request: Request) -> StreamingResponse:
    run_backend = request.app.state.run_backend
    range_header = request.headers.get("range")
    try:
        upstream = run_backend.stream_artifact(run_id, artifact_path, range_header)
    except ArtifactNotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    passthrough_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() in ("content-range", "accept-ranges", "content-length")
    }
    return StreamingResponse(
        _iter_and_close(upstream),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers=passthrough_headers,
    )
```

Modificar `webconsole/backend/src/eovrt_console/app.py`:

```python
from eovrt_console.routers import artifacts, catalog, compose, manifests, runs, stream
```

```python
    app.include_router(stream.router)
    app.include_router(artifacts.router)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `pytest tests/test_artifacts_routes.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add webconsole/backend/src/eovrt_console/routers/artifacts.py webconsole/backend/src/eovrt_console/app.py webconsole/backend/tests/test_artifacts_routes.py
git commit -m "feat(webconsole-backend): detecciones paginadas y artefactos con soporte de range"
```

---

### Task 14: Test de integración end-to-end

**Files:**
- Create: `webconsole/backend/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: toda la app ensamblada (Tasks 8-13).

- [ ] **Step 1: Escribir el test de integración**

Create `webconsole/backend/tests/test_end_to_end.py`:

```python
import pytest
import yaml
from fastapi.testclient import TestClient

from eovrt_console.app import create_app

PROMPT_SET_YAML = """
prompt_set:
  id: cr01_cr02_v2_short
  classes:
    - id: person
      phrasings: { default: ["person"] }
    - id: helmet
      phrasings: { default: ["helmet"] }
"""


@pytest.fixture
def client(monkeypatch, tmp_path, fake_service):
    monkeypatch.setenv("SERVICE_URL", fake_service.base_url)
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(tmp_path))
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "prompts" / "cr01_cr02_v2_short.yaml").write_text(PROMPT_SET_YAML)
    with TestClient(create_app()) as c:
        yield c, fake_service, tmp_path


def test_full_flow_compose_validate_launch_stream_save(client):
    c, fake, tmp_path = client

    compose_payload = {
        "ingest": {"plugin": "image_folder", "ref": "demo_v2", "config": {}},
        "prompts": {"prompt_set_id": "cr01_cr02_v2_short", "active_ids": ["person", "helmet"]},
        "run": {"stride": 2},
    }

    validation = c.post("/api/compose/validate", json=compose_payload).json()
    assert validation == {"valid": True, "errors": []}

    fake.state.stream_events["run_fake_001"] = [
        {"type": "started", "run_id": "run_fake_001"},
        {"type": "finished", "status": "succeeded"},
    ]
    run_id = c.post("/api/runs", json=compose_payload).json()["run_id"]
    assert fake.state.last_create_payload["run"]["stride"] == 2

    seen_types = []
    with c.websocket_connect(f"/api/runs/{run_id}/stream") as ws:
        for _ in range(2):
            seen_types.append(ws.receive_json()["type"])
    assert seen_types == ["started", "finished"]

    status_body = c.get(f"/api/runs/{run_id}").json()
    assert status_body["status"] == "succeeded"

    manifest_response = c.post(
        "/api/manifests", json={"name": "e2e_manifest", "compose": compose_payload}
    )
    assert manifest_response.status_code == 201
    manifest = yaml.safe_load((tmp_path / "experiments" / "e2e_manifest.yaml").read_text())
    assert manifest["prompts"]["active_ids"] == ["person", "helmet"]
    assert manifest["source"] == {"ref": "demo_v2"}
```

- [ ] **Step 2: Correr el test y verificar que pasa**

Run: `pytest tests/test_end_to_end.py -v`
Expected: 1 passed

- [ ] **Step 3: Correr toda la suite del BFF**

Run: `pytest -q`
Expected: todos los tests de los Tasks 1-14 en verde.

Run: `ruff check src tests`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add webconsole/backend/tests/test_end_to_end.py
git commit -m "test(webconsole-backend): integración end-to-end compose→validate→launch→stream→manifest"
```

---

## Self-Review Notes

- **Cobertura del spec (Spec B)**: §5.1 CatalogService → Task 8; §5.2 RunComposer → Tasks 7, 9, 10; §5.3 ManifestWriter → Tasks 5, 11; §5.4 RunBackend → Task 3; §5.5 TelemetryProxy/ResultsProxy → Tasks 12, 13; §3.1 invariante two-root loader → `prompts_dir`/`experiments_dir` en `settings.py` (Task 2) apuntan siempre a la raíz del repo, nunca a `webconsole/`; §4 relación con el servicio y modelo de nodo → `RunBackend` (Task 3) es la costura, un target en Fase 1 (documentado en Global Constraints); §8 manejo de errores → 422/409/404 mapeados en Tasks 9-11; §11.2 streaming de artefactos sin bufferizar → Task 13 usa `StreamingResponse` + `iter_bytes()` + forward de `Range`.
- **Desviaciones documentadas**: (1) el parámetro `node` de las firmas de Spec B se omite en Fase 1 — una instancia de `RunBackend` ya representa un target; Fase 2 lo generaliza a un diccionario `{node_id: RunBackend}` sin cambiar esta clase. (2) el flag `frozen` en `PromptSetSummary` lee un campo opcional `prompt_set.frozen` que hoy no existe en ningún YAML real (todos devuelven `False`) — es forward-compatible, no una fabricación: si algún prompt set define `frozen: true` en el futuro, se refleja solo con agregar esa clave al YAML. (3) `list_manifests` no recorre `experiments/bench_v2/` (no recursivo) — la matriz BENCH queda fuera del compositor ad-hoc, consistente con "evaluación BENCH + compare-runs" como ítem de Fase 2 en Spec B.
- **Placeholder scan**: sin TBD/TODO; todo el código de cada step es completo.
- **Consistencia de tipos**: `ComposeRequest`/`ComposeIngestRequest`/`ComposePromptsRequest`/`ComposeRunParams` definidos una vez en Task 6 y reusados sin renombrar en Tasks 7, 9, 10, 11, 14. `RunBackend` (Task 3) expone exactamente los métodos que Tasks 8-13 consumen (`get_model`, `get_ingest_plugins`, `get_datasets`, `launch`, `stop`, `status`, `list_runs`, `get_detections`, `stream_artifact`, `stream_ws_url`) — ninguno inventado tardíamente.
