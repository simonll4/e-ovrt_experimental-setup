# Plataforma DBE containerizada + orquestación desde la consola — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerizar el servicio media-plane y la consola, declarar el fleet de instancias (una por modelo) en un compose de plataforma, y orquestar su ciclo de vida (activar/apagar/switch atómico) desde la webconsole.

**Architecture:** Convención `/infra` en dos niveles: cada repo de servicio es dueño de su imagen y su deploy standalone (`e-ovrt_media-plane/infra/`, `e-ovrt_experimental-setup/infra/console/`); el compose de plataforma (`e-ovrt_experimental-setup/infra/platform/`) reutiliza esas imágenes y agrega la orquestación. El BFF gana `ComposeOrchestrator` (3 verbos `docker compose` por subprocess) + `TargetManager` (target dinámico con switch atómico), habilitados solo con `EOVRT_CONSOLE_COMPOSE_DIR`; sin esa var todo opera como hoy (modo static).

**Tech Stack:** Docker + compose plugin (host ya tiene 29.5.3 + nvidia-container-toolkit), FastAPI/httpx/pytest (BFF), React/vitest (frontend). Sin SDK de Docker (subprocess del CLI).

**Spec:** `docs/superpowers/specs/2026-07-05-plataforma-dbe-docker-orquestacion-design.md` (mismo repo).

## Global Constraints

- **NO COMMITS**: regla del workspace — nunca correr `git commit`; todo queda en working tree. El usuario commitea explícitamente. **Ningún task tiene paso de commit.**
- **Ramas actuales, sin merge a main**: `e-ovrt_media-plane` @ `feature/inference-service`; `e-ovrt_experimental-setup` @ `feature/webconsole`. Verificar branch antes de editar.
- **Modo static intacto**: sin `EOVRT_CONSOLE_COMPOSE_DIR`, la consola opera EXACTAMENTE como hoy (target fijo `EOVRT_CONSOLE_SERVICE_URL`); los 116 tests BFF y 26 vitest existentes deben seguir pasando sin modificación. Endpoints `/api/platform/*` → 501 en modo static.
- **Una activa a la vez, switch atómico** (aplica a TODAS las instancias del fleet, mock incluido): stop de las running → up de la nueva → poll `/readyz` → swap del target. Sin rollback automático si falla.
- **Allowlist**: todo nombre de instancia que entre por API se valida contra el fleet declarado (labels `eovrt.instance=true` en `docker compose config`); nunca input libre hacia el socket.
- **Una definición de imagen por servicio**, dueño el repo del servicio: la imagen mp es `e-ovrt_media-plane/infra/docker/Dockerfile` (el actual Dockerfile raíz MOVIDO, no copiado); la de consola es `e-ovrt_experimental-setup/infra/console/Dockerfile`. El compose de plataforma solo las referencia.
- **Nombre de proyecto compose fijo**: `--project-name eovrt` en toda invocación del BFF (constante `PROJECT_NAME = "eovrt"`).
- Labels exactos: `eovrt.instance: "true"`, `eovrt.model_ref: <ref>`. Instancias: `mp-mock`, `mp-gdino-tiny`, `mp-gdino-base`, `mp-yoloe-26s`, `mp-yoloe-26m`, `mp-yoloe-26l`, `mp-yoloe-26x`.
- El compose de plataforma usa **paths absolutos de host vía `${EOVRT_WORKSPACE}`** (`.env` en `infra/platform/`), NUNCA binds relativos: el BFF re-ejecuta compose desde dentro del contenedor y los relativos resolverían contra un filesystem que no es el del host.
- `up` siempre con `--no-build` (el BFF no construye imágenes; el build es un paso de bootstrap desde el host).
- Env vars nuevas de la consola: `EOVRT_CONSOLE_COMPOSE_DIR` (habilita orquestación), `EOVRT_CONSOLE_SWITCH_TIMEOUT` (segundos, default `300`), `EOVRT_CONSOLE_SPA_DIST` (path del dist embebido en la imagen).
- Artefactos two-node deprecados en `e-ovrt_media-plane/deploy/` NO se tocan.
- Comandos de test: BFF `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest <file> -q`; frontend `cd .../webconsole/frontend && npm test` y `npm run build`; media-plane `cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest -q`.

---

### Task 1: `/infra` del media-plane (imagen movida + compose standalone + README)

**Files:**
- Move: `e-ovrt_media-plane/Dockerfile` → `e-ovrt_media-plane/infra/docker/Dockerfile` (con `git mv`)
- Create: `e-ovrt_media-plane/infra/docker-compose.yml`
- Create: `e-ovrt_media-plane/infra/README.md`
- Modify: `e-ovrt_media-plane/CLAUDE.md` (nota de infra en Commands)

**Interfaces:**
- Produces: imagen `eovrt/media-plane:latest` construible con `docker compose -f infra/docker-compose.yml build`; deploy standalone de UNA instancia con `EOVRT_MODEL_REF` por env. Tasks 9–11 referencian este Dockerfile desde el compose de plataforma (`dockerfile: infra/docker/Dockerfile`, context = raíz del repo media-plane).
- Nota: el Dockerfile actual COPYa `pyproject.toml constraints.txt src configs` relativos al **build context** (raíz del repo), así que moverlo NO requiere cambiar su contenido — solo el `dockerfile:` del compose apunta al path nuevo. `.dockerignore` queda en la raíz (aplica al context).

- [x] **Step 1: Mover el Dockerfile**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane
mkdir -p infra/docker
git mv Dockerfile infra/docker/Dockerfile
```

- [x] **Step 2: Crear `infra/docker-compose.yml`** (deploy standalone: una instancia, modelo por env)

```yaml
# Deploy standalone del servicio media-plane: UNA instancia, modelo por env.
# Uso:  EOVRT_MODEL_REF=grounding-dino/gdino-tiny docker compose up -d
# Para host sin GPU (solo mock): comentar el bloque deploy.resources.
name: eovrt-mp
services:
  media-plane:
    build:
      context: ..
      dockerfile: infra/docker/Dockerfile
    image: eovrt/media-plane:latest
    environment:
      EOVRT_MODEL_REF: ${EOVRT_MODEL_REF:-mock}
    ports: ["8080:8080"]
    volumes:
      - ../models:/app/models:ro                      # pesos locales (catálogos usan paths CWD-relativos)
      - ../mobileclip2_b.ts:/app/mobileclip2_b.ts:ro  # cache del text-encoder de YOLOE (evita descarga)
      - ../runs:/data/runs                            # artefactos compartidos con el host
      - ../../e-ovrt_datasets:/e-ovrt_datasets:ro     # GT/datasets: ../e-ovrt_datasets resuelve desde /app
      - weights-cache:/data/weights                   # HF_HOME (fallback si falta un local_dir)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
volumes:
  weights-cache: {}
```

- [x] **Step 3: Crear `infra/README.md`**

```markdown
# Infra — servicio media-plane (deploy standalone)

Imagen y compose para desplegar **solo este servicio** (una instancia). La plataforma
completa (consola + fleet de modelos) vive en `e-ovrt_experimental-setup/infra/platform/`.

## Build + run

```bash
cd infra
docker compose build                                  # imagen eovrt/media-plane:latest
EOVRT_MODEL_REF=mock docker compose up -d             # o grounding-dino/gdino-tiny, yoloe/yoloe-26s, ...
curl -s http://localhost:8080/readyz                  # {"status":"ready","model":"..."}
```

Requisitos: pesos descargados en `../models/` (`make download-models`), repo
`e-ovrt_datasets` como hermano (para datasets/GT del BENCH), y para modelos GPU el
runtime NVIDIA (`nvidia-container-toolkit`). En host sin GPU, comentar el bloque
`deploy.resources` (solo `mock` tiene sentido ahí; `device: auto` cae a cpu solo).

## Smoke

