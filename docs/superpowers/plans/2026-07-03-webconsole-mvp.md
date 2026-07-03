# Webconsole MVP (Spec B, Fase 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la consola web MVP (`webconsole/`): un BFF FastAPI + SPA React que compone, lanza, monitorea en vivo y explora corridas contra **una instancia local del servicio media-plane** (Spec A Fase 1, ya implementado en `e-ovrt_media-plane` rama `feature/inference-service`).

**Architecture:** BFF FastAPI (`webconsole/backend`, paquete `eovrt_webconsole`) como **cliente HTTP/WS puro** del servicio (nunca importa `eovrt_media`): proxya catálogos/runs/artefactos/WS y resuelve `prompts/` y `experiments/` in-repo. Módulo de **traducción única** manifiesto ↔ composición ↔ run request. SPA React/Vite/TS (`webconsole/frontend`) servida por el BFF (un solo origen; el servicio **no tiene CORS**, el proxy es obligatorio).

**Tech Stack:** Python ≥3.11 (máquina actual: 3.14 — usar `python3`), FastAPI, httpx (+ASGITransport en tests), PyYAML, websockets, pytest + pytest-asyncio; Node ≥20 (actual: 22), React 18, Vite 5, TypeScript, react-router (HashRouter), Vitest.

## Global Constraints

- **Regla del workspace (projects/CLAUDE.md):** los pasos de commit se ejecutan SOLO si el usuario habilitó commits explícitamente en la sesión de ejecución. Si no, dejar los cambios en el working tree y reportar qué se habría commiteado.
- Repo: `/home/simonll4/projects/e-ovrt_experimental-setup`. Todos los paths de abajo son relativos a esa raíz. El backend se testea desde `webconsole/backend/` con su propio venv.
- El BFF **NUNCA importa `eovrt_media`** ni lee `runs/` por filesystem: todo pasa por la API del servicio. El contrato del servicio es el implementado (verificado 2026-07-03), no la Spec A literal.
- El run request al servicio **nunca lleva sección `model`** (→ 422). Thresholds son read-only desde `GET /api/model`.
- La ref de dataset viaja como `ingest.config.dataset` (el servicio la retraduce a `source: {ref}`).
- **Policy MVP del BFF:** plugins permitidos = `{image_folder, video_file}` (RTSP queda fuera por policy de consola, no del catálogo). Sets congelados = convención del BFF (`EOVRT_CONSOLE_FROZEN_SETS`, default `cr01_cr02_bench_v2`).
- Eventos WS reales del servicio: `metric{unit_id,fps,latency_total_ms,detections_count,gpu_memory_mb}`, `detection{unit_id,count}`, `error{unit_id,stage,message}`, `state{status,error}`. p95/per-label son post-run (`summary.json`). El GET de un run **activo** devuelve solo `{run_id,status,started_at,model}`; fallback de WS caído = **reconectar el WS**.
- Puertos: servicio 8080, BFF 8090, Vite dev 5173. Formato prompts: los YAML de `prompts/` tienen clave raíz `prompt_set:`; `set_inline` recibe el dict **interno**.
- `pytest -q` (backend) y `npx vitest run` (frontend) deben pasar al final de cada task. `ruff check src tests` con `line-length = 100`.
- Tests del backend contra un **servicio fake** (réplica de la API en `tests/fake_service.py`); nunca requieren el media-plane instalado ni levantado.

## File Structure (resultado final)

```
webconsole/
├── Makefile                      # install / test / dev / build / serve / smoke
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── src/eovrt_webconsole/
│   │   ├── __init__.py
│   │   ├── settings.py           # ConsoleSettings desde env + autodiscover repo root
│   │   ├── app.py                # create_app(settings, service_transport) + lifespan + SPA estática
│   │   ├── repo_catalog.py       # prompts/ y experiments/ in-repo (frozen policy)
│   │   ├── translation.py        # Composition + manifiesto ↔ composición ↔ run request
│   │   ├── run_backend.py        # RunBackend: cliente httpx del servicio (la costura §5.5)
│   │   ├── manifest_writer.py    # escritura atómica de manifiestos in-repo
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── meta.py           # GET /api/health, GET /api/target
│   │       ├── catalog.py        # prompt-sets, experiments (in-repo) + ingest-plugins, datasets (proxy)
│   │       ├── compose.py        # POST /api/compose/validate
│   │       ├── runs.py           # POST/GET /api/runs, stop, detections, artifacts (proxy)
│   │       ├── stream.py         # WS /api/runs/{id}/stream (proxy con coalescing)
│   │       └── manifests.py      # POST /api/manifests
│   └── tests/
│       ├── conftest.py           # fixtures: repo tmp, fake service, client
│       ├── fake_service.py       # réplica de la API del servicio media-plane
│       ├── test_settings.py
│       ├── test_meta.py
│       ├── test_repo_catalog.py
│       ├── test_catalog_proxy.py
│       ├── test_translation.py   # incluye ida-y-vuelta sobre los manifiestos REALES del repo
│       ├── test_run_backend.py
│       ├── test_compose.py
│       ├── test_runs_router.py
│       ├── test_artifacts_proxy.py
│       ├── test_stream_proxy.py  # contra fake service en uvicorn real (WS)
│       └── test_manifest_writer.py
└── frontend/
    ├── package.json / vite.config.ts / tsconfig.json / index.html
    └── src/
        ├── main.tsx / App.tsx    # HashRouter + header con TargetBadge
        ├── types.ts / api.ts     # cliente tipado del BFF
        ├── stream.ts             # applyEvent (reducer puro) + useRunStream (WS + reconexión)
        ├── pages/RunsPage.tsx
        ├── pages/ComposePage.tsx
        ├── pages/RunDetailPage.tsx
        ├── pages/CatalogPage.tsx
        ├── components/Sparkline.tsx
        └── __tests__/stream.test.ts, api.test.ts
```

---

### Task 1: Scaffold backend — pyproject + ConsoleSettings + app + `/api/health`

**Files:**
- Create: `webconsole/backend/pyproject.toml`, `webconsole/backend/src/eovrt_webconsole/__init__.py`, `.../settings.py`, `.../app.py`, `.../routers/__init__.py`, `.../routers/meta.py`
- Test: `webconsole/backend/tests/test_settings.py`, `webconsole/backend/tests/test_meta.py` (solo health en esta task)

**Interfaces:**
- Produces: `ConsoleSettings` (campos: `service_url: str`, `repo_root: Path`, `frozen_set_ids: frozenset[str]`, `mvp_plugins: frozenset[str]`, `hydration_limit: int`; propiedades `prompts_dir`/`experiments_dir`; `from_env(env) -> ConsoleSettings`); `create_app(settings: ConsoleSettings | None = None, service_transport: httpx.AsyncBaseTransport | None = None) -> FastAPI` con `app.state.settings` y `app.state.http` (httpx.AsyncClient hacia el servicio, creado en lifespan).

- [ ] **Step 1: Crear venv e instalar deps**

```bash
cd webconsole/backend
python3 -m venv .venv && source .venv/bin/activate
```

```toml
# webconsole/backend/pyproject.toml
[project]
name = "eovrt-webconsole"
version = "0.1.0"
description = "Web console BFF para el servicio media-plane (Spec B, MVP)"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]",
    "httpx",
    "pyyaml",
    "websockets>=12",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff"]

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```bash
pip install --upgrade pip && pip install -e ".[dev]"
```

- [ ] **Step 2: Tests que fallan**

```python
# webconsole/backend/tests/test_settings.py
from pathlib import Path

import pytest

from eovrt_webconsole.settings import ConsoleSettings


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    return tmp_path


def test_from_env_minimo(tmp_path):
    s = ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(_repo(tmp_path))})
    assert s.service_url == "http://localhost:8080"
    assert s.frozen_set_ids == frozenset({"cr01_cr02_bench_v2"})
    assert s.mvp_plugins == frozenset({"image_folder", "video_file"})
    assert s.prompts_dir == tmp_path / "prompts"
    assert s.experiments_dir == tmp_path / "experiments"


def test_from_env_completo(tmp_path):
    s = ConsoleSettings.from_env({
        "EOVRT_CONSOLE_REPO_ROOT": str(_repo(tmp_path)),
        "EOVRT_CONSOLE_SERVICE_URL": "http://gpu-node:8080/",
        "EOVRT_CONSOLE_FROZEN_SETS": "a, b",
    })
    assert s.service_url == "http://gpu-node:8080"  # sin slash final
    assert s.frozen_set_ids == frozenset({"a", "b"})


def test_autodiscover_repo_root():
    # El repo real tiene prompts/ y experiments/ en la raíz: el discovery sube desde el módulo.
    s = ConsoleSettings.from_env({})
    assert (s.repo_root / "prompts").is_dir()
    assert (s.repo_root / "experiments").is_dir()


def test_repo_root_invalido(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(tmp_path / "nada")})
```

```python
# webconsole/backend/tests/test_meta.py
from pathlib import Path

from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings


def _settings(tmp_path: Path) -> ConsoleSettings:
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "experiments").mkdir(exist_ok=True)
    return ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(tmp_path)})