```bash
curl -s -X POST http://localhost:8080/api/runs -H 'Content-Type: application/json' -d '{
  "ingest": {"plugin": "image_folder", "config": {"dataset": "demo_v2"}},
  "prompts": {"set_inline": {"id": "smoke", "classes": [{"id": "person", "phrasings": {"default": ["person"]}}]},
               "active_ids": null},
  "run": {"max_units": 3}
}'
# esperar succeeded:
curl -s http://localhost:8080/api/runs/<run_id>
```

Cambiar de modelo = `docker compose down` + `up` con otro `EOVRT_MODEL_REF` (sin
recarga in-process, por diseño del Spec A).
```

- [x] **Step 4: Nota en `CLAUDE.md` del media-plane** — en la sección Commands, después del bloque de `make serve`/smoke, agregar:

```markdown
# Docker (deploy standalone de este servicio; la plataforma completa vive en
# e-ovrt_experimental-setup/infra/platform/):
cd infra && EOVRT_MODEL_REF=mock docker compose up -d   # imagen: infra/docker/Dockerfile
```

- [x] **Step 5: Verificar que el compose resuelve y la suite no se rompió**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane/infra && docker compose config -q && echo CONFIG-OK`
Expected: `CONFIG-OK` (sin errores de sintaxis/paths).
Run: `cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: 421 passed (mover el Dockerfile no toca código).

- [x] **Step 6 (build real, lento — hacerlo una vez y seguir):**

Run: `cd /home/simonll4/projects/e-ovrt_media-plane/infra && docker compose build 2>&1 | tail -5`
Expected: imagen `eovrt/media-plane:latest` construida (descarga torch CUDA, puede tardar >10 min la primera vez). Si falla por red/espacio, reportarlo como concern y seguir — Tasks 10–11 lo necesitan resuelto.

---

### Task 2: Settings de la consola (`compose_dir`, `switch_timeout`, `spa_dist`) + override del dist

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/settings.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (solo la línea del `frontend_dist`)
- Test: `webconsole/backend/tests/test_settings.py` (extender)

**Interfaces:**
- Produces: `ConsoleSettings.compose_dir: Path | None` (env `EOVRT_CONSOLE_COMPOSE_DIR`; `None` = modo static), `switch_timeout_seconds: float` (env `EOVRT_CONSOLE_SWITCH_TIMEOUT`, default `300.0`), `spa_dist: Path | None` (env `EOVRT_CONSOLE_SPA_DIST`). `create_app` sirve la SPA desde `spa_dist` si está seteado, sino desde `repo_root/webconsole/frontend/dist` como hoy. Tasks 3–5 leen estos settings.

- [x] **Step 1: Tests que fallan** (agregar a `tests/test_settings.py`; usar el patrón de env-dict del archivo)

```python
def test_compose_dir_default_none_y_override(repo):
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).compose_dir is None
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_COMPOSE_DIR": "/x/infra/platform"})
    assert s.compose_dir == Path("/x/infra/platform")


def test_switch_timeout_default_y_override(repo):
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).switch_timeout_seconds == 300.0
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_SWITCH_TIMEOUT": "45"})
    assert s.switch_timeout_seconds == 45.0


def test_spa_dist_override(repo):
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).spa_dist is None
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_SPA_DIST": "/app/spa-dist"})
    assert s.spa_dist == Path("/app/spa-dist")
```

(Si `test_settings.py` no importa `Path`, agregar `from pathlib import Path`.)

- [x] **Step 2: Correr y verificar RED**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest tests/test_settings.py -q`
Expected: FAIL con `AttributeError`/`TypeError` (campos inexistentes).

- [x] **Step 3: Implementar en `settings.py`** — agregar al dataclass (después de `protected_groups`):

```python
    # Orquestación de plataforma (None = modo static, la consola opera como cliente
    # de un único EOVRT_CONSOLE_SERVICE_URL fijo, sin tocar Docker).
    compose_dir: Path | None = None
    switch_timeout_seconds: float = 300.0
    # Dist de la SPA embebido en la imagen de la consola; None = repo_root/webconsole/frontend/dist.
    spa_dist: Path | None = None
```

y en `from_env`, dentro del `return cls(...)`:

```python
            compose_dir=Path(env["EOVRT_CONSOLE_COMPOSE_DIR"]) if env.get("EOVRT_CONSOLE_COMPOSE_DIR") else None,
            switch_timeout_seconds=float(env.get("EOVRT_CONSOLE_SWITCH_TIMEOUT", "300")),
            spa_dist=Path(env["EOVRT_CONSOLE_SPA_DIST"]) if env.get("EOVRT_CONSOLE_SPA_DIST") else None,
```

- [x] **Step 4: Override del dist en `app.py`** — reemplazar la línea del mount:

```python
    frontend_dist = settings.spa_dist or (settings.repo_root / "webconsole" / "frontend" / "dist")
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
```

- [x] **Step 5: GREEN + regresión**

Run: `.venv/bin/python -m pytest tests/test_settings.py tests/test_compose.py -q`
Expected: PASS todos.

---

### Task 3: `ComposeOrchestrator` (3 verbos compose por subprocess, allowlist)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/orchestrator.py` (parte 1: orquestador; Task 4 agrega `TargetManager` al mismo archivo)
- Create: `webconsole/backend/tests/test_orchestrator.py`

**Interfaces:**
- Produces (Task 4/5 consumen): excepciones `ComposeError(RuntimeError)`, `UnknownInstance(KeyError)`; tipo `RunCmd = Callable[..., Awaitable[tuple[int, str, str]]]` (firma `run_cmd(*args: str, cwd: Path)` → `(returncode, stdout, stderr)`); clase `ComposeOrchestrator(compose_dir: Path, run_cmd: RunCmd | None = None)` con `async fleet() -> dict[str, str]` (name→model_ref, cacheado), `async ps() -> dict[str, str]` (name→state, solo instancias del fleet), `async up(name)`, `async stop(name)`, `async require(name)` (levanta `UnknownInstance`). Constantes `PROJECT_NAME = "eovrt"`, `INSTANCE_LABEL = "eovrt.instance"`, `MODEL_REF_LABEL = "eovrt.model_ref"`.

- [x] **Step 1: Tests que fallan** — crear `tests/test_orchestrator.py`:

```python
import json
from pathlib import Path

import pytest

from eovrt_webconsole.orchestrator import (
    ComposeError,
    ComposeOrchestrator,
    UnknownInstance,
)

CONFIG_JSON = json.dumps({
    "services": {
        "console": {"labels": {}},
        "mp-mock": {"labels": {"eovrt.instance": "true", "eovrt.model_ref": "mock"}},
        # compose puede normalizar labels a lista "k=v": el parser debe tolerar ambas formas
        "mp-gdino-tiny": {"labels": ["eovrt.instance=true", "eovrt.model_ref=grounding-dino/gdino-tiny"]},
    }
})


def make_fake_compose(state: dict):
    """run_cmd fake: sirve config/ps desde `state` y registra up/stop."""
    async def run_cmd(*args: str, cwd: Path):
        verb = args[4]  # docker compose --project-name eovrt <verb> ...
        state.setdefault("calls", []).append(list(args))
        if verb == "config":
            return 0, CONFIG_JSON, ""
        if verb == "ps":
            lines = "\n".join(
                json.dumps({"Service": n, "State": s}) for n, s in state.get("ps", {}).items()
            )
            return 0, lines, ""
        if verb == "up":
            if state.get("fail_up"):
                return 1, "", "boom del daemon"
            state["ps"][args[-1]] = "running"
            return 0, "", ""
        if verb == "stop":
            state["ps"][args[-1]] = "exited"
            return 0, "", ""
        return 1, "", f"verb inesperado: {verb}"
    return run_cmd


@pytest.fixture
def state():
    return {"ps": {"mp-mock": "exited"}}


@pytest.fixture
def orch(state, tmp_path):
    return ComposeOrchestrator(tmp_path, run_cmd=make_fake_compose(state))


async def test_fleet_filtra_por_label_y_tolera_lista(orch):
    fleet = await orch.fleet()
    assert fleet == {"mp-mock": "mock", "mp-gdino-tiny": "grounding-dino/gdino-tiny"}
    assert "console" not in fleet


async def test_ps_solo_instancias_del_fleet(orch, state):
    state["ps"]["console"] = "running"  # no debe aparecer
    assert await orch.ps() == {"mp-mock": "exited"}


async def test_up_y_stop_pasan_por_compose(orch, state):
    await orch.up("mp-mock")
    assert state["ps"]["mp-mock"] == "running"
    up_call = next(c for c in state["calls"] if "up" in c)
    assert "--no-build" in up_call and "--project-name" in up_call and "eovrt" in up_call
    await orch.stop("mp-mock")
    assert state["ps"]["mp-mock"] == "exited"


async def test_nombre_fuera_del_fleet_es_unknown(orch):
    with pytest.raises(UnknownInstance):
        await orch.up("console")
    with pytest.raises(UnknownInstance):
        await orch.stop("rm -rf")


async def test_error_de_compose_levanta_con_stderr(orch, state):
    state["fail_up"] = True
    with pytest.raises(ComposeError, match="boom del daemon"):
        await orch.up("mp-mock")
```