def test_health_ok(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 3: Verificar que fallan**

Run: `cd webconsole/backend && pytest -q`
Expected: ERROR con `ModuleNotFoundError: eovrt_webconsole`

- [ ] **Step 4: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/__init__.py
"""BFF de la consola web E-OVRT (Spec B, MVP) — cliente del servicio media-plane."""
```

```python
# webconsole/backend/src/eovrt_webconsole/settings.py
"""Configuración de la consola desde variables de entorno EOVRT_CONSOLE_*."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FROZEN_SETS = frozenset({"cr01_cr02_bench_v2"})
# Policy MVP (Spec B §6): RTSP/oak_d quedan fuera por decisión de la consola,
# no del catálogo del servicio (que marca rtsp como disponible).
MVP_PLUGINS = frozenset({"image_folder", "video_file"})


def _discover_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "prompts").is_dir() and (candidate / "experiments").is_dir():
            return candidate
    raise FileNotFoundError(
        "No se encontró la raíz del repo (directorio con prompts/ y experiments/); "
        "definí EOVRT_CONSOLE_REPO_ROOT"
    )


@dataclass(frozen=True)
class ConsoleSettings:
    service_url: str
    repo_root: Path
    frozen_set_ids: frozenset[str]
    mvp_plugins: frozenset[str] = MVP_PLUGINS
    hydration_limit: int = 50

    @property
    def prompts_dir(self) -> Path:
        return self.repo_root / "prompts"

    @property
    def experiments_dir(self) -> Path:
        return self.repo_root / "experiments"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ConsoleSettings:
        env = os.environ if env is None else env
        root_raw = env.get("EOVRT_CONSOLE_REPO_ROOT")
        if root_raw:
            repo_root = Path(root_raw)
            if not ((repo_root / "prompts").is_dir() and (repo_root / "experiments").is_dir()):
                raise FileNotFoundError(
                    f"EOVRT_CONSOLE_REPO_ROOT inválido (sin prompts/ y experiments/): {repo_root}"
                )
        else:
            repo_root = _discover_repo_root(Path(__file__).resolve())
        frozen_raw = env.get("EOVRT_CONSOLE_FROZEN_SETS")
        frozen = (
            frozenset(s.strip() for s in frozen_raw.split(",") if s.strip())
            if frozen_raw is not None
            else DEFAULT_FROZEN_SETS
        )
        return cls(
            service_url=env.get("EOVRT_CONSOLE_SERVICE_URL", "http://localhost:8080").rstrip("/"),
            repo_root=repo_root,
            frozen_set_ids=frozen,
            hydration_limit=int(env.get("EOVRT_CONSOLE_HYDRATION_LIMIT", "50")),
        )
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/__init__.py
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/meta.py
"""Salud del BFF y estado agregado del target (servicio media-plane)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

```python
# webconsole/backend/src/eovrt_webconsole/app.py
"""Factory de la app FastAPI del BFF de la consola."""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from eovrt_webconsole.routers import meta
from eovrt_webconsole.settings import ConsoleSettings


def create_app(
    settings: ConsoleSettings | None = None,
    service_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or ConsoleSettings.from_env()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(
            base_url=settings.service_url, transport=service_transport, timeout=30.0
        )
        # Task 6 agrega acá: app.state.backend = RunBackend(app.state.http)
        yield
        await app.state.http.aclose()

    app = FastAPI(title="eovrt-webconsole", lifespan=_lifespan)
    app.state.settings = settings
    app.include_router(meta.router)
    return app
```

- [ ] **Step 5: Verificar que pasan + lint**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo (5 tests).

- [ ] **Step 6: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend
git commit -m "feat(webconsole): scaffold del BFF — settings, app factory y /api/health"
```

---

### Task 2: Servicio fake (fixture) + `GET /api/target`

**Files:**
- Create: `webconsole/backend/tests/fake_service.py`, `webconsole/backend/tests/conftest.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/meta.py`
- Test: `webconsole/backend/tests/test_meta.py` (agregar tests de target)

**Interfaces:**
- Produces: `FakeState` (mutable: `ready: bool`, `active_run_id: str | None`, `launched: list[dict]`, `stopped: list[str]`, `stream_events: list[dict]`); `make_fake_service(state: FakeState) -> FastAPI` — réplica exacta de la API del servicio media-plane Fase 1 (shapes verificados contra la implementación real). Fixtures `fake_state`, `repo` (mini-repo con prompts/experiments), `client` (TestClient del BFF cableado al fake por ASGITransport). Endpoint `GET /api/target -> {service_url, healthy, ready, model}`.

- [ ] **Step 1: Escribir el fake service y fixtures**

```python
# webconsole/backend/tests/fake_service.py
"""Réplica mínima de la API del servicio media-plane (Fase 1) para tests del BFF.

Shapes copiados de la implementación real (e-ovrt_media-plane, service/):
runs.py, model.py, catalog.py, run_manager.py, stream.py, events.py.
"""
from __future__ import annotations

from fastapi import FastAPI, Query, WebSocket
from fastapi.responses import JSONResponse, Response

MODEL = {
    "ref": "mock",
    "name": "mock",
    "adapter": "mock",
    "device": "cpu",
    "thresholds": {"box": 0.35, "text": 0.25, "confidence": None, "iou": None},
    "runtime": {"half_precision": False, "warmup": False},
}
PLUGINS = [
    {"id": "image_folder", "kind": "bounded", "available": True, "description": "Carpeta de imágenes"},
    {"id": "video_file", "kind": "bounded", "available": True, "description": "Archivo de video local"},
    {"id": "rtsp", "kind": "live", "available": True, "description": "Stream RTSP (cámara IP)"},
    {"id": "oak_d", "kind": "live", "available": False, "description": "OAK-D Pro PoE (no disponible)"},
]
DATASETS = [
    {"id": "demo_v2", "description": "CHV demo v2", "path": "/data/demo", "available": True},
    {"id": "bench_v2_test", "description": "BENCH v2 test", "path": "/data/bench", "available": True},
    {"id": "roto", "description": "no montado", "path": "/nope", "available": False},
]
SUMMARY_FINISHED = {
    "schema_version": "media.summary.v2",
    "run_id": "run_done_1",
    "status": "succeeded",
    "model_name": "mock",
    "prompt_set_id": "demo_set",
    "source_type": "image_folder",
    "units_processed": 3,
    "total_detections": 7,
    "detections_by_label": {"person": 5, "helmet": 2},
    "p95_latency_ms": 40.0,
    "fps_effective": 12.5,
    "duration_seconds": 0.24,
    "device": "cpu",
    "started_at": "2026-07-03T10:00:00+00:00",
}
DETECTIONS = [{"unit_id": f"u{i}", "detections": [{"label": "person"}]} for i in range(5)]
ARTIFACTS = {"summary.json": b'{"status": "succeeded"}', "previews/u0.preview.jpg": b"JPEGDATA"}
DEFAULT_STREAM_EVENTS = [
    {"type": "metric", "unit_id": "u0", "fps": 1.0, "latency_total_ms": 100.0,
     "detections_count": 1, "gpu_memory_mb": 0.0},
    {"type": "metric", "unit_id": "u1", "fps": 2.0, "latency_total_ms": 90.0,
     "detections_count": 2, "gpu_memory_mb": 0.0},
    {"type": "detection", "unit_id": "u1", "count": 2},
    {"type": "error", "unit_id": "u1", "stage": "inference", "message": "boom"},
    {"type": "state", "status": "succeeded", "error": None},
]


class FakeState:
    def __init__(self) -> None:
        self.ready = True
        self.active_run_id: str | None = None
        self.launched: list[dict] = []
        self.stopped: list[str] = []
        self.stream_events: list[dict] = list(DEFAULT_STREAM_EVENTS)


def make_fake_service(state: FakeState) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz():
        if state.ready:
            return {"status": "ready", "model": MODEL["ref"]}
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": None})

    @app.get("/api/model")
    def model():
        return MODEL

    @app.get("/api/catalog/ingest-plugins")
    def plugins():
        return PLUGINS

    @app.get("/api/catalog/datasets")
    def datasets():
        return DATASETS

    @app.post("/api/runs", status_code=201)
    async def create_run(body: dict):
        if "model" in body:  # espejo del extra="forbid" del RunRequest real
            return JSONResponse(status_code=422, content={"detail": "sección 'model' no permitida"})
        if state.active_run_id:
            return JSONResponse(
                status_code=409,
                content={"detail": "run activo", "active_run_id": state.active_run_id},
            )
        state.launched.append(body)
        state.active_run_id = "run_active_1"
        return {"run_id": "run_active_1"}

    @app.get("/api/runs")
    def list_runs():
        runs = []
        if state.active_run_id:
            runs.append({"run_id": state.active_run_id, "status": "running"})
        runs.append({"run_id": "run_done_1", "status": "succeeded"})
        return runs

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        if run_id == state.active_run_id:
            return {"run_id": run_id, "status": "running",
                    "started_at": "2026-07-03T12:00:00+00:00", "model": MODEL["ref"]}
        if run_id == "run_done_1":
            return {"run_id": run_id, "status": "succeeded", "summary": SUMMARY_FINISHED}
        return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})

    @app.post("/api/runs/{run_id}/stop", status_code=202)
    def stop_run(run_id: str):
        if run_id != state.active_run_id and run_id != "run_done_1":
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        state.stopped.append(run_id)
        return {"run_id": run_id, "stopping": True}

    @app.get("/api/runs/{run_id}/detections")
    def detections(run_id: str, page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
        if run_id != "run_done_1":
            return JSONResponse(status_code=404, content={"detail": "Sin detecciones"})
        start = (page - 1) * page_size
        items = DETECTIONS[start : start + page_size]
        return {"page": page, "page_size": page_size, "total": len(DETECTIONS), "items": items}

    @app.get("/api/runs/{run_id}/artifacts/{artifact_path:path}")
    def artifact(run_id: str, artifact_path: str, request_range: str | None = None):
        data = ARTIFACTS.get(artifact_path)
        if run_id != "run_done_1" or data is None:
            return JSONResponse(status_code=404, content={"detail": "Artefacto no encontrado"})
        return Response(content=data, media_type="application/octet-stream",
                        headers={"accept-ranges": "bytes"})

    @app.websocket("/api/runs/{run_id}/stream")
    async def stream(ws: WebSocket, run_id: str):
        await ws.accept()
        if run_id not in (state.active_run_id, "run_done_1"):
            await ws.close(code=4404)
            return
        for event in state.stream_events:
            await ws.send_json(event)
        await ws.close(code=1000)

    return app
```

```python
# webconsole/backend/tests/conftest.py
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service

PROMPT_SET_YAML = """\
prompt_set:
  id: demo_set
  description: "Set de prueba"
  language: en
  classes:
    - id: person
      role: entity
      phrasings: { default: ["person"] }
    - id: helmet
      role: ppe
      phrasings: { default: ["helmet"] }
"""

FROZEN_SET_YAML = """\
prompt_set:
  id: frozen_set
  description: "Congelado para BENCH"
  classes:
    - id: person
      phrasings: { default: ["person"] }
"""

MANIFEST_YAML = """\
run:
  scenario: DBE
  name: demo_manifest
source:
  ref: demo_v2
model:
  ref: grounding-dino/gdino-tiny
prompts:
  ref: demo_set
  active_ids: [person, helmet]
"""

BENCH_MANIFEST_YAML = """\
run:
  scenario: DBE
  name: bench_manifest
source:
  ref: bench_v2_test
rate_control:
  stride: 2
model:
  ref: yoloe/yoloe-26l
prompts:
  ref: frozen_set
  active_ids: [person]
outputs:
  save_annotated_video: true
"""


@pytest.fixture
def fake_state() -> FakeState:
    return FakeState()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments" / "bench_v2").mkdir(parents=True)
    (tmp_path / "prompts" / "demo_set.yaml").write_text(PROMPT_SET_YAML)
    (tmp_path / "prompts" / "frozen_set.yaml").write_text(FROZEN_SET_YAML)
    (tmp_path / "experiments" / "demo_manifest.yaml").write_text(MANIFEST_YAML)
    (tmp_path / "experiments" / "bench_v2" / "bench_manifest.yaml").write_text(BENCH_MANIFEST_YAML)
    return tmp_path


@pytest.fixture
def settings(repo: Path) -> ConsoleSettings:
    return ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset({"frozen_set"}),
    )


@pytest.fixture
def client(settings: ConsoleSettings, fake_state: FakeState):
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    app = create_app(settings, service_transport=transport)
    with TestClient(app) as test_client:
        yield test_client
```

- [ ] **Step 2: Tests de target que fallan**

Agregar a `webconsole/backend/tests/test_meta.py`:

```python
def test_target_ready(client):
    r = client.get("/api/target")
    assert r.status_code == 200
    body = r.json()
    assert body["healthy"] is True
    assert body["ready"] is True
    assert body["model"]["ref"] == "mock"
    assert body["model"]["thresholds"]["box"] == 0.35  # read-only para la UI


def test_target_no_ready(client, fake_state):
    fake_state.ready = False
    body = client.get("/api/target").json()
    assert body["healthy"] is True
    assert body["ready"] is False
    assert body["model"] is None
```

- [ ] **Step 3: Verificar que fallan**

Run: `pytest tests/test_meta.py -q`
Expected: FAIL con 404 en `/api/target`

- [ ] **Step 4: Implementación**

Agregar a `webconsole/backend/src/eovrt_webconsole/routers/meta.py`:

```python
import httpx
from fastapi import Request


@router.get("/target")
async def target(request: Request) -> dict:
    """Estado agregado de la instancia del servicio: healthz + readyz + modelo."""
    http: httpx.AsyncClient = request.app.state.http
    settings = request.app.state.settings
    out: dict = {"service_url": settings.service_url, "healthy": False, "ready": False, "model": None}
    try:
        out["healthy"] = (await http.get("/healthz")).status_code == 200
        out["ready"] = (await http.get("/readyz")).status_code == 200
        if out["ready"]:
            out["model"] = (await http.get("/api/model")).json()
    except httpx.HTTPError:
        pass  # servicio caído: healthy/ready quedan en False
    return out
```

- [ ] **Step 5: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 6: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/tests webconsole/backend/src/eovrt_webconsole/routers/meta.py
git commit -m "feat(webconsole): fake service para tests y GET /api/target agregado"
```

---

### Task 3: Catálogos in-repo — prompt sets (frozen) y experiments

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/repo_catalog.py`, `webconsole/backend/src/eovrt_webconsole/routers/catalog.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (incluir router)
- Test: `webconsole/backend/tests/test_repo_catalog.py`

**Interfaces:**
- Produces: `list_prompt_sets(prompts_dir: Path, frozen_ids: frozenset[str]) -> list[dict]` (cada item: `{id, description, language, frozen: bool, classes: [{id, role, enabled_by_default, phrasings}]}`); `get_prompt_set(prompts_dir: Path, set_id: str) -> dict | None` (devuelve el dict **interno** de `prompt_set:` crudo — es lo que viaja como `set_inline`); `list_experiments(experiments_dir: Path) -> list[dict]` (`{id: relpath-sin-.yaml (posix), group: subdir-relativo-o-"", manifest: dict}`). Router: `GET /api/catalog/prompt-sets`, `GET /api/catalog/experiments`.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_repo_catalog.py
from eovrt_webconsole.repo_catalog import get_prompt_set, list_experiments, list_prompt_sets


def test_list_prompt_sets_con_frozen(repo):
    sets = {s["id"]: s for s in list_prompt_sets(repo / "prompts", frozenset({"frozen_set"}))}
    assert set(sets) == {"demo_set", "frozen_set"}
    assert sets["frozen_set"]["frozen"] is True
    assert sets["demo_set"]["frozen"] is False
    assert [c["id"] for c in sets["demo_set"]["classes"]] == ["person", "helmet"]
    assert sets["demo_set"]["classes"][0]["phrasings"] == {"default": ["person"]}


def test_get_prompt_set_devuelve_dict_interno(repo):
    ps = get_prompt_set(repo / "prompts", "demo_set")
    assert ps["id"] == "demo_set"
    assert "classes" in ps  # shape de PromptSet (set_inline), sin la clave raíz prompt_set


def test_get_prompt_set_inexistente(repo):
    assert get_prompt_set(repo / "prompts", "nope") is None


def test_list_experiments_recursivo_con_grupos(repo):
    exps = {e["id"]: e for e in list_experiments(repo / "experiments")}
    assert set(exps) == {"demo_manifest", "bench_v2/bench_manifest"}
    assert exps["demo_manifest"]["group"] == ""
    assert exps["bench_v2/bench_manifest"]["group"] == "bench_v2"
    assert exps["demo_manifest"]["manifest"]["source"] == {"ref": "demo_v2"}


def test_endpoints_catalogo_in_repo(client):
    sets = client.get("/api/catalog/prompt-sets").json()
    assert {s["id"] for s in sets} == {"demo_set", "frozen_set"}
    exps = client.get("/api/catalog/experiments").json()
    assert {e["id"] for e in exps} == {"demo_manifest", "bench_v2/bench_manifest"}
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_repo_catalog.py -q`
Expected: FAIL con `ModuleNotFoundError: eovrt_webconsole.repo_catalog`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/repo_catalog.py
"""Catálogos in-repo: prompt sets (prompts/) y manifiestos (experiments/)."""
from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text())
    except (yaml.YAMLError, OSError):
        return None
    return data if isinstance(data, dict) else None


def list_prompt_sets(prompts_dir: Path, frozen_ids: frozenset[str]) -> list[dict]:
    out: list[dict] = []
    if not prompts_dir.is_dir():
        return out
    for path in sorted(prompts_dir.glob("*.yaml")):
        data = _load_yaml(path)
        prompt_set = (data or {}).get("prompt_set")
        if not isinstance(prompt_set, dict) or "id" not in prompt_set:
            continue  # archivo ilegible o sin formato prompt_set: se omite
        out.append(
            {
                "id": prompt_set["id"],
                "description": prompt_set.get("description"),
                "language": prompt_set.get("language"),
                "frozen": prompt_set["id"] in frozen_ids,
                "classes": [
                    {
                        "id": c.get("id"),
                        "role": c.get("role"),
                        "enabled_by_default": c.get("enabled_by_default", True),
                        "phrasings": c.get("phrasings", {}),
                    }
                    for c in prompt_set.get("classes", [])
                ],
            }
        )
    return out


def get_prompt_set(prompts_dir: Path, set_id: str) -> dict | None:
    """Devuelve el dict interno de `prompt_set:` — el shape exacto de `set_inline`."""
    if not prompts_dir.is_dir():
        return None
    for path in sorted(prompts_dir.glob("*.yaml")):
        prompt_set = (_load_yaml(path) or {}).get("prompt_set")
        if isinstance(prompt_set, dict) and prompt_set.get("id") == set_id:
            return prompt_set
    return None


def list_experiments(experiments_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not experiments_dir.is_dir():
        return out
    for path in sorted(experiments_dir.rglob("*.yaml")):
        manifest = _load_yaml(path)
        if manifest is None:
            continue
        rel = path.relative_to(experiments_dir)
        out.append(
            {
                "id": rel.with_suffix("").as_posix(),
                "group": rel.parent.as_posix() if rel.parent != Path(".") else "",
                "manifest": manifest,
            }
        )
    return out
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/catalog.py
"""Catálogos: in-repo (prompts/experiments) y proxy del servicio (Task 4)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from eovrt_webconsole.repo_catalog import list_experiments, list_prompt_sets

router = APIRouter(prefix="/api/catalog")


@router.get("/prompt-sets")
def prompt_sets(request: Request) -> list[dict]:
    settings = request.app.state.settings
    return list_prompt_sets(settings.prompts_dir, settings.frozen_set_ids)


@router.get("/experiments")
def experiments(request: Request) -> list[dict]:
    return list_experiments(request.app.state.settings.experiments_dir)
```

En `app.py`, junto al include existente:

```python
from eovrt_webconsole.routers import catalog, meta
...
    app.include_router(meta.router)
    app.include_router(catalog.router)
```

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests/test_repo_catalog.py
git commit -m "feat(webconsole): catalogos in-repo de prompt sets y experiments"
```

---

### Task 4: Proxy de catálogos del servicio (plugins con policy MVP + datasets)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/catalog.py`
- Test: `webconsole/backend/tests/test_catalog_proxy.py`