- [x] **Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_orchestrator.py -q`
Expected: FAIL con `ModuleNotFoundError: eovrt_webconsole.orchestrator`.

- [x] **Step 3: Implementar `orchestrator.py`** (parte orquestador):

```python
"""Orquestación del fleet de instancias media-plane vía `docker compose` (spec §3).

El compose de plataforma es la única fuente de verdad del fleet; este módulo
ejecuta exactamente 3 verbos (config/ps/up/stop) con nombres validados contra
la allowlist de labels — nunca input libre hacia el socket de Docker.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

PROJECT_NAME = "eovrt"
INSTANCE_LABEL = "eovrt.instance"
MODEL_REF_LABEL = "eovrt.model_ref"
_COMPOSE_TIMEOUT_S = 60.0

RunCmd = Callable[..., Awaitable[tuple[int, str, str]]]


class ComposeError(RuntimeError):
    """docker compose falló (exit != 0, timeout o salida imparseable)."""


class UnknownInstance(KeyError):
    """Nombre fuera del fleet declarado."""


async def _run_subprocess(*args: str, cwd: Path) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=_COMPOSE_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        raise ComposeError(f"docker compose colgado (> {_COMPOSE_TIMEOUT_S:.0f}s): {' '.join(args)}")
    return proc.returncode or 0, stdout.decode(), stderr.decode()


def _normalize_labels(raw: Any) -> dict[str, str]:
    """compose config puede emitir labels como dict o como lista "k=v"."""
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    out: dict[str, str] = {}
    for item in raw or []:
        key, _, value = str(item).partition("=")
        out[key] = value
    return out


class ComposeOrchestrator:
    def __init__(self, compose_dir: Path, run_cmd: RunCmd | None = None) -> None:
        self._dir = compose_dir
        self._run_cmd = run_cmd or _run_subprocess
        self._fleet: dict[str, str] | None = None

    async def _compose(self, *args: str) -> str:
        code, out, err = await self._run_cmd(
            "docker", "compose", "--project-name", PROJECT_NAME, *args, cwd=self._dir
        )
        if code != 0:
            raise ComposeError(err.strip() or out.strip() or f"exit {code}: {' '.join(args)}")
        return out

    async def fleet(self) -> dict[str, str]:
        """Instancias declaradas (label eovrt.instance) → model_ref. Cacheado."""
        if self._fleet is None:
            out = await self._compose("config", "--format", "json")
            services = json.loads(out).get("services", {})
            fleet: dict[str, str] = {}
            for name, svc in services.items():
                labels = _normalize_labels(svc.get("labels"))
                if labels.get(INSTANCE_LABEL) == "true":
                    fleet[name] = labels.get(MODEL_REF_LABEL, "?")
            self._fleet = fleet
        return self._fleet

    async def require(self, name: str) -> None:
        if name not in await self.fleet():
            raise UnknownInstance(name)

    async def ps(self) -> dict[str, str]:
        """Estado actual de las instancias del fleet (ausente = nunca creada)."""
        out = await self._compose("ps", "-a", "--format", "json")
        text = out.strip()
        if not text:
            return {}
        try:  # compose emite array JSON o NDJSON según versión
            data = json.loads(text)
            rows = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        fleet = await self.fleet()
        return {
            r["Service"]: str(r.get("State", "unknown"))
            for r in rows
            if r.get("Service") in fleet
        }

    async def up(self, name: str) -> None:
        await self.require(name)
        await self._compose("up", "-d", "--no-build", name)

    async def stop(self, name: str) -> None:
        await self.require(name)
        await self._compose("stop", name)
```

- [x] **Step 4: GREEN**

Run: `.venv/bin/python -m pytest tests/test_orchestrator.py -q`
Expected: PASS (6 tests).

---

### Task 4: `TargetManager` (target dinámico + switch atómico)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/orchestrator.py` (agregar al final)
- Test: `webconsole/backend/tests/test_orchestrator.py` (extender)

**Interfaces:**
- Consumes: `ComposeOrchestrator` (Task 3), `RunBackend` (existente), `ConsoleSettings.switch_timeout_seconds` (Task 2), fake service existente (`tests/fake_service.py`: tiene `/readyz` gateado por `state.ready` y `/api/runs` con `active_run_id`).
- Produces (Task 5 consume): excepciones `PlatformBusy(run_id: str)`, `SwitchFailed(step: str, detail: str)`; clase `TargetManager(app, orchestrator, settings, service_transport=None, poll_interval: float = 2.0)` con `active: str | None`, `async bootstrap()`, `async switch(name) -> dict` (retorna `{"target": name, "model_ref": ref}`), `async stop_active()`, `async instances() -> list[dict]` (shape del spec §4). Constante `NO_TARGET_URL`.

- [x] **Step 1: Tests que fallan** (agregar a `tests/test_orchestrator.py`):

```python
import dataclasses

import httpx
from fastapi import FastAPI

from eovrt_webconsole.orchestrator import PlatformBusy, SwitchFailed, TargetManager
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service


@pytest.fixture
def fake_state():
    return FakeState()


@pytest.fixture
def manager(state, fake_state, tmp_path, repo):
    settings = ConsoleSettings(
        service_url="http://ignored", repo_root=repo, frozen_set_ids=frozenset(),
        compose_dir=tmp_path, switch_timeout_seconds=1.0,
    )
    app = FastAPI()
    orch = ComposeOrchestrator(tmp_path, run_cmd=make_fake_compose(state))
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    return TargetManager(app, orch, settings, service_transport=transport, poll_interval=0.01)


async def test_bootstrap_sin_running_deja_target_none(manager):
    await manager.bootstrap()
    assert manager.active is None


async def test_bootstrap_con_una_running_la_adopta(manager, state):
    state["ps"]["mp-mock"] = "running"
    await manager.bootstrap()
    assert manager.active == "mp-mock"


async def test_switch_apaga_running_levanta_y_espera_ready(manager, state):
    state["ps"] = {"mp-mock": "running", "mp-gdino-tiny": "exited"}
    await manager.bootstrap()
    result = await manager.switch("mp-gdino-tiny")
    assert result == {"target": "mp-gdino-tiny", "model_ref": "grounding-dino/gdino-tiny"}
    assert state["ps"]["mp-mock"] == "exited"
    assert state["ps"]["mp-gdino-tiny"] == "running"
    assert manager.active == "mp-gdino-tiny"


async def test_switch_con_run_activo_es_platform_busy(manager, state, fake_state):
    state["ps"] = {"mp-mock": "running"}
    fake_state.active_run_id = "run_x"
    await manager.bootstrap()
    with pytest.raises(PlatformBusy) as exc:
        await manager.switch("mp-gdino-tiny")
    assert exc.value.run_id == "run_x"


async def test_switch_readyz_timeout_es_switch_failed_sin_target(manager, state, fake_state):
    fake_state.ready = False  # /readyz responde 503 → nunca ready
    await manager.bootstrap()
    with pytest.raises(SwitchFailed) as exc:
        await manager.switch("mp-mock")
    assert exc.value.step == "readyz"
    assert manager.active is None  # sin rollback: estado honesto


async def test_switch_a_target_actual_ready_es_noop(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    calls_before = len(state.get("calls", []))
    await manager.switch("mp-mock")
    verbs = [c[4] for c in state["calls"][calls_before:]]
    assert "up" not in verbs and "stop" not in verbs


async def test_stop_active_apaga_y_deja_none(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    await manager.stop_active()
    assert manager.active is None
    assert state["ps"]["mp-mock"] == "exited"


async def test_instances_shape(manager, state):
    state["ps"] = {"mp-mock": "running"}
    await manager.bootstrap()
    rows = {r["name"]: r for r in await manager.instances()}
    assert rows["mp-mock"] == {"name": "mp-mock", "model_ref": "mock",
                               "state": "running", "ready": True, "is_target": True}
    assert rows["mp-gdino-tiny"]["state"] == "absent"
    assert rows["mp-gdino-tiny"]["ready"] is False
```

- [x] **Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_orchestrator.py -q`
Expected: FAIL con `ImportError: TargetManager`.

- [x] **Step 3: Implementar** (agregar al final de `orchestrator.py`):

```python
import time

import httpx
from fastapi import FastAPI

from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings

NO_TARGET_URL = "http://eovrt-no-target.invalid:8080"
_SERVICE_PORT = 8080


class PlatformBusy(RuntimeError):
    """Hay un run corriendo en el target actual: no se puede switchear/apagar."""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Run activo en el target actual: {run_id}")
        self.run_id = run_id


class SwitchFailed(RuntimeError):
    """El switch falló en un paso concreto; sin rollback automático (spec §3.2)."""

    def __init__(self, step: str, detail: str) -> None:
        super().__init__(f"{step}: {detail}")
        self.step = step
        self.detail = detail


class TargetManager:
    """Target dinámico de la consola: la instancia del fleet actualmente activa.

    Es dueño del httpx.AsyncClient/RunBackend en app.state — el swap del target
    reemplaza ambos, así los routers existentes no cambian.
    """

    def __init__(
        self,
        app: FastAPI,
        orchestrator: ComposeOrchestrator,
        settings: ConsoleSettings,
        service_transport: httpx.AsyncBaseTransport | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self._app = app
        self._orch = orchestrator
        self._settings = settings
        self._transport = service_transport
        self._poll_interval = poll_interval
        self.active: str | None = None

    @staticmethod
    def _url(name: str) -> str:
        return f"http://{name}:{_SERVICE_PORT}"

    async def bootstrap(self) -> None:
        """Adopta el estado real al arrancar: 1 running = target; 0 o N = sin target."""
        ps = await self._orch.ps()
        running = [name for name, state in ps.items() if state == "running"]
        if len(running) > 1:
            logger.warning(
                "Varias instancias running (%s): target indefinido; el próximo activate normaliza",
                running,
            )
        await self._set_target(running[0] if len(running) == 1 else None)

    async def _set_target(self, name: str | None) -> None:
        old = getattr(self._app.state, "http", None)
        client = httpx.AsyncClient(
            base_url=self._url(name) if name else NO_TARGET_URL,
            transport=self._transport,
            timeout=30.0,
        )
        self._app.state.http = client
        self._app.state.backend = RunBackend(client)
        self.active = name
        if old is not None:
            await old.aclose()

    async def _active_run_id(self) -> str | None:
        if self.active is None:
            return None
        try:
            runs = await self._app.state.backend.list_runs()
        except Exception:  # noqa: BLE001 — target caído/no listo: nada que proteger
            return None
        for row in runs:
            if row.get("status") == "running":
                return row.get("run_id")
        return None

    async def _is_ready(self, name: str) -> bool:
        try:
            async with httpx.AsyncClient(
                base_url=self._url(name), transport=self._transport, timeout=5.0
            ) as client:
                return (await client.get("/readyz")).status_code == 200
        except httpx.HTTPError:
            return False

    async def switch(self, name: str) -> dict:
        await self._orch.require(name)
        run_id = await self._active_run_id()
        if run_id:
            raise PlatformBusy(run_id)
        fleet = await self._orch.fleet()
        ps = await self._orch.ps()
        if name == self.active and ps.get(name) == "running" and await self._is_ready(name):
            return {"target": name, "model_ref": fleet[name]}  # no-op
        for other, state in ps.items():
            if state == "running":
                try:
                    await self._orch.stop(other)
                except ComposeError as exc:
                    raise SwitchFailed("stop", str(exc)) from exc
        await self._set_target(None)
        try:
            await self._orch.up(name)
        except ComposeError as exc:
            raise SwitchFailed("up", str(exc)) from exc
        deadline = time.monotonic() + self._settings.switch_timeout_seconds
        while time.monotonic() < deadline:
            if await self._is_ready(name):
                await self._set_target(name)
                return {"target": name, "model_ref": fleet[name]}
            await asyncio.sleep(self._poll_interval)
        raise SwitchFailed(
            "readyz",
            f"{name} no llegó a ready en {self._settings.switch_timeout_seconds:.0f}s "
            "(¿pesos presentes? ver logs del contenedor)",
        )

    async def stop_active(self) -> None:
        if self.active is None:
            return
        run_id = await self._active_run_id()
        if run_id:
            raise PlatformBusy(run_id)
        name = self.active
        await self._set_target(None)
        try:
            await self._orch.stop(name)
        except ComposeError as exc:
            raise SwitchFailed("stop", str(exc)) from exc

    async def instances(self) -> list[dict]:
        fleet = await self._orch.fleet()
        ps = await self._orch.ps()
        rows: list[dict] = []
        for name, model_ref in sorted(fleet.items()):
            state = ps.get(name, "absent")
            ready = state == "running" and await self._is_ready(name)
            rows.append(
                {
                    "name": name,
                    "model_ref": model_ref,
                    "state": state,
                    "ready": ready,
                    "is_target": name == self.active,
                }
            )
        return rows
```

- [x] **Step 4: GREEN + regresión del archivo**

Run: `.venv/bin/python -m pytest tests/test_orchestrator.py -q`
Expected: PASS (14 tests).

---

### Task 5: Router `/api/platform` + wiring del lifespan (modo static vs orquestado)

**Files:**
- Create: `webconsole/backend/src/eovrt_webconsole/routers/platform.py`
- Modify: `webconsole/backend/src/eovrt_webconsole/app.py` (lifespan + registro + firma de `create_app`)
- Create: `webconsole/backend/tests/test_platform_api.py`

**Interfaces:**
- Consumes: `TargetManager`/`ComposeOrchestrator`/excepciones (Tasks 3–4), `settings.compose_dir` (Task 2).
- Produces: `create_app(settings=None, service_transport=None, compose_runner: RunCmd | None = None)` — `compose_runner` solo para tests. `app.state.target_manager: TargetManager | None` (None = static). Endpoints: `GET /api/platform/instances` (200 lista / 501 static / 502 compose), `POST /api/platform/instances/{name}/activate` (200 `{"target","model_ref"}` / 404 / 409 `{"detail","run_id"}` / 502 `{"detail","step"}` / 504 readyz / 501), `POST /api/platform/stop` (200 `{"target": null}` / 409 / 501). El frontend (Tasks 6–7) consume estos shapes.

- [x] **Step 1: Tests que fallan** — crear `tests/test_platform_api.py`:

```python
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from eovrt_webconsole.app import create_app
from eovrt_webconsole.settings import ConsoleSettings
from tests.fake_service import FakeState, make_fake_service
from tests.test_orchestrator import CONFIG_JSON, make_fake_compose


@pytest.fixture
def state():
    return {"ps": {"mp-mock": "exited"}}


@pytest.fixture
def platform_client(state, fake_state, repo, tmp_path):
    settings = ConsoleSettings(
        service_url="http://ignored", repo_root=repo, frozen_set_ids=frozenset({"frozen_set"}),
        compose_dir=tmp_path, switch_timeout_seconds=1.0,
    )
    transport = httpx.ASGITransport(app=make_fake_service(fake_state))
    app = create_app(settings, service_transport=transport, compose_runner=make_fake_compose(state))
    with TestClient(app) as client:
        yield client


def test_static_mode_501(client):
    # `client` es el fixture existente de conftest (sin compose_dir)
    assert client.get("/api/platform/instances").status_code == 501
    assert client.post("/api/platform/instances/mp-mock/activate").status_code == 501
    assert client.post("/api/platform/stop").status_code == 501


def test_instances_lista_fleet(platform_client):
    rows = {r["name"]: r for r in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["state"] == "exited"
    assert rows["mp-gdino-tiny"]["state"] == "absent"
    assert all(r["is_target"] is False for r in rows.values())


def test_activate_ok_y_target_operativo(platform_client, fake_state):
    r = platform_client.post("/api/platform/instances/mp-mock/activate")
    assert r.status_code == 200
    assert r.json() == {"target": "mp-mock", "model_ref": "mock"}
    rows = {x["name"]: x for x in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["is_target"] is True and rows["mp-mock"]["ready"] is True
    # el target dinámico responde por los endpoints existentes:
    assert platform_client.get("/api/target").json()["ready"] is True


def test_activate_desconocida_404(platform_client):
    assert platform_client.post("/api/platform/instances/nope/activate").status_code == 404


def test_activate_con_run_activo_409(platform_client, fake_state):
    platform_client.post("/api/platform/instances/mp-mock/activate")
    fake_state.active_run_id = "run_x"
    r = platform_client.post("/api/platform/instances/mp-gdino-tiny/activate")
    assert r.status_code == 409
    assert r.json()["run_id"] == "run_x"


def test_activate_readyz_timeout_504(platform_client, fake_state):
    fake_state.ready = False
    r = platform_client.post("/api/platform/instances/mp-mock/activate")
    assert r.status_code == 504
    assert r.json()["step"] == "readyz"


def test_stop_apaga_el_target(platform_client):
    platform_client.post("/api/platform/instances/mp-mock/activate")
    r = platform_client.post("/api/platform/stop")
    assert r.status_code == 200 and r.json() == {"target": None}
    rows = {x["name"]: x for x in platform_client.get("/api/platform/instances").json()}
    assert rows["mp-mock"]["state"] == "exited"
```

(`fake_state` y `repo` ya existen en `tests/conftest.py`; `client` es el fixture static existente.)

- [x] **Step 2: RED**

Run: `.venv/bin/python -m pytest tests/test_platform_api.py -q`
Expected: FAIL — 404 en `/api/platform/*` (router inexistente) y `TypeError` por `compose_runner`.

- [x] **Step 3: Implementar `routers/platform.py`**:

```python
"""Plataforma: ciclo de vida del fleet de instancias media-plane (spec §4)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from eovrt_webconsole.orchestrator import (
    ComposeError,
    PlatformBusy,
    SwitchFailed,
    TargetManager,
    UnknownInstance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platform")


def _manager(request: Request) -> TargetManager:
    manager = getattr(request.app.state, "target_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=501,
            detail="Orquestación no habilitada (definí EOVRT_CONSOLE_COMPOSE_DIR)",
        )
    return manager


@router.get("/instances")
async def instances(request: Request) -> list[dict]:
    try:
        return await _manager(request).instances()
    except ComposeError as exc:
        logger.warning("instances: docker compose falló: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/instances/{name}/activate")
async def activate(name: str, request: Request):
    manager = _manager(request)
    try:
        return await manager.switch(name)
    except UnknownInstance as exc:
        raise HTTPException(status_code=404, detail=f"Instancia fuera del fleet: {name}") from exc
    except PlatformBusy as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": "Hay un run activo en el target actual", "run_id": exc.run_id},
        )
    except SwitchFailed as exc:
        status = 504 if exc.step == "readyz" else 502
        logger.warning("activate(%s) falló en %s: %s", name, exc.step, exc.detail)
        return JSONResponse(status_code=status, content={"detail": exc.detail, "step": exc.step})
    except ComposeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stop")