**Interfaces:**
- Produces: `GET /api/catalog/ingest-plugins` → items del servicio + campo **`mvp_enabled: bool`** (policy de consola: `settings.mvp_plugins` ∩ `available`); `GET /api/catalog/datasets` → pass-through del servicio. Ante servicio caído: `502 {"detail": ...}`.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_catalog_proxy.py
def test_ingest_plugins_con_policy_mvp(client):
    plugins = {p["id"]: p for p in client.get("/api/catalog/ingest-plugins").json()}
    assert set(plugins) == {"image_folder", "video_file", "rtsp", "oak_d"}
    assert plugins["image_folder"]["mvp_enabled"] is True
    assert plugins["video_file"]["mvp_enabled"] is True
    # rtsp está available en el servicio, pero fuera del MVP por policy del BFF
    assert plugins["rtsp"]["available"] is True
    assert plugins["rtsp"]["mvp_enabled"] is False
    assert plugins["oak_d"]["mvp_enabled"] is False


def test_datasets_pass_through(client):
    datasets = {d["id"]: d for d in client.get("/api/catalog/datasets").json()}
    assert "demo_v2" in datasets
    assert datasets["roto"]["available"] is False


def test_servicio_caido_502(settings):
    import httpx
    from fastapi.testclient import TestClient

    from eovrt_webconsole.app import create_app

    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    app = create_app(settings, service_transport=httpx.MockTransport(_down))
    with TestClient(app) as c:
        assert c.get("/api/catalog/ingest-plugins").status_code == 502
        assert c.get("/api/catalog/datasets").status_code == 502
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_catalog_proxy.py -q`
Expected: FAIL con 404 en `/api/catalog/ingest-plugins`

- [ ] **Step 3: Implementación**

Agregar a `routers/catalog.py`:

```python
import httpx
from fastapi import HTTPException


async def _service_get(request: Request, path: str) -> list[dict]:
    http: httpx.AsyncClient = request.app.state.http
    try:
        response = await http.get(path)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Servicio media-plane inaccesible: {exc}") from exc
    return response.json()


@router.get("/ingest-plugins")
async def ingest_plugins(request: Request) -> list[dict]:
    settings = request.app.state.settings
    plugins = await _service_get(request, "/api/catalog/ingest-plugins")
    # mvp_enabled es policy de la CONSOLA (Spec B §6): el catálogo del servicio marca
    # rtsp como disponible, pero el MVP solo lanza fuentes acotadas.
    return [
        {**p, "mvp_enabled": p["id"] in settings.mvp_plugins and p.get("available", False)}
        for p in plugins
    ]


@router.get("/datasets")
async def datasets_proxy(request: Request) -> list[dict]:
    return await _service_get(request, "/api/catalog/datasets")
```

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole/routers/catalog.py webconsole/backend/tests/test_catalog_proxy.py
git commit -m "feat(webconsole): proxy de catalogos del servicio con policy MVP de plugins"
```

---

### Task 5: Módulo de traducción — manifiesto ↔ composición ↔ run request

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/translation.py`
- Test: `webconsole/backend/tests/test_translation.py`

**Interfaces:**
- Produces (dueño único de la traducción, Spec B §5.3/§5.4):
  - `Composition` (Pydantic, `extra="forbid"` en todos los niveles): `ingest: IngestSpec{plugin: str, config: dict}`, `prompts: PromptsSpec{set_id: str, active_ids: list[str] | None}`, `run: RunParams{stride: int|None, max_units: int|None, save_annotated_video: bool=False, save_previews: bool=True, name: str|None}`, `manifest_model_ref: str | None` (para la policy §5.4), `confirm_target_model: bool = False`.
  - `composition_to_run_request(comp: Composition, prompts_dir: Path) -> dict` — resuelve el set in-repo → `set_inline`; **nunca** incluye `model`. Lanza `UnknownPromptSetError(ValueError)`.
  - `manifest_to_composition(manifest: dict) -> Composition` — `source.ref` → `ingest.config.dataset`; `model.ref` → `manifest_model_ref`.
  - `composition_to_manifest(comp: Composition, target_model_ref: str) -> dict` — formato declarativo actual; `model.ref` = `manifest_model_ref` si existe, sino el del target.
- Nota semántica: el round-trip preserva `source`, `prompts.ref/active_ids`, `rate_control.stride`, `run.name/max_units`, `outputs` y `model.ref`. **`model.device` y `run.description/scenario` no se preservan** (el device es de la instancia ahora; simplificación documentada).

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_translation.py
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.translation import (
    Composition,
    UnknownPromptSetError,
    composition_to_manifest,
    composition_to_run_request,
    manifest_to_composition,
)

# Raíz REAL del repo (tests corren desde webconsole/backend): ida-y-vuelta sobre
# los manifiestos reales de experiments/ (incluida la matriz bench_v2/).
REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_MANIFESTS = sorted((REPO_ROOT / "experiments").rglob("*.yaml"))


def _composition(**overrides) -> Composition:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 2, "max_units": 10, "save_annotated_video": True},
    }
    body.update(overrides)
    return Composition(**body)


def test_composition_to_run_request(repo):
    raw = composition_to_run_request(_composition(), repo / "prompts")
    assert "model" not in raw  # el modelo NUNCA viaja (422 del servicio)
    assert raw["ingest"] == {"plugin": "image_folder", "config": {"dataset": "demo_v2"}}
    assert raw["prompts"]["set_inline"]["id"] == "demo_set"
    assert raw["prompts"]["active_ids"] == ["person"]
    assert raw["run"]["stride"] == 2
    assert raw["run"]["max_units"] == 10
    assert raw["run"]["save_annotated_video"] is True
    assert raw["run"]["save_previews"] is True


def test_composition_to_run_request_set_inexistente(repo):
    comp = _composition(prompts={"set_id": "nope", "active_ids": None})
    with pytest.raises(UnknownPromptSetError):
        composition_to_run_request(comp, repo / "prompts")


def test_manifest_to_composition_dataset_ref():
    manifest = {
        "run": {"scenario": "DBE", "name": "x"},
        "source": {"ref": "bench_v2_test"},
        "rate_control": {"stride": 3},
        "model": {"ref": "yoloe/yoloe-26l", "device": "cuda"},
        "prompts": {"ref": "frozen_set", "active_ids": ["person"]},
        "outputs": {"save_annotated_video": True},
    }
    comp = manifest_to_composition(manifest)
    assert comp.ingest.config == {"dataset": "bench_v2_test"}
    assert comp.prompts.set_id == "frozen_set"
    assert comp.run.stride == 3
    assert comp.run.name == "x"
    assert comp.run.save_annotated_video is True
    assert comp.manifest_model_ref == "yoloe/yoloe-26l"


def test_manifest_sin_source_falla():
    with pytest.raises(ValueError, match="source"):
        manifest_to_composition({"prompts": {"ref": "x"}})


def test_manifest_sin_prompts_ref_falla():
    with pytest.raises(ValueError, match="prompts"):
        manifest_to_composition({"source": {"ref": "demo_v2"}})


@pytest.mark.parametrize("path", REAL_MANIFESTS, ids=lambda p: p.stem)
def test_ida_y_vuelta_sobre_manifiestos_reales(path):
    original = yaml.safe_load(path.read_text())
    comp = manifest_to_composition(original)
    regenerated = composition_to_manifest(comp, target_model_ref="ignored/target")
    # Subconjunto que la traducción posee (device/description/scenario no se preservan):
    assert regenerated["source"] == {
        k: v for k, v in original["source"].items() if k in ("ref", "type", "path")
    } or regenerated["source"] == original["source"]
    assert regenerated["prompts"]["ref"] == original["prompts"]["ref"]
    assert regenerated["prompts"].get("active_ids") == original["prompts"].get("active_ids")
    assert regenerated.get("rate_control") == original.get("rate_control")
    assert regenerated["model"]["ref"] == original["model"]["ref"]
    assert regenerated.get("outputs", {}).get("save_annotated_video", False) == bool(
        original.get("outputs", {}).get("save_annotated_video", False)
    )
    assert regenerated["run"].get("name") == original.get("run", {}).get("name")


def test_composition_to_manifest_usa_target_si_no_hay_ref(repo):
    manifest = composition_to_manifest(_composition(), target_model_ref="grounding-dino/gdino-tiny")
    assert manifest["model"] == {"ref": "grounding-dino/gdino-tiny"}
    assert manifest["source"] == {"ref": "demo_v2"}
    assert manifest["rate_control"] == {"stride": 2}
    assert manifest["run"]["max_units"] == 10
    assert manifest["outputs"] == {"save_annotated_video": True}
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_translation.py -q`
Expected: FAIL con `ModuleNotFoundError: eovrt_webconsole.translation`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/translation.py
"""Traducción manifiesto ↔ composición ↔ run request (dueño único, Spec B §5.3/§5.4).

La composición es el contrato form/BFF. El run request es el contrato del servicio
(Spec A §3.1 implementada): {ingest:{plugin,config}, prompts:{set_inline,active_ids},
run:{stride,max_units,save_annotated_video,save_previews,name}} — sin sección model.
La ref de dataset viaja como ingest.config.dataset (el servicio la retraduce a source.ref).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eovrt_webconsole.repo_catalog import get_prompt_set

_SOURCE_TYPE_TO_PLUGIN = {"image_folder": "image_folder", "video_file": "video_file",
                          "video": "video_file", "video_frame": "video_file"}
_PLUGIN_TO_SOURCE_TYPE = {"image_folder": "image_folder", "video_file": "video_file"}


class UnknownPromptSetError(ValueError):
    """El set_id no existe en prompts/ del repo."""


class IngestSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plugin: str
    config: dict[str, Any] = Field(default_factory=dict)


class PromptsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    set_id: str
    active_ids: list[str] | None = None


class RunParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stride: int | None = None
    max_units: int | None = None
    save_annotated_video: bool = False
    save_previews: bool = True
    name: str | None = None


class Composition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingest: IngestSpec
    prompts: PromptsSpec
    run: RunParams = Field(default_factory=RunParams)
    manifest_model_ref: str | None = None  # policy §5.4: bloqueo si ≠ modelo del target
    confirm_target_model: bool = False


def composition_to_run_request(comp: Composition, prompts_dir: Path) -> dict[str, Any]:
    prompt_set = get_prompt_set(prompts_dir, comp.prompts.set_id)
    if prompt_set is None:
        raise UnknownPromptSetError(f"Prompt set desconocido: {comp.prompts.set_id!r}")
    run: dict[str, Any] = {
        "save_annotated_video": comp.run.save_annotated_video,
        "save_previews": comp.run.save_previews,
    }
    if comp.run.stride is not None:
        run["stride"] = comp.run.stride
    if comp.run.max_units is not None:
        run["max_units"] = comp.run.max_units
    if comp.run.name:
        run["name"] = comp.run.name
    return {
        "ingest": {"plugin": comp.ingest.plugin, "config": dict(comp.ingest.config)},
        "prompts": {"set_inline": prompt_set, "active_ids": comp.prompts.active_ids},
        "run": run,
    }


def manifest_to_composition(manifest: dict) -> Composition:
    source = manifest.get("source") or {}
    if source.get("ref"):
        # El plugin es nominal cuando viaja una ref: el servicio resuelve el tipo real
        # desde su catálogo de datasets (run_request.py:to_raw_run_config).
        ingest = {"plugin": "image_folder", "config": {"dataset": source["ref"]}}
    elif source.get("type"):
        plugin = _SOURCE_TYPE_TO_PLUGIN.get(source["type"])
        if plugin is None:
            raise ValueError(f"source.type fuera del MVP: {source['type']!r}")
        ingest = {"plugin": plugin, "config": {k: v for k, v in source.items() if k != "type"}}
    else:
        raise ValueError("Manifiesto sin source.ref ni source.type")
    prompts = manifest.get("prompts") or {}
    if not prompts.get("ref"):
        raise ValueError("Manifiesto sin prompts.ref")
    run_section = manifest.get("run") or {}
    outputs = manifest.get("outputs") or {}
    return Composition(
        ingest=ingest,
        prompts={"set_id": prompts["ref"], "active_ids": prompts.get("active_ids")},
        run={
            "stride": (manifest.get("rate_control") or {}).get("stride"),
            "max_units": run_section.get("max_units"),
            "save_annotated_video": bool(outputs.get("save_annotated_video", False)),
            "save_previews": bool(outputs.get("save_previews", True)),
            "name": run_section.get("name"),
        },
        manifest_model_ref=(manifest.get("model") or {}).get("ref"),
    )


def composition_to_manifest(comp: Composition, target_model_ref: str) -> dict[str, Any]:
    """Formato declarativo actual (source.ref / rate_control / model.ref / prompts.ref)."""
    run_block: dict[str, Any] = {"scenario": "DBE"}
    if comp.run.name:
        run_block["name"] = comp.run.name
    if comp.run.max_units is not None:
        run_block["max_units"] = comp.run.max_units
    dataset = comp.ingest.config.get("dataset")
    if dataset:
        source: dict[str, Any] = {"ref": dataset}
    else:
        source = {"type": _PLUGIN_TO_SOURCE_TYPE[comp.ingest.plugin],
                  **{k: v for k, v in comp.ingest.config.items()}}
    manifest: dict[str, Any] = {"run": run_block, "source": source}
    if comp.run.stride is not None:
        manifest["rate_control"] = {"stride": comp.run.stride}
    manifest["model"] = {"ref": comp.manifest_model_ref or target_model_ref}
    manifest["prompts"] = {"ref": comp.prompts.set_id}
    if comp.prompts.active_ids is not None:
        manifest["prompts"]["active_ids"] = comp.prompts.active_ids
    outputs: dict[str, Any] = {}
    if comp.run.save_annotated_video:
        outputs["save_annotated_video"] = True
    if comp.run.save_previews is False:
        outputs["save_previews"] = False
    if outputs:
        manifest["outputs"] = outputs
    return manifest
```

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest tests/test_translation.py -q && pytest -q`
Expected: PASS todo — incluidos los ~19 casos parametrizados sobre los manifiestos reales. Si algún manifiesto real usa un campo no contemplado, el test lo revela: ajustar la traducción (no el test) para poseer ese campo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole/translation.py webconsole/backend/tests/test_translation.py
git commit -m "feat(webconsole): traduccion manifiesto <-> composicion <-> run request con ida y vuelta"
```

---

### Task 6: RunBackend — cliente httpx del servicio (la costura §5.5)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/run_backend.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (instanciar en lifespan)
- Test: `webconsole/backend/tests/test_run_backend.py`

**Interfaces:**
- Produces: excepciones `ServiceUnavailable(Exception)`, `RunBusy(Exception)` (attr `active_run_id: str | None`, `detail: str`), `ServiceRejected(Exception)` (attr `detail: str`, para 422 del servicio), `UnknownRun(Exception)`; clase `RunBackend(http: httpx.AsyncClient)` con métodos async: `model() -> dict`, `ingest_plugins() -> list[dict]`, `datasets() -> list[dict]`, `launch(run_request: dict) -> str`, `list_runs() -> list[dict]`, `status(run_id: str) -> dict`, `stop(run_id: str) -> None`, `detections(run_id: str, page: int, page_size: int) -> dict`, `open_artifact(run_id: str, artifact_path: str, range_header: str | None) -> httpx.Response` (streaming; el caller hace `aclose()`). `app.state.backend` disponible tras el lifespan.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_run_backend.py
import httpx
import pytest

from eovrt_webconsole.run_backend import (
    RunBackend,
    RunBusy,
    ServiceRejected,
    ServiceUnavailable,
    UnknownRun,
)
from tests.fake_service import FakeState, make_fake_service

RUN_REQUEST = {
    "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
    "prompts": {"set_inline": {"id": "demo_set", "classes": []}, "active_ids": None},
    "run": {"save_annotated_video": False, "save_previews": True},
}


@pytest.fixture
def state() -> FakeState:
    return FakeState()


@pytest.fixture
async def backend(state: FakeState):
    transport = httpx.ASGITransport(app=make_fake_service(state))
    async with httpx.AsyncClient(transport=transport, base_url="http://service.fake") as http:
        yield RunBackend(http)


async def test_launch_ok(backend, state):
    run_id = await backend.launch(RUN_REQUEST)
    assert run_id == "run_active_1"
    assert state.launched == [RUN_REQUEST]


async def test_launch_busy(backend, state):
    state.active_run_id = "run_activo_previo"
    with pytest.raises(RunBusy) as exc:
        await backend.launch(RUN_REQUEST)
    assert exc.value.active_run_id == "run_activo_previo"


async def test_launch_rechazado_422(backend):
    with pytest.raises(ServiceRejected):
        await backend.launch({**RUN_REQUEST, "model": {"ref": "x"}})


async def test_status_activo_y_terminado(backend, state):
    state.active_run_id = "run_active_1"
    active = await backend.status("run_active_1")
    assert active == {"run_id": "run_active_1", "status": "running",
                      "started_at": "2026-07-03T12:00:00+00:00", "model": "mock"}
    done = await backend.status("run_done_1")
    assert done["summary"]["fps_effective"] == 12.5


async def test_status_desconocido(backend):
    with pytest.raises(UnknownRun):
        await backend.status("nope")


async def test_stop_y_list(backend, state):
    state.active_run_id = "run_active_1"
    await backend.stop("run_active_1")
    assert state.stopped == ["run_active_1"]
    runs = await backend.list_runs()
    assert {r["run_id"] for r in runs} == {"run_active_1", "run_done_1"}


async def test_detections_paginadas(backend):
    page = await backend.detections("run_done_1", page=1, page_size=2)
    assert page["total"] == 5 and len(page["items"]) == 2


async def test_servicio_caido():
    def _down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_down),
                                 base_url="http://service.fake") as http:
        with pytest.raises(ServiceUnavailable):
            await RunBackend(http).model()
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_run_backend.py -q`
Expected: FAIL con `ModuleNotFoundError: eovrt_webconsole.run_backend`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/run_backend.py
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
        response.raise_for_status()

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
```

En `app.py`, dentro del lifespan (reemplaza el comentario de Task 1):

```python
from eovrt_webconsole.run_backend import RunBackend
...
        app.state.http = httpx.AsyncClient(
            base_url=settings.service_url, transport=service_transport, timeout=30.0
        )
        app.state.backend = RunBackend(app.state.http)
        yield
        await app.state.http.aclose()
```

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests/test_run_backend.py
git commit -m "feat(webconsole): RunBackend cliente httpx del servicio"
```

---

### Task 7: Validación de composición + `POST /api/compose/validate`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/compose.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (incluir router)
- Test: `webconsole/backend/tests/test_compose.py`

**Interfaces:**
- Produces: `validate_composition(comp: Composition, settings: ConsoleSettings, backend: RunBackend) -> list[dict]` (async; cada error: `{"field": str, "message": str}`; campos con notación del form: `ingest.plugin`, `ingest.config.dataset`, `ingest.config.path`, `prompts.set_id`, `prompts.active_ids`, `run.stride`, `run.max_units`, `model`, `_target`); endpoint `POST /api/compose/validate` → `{"valid": bool, "errors": [...]}`. La reusa Task 8 antes de lanzar.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_compose.py
def _body(**overrides) -> dict:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 1},
    }
    body.update(overrides)
    return body


def test_composicion_valida(client):
    r = client.post("/api/compose/validate", json=_body())
    assert r.status_code == 200
    assert r.json() == {"valid": True, "errors": []}


def test_plugin_fuera_del_mvp(client):
    r = client.post("/api/compose/validate", json=_body(ingest={"plugin": "rtsp", "config": {}}))
    errors = r.json()["errors"]
    assert any(e["field"] == "ingest.plugin" for e in errors)


def test_dataset_desconocido_o_no_disponible(client):
    for dataset in ("nope", "roto"):
        body = _body(ingest={"plugin": "image_folder", "config": {"dataset": dataset}})
        errors = client.post("/api/compose/validate", json=body).json()["errors"]
        assert any(e["field"] == "ingest.config.dataset" for e in errors)


def test_image_folder_sin_dataset_ni_path(client):
    body = _body(ingest={"plugin": "image_folder", "config": {}})
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert any(e["field"] == "ingest.config.path" for e in errors)


def test_prompt_set_inexistente_y_active_ids_invalidos(client):
    errors = client.post(
        "/api/compose/validate", json=_body(prompts={"set_id": "nope", "active_ids": None})
    ).json()["errors"]
    assert any(e["field"] == "prompts.set_id" for e in errors)
    errors = client.post(
        "/api/compose/validate",
        json=_body(prompts={"set_id": "demo_set", "active_ids": ["person", "alien"]}),
    ).json()["errors"]
    assert any(e["field"] == "prompts.active_ids" and "alien" in e["message"] for e in errors)


def test_params_invalidos(client):
    errors = client.post(
        "/api/compose/validate", json=_body(run={"stride": 0, "max_units": 0})
    ).json()["errors"]
    fields = {e["field"] for e in errors}
    assert "run.stride" in fields and "run.max_units" in fields


def test_policy_model_ref_distinto_bloquea(client):
    body = _body(manifest_model_ref="yoloe/yoloe-26l")  # el target tiene 'mock'
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert any(e["field"] == "model" and "mock" in e["message"] for e in errors)
    # con confirmación explícita, pasa
    body["confirm_target_model"] = True
    assert client.post("/api/compose/validate", json=body).json()["valid"] is True


def test_body_malformado_422(client):
    r = client.post("/api/compose/validate", json={"ingest": {"plugin": "x"}, "extra": 1})
    assert r.status_code == 422  # extra="forbid" de Composition
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_compose.py -q`
Expected: FAIL con 404 en `/api/compose/validate`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/routers/compose.py
"""Validación de composiciones contra el target y el repo (Spec B §5.2)."""
from __future__ import annotations

from fastapi import APIRouter, Request

from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole.run_backend import RunBackend, ServiceUnavailable
from eovrt_webconsole.settings import ConsoleSettings
from eovrt_webconsole.translation import Composition

router = APIRouter(prefix="/api/compose")


async def validate_composition(
    comp: Composition, settings: ConsoleSettings, backend: RunBackend
) -> list[dict]:
    errors: list[dict] = []

    if comp.ingest.plugin not in settings.mvp_plugins:
        errors.append({
            "field": "ingest.plugin",
            "message": f"Plugin '{comp.ingest.plugin}' fuera del MVP "
                       f"(permitidos: {sorted(settings.mvp_plugins)})",
        })

    try:
        plugins = {p["id"]: p for p in await backend.ingest_plugins()}
        datasets = {d["id"]: d for d in await backend.datasets()}
        model = await backend.model()
    except ServiceUnavailable as exc:
        errors.append({"field": "_target", "message": f"Servicio media-plane inaccesible: {exc}"})
        return errors

    plugin_entry = plugins.get(comp.ingest.plugin)
    if plugin_entry is not None and not plugin_entry.get("available", False):
        errors.append({"field": "ingest.plugin",
                       "message": f"Plugin '{comp.ingest.plugin}' no disponible en el target"})

    dataset = comp.ingest.config.get("dataset")
    if dataset:
        entry = datasets.get(dataset)
        if entry is None:
            errors.append({"field": "ingest.config.dataset",
                           "message": f"Dataset '{dataset}' no existe en el catálogo del target"})
        elif not entry.get("available", False):
            errors.append({"field": "ingest.config.dataset",
                           "message": f"Dataset '{dataset}' no disponible (path no montado)"})
    elif not comp.ingest.config.get("path"):
        errors.append({"field": "ingest.config.path",
                       "message": "Se requiere 'dataset' (catálogo) o 'path' explícito"})

    prompt_set = get_prompt_set(settings.prompts_dir, comp.prompts.set_id)
    if prompt_set is None:
        errors.append({"field": "prompts.set_id",
                       "message": f"Prompt set '{comp.prompts.set_id}' no existe en prompts/"})
    elif comp.prompts.active_ids:
        known = {c.get("id") for c in prompt_set.get("classes", [])}
        unknown = [i for i in comp.prompts.active_ids if i not in known]
        if unknown:
            errors.append({"field": "prompts.active_ids",
                           "message": f"Clases desconocidas en el set: {unknown}"})

    if comp.run.stride is not None and comp.run.stride < 1:
        errors.append({"field": "run.stride", "message": "stride debe ser >= 1"})
    if comp.run.max_units is not None and comp.run.max_units < 1:
        errors.append({"field": "run.max_units", "message": "max_units debe ser >= 1"})

    # Policy §5.4: manifiesto con model.ref ≠ modelo del target bloquea sin confirmación.
    if (
        comp.manifest_model_ref
        and comp.manifest_model_ref != model["ref"]
        and not comp.confirm_target_model
    ):
        errors.append({
            "field": "model",
            "message": f"El manifiesto declara '{comp.manifest_model_ref}' pero el target tiene "
                       f"'{model['ref']}'. Confirmá «usar el modelo del target» para lanzar.",
        })
    return errors


@router.post("/validate")
async def validate(comp: Composition, request: Request) -> dict:
    errors = await validate_composition(
        comp, request.app.state.settings, request.app.state.backend
    )
    return {"valid": not errors, "errors": errors}
```

En `app.py`: `from eovrt_webconsole.routers import catalog, compose, meta` y `app.include_router(compose.router)`.

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests/test_compose.py
git commit -m "feat(webconsole): validacion de composicion contra target y repo"
```

---

### Task 8: Runs router — lanzar, listar (hidratado), estado, stop

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/runs.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (incluir router)
- Test: `webconsole/backend/tests/test_runs_router.py`

**Interfaces:**
- Consumes: `validate_composition` (Task 7), `composition_to_run_request` (Task 5), `RunBackend` (Task 6).
- Produces: `POST /api/runs` (body = `Composition`) → `201 {run_id}` | `422 {"errors":[...]}` (validación BFF o rechazo del servicio, campo `_service`) | `409 {detail, active_run_id}` | `502` servicio caído; `GET /api/runs` → filas hidratadas `{run_id, status, model, source_type, prompt_set_id, fps_effective, total_detections, duration_seconds, started_at}` (N+1 acotado por `settings.hydration_limit`); `GET /api/runs/{id}` → pass-through del servicio (404); `POST /api/runs/{id}/stop` → `202 {run_id, stopping}`.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_runs_router.py
def _body(**overrides) -> dict:
    body = {
        "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
        "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
        "run": {"stride": 1, "max_units": 5},
    }
    body.update(overrides)
    return body


def test_lanzar_ok_y_request_sin_model(client, fake_state):
    r = client.post("/api/runs", json=_body())
    assert r.status_code == 201
    assert r.json() == {"run_id": "run_active_1"}
    sent = fake_state.launched[0]
    assert "model" not in sent
    assert sent["prompts"]["set_inline"]["id"] == "demo_set"
    assert sent["ingest"]["config"] == {"dataset": "demo_v2"}
    assert sent["run"]["stride"] == 1


def test_lanzar_invalido_422_con_errores_de_campo(client):
    r = client.post("/api/runs", json=_body(prompts={"set_id": "nope", "active_ids": None}))
    assert r.status_code == 422
    assert any(e["field"] == "prompts.set_id" for e in r.json()["errors"])


def test_lanzar_busy_409(client, fake_state):
    fake_state.active_run_id = "run_previo"
    r = client.post("/api/runs", json=_body())
    assert r.status_code == 409
    assert r.json()["active_run_id"] == "run_previo"


def test_listado_hidratado(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    rows = {r["run_id"]: r for r in client.get("/api/runs").json()}
    assert rows["run_active_1"]["status"] == "running"
    assert rows["run_active_1"]["model"] == "mock"
    done = rows["run_done_1"]
    assert done["fps_effective"] == 12.5
    assert done["total_detections"] == 7
    assert done["source_type"] == "image_folder"
    assert done["prompt_set_id"] == "demo_set"


def test_get_run_pass_through_y_404(client):
    assert client.get("/api/runs/run_done_1").json()["summary"]["total_detections"] == 7
    assert client.get("/api/runs/nope").status_code == 404


def test_stop_202(client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = client.post("/api/runs/run_active_1/stop")
    assert r.status_code == 202
    assert fake_state.stopped == ["run_active_1"]
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_runs_router.py -q`
Expected: FAIL con 404 en `POST /api/runs`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/routers/runs.py
"""Runs: lanzar (compose→launch), listar hidratado, estado y stop (Spec B §5.5/§6)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.routers.compose import validate_composition
from eovrt_webconsole.run_backend import RunBusy, ServiceUnavailable, UnknownRun
from eovrt_webconsole.translation import Composition, composition_to_run_request

router = APIRouter(prefix="/api/runs")


def _row(info: dict) -> dict:
    summary = info.get("summary") or {}
    return {
        "run_id": info["run_id"],
        "status": info["status"],
        "model": info.get("model") or summary.get("model_name"),
        "source_type": summary.get("source_type"),
        "prompt_set_id": summary.get("prompt_set_id"),
        "fps_effective": summary.get("fps_effective"),
        "total_detections": summary.get("total_detections"),
        "duration_seconds": summary.get("duration_seconds"),
        "started_at": info.get("started_at") or summary.get("started_at"),
    }


@router.post("", status_code=201)
async def launch(comp: Composition, request: Request):
    settings = request.app.state.settings
    backend = request.app.state.backend
    errors = await validate_composition(comp, settings, backend)
    if errors:
        return JSONResponse(status_code=422, content={"errors": errors})
    run_request = composition_to_run_request(comp, settings.prompts_dir)
    try:
        run_id = await backend.launch(run_request)
    except RunBusy as exc:
        return JSONResponse(
            status_code=409, content={"detail": exc.detail, "active_run_id": exc.active_run_id}
        )
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"run_id": run_id}