async def stop(request: Request):
    manager = _manager(request)
    try:
        await manager.stop_active()
    except PlatformBusy as exc:
        return JSONResponse(
            status_code=409,
            content={"detail": "Hay un run activo en el target actual", "run_id": exc.run_id},
        )
    except SwitchFailed as exc:
        return JSONResponse(status_code=502, content={"detail": exc.detail, "step": exc.step})
    return {"target": None}
```

- [x] **Step 4: Wiring en `app.py`** — reemplazar el archivo completo por:

```python
"""Factory de la app FastAPI del BFF de la consola."""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from eovrt_webconsole.orchestrator import ComposeOrchestrator, RunCmd, TargetManager
from eovrt_webconsole.routers import catalog, compose, manifests, meta, platform, runs, stream
from eovrt_webconsole.run_backend import RunBackend
from eovrt_webconsole.settings import ConsoleSettings


def create_app(
    settings: ConsoleSettings | None = None,
    service_transport: httpx.AsyncBaseTransport | None = None,
    compose_runner: RunCmd | None = None,
) -> FastAPI:
    settings = settings or ConsoleSettings.from_env()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        if settings.compose_dir is not None:
            # Modo orquestado: el target es dinámico (la instancia activa del fleet);
            # TargetManager es dueño de app.state.http/backend y los swapea al switchear.
            orchestrator = ComposeOrchestrator(settings.compose_dir, run_cmd=compose_runner)
            manager = TargetManager(
                app, orchestrator, settings, service_transport=service_transport
            )
            app.state.target_manager = manager
            await manager.bootstrap()
        else:
            # Modo static: target fijo, comportamiento histórico intacto.
            app.state.target_manager = None
            app.state.http = httpx.AsyncClient(
                base_url=settings.service_url, transport=service_transport, timeout=30.0
            )
            app.state.backend = RunBackend(app.state.http)
        yield
        await app.state.http.aclose()

    app = FastAPI(title="eovrt-webconsole", lifespan=_lifespan)
    app.state.settings = settings
    app.include_router(meta.router)
    app.include_router(catalog.router)
    app.include_router(compose.router)
    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(manifests.router)
    app.include_router(platform.router)

    frontend_dist = settings.spa_dist or (settings.repo_root / "webconsole" / "frontend" / "dist")
    if frontend_dist.is_dir():
        # Mount al final: los routers /api/* y el WS ya registrados tienen precedencia.
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")
    return app
```

(Nota: en modo orquestado `bootstrap()` siempre crea `app.state.http` — apuntando a `NO_TARGET_URL` si no hay instancia running — así el `aclose()` final y los routers existentes nunca encuentran el estado ausente.)

- [x] **Step 5: GREEN + suite BFF completa**

Run: `.venv/bin/python -m pytest tests/test_platform_api.py -q && .venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: nuevos PASS y **suite completa PASS** (los 116 existentes + nuevos; el modo static por default garantiza cero regresión). `ruff check src tests` limpio.

---

### Task 6: Frontend — tipos y cliente API de plataforma

**Files:**
- Modify: `webconsole/frontend/src/types.ts`
- Modify: `webconsole/frontend/src/api.ts`
- Test: `webconsole/frontend/src/__tests__/api.test.ts` (extender)

**Interfaces:**
- Produces (Task 7 consume por estos nombres exactos): tipo `PlatformInstance`; funciones `getInstances(): Promise<PlatformInstance[]>`, `activateInstance(name: string): Promise<{ target: string; model_ref: string }>`, `stopPlatform(): Promise<{ target: null }>`.

- [x] **Step 1: Tests que fallan** (agregar a `__tests__/api.test.ts`; sumar `activateInstance, getInstances` al import de `'../api'`):