@router.get("")
async def list_runs(request: Request) -> list[dict]:
    settings = request.app.state.settings
    backend = request.app.state.backend
    try:
        base = await backend.list_runs()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    rows: list[dict] = []
    for item in base[: settings.hydration_limit]:
        try:
            rows.append(_row(await backend.status(item["run_id"])))
        except (UnknownRun, ServiceUnavailable):
            rows.append({"run_id": item["run_id"], "status": item["status"]})
    rows.extend(
        {"run_id": item["run_id"], "status": item["status"]}
        for item in base[settings.hydration_limit :]
    )
    return rows


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request) -> dict:
    try:
        return await request.app.state.backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{run_id}/stop", status_code=202)
async def stop_run(run_id: str, request: Request) -> dict:
    try:
        await request.app.state.backend.stop(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"run_id": run_id, "stopping": True}
```

En `app.py`: importar y `app.include_router(runs.router)`.

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests/test_runs_router.py
git commit -m "feat(webconsole): runs router — launch, listado hidratado, estado y stop"
```

---

### Task 9: Proxy de detections y artefactos (streaming + Range)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/runs.py`
- Test: `webconsole/backend/tests/test_artifacts_proxy.py`

**Interfaces:**
- Produces: `GET /api/runs/{id}/detections?page=&page_size=` → pass-through paginado del servicio; `GET /api/runs/{id}/artifacts/{path}` → **streaming pass-through** (sin bufferizar en el BFF, Spec B §5.6) reenviando el header `Range` hacia el servicio y devolviendo status (200/206) + headers `content-type`, `content-length`, `content-range`, `accept-ranges` del upstream.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_artifacts_proxy.py
def test_detections_proxy(client):
    r = client.get("/api/runs/run_done_1/detections", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5 and len(body["items"]) == 2


def test_detections_404(client):
    assert client.get("/api/runs/nope/detections").status_code == 404


def test_artifact_pass_through(client):
    r = client.get("/api/runs/run_done_1/artifacts/summary.json")
    assert r.status_code == 200
    assert r.content == b'{"status": "succeeded"}'
    assert r.headers.get("accept-ranges") == "bytes"


def test_artifact_anidado_y_404(client):
    assert client.get("/api/runs/run_done_1/artifacts/previews/u0.preview.jpg").status_code == 200
    assert client.get("/api/runs/run_done_1/artifacts/nope.bin").status_code == 404
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_artifacts_proxy.py -q`
Expected: FAIL con 404 (rutas inexistentes en el BFF)

- [ ] **Step 3: Implementación**

Agregar a `routers/runs.py`:

```python
from fastapi import Query
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

_FORWARD_HEADERS = {"content-type", "content-length", "content-range", "accept-ranges"}


@router.get("/{run_id}/detections")
async def detections(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
) -> dict:
    try:
        return await request.app.state.backend.detections(run_id, page=page, page_size=page_size)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Sin detecciones para: {run_id}") from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{run_id}/artifacts/{artifact_path:path}")
async def artifact(run_id: str, artifact_path: str, request: Request):
    backend = request.app.state.backend
    try:
        upstream = await backend.open_artifact(
            run_id, artifact_path, range_header=request.headers.get("range")
        )
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if upstream.status_code == 404:
        await upstream.aclose()
        raise HTTPException(status_code=404, detail="Artefacto no encontrado")
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in _FORWARD_HEADERS}
    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,  # 200 o 206 (Range) del servicio
        headers=headers,
        background=BackgroundTask(upstream.aclose),
    )
```

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole/routers/runs.py webconsole/backend/tests/test_artifacts_proxy.py
git commit -m "feat(webconsole): proxy de detections y artefactos con streaming y Range"
```

---

### Task 10: Proxy WebSocket de telemetría con coalescing

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/stream.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (incluir router), `webconsole/backend/tests/conftest.py` (fixture uvicorn)
- Test: `webconsole/backend/tests/test_stream_proxy.py`

**Interfaces:**
- Produces: `WS /api/runs/{run_id}/stream` — el BFF se conecta al WS del servicio (`websockets.connect`), coalesce métricas (último gana) sobre cola acotada drop-oldest (espejo del servicio) y flushea al SPA cada `FLUSH_INTERVAL=0.1s`; al cerrar el upstream hace **drain final** y reenvía el close code del servicio (1000/4404/4503). Clase interna `_CoalescingBuffer` con `push(event)` / `drain() -> list[dict]`. Fixture `live_client` (BFF real + fake service en uvicorn sobre puerto efímero — ASGITransport no soporta WS).

- [ ] **Step 1: Fixture de servicio vivo + tests que fallan**

Agregar a `tests/conftest.py`:

```python
import socket
import threading
import time

import uvicorn


@pytest.fixture
def live_client(repo: Path, fake_state: FakeState):
    """BFF (TestClient) apuntando a un fake service REAL en uvicorn (para WS)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    config = uvicorn.Config(
        make_fake_service(fake_state), host="127.0.0.1", port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5.0
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("El fake service no arrancó")
        time.sleep(0.02)
    settings = ConsoleSettings(
        service_url=f"http://127.0.0.1:{port}",
        repo_root=repo,
        frozen_set_ids=frozenset({"frozen_set"}),
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
    server.should_exit = True
    thread.join(timeout=5)
```

```python
# webconsole/backend/tests/test_stream_proxy.py
from eovrt_webconsole.routers.stream import _CoalescingBuffer


def test_buffer_coalesce_metricas_y_ordena_discretos():
    buffer = _CoalescingBuffer()
    for i in range(5):
        buffer.push({"type": "metric", "unit_id": f"u{i}"})
    buffer.push({"type": "detection", "unit_id": "u4", "count": 1})
    buffer.push({"type": "error", "message": "x"})
    events = buffer.drain()
    metrics = [e for e in events if e["type"] == "metric"]
    assert len(metrics) == 1 and metrics[0]["unit_id"] == "u4"
    assert [e["type"] for e in events if e["type"] != "metric"] == ["detection", "error"]
    assert buffer.drain() == []


def test_ws_proxy_reenvia_eventos(live_client, fake_state):
    fake_state.active_run_id = "run_active_1"
    received = []
    with live_client.websocket_connect("/api/runs/run_active_1/stream") as ws:
        # El fake emite 2 metric + detection + error + state y cierra: el proxy
        # coalesce las métricas y hace drain final antes de cerrar.
        try:
            while True:
                received.append(ws.receive_json())
        except Exception:  # noqa: BLE001 — el cierre del WS corta el loop
            pass
    types = [e["type"] for e in received]
    assert "state" in types
    assert "detection" in types
    metrics = [e for e in received if e["type"] == "metric"]
    assert len(metrics) >= 1
    assert metrics[-1]["unit_id"] == "u1"  # la última gana


def test_ws_run_desconocido_cierra_4404(live_client):
    with live_client.websocket_connect("/api/runs/nope/stream") as ws:
        try:
            while True:
                ws.receive_json()
        except Exception:  # noqa: BLE001
            pass
    # el cierre llegó sin eventos: el fake cerró 4404 y el proxy lo reenvió
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_stream_proxy.py -q`
Expected: FAIL con `ModuleNotFoundError: eovrt_webconsole.routers.stream`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/routers/stream.py
"""Proxy WS de telemetría: servicio → BFF → SPA, con coalescing (Spec B §5.6).

Espejo de la política del servicio: métricas coalescidas (última gana), eventos
discretos en cola acotada drop-oldest. Un SPA lento nunca acumula memoria acá.
El fallback ante caída es RECONECTAR el WS (responsabilidad del SPA); este proxy
reenvía el close code del servicio (1000 fin normal, 4404 run desconocido,
4503 servicio no listo) para que el cliente decida.
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_COALESCE_TYPES = {"metric"}
FLUSH_INTERVAL = 0.1
_MAX_DISCRETE = 200


class _CoalescingBuffer:
    def __init__(self, max_discrete: int = _MAX_DISCRETE) -> None:
        self._latest: dict[str, dict[str, Any]] = {}
        self._discrete: deque[dict[str, Any]] = deque(maxlen=max_discrete)

    def push(self, event: dict[str, Any]) -> None:
        if event.get("type") in _COALESCE_TYPES:
            self._latest[event["type"]] = event
        else:
            self._discrete.append(event)

    def drain(self) -> list[dict[str, Any]]:
        out = list(self._discrete)
        self._discrete.clear()
        out.extend(self._latest.values())
        self._latest.clear()
        return out


def _ws_url(service_url: str, run_id: str) -> str:
    base = service_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    return f"{base}/api/runs/{run_id}/stream"


@router.websocket("/api/runs/{run_id}/stream")
async def stream(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    settings = websocket.app.state.settings
    buffer = _CoalescingBuffer()
    close_code = 1000
    try:
        async with websockets.connect(_ws_url(settings.service_url, run_id)) as upstream:

            async def _pump() -> None:
                async for raw in upstream:
                    buffer.push(json.loads(raw))

            pump = asyncio.create_task(_pump())
            try:
                while not pump.done():
                    await asyncio.sleep(FLUSH_INTERVAL)
                    for event in buffer.drain():
                        await websocket.send_json(event)
                for event in buffer.drain():  # drain final: no perder la cola
                    await websocket.send_json(event)
            finally:
                pump.cancel()
            close_code = upstream.close_code or 1000
    except (OSError, websockets.exceptions.WebSocketException):
        close_code = 4503  # servicio inaccesible: el SPA reintenta la conexión
    except WebSocketDisconnect:
        return  # el SPA se fue: nada que cerrar
    try:
        await websocket.close(code=close_code)
    except RuntimeError:
        pass  # ya cerrado por el cliente
```

En `app.py`: importar y `app.include_router(stream.router)`.

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo (los tests de WS usan uvicorn real; tardan ~1-2s extra).

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests
git commit -m "feat(webconsole): proxy WS de telemetria con coalescing y drain final"
```

---

### Task 11: ManifestWriter + `POST /api/manifests`

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/manifest_writer.py`, `webconsole/backend/src/eovrt_webconsole/routers/manifests.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (incluir router)
- Test: `webconsole/backend/tests/test_manifest_writer.py`

**Interfaces:**
- Produces: `write_manifest(experiments_dir: Path, name: str, group: str | None, manifest: dict, overwrite: bool = False) -> Path` (escritura atómica tmp+`os.replace`; valida `name`/`group` con `^[a-z0-9][a-z0-9_-]*$`; lanza `ManifestExistsError` si existe y no `overwrite`); endpoint `POST /api/manifests` body `{name, group?, overwrite?, composition}` → `201 {"path": "<relativo a experiments/>"}` | `409` si existe | `422` si el set no existe o el name es inválido. El `model.ref` del manifiesto se completa con el modelo del target (`backend.model()`), Spec B §5.3.

- [ ] **Step 1: Tests que fallan**

```python
# webconsole/backend/tests/test_manifest_writer.py
import pytest
import yaml

from eovrt_webconsole.manifest_writer import ManifestExistsError, write_manifest


def test_escritura_atomica_y_contenido(repo):
    path = write_manifest(
        repo / "experiments", "nuevo_exp", None, {"run": {"scenario": "DBE"}}
    )
    assert path == repo / "experiments" / "nuevo_exp.yaml"
    assert yaml.safe_load(path.read_text()) == {"run": {"scenario": "DBE"}}
    assert not path.with_suffix(".yaml.tmp").exists()


def test_grupo_crea_subdir(repo):
    path = write_manifest(repo / "experiments", "exp_b", "grupo_x", {"a": 1})
    assert path == repo / "experiments" / "grupo_x" / "exp_b.yaml"


def test_colision_sin_overwrite(repo):
    write_manifest(repo / "experiments", "dup", None, {"a": 1})
    with pytest.raises(ManifestExistsError):
        write_manifest(repo / "experiments", "dup", None, {"a": 2})
    write_manifest(repo / "experiments", "dup", None, {"a": 2}, overwrite=True)


def test_nombre_invalido(repo):
    for bad in ("../evil", "CON ESPACIOS", "", "Mayus"):
        with pytest.raises(ValueError):
            write_manifest(repo / "experiments", bad, None, {})


def test_endpoint_guarda_con_modelo_del_target(client, repo):
    body = {
        "name": "desde_consola",
        "composition": {
            "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
            "prompts": {"set_id": "demo_set", "active_ids": ["person"]},
            "run": {"stride": 2},
        },
    }
    r = client.post("/api/manifests", json=body)
    assert r.status_code == 201
    assert r.json() == {"path": "desde_consola.yaml"}
    saved = yaml.safe_load((repo / "experiments" / "desde_consola.yaml").read_text())
    assert saved["model"] == {"ref": "mock"}  # completado con el modelo del target
    assert saved["source"] == {"ref": "demo_v2"}
    assert saved["prompts"] == {"ref": "demo_set", "active_ids": ["person"]}
    # segunda escritura sin overwrite → 409
    assert client.post("/api/manifests", json=body).status_code == 409


def test_endpoint_set_inexistente_422(client):
    body = {
        "name": "x",
        "composition": {
            "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
            "prompts": {"set_id": "nope", "active_ids": None},
        },
    }
    assert client.post("/api/manifests", json=body).status_code == 422
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest tests/test_manifest_writer.py -q`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Implementación**

```python
# webconsole/backend/src/eovrt_webconsole/manifest_writer.py
"""Escritura atómica de manifiestos in-repo (experiments/), Spec B §5.3."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ManifestExistsError(Exception):
    pass


def write_manifest(
    experiments_dir: Path,
    name: str,
    group: str | None,
    manifest: dict,
    overwrite: bool = False,
) -> Path:
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"Nombre de manifiesto inválido: {name!r} (usar [a-z0-9_-])")
    if group and not _NAME_RE.match(group):
        raise ValueError(f"Grupo inválido: {group!r} (usar [a-z0-9_-])")
    target_dir = experiments_dir / group if group else experiments_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.yaml"
    if target.exists() and not overwrite:
        raise ManifestExistsError(str(target))
    tmp = target.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
    os.replace(tmp, target)  # atómico en el mismo filesystem
    return target