```ts
  it('getInstances parsea la lista', async () => {
    stubFetch(200, [{ name: 'mp-mock', model_ref: 'mock', state: 'exited', ready: false, is_target: false }])
    expect(await getInstances()).toHaveLength(1)
  })

  it('activateInstance postea al endpoint con el nombre encodeado', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ target: 'mp-mock', model_ref: 'mock' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await activateInstance('mp-mock')
    const calls = fetchMock.mock.calls as Array<unknown[]>
    expect(calls?.[0]?.[0]).toBe('/api/platform/instances/mp-mock/activate')
    expect((calls?.[0]?.[1] as RequestInit)?.method).toBe('POST')
  })

  it('activateInstance lanza ApiError con payload en 409', async () => {
    stubFetch(409, { detail: 'Hay un run activo en el target actual', run_id: 'run_x' })
    const error = await activateInstance('mp-mock').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
  })
```

- [x] **Step 2: RED**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npm test`
Expected: FAIL (imports inexistentes).

- [x] **Step 3: Implementar** — en `types.ts` (al final):

```ts
export interface PlatformInstance {
  name: string
  model_ref: string
  state: string // running | exited | created | absent
  ready: boolean
  is_target: boolean
}
```

En `api.ts` (sumar `PlatformInstance` al import de tipos; agregar después de `getCompare`):

```ts
export const getInstances = () => request<PlatformInstance[]>('/api/platform/instances')
export const activateInstance = (name: string) =>
  request<{ target: string; model_ref: string }>(
    `/api/platform/instances/${encodeURIComponent(name)}/activate`,
    { method: 'POST' },
  )
export const stopPlatform = () =>
  request<{ target: null }>('/api/platform/stop', { method: 'POST' })
```

- [x] **Step 4: GREEN + build**

Run: `npm test && npm run build`
Expected: PASS / build limpio.

---

### Task 7: Frontend — página Plataforma + nav

**Files:**
- Create: `webconsole/frontend/src/pages/PlatformPage.tsx`
- Modify: `webconsole/frontend/src/App.tsx` (import + link "Plataforma" + ruta `/platform`)
- Create: `webconsole/frontend/src/__tests__/PlatformPage.test.tsx`

**Interfaces:**
- Consumes: `getInstances`/`activateInstance`/`stopPlatform`/`PlatformInstance` (Task 6), `ApiError` (existente).

- [x] **Step 1: Tests que fallan** — crear `__tests__/PlatformPage.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PlatformPage from '../pages/PlatformPage'
import { activateInstance, getInstances } from '../api'
import type { PlatformInstance } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getInstances: vi.fn(),
  activateInstance: vi.fn(),
  stopPlatform: vi.fn(),
}))

const FLEET: PlatformInstance[] = [
  { name: 'mp-mock', model_ref: 'mock', state: 'exited', ready: false, is_target: false },
  { name: 'mp-gdino-tiny', model_ref: 'grounding-dino/gdino-tiny', state: 'absent', ready: false, is_target: false },
]

const FLEET_ACTIVE: PlatformInstance[] = [
  { ...FLEET[0], state: 'running', ready: true, is_target: true },
  FLEET[1],
]

beforeEach(() => vi.clearAllMocks())

describe('PlatformPage', () => {
  it('lista el fleet y activa una instancia', async () => {
    vi.mocked(getInstances)
      .mockResolvedValueOnce(FLEET)         // carga inicial
      .mockResolvedValue(FLEET_ACTIVE)      // refresh post-activate
    vi.mocked(activateInstance).mockResolvedValue({ target: 'mp-mock', model_ref: 'mock' })

    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText('mp-mock')).toBeTruthy())

    fireEvent.click(screen.getAllByText('Activar')[0])

    await waitFor(() => expect(activateInstance).toHaveBeenCalledWith('mp-mock'))
    await waitFor(() => expect(screen.getByText('TARGET')).toBeTruthy())
  })

  it('409 muestra el mensaje de run activo', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET)
    const { ApiError } = await import('../api')
    vi.mocked(activateInstance).mockRejectedValue(
      new ApiError(409, { detail: 'Hay un run activo en el target actual', run_id: 'run_x' }),
    )
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText('mp-mock')).toBeTruthy())
    fireEvent.click(screen.getAllByText('Activar')[0])
    await waitFor(() => expect(screen.getByText(/run activo/i)).toBeTruthy())
  })

  it('501 muestra el hint de orquestación no habilitada', async () => {
    const { ApiError } = await import('../api')
    vi.mocked(getInstances).mockRejectedValue(new ApiError(501, { detail: 'x' }))
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText(/no habilitada/i)).toBeTruthy())
  })
})
```

- [x] **Step 2: RED**

Run: `npm test`
Expected: FAIL (página inexistente).

- [x] **Step 3: Implementar `pages/PlatformPage.tsx`**:

```tsx
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { ApiError, activateInstance, getInstances, stopPlatform } from '../api'
import type { PlatformInstance } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: string; step?: string; run_id?: string }
    if (e.status === 409) return `Hay un run activo (${payload.run_id ?? '?'}): esperá a que termine o detenelo.`
    if (e.status === 504) return `La instancia no llegó a ready: ${payload.detail ?? 'timeout'}`
    if (e.status === 502) return `Docker falló${payload.step ? ` (${payload.step})` : ''}: ${payload.detail ?? ''}`
  }
  return String(e)
}

export default function PlatformPage() {
  const [rows, setRows] = useState<PlatformInstance[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null) // instancia activándose/deteniéndose
  const [notEnabled, setNotEnabled] = useState(false)

  const refresh = () =>
    getInstances()
      .then((r) => {
        setRows(r)
        setNotEnabled(false)
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 501) setNotEnabled(true)
        else setError(errorMessage(e))
      })

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [])

  const activate = async (name: string) => {
    setBusy(name)
    setError(null)
    try {
      await activateInstance(name)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
      refresh()
    }
  }

  const stop = async () => {
    setBusy('__stop__')
    setError(null)
    try {
      await stopPlatform()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
      refresh()
    }
  }

  if (notEnabled)
    return (
      <p>
        Orquestación no habilitada: la consola corre en modo target fijo. Desplegá la
        plataforma con <code>infra/platform/</code> (define <code>EOVRT_CONSOLE_COMPOSE_DIR</code>).
      </p>
    )
  if (error && !rows) return <p style={{ color: '#b00' }}>Error: {error}</p>
  if (!rows) return <p>Cargando…</p>
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h2>Plataforma — instancias del servicio</h2>
      <p>
        <small>
          Una instancia activa a la vez: activar otra apaga la actual y espera a que el
          modelo cargue (puede tardar minutos).
        </small>
      </p>
      {error && <p style={{ color: '#b00' }}>{error}</p>}
      <table style={{ borderCollapse: 'collapse', maxWidth: 760 }}>
        <thead>
          <tr>
            {['instancia', 'modelo', 'estado', 'ready', '', ''].map((h, i) => (
              <th key={i} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td style={CELL}>{r.name}</td>
              <td style={CELL}>{r.model_ref}</td>
              <td style={CELL}>
                {busy === r.name ? 'activando…' : r.state}
                {r.is_target && (
                  <b style={{ marginLeft: 8, color: '#080' }}>TARGET</b>
                )}
              </td>
              <td style={CELL}>{r.ready ? '✓' : '—'}</td>
              <td style={CELL}>
                {!r.is_target && (
                  <button onClick={() => activate(r.name)} disabled={busy !== null}>
                    {busy === r.name ? 'Activando…' : 'Activar'}
                  </button>
                )}
              </td>
              <td style={CELL}>
                {r.is_target && (
                  <button onClick={stop} disabled={busy !== null}>Apagar</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [x] **Step 4: Nav y ruta en `App.tsx`** — sumar import `import PlatformPage from './pages/PlatformPage'`; en el nav, después de "Comparar": `<Link to="/platform">Plataforma</Link>`; en Routes: `<Route path="/platform" element={<PlatformPage />} />`.

- [x] **Step 5: GREEN + suite frontend + build**

Run: `npm test && npm run build`
Expected: PASS (todas, 26 previas + nuevas) / build limpio.

---

### Task 8: `/infra/console` (imagen de la consola + compose standalone)

**Files:**
- Create: `e-ovrt_experimental-setup/infra/console/Dockerfile`
- Create: `e-ovrt_experimental-setup/infra/console/docker-compose.yml`

**Interfaces:**
- Consumes: `create_app` como factory (`python -m uvicorn --factory`), `EOVRT_CONSOLE_SPA_DIST` (Task 2), `/api/health` (existente, para healthcheck).
- Produces: imagen `eovrt/console:latest` (Task 9 la referencia desde el compose de plataforma).

- [x] **Step 1: Crear `infra/console/Dockerfile`** (build context = raíz del repo experimental-setup):

```dockerfile
# Imagen de la webconsole (BFF FastAPI + SPA embebida + docker CLI para orquestar).
# Build context: raíz del repo e-ovrt_experimental-setup.
FROM node:20-slim AS spa
WORKDIR /build
COPY webconsole/frontend/package.json webconsole/frontend/package-lock.json ./
RUN npm ci
COPY webconsole/frontend ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
# docker CLI + compose plugin (solo cliente; opera contra el socket montado)
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY webconsole/backend/pyproject.toml ./backend/pyproject.toml
COPY webconsole/backend/src ./backend/src
RUN pip install --no-cache-dir ./backend
COPY --from=spa /build/dist /app/spa-dist

ENV EOVRT_CONSOLE_SPA_DIST=/app/spa-dist
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -sf http://localhost:8090/api/health || exit 1
CMD ["python", "-m", "uvicorn", "--factory", "eovrt_webconsole.app:create_app", \
     "--host", "0.0.0.0", "--port", "8090"]
```

- [x] **Step 2: Crear `infra/console/docker-compose.yml`** (standalone: modo static, SIN socket):

```yaml
# Consola standalone (modo static): cliente de UN servicio media-plane externo.
# Sin socket de Docker: acá no hay orquestación. La plataforma completa vive en ../platform.
name: eovrt-console
services:
  console:
    build:
      context: ../..
      dockerfile: infra/console/Dockerfile
    image: eovrt/console:latest
    ports: ["8090:8090"]
    environment:
      EOVRT_CONSOLE_SERVICE_URL: ${EOVRT_CONSOLE_SERVICE_URL:-http://host.docker.internal:8080}
      EOVRT_CONSOLE_REPO_ROOT: /repo
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - ../..:/repo:ro
      - ../../experiments:/repo/experiments:rw
```

- [x] **Step 3: Verificar config + build**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/infra/console && docker compose config -q && echo CONFIG-OK && docker compose build 2>&1 | tail -3`
Expected: `CONFIG-OK` y build exitoso de `eovrt/console:latest` (npm ci + pip; algunos minutos la primera vez).

- [x] **Step 4: Smoke standalone rápido** (contra un servicio del host o sin servicio — alcanza ver la SPA y el 501):

```bash
docker compose up -d
sleep 3
python3 - <<'EOF'
import urllib.request
print(urllib.request.urlopen("http://localhost:8090/api/health", timeout=5).status)      # 200
print(urllib.request.urlopen("http://localhost:8090/", timeout=5).status)               # 200 (SPA embebida)
import urllib.error
try:
    urllib.request.urlopen("http://localhost:8090/api/platform/instances", timeout=5)
except urllib.error.HTTPError as e:
    print(e.code)                                                                        # 501 (modo static)
EOF
docker compose down
```
Expected: `200`, `200`, `501`.

---

### Task 9: `/infra/platform` (compose de la plataforma + .env + README)

**Files:**
- Create: `e-ovrt_experimental-setup/infra/platform/docker-compose.yml`
- Create: `e-ovrt_experimental-setup/infra/platform/.env.example`
- Create: `e-ovrt_experimental-setup/infra/platform/README.md`

**Interfaces:**
- Consumes: imagen `eovrt/media-plane:latest` (Task 1) + `eovrt/console:latest` (Task 8) — el compose referencia sus Dockerfiles para poder `build` desde el host, pero el BFF solo hace `up --no-build`.
- Produces: el fleet con los labels EXACTOS que `ComposeOrchestrator.fleet()` filtra (`eovrt.instance: "true"`, `eovrt.model_ref`); paths de host absolutos vía `${EOVRT_WORKSPACE}`.

- [x] **Step 1: Crear `.env.example`**

```bash
# Copiar a .env y ajustar. Raíz ABSOLUTA del workspace en el host (contiene
# e-ovrt_media-plane, e-ovrt_experimental-setup y e-ovrt_datasets como hermanos).
# El compose usa paths absolutos de host porque la consola re-ejecuta compose
# DESDE DENTRO de su contenedor: binds relativos resolverían contra el filesystem
# equivocado.
EOVRT_WORKSPACE=/home/simonll4/projects
```

- [x] **Step 2: Crear `docker-compose.yml`**

```yaml
# Plataforma E-OVRT (DBE single-host): consola + fleet de instancias del servicio
# media-plane (una por modelo, apagadas; la consola las orquesta vía este mismo
# compose). Bootstrap: ver README.md.
name: eovrt

x-mp-common: &mp-common
  image: eovrt/media-plane:latest
  build:
    context: ${EOVRT_WORKSPACE:?definí EOVRT_WORKSPACE en infra/platform/.env}/e-ovrt_media-plane
    dockerfile: infra/docker/Dockerfile
  networks: [eovrt]
  profiles: [models]
  volumes:
    - ${EOVRT_WORKSPACE}/e-ovrt_media-plane/models:/app/models:ro
    - ${EOVRT_WORKSPACE}/e-ovrt_media-plane/mobileclip2_b.ts:/app/mobileclip2_b.ts:ro
    - ${EOVRT_WORKSPACE}/e-ovrt_media-plane/runs:/data/runs
    - ${EOVRT_WORKSPACE}/e-ovrt_datasets:/e-ovrt_datasets:ro
    - weights-cache:/data/weights

x-gpu: &gpu
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

services:
  console:
    image: eovrt/console:latest
    build:
      context: ${EOVRT_WORKSPACE}/e-ovrt_experimental-setup
      dockerfile: infra/console/Dockerfile
    ports: ["8090:8090"]
    networks: [eovrt]
    environment:
      EOVRT_CONSOLE_COMPOSE_DIR: /repo/infra/platform
      EOVRT_CONSOLE_REPO_ROOT: /repo
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ${EOVRT_WORKSPACE}/e-ovrt_experimental-setup:/repo:ro
      - ${EOVRT_WORKSPACE}/e-ovrt_experimental-setup/experiments:/repo/experiments:rw

  mp-mock:
    <<: *mp-common
    environment: { EOVRT_MODEL_REF: mock }
    labels: { eovrt.instance: "true", eovrt.model_ref: mock }

  mp-gdino-tiny:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: grounding-dino/gdino-tiny }
    labels: { eovrt.instance: "true", eovrt.model_ref: grounding-dino/gdino-tiny }

  mp-gdino-base:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: grounding-dino/gdino-base }
    labels: { eovrt.instance: "true", eovrt.model_ref: grounding-dino/gdino-base }

  mp-yoloe-26s:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: yoloe/yoloe-26s }
    labels: { eovrt.instance: "true", eovrt.model_ref: yoloe/yoloe-26s }

  mp-yoloe-26m:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: yoloe/yoloe-26m }
    labels: { eovrt.instance: "true", eovrt.model_ref: yoloe/yoloe-26m }

  mp-yoloe-26l:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: yoloe/yoloe-26l }
    labels: { eovrt.instance: "true", eovrt.model_ref: yoloe/yoloe-26l }

  mp-yoloe-26x:
    <<: [*gpu, *mp-common]
    environment: { EOVRT_MODEL_REF: yoloe/yoloe-26x }
    labels: { eovrt.instance: "true", eovrt.model_ref: yoloe/yoloe-26x }