```

```python
# webconsole/backend/src/eovrt_webconsole/routers/manifests.py
"""POST /api/manifests — guardar la composición como manifiesto declarativo in-repo."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from eovrt_webconsole.manifest_writer import ManifestExistsError, write_manifest
from eovrt_webconsole.repo_catalog import get_prompt_set
from eovrt_webconsole.run_backend import ServiceUnavailable
from eovrt_webconsole.translation import Composition, composition_to_manifest

router = APIRouter(prefix="/api/manifests")


class ManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    name: str
    group: str | None = None
    overwrite: bool = False
    composition: Composition


@router.post("", status_code=201)
async def save_manifest(body: ManifestRequest, request: Request) -> dict:
    settings = request.app.state.settings
    if get_prompt_set(settings.prompts_dir, body.composition.prompts.set_id) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt set desconocido: {body.composition.prompts.set_id!r}",
        )
    try:
        model = await request.app.state.backend.model()
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    manifest = composition_to_manifest(body.composition, target_model_ref=model["ref"])
    try:
        path = write_manifest(
            settings.experiments_dir, body.name, body.group, manifest, overwrite=body.overwrite
        )
    except ManifestExistsError as exc:
        raise HTTPException(status_code=409, detail=f"Ya existe: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"path": path.relative_to(settings.experiments_dir).as_posix()}
```

En `app.py`: importar y `app.include_router(manifests.router)`.

- [ ] **Step 4: Verificar + suite completa**

Run: `pytest -q && ruff check src tests`
Expected: PASS todo.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/backend/src/eovrt_webconsole webconsole/backend/tests/test_manifest_writer.py
git commit -m "feat(webconsole): escritura atomica de manifiestos in-repo"
```

---

### Task 12: Scaffold frontend — Vite + React + TS + cliente API tipado

**Files:**
- Create: `webconsole/frontend/package.json`, `webconsole/frontend/vite.config.ts`, `webconsole/frontend/tsconfig.json`, `webconsole/frontend/index.html`, `webconsole/frontend/src/main.tsx`, `webconsole/frontend/src/App.tsx`, `webconsole/frontend/src/types.ts`, `webconsole/frontend/src/api.ts`
- Test: `webconsole/frontend/src/__tests__/api.test.ts`

**Interfaces:**
- Produces: cliente tipado del BFF en `api.ts`: `getTarget()`, `getPromptSets()`, `getExperiments()`, `getIngestPlugins()`, `getDatasets()`, `validateComposition(comp)`, `launchRun(comp)` (lanza `ApiError` con `status` y `payload` en 409/422/502), `listRuns()`, `getRun(id)`, `stopRun(id)`, `getDetections(id, page)`, `saveManifest(body)`, `artifactUrl(id, path)`, `streamUrl(id)`. Tipos en `types.ts` espejan los shapes del BFF (Tasks 2-11). Router: **HashRouter** (sirve estática sin fallback server-side).

- [ ] **Step 1: Scaffold**

```json
// webconsole/frontend/package.json
{
  "name": "eovrt-webconsole-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.3",
    "vite": "^5.4.0",
    "vitest": "^2.0.5"
  }
}
```

```typescript
// webconsole/frontend/vite.config.ts
/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev el SPA corre en :5173 y proxya /api al BFF en :8090 (un solo origen
// también en dev; el servicio media-plane NO tiene CORS y nunca se toca directo).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8090', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
```

```json
// webconsole/frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vite/client", "vitest/globals"]
  },
  "include": ["src", "vite.config.ts"]
}
```

```html
<!-- webconsole/frontend/index.html -->
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>E-OVRT Console</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```typescript
// webconsole/frontend/src/types.ts
export interface TargetStatus {
  service_url: string
  healthy: boolean
  ready: boolean
  model: ModelInfo | null
}
export interface ModelInfo {
  ref: string
  name: string | null
  adapter: string | null
  device: string | null
  thresholds: Record<string, number | null>
  runtime: Record<string, unknown>
}
export interface PromptClass {
  id: string
  role: string | null
  enabled_by_default: boolean
  phrasings: Record<string, string[]>
}
export interface PromptSet {
  id: string
  description: string | null
  language: string | null
  frozen: boolean
  classes: PromptClass[]
}
export interface Experiment {
  id: string
  group: string
  manifest: Record<string, unknown>
}
export interface IngestPlugin {
  id: string
  kind: string
  available: boolean
  description: string
  mvp_enabled: boolean
}
export interface DatasetEntry {
  id: string
  description: string | null
  path: string
  available: boolean
}
export interface Composition {
  ingest: { plugin: string; config: Record<string, unknown> }
  prompts: { set_id: string; active_ids: string[] | null }
  run: {
    stride?: number | null
    max_units?: number | null
    save_annotated_video?: boolean
    save_previews?: boolean
    name?: string | null
  }
  manifest_model_ref?: string | null
  confirm_target_model?: boolean
}
export interface FieldError {
  field: string
  message: string
}
export interface RunRow {
  run_id: string
  status: string
  model?: string | null
  source_type?: string | null
  prompt_set_id?: string | null
  fps_effective?: number | null
  total_detections?: number | null
  duration_seconds?: number | null
  started_at?: string | null
}
export interface RunDetail {
  run_id: string
  status: string
  started_at?: string
  model?: string
  summary?: Record<string, unknown>
}
export interface DetectionsPage {
  page: number
  page_size: number
  total: number
  items: Array<Record<string, unknown>>
}
export type StreamEvent =
  | { type: 'metric'; unit_id: string; fps: number; latency_total_ms: number;
      detections_count: number; gpu_memory_mb: number }
  | { type: 'detection'; unit_id: string; count: number }
  | { type: 'error'; unit_id: string | null; stage: string | null; message: string | null }
  | { type: 'state'; status: string; error: string | null }
```

```typescript
// webconsole/frontend/src/api.ts
import type {
  Composition, DatasetEntry, DetectionsPage, Experiment, FieldError,
  IngestPlugin, PromptSet, RunDetail, RunRow, TargetStatus,
} from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: unknown,
  ) {
    super(`API ${status}`)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      /* cuerpo no-JSON */
    }
    throw new ApiError(response.status, payload)
  }
  return (await response.json()) as T
}

export const getTarget = () => request<TargetStatus>('/api/target')
export const getPromptSets = () => request<PromptSet[]>('/api/catalog/prompt-sets')
export const getExperiments = () => request<Experiment[]>('/api/catalog/experiments')
export const getIngestPlugins = () => request<IngestPlugin[]>('/api/catalog/ingest-plugins')
export const getDatasets = () => request<DatasetEntry[]>('/api/catalog/datasets')
export const validateComposition = (comp: Composition) =>
  request<{ valid: boolean; errors: FieldError[] }>('/api/compose/validate', {
    method: 'POST',
    body: JSON.stringify(comp),
  })
export const launchRun = (comp: Composition) =>
  request<{ run_id: string }>('/api/runs', { method: 'POST', body: JSON.stringify(comp) })
export const listRuns = () => request<RunRow[]>('/api/runs')
export const getRun = (id: string) => request<RunDetail>(`/api/runs/${id}`)
export const stopRun = (id: string) =>
  request<{ run_id: string; stopping: boolean }>(`/api/runs/${id}/stop`, { method: 'POST' })
export const getDetections = (id: string, page = 1, pageSize = 50) =>
  request<DetectionsPage>(`/api/runs/${id}/detections?page=${page}&page_size=${pageSize}`)
export const saveManifest = (body: {
  name: string
  group?: string | null
  overwrite?: boolean
  composition: Composition
}) => request<{ path: string }>('/api/manifests', { method: 'POST', body: JSON.stringify(body) })

export const artifactUrl = (id: string, path: string) => `/api/runs/${id}/artifacts/${path}`
export const streamUrl = (id: string) => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/runs/${id}/stream`
}
```

```tsx
// webconsole/frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
```

```tsx
// webconsole/frontend/src/App.tsx
import { Link, Route, Routes } from 'react-router-dom'

// Las páginas se agregan en Tasks 13-16; este shell compila desde ya.
export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', margin: '0 auto', maxWidth: 1100, padding: 16 }}>
      <header style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 20, margin: 0 }}>E-OVRT Console</h1>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/">Runs</Link>
          <Link to="/compose">Nueva corrida</Link>
          <Link to="/catalog">Catálogos</Link>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<p>Home (Task 14)</p>} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 2: Instalar y test que falla**

```bash
cd webconsole/frontend && npm install
```

```typescript
// webconsole/frontend/src/__tests__/api.test.ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, launchRun, listRuns } from '../api'

const COMP = {
  ingest: { plugin: 'image_folder', config: { dataset: 'demo_v2' } },
  prompts: { set_id: 'demo_set', active_ids: ['person'] },
  run: {},
}

function stubFetch(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })))
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('launchRun devuelve run_id en 201', async () => {
    stubFetch(201, { run_id: 'run_x' })
    expect(await launchRun(COMP)).toEqual({ run_id: 'run_x' })
  })

  it('launchRun lanza ApiError con payload en 409', async () => {
    stubFetch(409, { detail: 'busy', active_run_id: 'run_a' })
    const error = await launchRun(COMP).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.payload.active_run_id).toBe('run_a')
  })

  it('launchRun lanza ApiError con errores de campo en 422', async () => {
    stubFetch(422, { errors: [{ field: 'prompts.set_id', message: 'no existe' }] })
    const error = await launchRun(COMP).catch((e) => e)
    expect(error.status).toBe(422)
    expect(error.payload.errors[0].field).toBe('prompts.set_id')
  })

  it('listRuns parsea filas', async () => {
    stubFetch(200, [{ run_id: 'r1', status: 'succeeded' }])
    expect(await listRuns()).toHaveLength(1)
  })
})
```

Run: `npx vitest run`
Expected: PASS (el cliente ya está implementado en Step 1; este test fija el contrato de errores 409/422 que las páginas consumen)

- [ ] **Step 3: Verificar build y tipos**

Run: `npm run build`
Expected: compila sin errores de TS; genera `dist/`.

- [ ] **Step 4: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/frontend
git commit -m "feat(webconsole): scaffold frontend Vite+React+TS con cliente API tipado"
```

---

### Task 13: Header con TargetBadge + página de Catálogos

**Files:**
- Create: `webconsole/frontend/src/components/TargetBadge.tsx`, `webconsole/frontend/src/pages/CatalogPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx`

**Interfaces:**
- Consumes: `getTarget`, `getPromptSets`, `getIngestPlugins`, `getDatasets` (api.ts).
- Produces: `<TargetBadge />` (polling de `/api/target` cada 5s; muestra `ready`+`model.ref` o estado de error — Spec B §4: la UI muestra el modelo del target, no hay dropdown); `<CatalogPage />` en ruta `/catalog` (modelo con thresholds **read-only**, plugins con badges `mvp_enabled`/`available`, datasets, prompt sets con badge `frozen`).

- [ ] **Step 1: Implementación**

```tsx
// webconsole/frontend/src/components/TargetBadge.tsx
import { useEffect, useState } from 'react'
import { getTarget } from '../api'
import type { TargetStatus } from '../types'

export default function TargetBadge() {
  const [target, setTarget] = useState<TargetStatus | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      getTarget().then((t) => alive && setTarget(t)).catch(() => alive && setTarget(null))
    tick()
    const timer = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  if (!target) return <span style={{ color: '#b00' }}>● BFF inaccesible</span>
  if (!target.healthy) return <span style={{ color: '#b00' }}>● servicio caído</span>
  if (!target.ready) return <span style={{ color: '#c80' }}>● cargando modelo…</span>
  return (
    <span style={{ color: '#080' }}>
      ● {target.model?.ref} <small>({target.model?.device ?? '?'})</small>
    </span>
  )
}
```

```tsx
// webconsole/frontend/src/pages/CatalogPage.tsx
import { useEffect, useState } from 'react'
import { getDatasets, getIngestPlugins, getPromptSets, getTarget } from '../api'
import type { DatasetEntry, IngestPlugin, PromptSet, TargetStatus } from '../types'

export default function CatalogPage() {
  const [target, setTarget] = useState<TargetStatus | null>(null)
  const [plugins, setPlugins] = useState<IngestPlugin[]>([])
  const [datasets, setDatasets] = useState<DatasetEntry[]>([])
  const [sets, setSets] = useState<PromptSet[]>([])
  useEffect(() => {
    getTarget().then(setTarget).catch(() => setTarget(null))
    getIngestPlugins().then(setPlugins).catch(() => setPlugins([]))
    getDatasets().then(setDatasets).catch(() => setDatasets([]))
    getPromptSets().then(setSets).catch(() => setSets([]))
  }, [])
  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <section>
        <h2>Modelo del target (read-only)</h2>
        {target?.model ? (
          <ul>
            <li><b>{target.model.ref}</b> — adapter {target.model.adapter}, device {target.model.device}</li>
            <li>
              thresholds:{' '}
              {Object.entries(target.model.thresholds)
                .filter(([, v]) => v != null)
                .map(([k, v]) => `${k}=${v}`)
                .join(', ') || '—'}
              {' '}<em>(fijos por instancia; cambiar de modelo = otra instancia)</em>
            </li>
          </ul>
        ) : (
          <p>Servicio no listo.</p>
        )}
      </section>
      <section>
        <h2>Plugins de ingesta</h2>
        <ul>
          {plugins.map((p) => (
            <li key={p.id}>
              <b>{p.id}</b> ({p.kind}) — {p.description}{' '}
              {!p.available && <em>[no disponible]</em>}
              {p.available && !p.mvp_enabled && <em>[fuera del MVP]</em>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Datasets</h2>
        <ul>
          {datasets.map((d) => (
            <li key={d.id}>
              <b>{d.id}</b> — {d.description} {!d.available && <em>[no montado]</em>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>Prompt sets (in-repo)</h2>
        <ul>
          {sets.map((s) => (
            <li key={s.id}>
              <b>{s.id}</b> {s.frozen && <em>[congelado]</em>} —{' '}
              {s.classes.map((c) => c.id).join(', ')}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
```

En `App.tsx`, header y rutas:

```tsx
import { Link, Route, Routes } from 'react-router-dom'
import TargetBadge from './components/TargetBadge'
import CatalogPage from './pages/CatalogPage'

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', margin: '0 auto', maxWidth: 1100, padding: 16 }}>
      <header style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 20, margin: 0 }}>E-OVRT Console</h1>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/">Runs</Link>
          <Link to="/compose">Nueva corrida</Link>
          <Link to="/catalog">Catálogos</Link>
        </nav>
        <div style={{ marginLeft: 'auto' }}><TargetBadge /></div>
      </header>
      <Routes>
        <Route path="/" element={<p>Home (Task 14)</p>} />
        <Route path="/catalog" element={<CatalogPage />} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 2: Verificar**

Run: `npm run build && npx vitest run`
Expected: compila y tests pasan.

- [ ] **Step 3: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/frontend/src
git commit -m "feat(webconsole): TargetBadge y pagina de catalogos read-only"
```

---

### Task 14: Página Runs (home) — tabla hidratada

**Files:**
- Create: `webconsole/frontend/src/pages/RunsPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (ruta `/`)

**Interfaces:**
- Consumes: `listRuns()` (filas ya hidratadas por el BFF, Task 8).
- Produces: tabla home (Spec B §6): run_id (link a `/runs/{id}`), estado, modelo, plugin/source, prompt set, FPS, detecciones, duración; refresco cada 4s mientras haya un run `running`; botón *Nueva corrida*.

- [ ] **Step 1: Implementación**

```tsx
// webconsole/frontend/src/pages/RunsPage.tsx
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api'
import type { RunRow } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      listRuns()
        .then((r) => {
          if (!alive) return
          setRows(r)
          setError(null)
          // refresco solo mientras hay actividad (el resto es historial estático)
          if (r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
        })
        .catch((e) => alive && setError(String(e)))
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])
  if (error) return <p style={{ color: '#b00' }}>Error listando runs: {error}</p>
  if (!rows) return <p>Cargando…</p>
  return (
    <div>
      <p><Link to="/compose">➕ Nueva corrida</Link></p>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            {['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)'].map((h) => (
              <th key={h} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id}>
              <td style={CELL}><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
              <td style={CELL}>{r.status === 'running' ? '🟢 running' : r.status}</td>
              <td style={CELL}>{r.model ?? '—'}</td>
              <td style={CELL}>{r.source_type ?? '—'}</td>
              <td style={CELL}>{r.prompt_set_id ?? '—'}</td>
              <td style={CELL}>{r.fps_effective ?? '—'}</td>
              <td style={CELL}>{r.total_detections ?? '—'}</td>
              <td style={CELL}>{r.duration_seconds ?? '—'}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td style={CELL} colSpan={8}>Sin corridas todavía.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

En `App.tsx`: `import RunsPage from './pages/RunsPage'` y reemplazar la ruta `/`:

```tsx
        <Route path="/" element={<RunsPage />} />
```

- [ ] **Step 2: Verificar**

Run: `npm run build && npx vitest run`
Expected: compila y tests pasan.

- [ ] **Step 3: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/frontend/src
git commit -m "feat(webconsole): pagina home con tabla de runs hidratada"
```

---

### Task 15: Página Compositor — form + validación + lanzar + guardar manifiesto

**Files:**
- Create: `webconsole/frontend/src/pages/ComposePage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (ruta `/compose`)

**Interfaces:**
- Consumes: `getIngestPlugins`, `getDatasets`, `getPromptSets`, `getExperiments`, `validateComposition`, `launchRun`, `saveManifest`, `ApiError`.
- Produces: compositor (Spec B §6): plugin (solo `mvp_enabled` seleccionables) → dataset del catálogo **o** path/video; prompt set con toggles de clases activas (sets `frozen` muestran badge, las clases igual se togglean — lo congelado es el set en disco, no la selección); overrides `stride`/`max_units`/`save_annotated_video` (**sin thresholds** — read-only en Catálogos); errores de campo del BFF renderizados junto a cada control; 409 ofrece link al run activo; puede partir de un manifiesto (`?from=<experiment_id>`) aplicando `manifest_to_composition` **del BFF** vía el manifiesto crudo de `/api/catalog/experiments`, con la policy `model.ref` (checkbox de confirmación cuando el BFF devuelve error de campo `model`).

- [ ] **Step 1: Implementación**

```tsx
// webconsole/frontend/src/pages/ComposePage.tsx
import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ApiError, getDatasets, getExperiments, getIngestPlugins, getPromptSets,
  launchRun, saveManifest,
} from '../api'
import type {
  Composition, DatasetEntry, Experiment, FieldError, IngestPlugin, PromptSet,
} from '../types'

const ROW: CSSProperties = { display: 'grid', gap: 4, marginBottom: 14, maxWidth: 560 }

function FieldMsg({ errors, field }: { errors: FieldError[]; field: string }) {
  const msg = errors.filter((e) => e.field === field).map((e) => e.message).join('; ')
  return msg ? <small style={{ color: '#b00' }}>{msg}</small> : null
}

export default function ComposePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [plugins, setPlugins] = useState<IngestPlugin[]>([])
  const [datasets, setDatasets] = useState<DatasetEntry[]>([])
  const [sets, setSets] = useState<PromptSet[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [plugin, setPlugin] = useState('image_folder')
  const [dataset, setDataset] = useState('')
  const [path, setPath] = useState('')
  const [setId, setSetId] = useState('')
  const [activeIds, setActiveIds] = useState<string[]>([])
  const [stride, setStride] = useState('')
  const [maxUnits, setMaxUnits] = useState('')
  const [annotated, setAnnotated] = useState(false)
  const [manifestModelRef, setManifestModelRef] = useState<string | null>(null)
  const [confirmModel, setConfirmModel] = useState(false)
  const [errors, setErrors] = useState<FieldError[]>([])
  const [busyRunId, setBusyRunId] = useState<string | null>(null)
  const [saveName, setSaveName] = useState('')
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  useEffect(() => {
    getIngestPlugins().then(setPlugins).catch(() => setPlugins([]))
    getDatasets().then(setDatasets).catch(() => setDatasets([]))
    getPromptSets().then(setSets).catch(() => setSets([]))
    getExperiments().then(setExperiments).catch(() => setExperiments([]))
  }, [])

  const selectedSet = useMemo(() => sets.find((s) => s.id === setId), [sets, setId])
  useEffect(() => {
    if (selectedSet) setActiveIds(selectedSet.classes.filter((c) => c.enabled_by_default).map((c) => c.id))
  }, [selectedSet])

  // Prefill desde manifiesto (?from=<experiment_id>) — la traducción canónica vive en el
  // BFF; acá solo mapeamos el manifiesto crudo a los campos del form (mismo mapeo §5.4).
  useEffect(() => {
    const from = params.get('from')
    if (!from || experiments.length === 0) return
    const exp = experiments.find((e) => e.id === from)
    if (!exp) return
    const m = exp.manifest as Record<string, any>
    const source = m.source ?? {}
    if (source.ref) {
      setPlugin('image_folder')
      setDataset(source.ref)
    } else if (source.type) {
      setPlugin(source.type.includes('video') ? 'video_file' : source.type)
      setPath(source.path ?? '')
    }
    if (m.prompts?.ref) setSetId(m.prompts.ref)
    if (m.prompts?.active_ids) setActiveIds(m.prompts.active_ids)
    if (m.rate_control?.stride != null) setStride(String(m.rate_control.stride))
    if (m.run?.max_units != null) setMaxUnits(String(m.run.max_units))
    if (m.outputs?.save_annotated_video) setAnnotated(true)
    if (m.model?.ref) setManifestModelRef(m.model.ref)
  }, [params, experiments])

  const composition = (): Composition => ({
    ingest: {
      plugin,
      config: dataset ? { dataset } : path ? { path } : {},
    },
    prompts: { set_id: setId, active_ids: activeIds },
    run: {
      stride: stride ? Number(stride) : null,
      max_units: maxUnits ? Number(maxUnits) : null,
      save_annotated_video: annotated,
    },
    manifest_model_ref: manifestModelRef,
    confirm_target_model: confirmModel,
  })

  const submit = async () => {
    setErrors([])
    setBusyRunId(null)
    try {
      const { run_id } = await launchRun(composition())
      navigate(`/runs/${run_id}`)
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const payload = e.payload as { errors?: FieldError[]; detail?: string }
        setErrors(payload.errors ?? [{ field: '_service', message: String(payload.detail) }])
      } else if (e instanceof ApiError && e.status === 409) {
        setBusyRunId((e.payload as { active_run_id?: string }).active_run_id ?? null)
      } else {
        setErrors([{ field: '_target', message: String(e) }])
      }
    }
  }

  const save = async () => {
    setSaveMsg(null)
    try {
      const { path: saved } = await saveManifest({ name: saveName, composition: composition() })
      setSaveMsg(`Guardado en experiments/${saved}`)
    } catch (e) {
      setSaveMsg(`Error: ${e instanceof ApiError ? JSON.stringify(e.payload) : String(e)}`)
    }
  }

  const modelError = errors.some((e) => e.field === 'model')
  return (
    <div>
      <h2>Nueva corrida</h2>
      <div style={ROW}>
        <label>Partir de un manifiesto</label>
        <select
          value={params.get('from') ?? ''}
          onChange={(e) => navigate(`/compose?from=${encodeURIComponent(e.target.value)}`)}
        >
          <option value="">— desde cero —</option>
          {experiments.map((x) => (
            <option key={x.id} value={x.id}>{x.group ? `[${x.group}] ` : ''}{x.id}</option>
          ))}
        </select>
      </div>
      <div style={ROW}>
        <label>Plugin de ingesta</label>
        <select value={plugin} onChange={(e) => setPlugin(e.target.value)}>
          {plugins.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.mvp_enabled}>
              {p.id}{!p.mvp_enabled ? ' (no disponible en MVP)' : ''}
            </option>
          ))}
        </select>
        <FieldMsg errors={errors} field="ingest.plugin" />
      </div>
      <div style={ROW}>
        <label>Dataset del catálogo (o dejar vacío y dar un path)</label>
        <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
          <option value="">— path manual —</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id} disabled={!d.available}>
              {d.id}{!d.available ? ' (no montado)' : ''}
            </option>
          ))}
        </select>
        <FieldMsg errors={errors} field="ingest.config.dataset" />
        {!dataset && (
          <>
            <input placeholder="/ruta/a/imagenes o /ruta/video.mp4" value={path}
                   onChange={(e) => setPath(e.target.value)} />
            <FieldMsg errors={errors} field="ingest.config.path" />
          </>
        )}
      </div>
      <div style={ROW}>
        <label>Prompt set</label>
        <select value={setId} onChange={(e) => setSetId(e.target.value)}>
          <option value="">— elegir —</option>
          {sets.map((s) => (
            <option key={s.id} value={s.id}>{s.id}{s.frozen ? ' ❄' : ''}</option>
          ))}
        </select>
        <FieldMsg errors={errors} field="prompts.set_id" />
        {selectedSet && (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {selectedSet.classes.map((c) => (
              <label key={c.id}>
                <input
                  type="checkbox"
                  checked={activeIds.includes(c.id)}
                  onChange={(e) =>
                    setActiveIds((prev) =>
                      e.target.checked ? [...prev, c.id] : prev.filter((i) => i !== c.id),
                    )
                  }
                />{' '}
                {c.id}
              </label>
            ))}
          </div>
        )}
        <FieldMsg errors={errors} field="prompts.active_ids" />
      </div>
      <div style={ROW}>
        <label>Overrides (thresholds: read-only del modelo, ver Catálogos)</label>
        <input placeholder="stride (opcional)" value={stride} onChange={(e) => setStride(e.target.value)} />
        <FieldMsg errors={errors} field="run.stride" />
        <input placeholder="max_units (opcional)" value={maxUnits} onChange={(e) => setMaxUnits(e.target.value)} />
        <FieldMsg errors={errors} field="run.max_units" />
        <label>
          <input type="checkbox" checked={annotated} onChange={(e) => setAnnotated(e.target.checked)} />{' '}
          save_annotated_video
        </label>
      </div>
      {manifestModelRef && (
        <div style={ROW}>
          <small>El manifiesto declara modelo <b>{manifestModelRef}</b>.</small>
          {modelError && (
            <label style={{ color: '#b00' }}>
              <input type="checkbox" checked={confirmModel}
                     onChange={(e) => setConfirmModel(e.target.checked)} />{' '}
              Usar el modelo del target de todas formas
            </label>
          )}
          <FieldMsg errors={errors} field="model" />
        </div>
      )}
      <FieldMsg errors={errors} field="_target" />
      <FieldMsg errors={errors} field="_service" />
      {busyRunId && (
        <p style={{ color: '#c80' }}>
          Ya hay un run activo: <a href={`#/runs/${busyRunId}`}>{busyRunId}</a>
        </p>
      )}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button onClick={submit}>Lanzar</button>
        <input placeholder="nombre_manifiesto" value={saveName}
               onChange={(e) => setSaveName(e.target.value)} />
        <button onClick={save} disabled={!saveName}>Guardar como manifiesto</button>
      </div>
      {saveMsg && <p><small>{saveMsg}</small></p>}
    </div>
  )
}
```

En `App.tsx`: `import ComposePage from './pages/ComposePage'` y agregar `<Route path="/compose" element={<ComposePage />} />`.

- [ ] **Step 2: Verificar**

Run: `npm run build && npx vitest run`
Expected: compila y tests pasan.

- [ ] **Step 3: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/frontend/src
git commit -m "feat(webconsole): compositor con validacion de campos, 409 y guardar manifiesto"
```

---

### Task 16: Detalle de corrida — telemetría en vivo (WS) + resultados

**Files:**
- Create: `webconsole/frontend/src/stream.ts`, `webconsole/frontend/src/components/Sparkline.tsx`, `webconsole/frontend/src/pages/RunDetailPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (ruta `/runs/:id`)
- Test: `webconsole/frontend/src/__tests__/stream.test.ts`

**Interfaces:**
- Produces: `stream.ts` exporta `LiveState` (`{lastMetric, fpsHistory: number[], latencyHistory: number[], detectionsTotal: number, errors: [...], finalState: {status, error} | null}`), **`applyEvent(state: LiveState, event: StreamEvent): LiveState` (reducer puro — testeable sin DOM)** y `useRunStream(runId: string, enabled: boolean)` (WebSocket nativo a `streamUrl`; **reconexión con backoff 2s mientras `enabled`** — el fallback ante WS caído es reconectar, no polling de telemetría); `<Sparkline values={number[]} />` (SVG polyline, sin dependencias); `<RunDetailPage />`: en vivo muestra FPS/latencia por unidad (sparklines), VRAM, total de detecciones y tail de `error` como consola; **p95 y detecciones-por-label aparecen al terminar, desde `summary`** (contrato real; no son eventos en vivo); resultados: summary, tabla de detecciones (página 1), galería de previews (derivada de `unit_id` de las detecciones → `previews/{unit_id}.preview.jpg`), player de `annotated.mp4` si el artefacto existe, botón *Detener* (202 → esperar `state` final).

- [ ] **Step 1: Test del reducer que falla**

```typescript
// webconsole/frontend/src/__tests__/stream.test.ts
import { describe, expect, it } from 'vitest'
import { applyEvent, initialLiveState } from '../stream'

describe('applyEvent', () => {
  it('acumula métricas con historia acotada', () => {
    let state = initialLiveState()
    for (let i = 0; i < 400; i++) {
      state = applyEvent(state, {
        type: 'metric', unit_id: `u${i}`, fps: i, latency_total_ms: 100,
        detections_count: 1, gpu_memory_mb: 0,
      })
    }
    expect(state.lastMetric?.fps).toBe(399)
    expect(state.fpsHistory.length).toBeLessThanOrEqual(300) // acotada
  })

  it('suma detecciones y acota el tail de errores', () => {
    let state = initialLiveState()
    state = applyEvent(state, { type: 'detection', unit_id: 'u0', count: 3 })
    state = applyEvent(state, { type: 'detection', unit_id: 'u1', count: 2 })
    expect(state.detectionsTotal).toBe(5)
    for (let i = 0; i < 150; i++) {
      state = applyEvent(state, { type: 'error', unit_id: `u${i}`, stage: 'x', message: 'boom' })
    }
    expect(state.errors.length).toBeLessThanOrEqual(100)
  })

  it('registra el estado final', () => {
    const state = applyEvent(initialLiveState(), { type: 'state', status: 'succeeded', error: null })
    expect(state.finalState?.status).toBe('succeeded')
  })
})
```

Run: `npx vitest run src/__tests__/stream.test.ts`
Expected: FAIL (módulo `../stream` no existe)

- [ ] **Step 2: Implementación**

```typescript
// webconsole/frontend/src/stream.ts
import { useEffect, useReducer, useRef } from 'react'
import { streamUrl } from './api'
import type { StreamEvent } from './types'

const HISTORY_MAX = 300
const ERRORS_MAX = 100
const RECONNECT_MS = 2000

export interface LiveState {
  lastMetric: Extract<StreamEvent, { type: 'metric' }> | null
  fpsHistory: number[]
  latencyHistory: number[]
  detectionsTotal: number
  errors: Array<Extract<StreamEvent, { type: 'error' }>>
  finalState: { status: string; error: string | null } | null
}

export const initialLiveState = (): LiveState => ({
  lastMetric: null,
  fpsHistory: [],
  latencyHistory: [],
  detectionsTotal: 0,
  errors: [],
  finalState: null,
})

export function applyEvent(state: LiveState, event: StreamEvent): LiveState {
  switch (event.type) {
    case 'metric':
      return {
        ...state,
        lastMetric: event,
        fpsHistory: [...state.fpsHistory, event.fps].slice(-HISTORY_MAX),
        latencyHistory: [...state.latencyHistory, event.latency_total_ms].slice(-HISTORY_MAX),
      }
    case 'detection':
      return { ...state, detectionsTotal: state.detectionsTotal + event.count }
    case 'error':
      return { ...state, errors: [...state.errors, event].slice(-ERRORS_MAX) }
    case 'state':
      return { ...state, finalState: { status: event.status, error: event.error } }
    default:
      return state
  }
}

export function useRunStream(runId: string, enabled: boolean): LiveState {
  const [state, dispatch] = useReducer(applyEvent, undefined, initialLiveState)
  const stopped = useRef(false)
  useEffect(() => {
    if (!enabled) return
    stopped.current = false
    let socket: WebSocket | null = null
    let timer: ReturnType<typeof setTimeout>
    const connect = () => {
      socket = new WebSocket(streamUrl(runId))
      socket.onmessage = (message) => dispatch(JSON.parse(message.data) as StreamEvent)
      // Fallback ante caída: RECONECTAR (el run activo sigue siendo suscribible);
      // el polling de GET /api/runs/{id} solo re-hidrata estado, no telemetría.
      socket.onclose = (ev) => {
        if (!stopped.current && ev.code !== 4404 && ev.code !== 1000) {
          timer = setTimeout(connect, RECONNECT_MS)
        }
      }
    }
    connect()
    return () => {
      stopped.current = true
      clearTimeout(timer)
      socket?.close()
    }
  }, [runId, enabled])
  return state
}
```

```tsx
// webconsole/frontend/src/components/Sparkline.tsx
export default function Sparkline({ values, width = 220, height = 40 }: {
  values: number[]; width?: number; height?: number
}) {
  if (values.length < 2) return <svg width={width} height={height} />
  const max = Math.max(...values, 1e-9)
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * width},${height - (v / max) * (height - 2)}`)
    .join(' ')
  return (
    <svg width={width} height={height}>
      <polyline points={points} fill="none" stroke="#36c" strokeWidth={1.5} />
    </svg>
  )
}
```

```tsx
// webconsole/frontend/src/pages/RunDetailPage.tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { artifactUrl, getDetections, getRun, stopRun } from '../api'
import Sparkline from '../components/Sparkline'
import { useRunStream } from '../stream'
import type { DetectionsPage, RunDetail } from '../types'

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [detections, setDetections] = useState<DetectionsPage | null>(null)
  const [hasVideo, setHasVideo] = useState(false)
  const running = run?.status === 'running'
  const live = useRunStream(id, Boolean(running))

  const refresh = () => getRun(id).then(setRun).catch(() => setRun(null))
  useEffect(() => {
    refresh()
  }, [id])
  // El evento `state` marca el fin: re-hidratar estado+summary desde el BFF.
  useEffect(() => {
    if (live.finalState) refresh()
  }, [live.finalState])
  useEffect(() => {
    if (run && !running) {
      getDetections(id, 1, 24).then(setDetections).catch(() => setDetections(null))
      fetch(artifactUrl(id, 'annotated.mp4'), { method: 'GET', headers: { range: 'bytes=0-0' } })
        .then((r) => setHasVideo(r.ok))
        .catch(() => setHasVideo(false))
    }
  }, [run?.status])

  if (!run) return <p>Cargando run {id}…</p>
  const summary = (run.summary ?? {}) as Record<string, any>
  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <h2>
        {run.run_id} — {run.status}{' '}
        {running && <button onClick={() => stopRun(id)}>■ Detener</button>}
      </h2>
      {running && (
        <section style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          <div>
            <b>FPS</b> {live.lastMetric?.fps ?? '—'}
            <Sparkline values={live.fpsHistory} />
          </div>
          <div>
            <b>Latencia/unidad (ms)</b> {live.lastMetric?.latency_total_ms ?? '—'}
            <Sparkline values={live.latencyHistory} />
          </div>
          <div><b>VRAM (MB)</b> {live.lastMetric?.gpu_memory_mb ?? '—'}</div>
          <div><b>Detecciones</b> {live.detectionsTotal}</div>
          <div style={{ width: '100%' }}>
            <b>Errores (tail)</b>
            <pre style={{ maxHeight: 140, overflow: 'auto', background: '#f6f6f6', padding: 8 }}>
              {live.errors.map((e) => `${e.unit_id ?? '?'} [${e.stage}] ${e.message}\n`)}
              {live.errors.length === 0 && 'sin errores'}
            </pre>
          </div>
          <small>p95 y detecciones-por-label se calculan al terminar (summary).</small>
        </section>
      )}
      {!running && run.summary && (
        <section>
          <h3>Summary</h3>
          <ul>
            <li>modelo: {summary.model_name} ({summary.device}) — prompts: {summary.prompt_set_id}</li>
            <li>unidades: {summary.units_processed} · detecciones: {summary.total_detections}</li>
            <li>FPS: {summary.fps_effective} · p95: {summary.p95_latency_ms} ms · dur: {summary.duration_seconds}s</li>
            <li>
              por label:{' '}
              {Object.entries(summary.detections_by_label ?? {})
                .map(([k, v]) => `${k}=${v}`)
                .join(', ') || '—'}
            </li>
          </ul>
          {hasVideo && (
            <video controls width={640} src={artifactUrl(id, 'annotated.mp4')} />
          )}
          {detections && (
            <>
              <h3>Detecciones (pág. 1 de {Math.ceil(detections.total / detections.page_size)})</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {detections.items.map((d: any) => (
                  <figure key={d.unit_id} style={{ margin: 0 }}>
                    <img
                      src={artifactUrl(id, `previews/${d.unit_id}.preview.jpg`)}
                      alt={d.unit_id}
                      width={160}
                      onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
                    />
                    <figcaption><small>{d.unit_id} ({(d.detections ?? []).length})</small></figcaption>
                  </figure>
                ))}
              </div>
            </>
          )}
        </section>
      )}
    </div>
  )
}
```

En `App.tsx`: `import RunDetailPage from './pages/RunDetailPage'` y agregar `<Route path="/runs/:id" element={<RunDetailPage />} />`.

- [ ] **Step 3: Verificar**

Run: `npx vitest run && npm run build`
Expected: PASS (3 tests de stream + api) y build limpio.

- [ ] **Step 4: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole/frontend/src
git commit -m "feat(webconsole): detalle de corrida con telemetria WS en vivo y resultados"
```

---

### Task 17: Integración — SPA estática desde el BFF + Makefile + README + smoke E2E

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (montar SPA), `README.md` del repo (sección webconsole)
- Create: `webconsole/Makefile`, `webconsole/README.md`
- Test: `webconsole/backend/tests/test_meta.py` (agregar test del mount estático)

**Interfaces:**
- Produces: el BFF sirve `webconsole/frontend/dist/` en `/` (mount `StaticFiles(html=True)` **después** de los routers — `/api/*` y el WS tienen precedencia; el SPA usa HashRouter así que no hace falta fallback de rutas profundas); `make -C webconsole {install,test,build,serve,dev-backend,dev-frontend,smoke}`.

- [ ] **Step 1: Test que falla**

Agregar a `tests/test_meta.py`:

```python
def test_spa_estatica_montada(tmp_path):
    settings = _settings(tmp_path)
    dist = tmp_path / "webconsole" / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>console</body></html>")
    with TestClient(create_app(settings)) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "console" in r.text
        # /api sigue teniendo precedencia sobre el mount estático
        assert client.get("/api/health").json() == {"status": "ok"}


def test_sin_dist_no_rompe(tmp_path):
    with TestClient(create_app(_settings(tmp_path))) as client:
        assert client.get("/api/health").status_code == 200
```

Run: `pytest tests/test_meta.py -q` → Expected: FAIL (404 en `/`)

- [ ] **Step 2: Implementación**

En `app.py`, al final de `create_app` (después de todos los `include_router`):

```python
from fastapi.staticfiles import StaticFiles
...
    frontend_dist = settings.repo_root / "webconsole" / "frontend" / "dist"
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
    return app
```

```makefile
# webconsole/Makefile
PY = backend/.venv/bin/python
PORT ?= 8090

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

test:
	cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests
	cd frontend && npx vitest run

build:
	cd frontend && npm run build

serve: build
	cd backend && .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --host 0.0.0.0 --port $(PORT)

dev-backend:
	cd backend && .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --port $(PORT) --reload

dev-frontend:
	cd frontend && npm run dev

smoke:
	curl -sf http://localhost:$(PORT)/api/health && curl -sf http://localhost:$(PORT)/api/target && echo OK
```

```markdown
<!-- webconsole/README.md -->
# E-OVRT Web Console (MVP)

Consola web de la plataforma E-OVRT-VDP: BFF FastAPI (`backend/`) + SPA React (`frontend/`),
**cliente** del servicio media-plane (Spec B). No ejecuta el pipeline: habla HTTP/WS con la
instancia del servicio (`EOVRT_CONSOLE_SERVICE_URL`, default `http://localhost:8080`).

## Uso

```bash
make install                       # venv backend + npm install
make test                          # pytest + ruff + vitest
make serve                         # build SPA + BFF en :8090 (sirve la SPA)
# Dev con hot-reload (dos terminales):
make dev-backend                   # BFF :8090
make dev-frontend                  # Vite :5173 (proxy /api -> :8090)
```

Requiere el servicio media-plane corriendo (p.ej. `EOVRT_MODEL_REF=mock make serve`
en `../e-ovrt_media-plane`). Env vars: `EOVRT_CONSOLE_SERVICE_URL`,
`EOVRT_CONSOLE_REPO_ROOT` (default: autodescubierto), `EOVRT_CONSOLE_FROZEN_SETS`
(default `cr01_cr02_bench_v2`).
```

En el `README.md` de la raíz del repo, agregar a la descripción del layout una línea:

```markdown
- `webconsole/` — consola web (BFF FastAPI + SPA React), cliente del servicio media-plane. Ver `webconsole/README.md`.
```

- [ ] **Step 3: Verificar backend + build**

Run: `cd webconsole/backend && pytest -q && ruff check src tests && cd ../frontend && npm run build && npx vitest run`
Expected: PASS todo.

- [ ] **Step 4: Smoke E2E contra el servicio real (mock) — verificación manual**

```bash
# Terminal 1 — servicio media-plane con detector mock:
cd ../e-ovrt_media-plane && source .venv/bin/activate && EOVRT_MODEL_REF=mock make serve
# Terminal 2 — consola:
cd e-ovrt_experimental-setup && make -C webconsole serve
# Terminal 3 — smoke:
make -C webconsole smoke                       # OK
curl -s localhost:8090/api/target | python3 -m json.tool   # ready:true, model.ref:"mock"
curl -s localhost:8090/api/catalog/prompt-sets | python3 -m json.tool
# Lanzar una corrida real vía la consola (dataset del catálogo del servicio):
curl -X POST localhost:8090/api/runs -H 'Content-Type: application/json' -d '{
  "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
  "prompts": {"set_id": "cr01_cr02_v2_short", "active_ids": ["person"]},
  "run": {"max_units": 5}
}'
# -> 201 {"run_id": ...}; abrir http://localhost:8090/#/runs/<run_id> y ver telemetría en vivo.
```

Expected: 201, telemetría visible en el navegador, y al terminar summary + detecciones en el detalle. Reportar el resultado (o el error exacto) en el resumen de la task.

- [ ] **Step 5: Commit** *(solo si el usuario habilitó commits)*

```bash
git add webconsole README.md webconsole/backend/tests/test_meta.py
git commit -m "feat(webconsole): SPA servida por el BFF, Makefile y smoke E2E"
```

---

## Cobertura Spec B → tasks (self-review)

| Spec B | Task(s) |
|---|---|
| §3 settings BFF (`SERVICE_URL`, raíz in-repo) | 1 |
| §4 modelo por instancia (UI muestra `GET /api/model`) | 2, 13 |
| §5.1 CatalogService (proxy + in-repo + `frozen` convención BFF) | 3, 4 |
| §5.2 RunComposer (form→request, validación contra target, `POST /api/compose/validate`) | 5, 7 |
| §5.3 ManifestWriter (in-repo, atómico, `model.ref` del target) | 11 |
| §5.4 traducción manifiesto↔request (`config.dataset`, tests ida-y-vuelta reales, policy model.ref) | 5, 7 |
| §5.5 RunBackend (launch/stop/status/stream/list/artifacts) | 6, 8, 9, 10 |
| §5.6 TelemetryProxy (coalescing, drop-oldest, reconexión) + ResultsProxy (Range pass-through) | 9, 10, 16 |
| §6 pantallas (home hidratada N+1, compositor sin thresholds, detalle con eventos reales, catálogos con badges por policy) | 13, 14, 15, 16 |
| §7 flujo de datos | 8, 10, 16 |
| §8 errores (422 mapeado a campos, 409 busy con link, servicio no ready, WS caído→reconectar) | 7, 8, 15, 16 |
| §9 testing (fake service, ida-y-vuelta sobre manifiestos reales, RunBackend contra fake, Vitest) | 2, 5, 6, 10, 12, 16 |
| §11 riesgos (proxy WS obligatorio sin CORS, streaming sin bufferizar, traducción centralizada) | 9, 10, y Global Constraints |

Fuera del MVP (explícito en Spec B §1): RTSP vivo, registro de cámaras, editor de manifiestos/prompt sets, evaluación BENCH/compare-runs, multi-nodo, auth.