networks:
  eovrt:
    driver: bridge

volumes:
  weights-cache: {}
```

- [x] **Step 3: Crear `README.md`**

```markdown
# Plataforma E-OVRT — deploy integral (DBE single-host)

Consola web + fleet de instancias del servicio media-plane (una por modelo, mismo
image, distinto `EOVRT_MODEL_REF`). Las instancias arrancan **apagadas** (profile
`models`); se encienden/apagan desde la página **Plataforma** de la consola, con la
política *una activa a la vez* (switch atómico).

## Bootstrap (una vez)

```bash
cp .env.example .env                # ajustar EOVRT_WORKSPACE (raíz absoluta del workspace)
docker compose build                # imágenes eovrt/media-plane + eovrt/console (lento la 1ª vez)
docker compose up -d console        # solo la consola; el fleet lo maneja ella
```

Abrir http://localhost:8090 → página **Plataforma** → Activar `mp-mock` (o un modelo).
Requisitos en el host: pesos en `e-ovrt_media-plane/models/` (`make download-models`),
`nvidia-container-toolkit` para instancias GPU.

## Smoke de aceptación

1. `docker compose up -d console` → http://localhost:8090 responde y `/platform` lista el fleet.
2. Activar `mp-mock` → pasa a TARGET ready; lanzar una corrida `demo_v2` corta → succeeded.
3. Activar `mp-gdino-tiny` (apaga mock solo) → correr BENCH corto (`bench_v2_test`,
   `max_units` 10) → Evaluar → métricas visibles.
4. `docker compose stop` para bajar todo.

## Operación

- La consola ejecuta `docker compose --project-name eovrt up -d --no-build <instancia>` /
  `stop` contra este directorio (montado en `/repo/infra/platform`). El `.env` con
  `EOVRT_WORKSPACE` viaja con el directorio: **paths absolutos de host**, necesarios
  porque compose corre dentro del contenedor de la consola pero los binds los resuelve
  el daemon en el host.
- `runs/` es compartido entre TODAS las instancias: historial y compare cross-model
  completos desde cualquier target.
- Cambiar de modelo NO recarga in-process (Spec A): siempre es stop + up + carga.

## Seguridad

El socket de Docker montado en la consola es **root-equivalente en el host**. Aceptado
para este despliegue de laboratorio (single-user, sin exposición externa). Mitigación:
el BFF solo ejecuta 3 verbos compose con nombres validados contra el fleet declarado.
No exponer el puerto 8090 fuera del host sin revisar esto.
```

- [x] **Step 4: Verificar resolución del compose**

Run: `cd /home/simonll4/projects/e-ovrt_experimental-setup/infra/platform && cp .env.example .env && docker compose config --format json | python3 -c "import json,sys; d=json.load(sys.stdin); svcs=d['services']; fleet=[n for n,s in svcs.items() if (s.get('labels') or {}).get('eovrt.instance')=='true' or 'eovrt.instance=true' in (s.get('labels') or [])]; print(sorted(fleet))"`
Expected: las 7 instancias `mp-*` listadas; sin errores de interpolación (`.env` presente).

---

### Task 10: Smoke integral de la plataforma (criterio de aceptación, spec §9)

**Files:** ninguno (verificación operativa; requiere Tasks 1–9 completos y las imágenes construidas).

- [x] **Step 1: Suites completas previas**

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && .venv/bin/python -m pytest -q | tail -1 && .venv/bin/python -m ruff check src tests | tail -1
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && .venv/bin/python -m pytest -q | tail -1 && .venv/bin/python -m ruff check src tests | tail -1
cd ../frontend && npm test 2>&1 | tail -2 && npm run build 2>&1 | tail -1
```
Expected: todo PASS/limpio.

- [x] **Step 2: Levantar la plataforma**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/infra/platform
docker compose up -d console
sleep 5
python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8090/api/platform/instances', timeout=10).read().decode())"
```
Expected: JSON con las 7 instancias, todas `state: absent|exited`, ninguna `is_target`.

- [x] **Step 3: Activar mock desde la API de la plataforma y correr un run e2e**

```bash
python3 -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8090/api/platform/instances/mp-mock/activate', method='POST')
print(json.loads(urllib.request.urlopen(req, timeout=360).read()))   # {'target': 'mp-mock', 'model_ref': 'mock'}
"
# run corto por la consola (demo_v2) y esperar succeeded — mismo flujo del smoke previo del MVP
```
Expected: activate 200; `/api/target` ready; run mock `succeeded`; el run aparece en el listado.

- [x] **Step 4: Switch a GDINO-tiny + BENCH corto + evaluar**

```bash
python3 -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8090/api/platform/instances/mp-gdino-tiny/activate', method='POST')
print(json.loads(urllib.request.urlopen(req, timeout=360).read()))
"
# correr bench_v2_test con max_units 10 vía la consola, evaluar (POST /api/runs/<id>/evaluate),
# verificar mAP50 presente y n_gt restringido (~decenas, no 196 imgs).
```
Expected: el switch apaga mock y deja gdino-tiny TARGET ready (device cuda); run BENCH + eval OK. Verificar también en el browser: http://localhost:8090/platform muestra el estado real.

- [x] **Step 5: Bajar todo y verificar estado limpio**

```bash
docker compose stop && docker compose ps -a --format json | head -3
ss -ltnp | grep -E ':(8080|8090)' || echo "puertos libres"
```
Expected: contenedores stopped, puertos libres. **Este smoke completo es el criterio de aceptación de la fase.**

**Resultado (2026-07-05):** ejecutado end-to-end. Imágenes `eovrt/media-plane:latest` (13.2GB) y `eovrt/console:latest` (399MB) construidas; consola healthy con las 7 instancias listadas; mock activado → run demo_v2 (5 imgs) succeeded; switch a mp-gdino-tiny (apagó mock automático) → BENCH `bench_v2_test` (10 imgs, cuda) succeeded → evaluate → mAP50=0.6762 (person 0.82, helmet 0.82, vest 0.52, bare_head 0.55; n_gt en decenas, no las 196 imgs completas del split); `docker compose stop` dejó todo Exited y los puertos 8080/8090 libres. Detalle completo en `.superpowers/sdd/progress-plataforma-docker.md` (Task 10) y en los artefactos `e-ovrt_media-plane/runs/run_20260705_093716_dbe_mock_c362d5/` y `run_20260705_093926_dbe_grounding_dino_7eb789/`.

---

## Self-review (hecho al escribir el plan)

- **Cobertura del spec**: §0→Global Constraints; §1 convención /infra→T1/T8/T9; §2 imagen+volúmenes→T1+T9; §3.1 orchestrator→T3; §3.2 TargetManager→T4; §3.3 modo static→T2/T5 (test 501 + suite completa); §4 API→T5; §5 UI→T6/T7; §6 imagen consola→T8; §7 errores→T4/T5/T7 (tests 409/404/502/504/501); §8 seguridad→README T9 + allowlist T3; §9 testing/smoke→tests por task + T10. Sin gaps.
- **Consistencia de tipos**: `RunCmd`/`ComposeOrchestrator`/`TargetManager` firmas idénticas entre T3/T4/T5; `create_app(settings, service_transport, compose_runner)` (T5) = como lo usan los tests de T5; labels del compose (T9) = constantes de T3; shapes de instances/activate (T4/T5) = tipos TS de T6 = asserts de T7; `EOVRT_CONSOLE_SPA_DIST` (T2) = ENV del Dockerfile (T8).
- **Placeholders**: ninguno; todo paso con código lo trae completo.
- **Nota para el ejecutor**: T1 Step 6 y T8 Step 3 (builds Docker) son lentos y requieren red — si el entorno no puede, reportar concern y dejar T10 como pendiente del usuario; el resto de los tasks no dependen de las imágenes.
