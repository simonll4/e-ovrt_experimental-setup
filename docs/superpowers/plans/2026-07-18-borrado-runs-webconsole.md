# Borrado de runs completos desde la web console — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir borrar runs terminados desde la web console — hard delete físico en ambos planos (media-plane y control-plane), orquestado por el webconsole backend, con confirmación en el frontend.

**Architecture:** El control-plane gana un `DELETE /api/runs/{id}` (mirror del que ya existe en media-plane). El webconsole backend agrega un `DELETE /api/runs/{id}` orquestador que resuelve la correlación media↔control, valida que ningún lado esté `running`, y borra en ambos. El frontend agrega un botón "Borrar" (con `window.confirm`, patrón ya usado en `PromptSetEditor.tsx`) en `RunsPage` y `RunDetailPage`, visible solo para runs no-`running`.

**Tech Stack:** Python 3.11 / FastAPI / httpx (backends), pytest, React + TypeScript (frontend), Vitest (si existe) — este repo no tiene tests de frontend automatizados actualmente (verificar en Task 6/7; si no hay suite, el paso de test se reduce a verificación manual descripta en el propio paso).

## Global Constraints

- Borrado **físico** (hard delete), no soft-delete. Ver spec §Alcance.
- Solo permitido sobre runs en estado **terminal** (no `running`). Ver spec §Alcance.
- Botón disponible en **RunsPage y RunDetailPage**, con modal/diálogo de confirmación antes de borrar.
- Fallo parcial (un plano borra, el otro falla): se reporta explícitamente, **no rollback**, el run queda visible para reintentar; el reintento es **idempotente**.
- Nunca hacer `git commit` salvo pedido explícito del usuario en ese turno (regla del workspace, `projects/CLAUDE.md`).
- Spec completo: `e-ovrt_experimental-setup/docs/superpowers/specs/2026-07-18-borrado-runs-webconsole-design.md`.

---

## Task 1: Control-plane — `DELETE /api/runs/{id}`

**Files:**
- Modify: `e-ovrt_control-plane/src/eovrt_control/service/routers/runs.py`
- Test: `e-ovrt_control-plane/tests/test_service_api.py`

**Interfaces:**
- Consumes: `RunManager.get(run_id)` (ya existe, `run_manager.py:142`) — devuelve dict con `status`; lanza `UnknownRunError` si no existe. `request.app.state.settings.runs_dir` (ya existe, `app.py:33`).
- Produces: endpoint `DELETE /api/runs/{run_id}` → 204 (borrado), 404 (desconocido), 409 (run activo). Mismo contrato que el ya existente en media-plane (`src/eovrt_media/service/routers/runs.py:66-78`).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `e-ovrt_control-plane/tests/test_service_api.py`:

```python
def test_delete_run_terminado(client, tmp_path) -> None:
    response = client.post("/api/runs", json={"mode": "replay", "config": _payload(tmp_path)})
    run_id = response.json()["control_run_id"]
    client.app.state.manager.join_active(timeout=30.0)

    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_delete_404_desconocido(client) -> None:
    assert client.delete("/api/runs/nope").status_code == 404


def test_delete_409_run_activo(client, tmp_path, bus_endpoint) -> None:
    client.post("/api/runs", json={"mode": "live", "config": _idle_live_payload(bus_endpoint)})
    try:
        assert client.delete("/api/runs/idle-run").status_code == 409
    finally:
        client.app.state.manager.shutdown()
        client.app.state.manager.join_active(timeout=15.0)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd e-ovrt_control-plane && source .venv/bin/activate && pytest tests/test_service_api.py -k delete -v`
Expected: FAIL — `405 Method Not Allowed` (no existe la ruta DELETE) en las tres.

- [ ] **Step 3: Implementar el endpoint**

En `e-ovrt_control-plane/src/eovrt_control/service/routers/runs.py`, agregar los imports necesarios y la ruta (después de `get_run`, antes de `get_run_alerts`):

```python
"""API de corridas del control-plane (spec 41 SS5)."""

from __future__ import annotations

import shutil

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response

from eovrt_control.service.run_ids import require_valid_run_id
from eovrt_control.service.run_manager import RunBusyError, RunManager, UnknownRunError
from eovrt_control.service.run_request import ControlRunRequest

router = APIRouter(prefix="/api")
```

(Solo se agregan `shutil` y `Response` a los imports existentes — el resto del archivo no cambia.)

```python
@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str, request: Request):
    require_valid_run_id(run_id)
    manager = _manager(request)
    try:
        info = manager.get(run_id)
    except UnknownRunError as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    if info["status"] == "running":
        raise HTTPException(status_code=409, detail="No se puede borrar un run activo")
    run_dir = request.app.state.settings.runs_dir / run_id
    shutil.rmtree(run_dir, ignore_errors=True)
    return Response(status_code=204)
```

Insertarlo justo debajo de `get_run` (línea 54 actual), antes de `get_run_alerts`.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd e-ovrt_control-plane && pytest tests/test_service_api.py -k delete -v`
Expected: 3 passed.

- [ ] **Step 5: Correr la suite completa y lint**

Run: `cd e-ovrt_control-plane && pytest -q && ruff check src tests`
Expected: todo verde (sin regresiones).

- [ ] **Step 6: Commit**

```bash
cd e-ovrt_control-plane
git add src/eovrt_control/service/routers/runs.py tests/test_service_api.py
git commit -m "feat: agregar DELETE /api/runs/{id} al control-plane"
```

---

## Task 2: Webconsole — fakes de test soportan DELETE

Antes de escribir los clientes (`RunBackend`, `ControlPlaneBackend`) hace falta que los dobles de test (`fake_service.py`, `fake_control_service.py`) entiendan `DELETE /api/runs/{id}`, porque los tests de las Tasks 3 y 4 corren contra ellos.

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/backend/tests/fake_service.py`
- Modify: `e-ovrt_experimental-setup/webconsole/backend/tests/fake_control_service.py`

**Interfaces:**
- Produces: `FakeState.deleted: list[str]` (media), `FakeControlState.deleted: list[str]` (control) — listas que los tests de las próximas tasks usan para verificar qué se borró.

- [ ] **Step 1: Media-plane fake — agregar `DELETE /api/runs/{run_id}`**

En `fake_service.py`, agregar a `FakeState.__init__` (después de `self.dropped: dict[str, list[dict]] = {}`):

```python
        self.deleted: list[str] = []
```

Y agregar la ruta en `make_fake_service`, justo después de `stop_run`:

```python
    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: str):
        if not state.ready:
            return JSONResponse(status_code=503, content={"detail": "Servicio no listo (modelo no cargado)"})
        if run_id == state.active_run_id:
            return JSONResponse(status_code=409, content={"detail": "No se puede borrar un run activo"})
        if run_id != "run_done_1" or run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        state.deleted.append(run_id)
        return Response(status_code=204)
```

Agregar `Response` al import existente de `fastapi.responses` (línea 11: `from fastapi.responses import JSONResponse, Response`).

- [ ] **Step 2: Control-plane fake — agregar `DELETE /api/runs/{run_id}`**

En `fake_control_service.py`, agregar a `FakeControlState.__init__` (después de `self.received_units: dict[str, list[dict]] = {}`):

```python
        self.deleted: list[str] = []
```

Agregar `Response` al import (línea 11: `from fastapi.responses import JSONResponse, Response`).

Agregar la ruta en `make_fake_control_service`, después de `get_run_alerts`:

```python
    @app.delete("/api/runs/{run_id}", status_code=204)
    def delete_run(run_id: str):
        if run_id == state.active_run_id and state.finish_status is None:
            return JSONResponse(status_code=409, content={"detail": "No se puede borrar un run activo"})
        if run_id in state.deleted:
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        if not _known_run(run_id):
            return JSONResponse(status_code=404, content={"detail": f"Run desconocido: {run_id}"})
        state.deleted.append(run_id)
        state.alerts.pop(run_id, None)
        state.runs_index = [r for r in state.runs_index if r.get("control_run_id") != run_id]
        return Response(status_code=204)
```

Esta ruta debe ir **después** de la definición de `_known_run` (línea 158 actual) para poder usarla — o mover `_known_run` más arriba, antes de todas las rutas que lo usan. Reordenar: mover la función `_known_run` (líneas 158-167 actuales) a inmediatamente después de `get_effective_config` (antes de `list_runs`), y agregar la ruta `delete_run` después de `list_runs`.

- [ ] **Step 3: Verificar que nada se rompió**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && source .venv/bin/activate && pytest -q`
Expected: misma cantidad de tests que antes, todos passed (los fakes no tienen tests propios; esto solo confirma que no rompiste la importación/arranque de la app).

- [ ] **Step 4: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/backend/tests/fake_service.py webconsole/backend/tests/fake_control_service.py
git commit -m "test: los fakes de media-plane y control-plane soportan DELETE /api/runs/{id}"
```

---

## Task 3: Webconsole backend — clientes `RunBackend.delete` y `ControlPlaneBackend.delete`

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/backend/src/eovrt_webconsole/run_backend.py`
- Modify: `e-ovrt_experimental-setup/webconsole/backend/src/eovrt_webconsole/experiment/control_backend.py`
- Test: `e-ovrt_experimental-setup/webconsole/backend/tests/test_run_backend.py`
- Test: `e-ovrt_experimental-setup/webconsole/backend/tests/test_control_backend.py`

**Interfaces:**
- Consumes: `FakeState.deleted`/`FakeControlState.deleted` (Task 2).
- Produces: `RunBackend.delete(run_id: str) -> None`, `RunBackend.RunActive` (excepción, atributo `.detail: str`). `ControlPlaneBackend.delete(control_run_id: str) -> None`, `ControlPlaneBackend.RunActive` (excepción, atributo `.detail: str`). Estas dos clases `RunActive` son independientes (mismo nombre, dos módulos distintos) — Task 4 las importa con alias.

- [ ] **Step 1: Escribir los tests que fallan (media-plane client)**

Agregar al final de `test_run_backend.py`:

```python
from eovrt_webconsole.run_backend import RunActive


async def test_delete_ok(backend, state):
    await backend.delete("run_done_1")
    assert state.deleted == ["run_done_1"]


async def test_delete_404_desconocido(backend):
    with pytest.raises(UnknownRun):
        await backend.delete("nope")


async def test_delete_409_run_activo(backend, state):
    state.active_run_id = "run_x"
    with pytest.raises(RunActive) as exc:
        await backend.delete("run_x")
    assert "activo" in exc.value.detail
```

(El `from eovrt_webconsole.run_backend import RunActive` reemplaza la línea de import existente — agregarlo al import ya existente en la cabecera del archivo, no como línea suelta.)

- [ ] **Step 2: Escribir los tests que fallan (control-plane client)**

Agregar al final de `test_control_backend.py` (agregar `RunActive` al import existente de `eovrt_webconsole.experiment.control_backend`):

```python
async def test_delete_ok(control_backend):
    backend, state = control_backend
    run_id = await backend.launch({"input": {"type": "file"}}, mode="replay", experiment_id="exp-5")
    await backend.delete(run_id)
    assert state.deleted == [run_id]


async def test_delete_404_desconocido(control_backend):
    backend, _ = control_backend
    with pytest.raises(UnknownRun):
        await backend.delete("nope")


async def test_delete_409_run_activo(control_backend):
    backend, state = control_backend
    state.active_run_id = "otro"
    with pytest.raises(RunActive):
        await backend.delete("otro")
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest tests/test_run_backend.py tests/test_control_backend.py -k delete -v`
Expected: FAIL — `ImportError: cannot import name 'RunActive'` (no existe todavía en ninguno de los dos módulos) y `AttributeError: 'RunBackend'/'ControlPlaneBackend' object has no attribute 'delete'`.

- [ ] **Step 4: Implementar `RunBackend.delete`**

En `run_backend.py`, agregar después de la clase `UnknownRun` (línea 41):

```python
class RunActive(Exception):
    """409 al borrar: el run sigue activo."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
```

Y agregar el método al final de la clase `RunBackend` (después de `open_artifact`):

```python
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
```

- [ ] **Step 5: Implementar `ControlPlaneBackend.delete`**

En `control_backend.py`, agregar después de la clase `UnknownRun` (línea 34):

```python
class RunActive(Exception):
    """409 al borrar: el run sigue activo."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
```

Y agregar el método al final de la clase `ControlPlaneBackend` (después de `received_units`):

```python
    async def delete(self, control_run_id: str) -> None:
        try:
            response = await self._http.delete(f"/api/runs/{control_run_id}")
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(str(exc)) from exc
        if response.status_code == 404:
            raise UnknownRun(control_run_id)
        if response.status_code == 409:
            raise RunActive(response.json().get("detail", "run activo"))
        if response.status_code >= 500 or response.status_code == 503:
            raise ServiceUnavailable(f"DELETE /api/runs/{control_run_id} -> {response.status_code}")
        response.raise_for_status()
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest tests/test_run_backend.py tests/test_control_backend.py -v`
Expected: todos passed (los nuevos + los preexistentes).

- [ ] **Step 7: Suite completa + lint**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest -q && ruff check src tests`
Expected: todo verde.

- [ ] **Step 8: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/backend/src/eovrt_webconsole/run_backend.py \
        webconsole/backend/src/eovrt_webconsole/experiment/control_backend.py \
        webconsole/backend/tests/test_run_backend.py \
        webconsole/backend/tests/test_control_backend.py
git commit -m "feat: RunBackend.delete y ControlPlaneBackend.delete (clientes DELETE /api/runs/{id})"
```

---

## Task 4: Webconsole backend — endpoint orquestador `DELETE /api/runs/{id}`

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/backend/src/eovrt_webconsole/routers/runs.py`
- Test: `e-ovrt_experimental-setup/webconsole/backend/tests/test_runs_router.py`

**Interfaces:**
- Consumes: `RunBackend.status`, `RunBackend.delete`, `RunBackend.RunActive` (Task 3); `ControlPlaneBackend.list_runs`, `ControlPlaneBackend.status`, `ControlPlaneBackend.delete`, `ControlPlaneBackend.RunActive` (Task 3); fixture `two_plane_client` (ya existe, `conftest.py:110-121`).
- Produces: `DELETE /api/runs/{run_id}` → 204 (borrado completo), 404 (run desconocido en ambos planos), 409 (algún lado sigue `running`), 207 (borrado parcial, body `{"detail": "borrado parcial", "errors": {"media": "...", "control": "..."}}`, al menos una clave presente).

**Nota de diseño (idempotencia):** si el media-plane ya fue borrado en un intento previo pero el control-plane falló, un reintento debe seguir intentando borrar el lado control. Por eso el chequeo inicial no aborta con 404 apenas el media-plane devuelve "desconocido" — solo lo hace si **además** no hay ningún `control_run_id` correlacionado pendiente. Ver spec §Componente 2 punto 5.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar al final de `test_runs_router.py`:

```python
def test_delete_run_ok_ambos_planos(two_plane_client, fake_state, control_state):
    control_state.runs_index = [
        {"control_run_id": "ctrl-1", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-1"] = []

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 204
    assert fake_state.deleted == ["run_done_1"]
    assert control_state.deleted == ["ctrl-1"]


def test_delete_run_sin_control_correlacionado(two_plane_client, fake_state):
    r = two_plane_client.delete("/api/runs/run_done_1")
    assert r.status_code == 204
    assert fake_state.deleted == ["run_done_1"]


def test_delete_404_desconocido_en_ambos_planos(two_plane_client):
    assert two_plane_client.delete("/api/runs/nope").status_code == 404


def test_delete_409_run_activo_en_media(two_plane_client, fake_state):
    fake_state.active_run_id = "run_active_1"
    r = two_plane_client.delete("/api/runs/run_active_1")
    assert r.status_code == 409


def test_delete_409_run_activo_en_control(two_plane_client, control_state):
    control_state.runs_index = [
        {"control_run_id": "ctrl-2", "status": "running", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.active_run_id = "ctrl-2"

    r = two_plane_client.delete("/api/runs/run_done_1")

    assert r.status_code == 409


def test_delete_reintento_idempotente_tras_fallo_parcial(two_plane_client, fake_state, control_state, monkeypatch):
    from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable

    control_state.runs_index = [
        {"control_run_id": "ctrl-3", "status": "succeeded", "started_at": "2026-07-18T00:00:00+00:00",
         "alerts_count": 0, "media_run_id": "run_done_1"},
    ]
    control_state.alerts["ctrl-3"] = []

    original_delete = two_plane_client.app.state.control_backend.delete
    call_count = {"n": 0}

    async def flaky_delete(control_run_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ControlServiceUnavailable("caído")
        return await original_delete(control_run_id)

    monkeypatch.setattr(two_plane_client.app.state.control_backend, "delete", flaky_delete)

    r1 = two_plane_client.delete("/api/runs/run_done_1")
    assert r1.status_code == 207
    assert "control" in r1.json()["errors"]
    assert fake_state.deleted == ["run_done_1"]  # el lado media sí se borró

    monkeypatch.setattr(two_plane_client.app.state.control_backend, "delete", original_delete)
    r2 = two_plane_client.delete("/api/runs/run_done_1")
    assert r2.status_code == 204
    assert control_state.deleted == ["ctrl-3"]
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest tests/test_runs_router.py -k delete -v`
Expected: FAIL — `405 Method Not Allowed` (no existe la ruta DELETE en el router del BFF).

- [ ] **Step 3: Implementar el endpoint orquestador**

En `routers/runs.py`, actualizar los imports (línea 8-15 actuales):

```python
from eovrt_webconsole.experiment.control_backend import (
    RunActive as ControlRunActive,
    ServiceUnavailable as ControlServiceUnavailable,
    UnknownRun as ControlUnknownRun,
)
from eovrt_webconsole.routers.compose import validate_composition
from eovrt_webconsole.run_backend import (
    RunActive, RunBusy, RunNotFinished, ServiceRejected, ServiceUnavailable, UnknownRun,
)
```

Y el import de `fastapi.responses` (línea 7 actual) agrega `Response`:

```python
from fastapi.responses import JSONResponse, Response, StreamingResponse
```

Agregar el endpoint, después de `stop_run` (línea 134 actual) y antes de `evaluate_run`:

```python
@router.delete("/{run_id}", status_code=204)
async def delete_run(run_id: str, request: Request):
    backend = request.app.state.backend
    control = request.app.state.control_backend

    media_gone = False
    try:
        media_status = await backend.status(run_id)
    except UnknownRun:
        media_gone = True
    except ServiceUnavailable as exc:
        logger.warning("delete_run(%s): servicio media inaccesible: %s", run_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        if media_status.get("status") == "running":
            raise HTTPException(status_code=409, detail="No se puede borrar un run activo")

    try:
        candidates = await control.list_runs(media_run_id=run_id)
    except ControlServiceUnavailable as exc:
        logger.warning(
            "delete_run(%s): control-plane inaccesible al resolver correlación: %s", run_id, exc
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    control_run_ids = [item["control_run_id"] for item in candidates]

    if media_gone and not control_run_ids:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}")

    for control_run_id in control_run_ids:
        try:
            control_status = await control.status(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlServiceUnavailable as exc:
            logger.warning("delete_run(%s): control-plane inaccesible: %s", run_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if control_status.get("status") == "running":
            raise HTTPException(
                status_code=409, detail=f"No se puede borrar: {control_run_id} sigue activo"
            )

    errors: dict[str, str] = {}
    if not media_gone:
        try:
            await backend.delete(run_id)
        except UnknownRun:
            pass
        except RunActive as exc:
            errors["media"] = exc.detail
        except ServiceUnavailable as exc:
            errors["media"] = str(exc)

    for control_run_id in control_run_ids:
        try:
            await control.delete(control_run_id)
        except ControlUnknownRun:
            continue
        except ControlRunActive as exc:
            errors["control"] = exc.detail
        except ControlServiceUnavailable as exc:
            errors["control"] = str(exc)

    if errors:
        logger.warning("delete_run(%s): borrado parcial: %s", run_id, errors)
        return JSONResponse(status_code=207, content={"detail": "borrado parcial", "errors": errors})
    logger.info("delete_run: run_id=%s borrado en ambos planos", run_id)
    return Response(status_code=204)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest tests/test_runs_router.py -v`
Expected: todos passed (los nuevos + los preexistentes).

- [ ] **Step 5: Suite completa + lint**

Run: `cd e-ovrt_experimental-setup/webconsole/backend && pytest -q && ruff check src tests`
Expected: todo verde.

- [ ] **Step 6: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/backend/src/eovrt_webconsole/routers/runs.py webconsole/backend/tests/test_runs_router.py
git commit -m "feat: DELETE /api/runs/{id} orquestador en el webconsole backend (media+control)"
```

---

## Task 5: Frontend — cliente `deleteRun` en `api.ts`

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/frontend/src/api.ts`

**Interfaces:**
- Produces: `deleteRun(id: string): Promise<{ detail: string; errors: Record<string, string> } | undefined>` — `undefined` en borrado completo (204), el objeto con `errors` en borrado parcial (207, `response.ok` es `true` para 207 así que `request<T>` no tira `ApiError`).

- [ ] **Step 1: Verificar si hay suite de tests de frontend**

Run: `cd e-ovrt_experimental-setup/webconsole/frontend && cat package.json | grep -A3 '"scripts"'`
Si hay un script `test` (Vitest/Jest), este task usará TDD normal (Step 2-5 con test real). Si no lo hay, saltar a Step 3 directamente (implementación) y verificar manualmente en Task 6.

- [ ] **Step 2 (si hay suite de tests): escribir el test que falla**

Si existe `src/api.test.ts` o similar con tests de `request`/otros exports de `api.ts`, agregar ahí:

```ts
import { deleteRun } from './api'

test('deleteRun hace DELETE al endpoint del run', async () => {
  const spy = vi.spyOn(global, 'fetch').mockResolvedValue(
    new Response(null, { status: 204 }),
  )
  const result = await deleteRun('run-1')
  expect(spy).toHaveBeenCalledWith(
    '/api/runs/run-1',
    expect.objectContaining({ method: 'DELETE' }),
  )
  expect(result).toBeUndefined()
})
```

Run: el comando de test del proyecto (ver Step 1). Expected: FAIL — `deleteRun is not exported`.

- [ ] **Step 3: Implementar `deleteRun`**

En `api.ts`, agregar después de `stopRun` (línea 51 actual):

```ts
export const deleteRun = (id: string) =>
  request<{ detail: string; errors: Record<string, string> } | undefined>(
    `/api/runs/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
  )
```

- [ ] **Step 4 (si hay suite de tests): correr y verificar que pasa**

Run: el comando de test del proyecto.
Expected: passed.

- [ ] **Step 5: Typecheck**

Run: `cd e-ovrt_experimental-setup/webconsole/frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 6: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/frontend/src/api.ts
git commit -m "feat: cliente deleteRun en el frontend (DELETE /api/runs/{id})"
```

---

## Task 6: Frontend — botón de borrado en `RunsPage.tsx`

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/frontend/src/pages/RunsPage.tsx`

**Interfaces:**
- Consumes: `deleteRun` (Task 5), `isRunning` (ya existe, `runview.ts:21-23`).

- [ ] **Step 1: Implementar el botón + confirmación**

Reemplazar el contenido completo de `RunsPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, EmptyState, ErrorBanner } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)', '']

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const refresh = () =>
    listRuns()
      .then((r) => {
        setRows(r)
        setError(null)
        return r
      })
      .catch((e) => {
        setError(String(e))
        return null
      })

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      refresh().then((r) => {
        // refresco solo mientras hay actividad (el resto es historial estático)
        if (alive && r && r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
      })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const handleDelete = async (row: RunRow) => {
    if (!window.confirm(`¿Borrar el run ${row.run_id}? No se puede deshacer.`)) return
    setDeletingId(row.run_id)
    try {
      const result = await deleteRun(row.run_id)
      if (result?.errors) {
        setError(
          `Borrado parcial de ${row.run_id}: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
      } else {
        setError(null)
      }
    } catch (e) {
      setError(`No se pudo borrar ${row.run_id}: ${String(e)}`)
    } finally {
      setDeletingId(null)
      await refresh()
    }
  }

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
      <table className="eo-table">
        <thead>
          <tr>{HEADERS.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id}>
              <td><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
              <td>
                <Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge>
                {r.topology === 'two_node' ? <small> two-node</small> : null}
              </td>
              <td>{r.model ?? '—'}</td>
              <td>{r.source_type ?? '—'}</td>
              <td>{r.prompt_set_id ?? '—'}</td>
              <td className="eo-num">{r.fps_effective ?? '—'}</td>
              <td className="eo-num">{r.total_detections ?? '—'}</td>
              <td className="eo-num">{r.duration_seconds ?? '—'}</td>
              <td>
                {!isRunning(r) && (
                  <button
                    type="button"
                    disabled={deletingId === r.run_id}
                    onClick={() => void handleDelete(r)}
                  >
                    Borrar
                  </button>
                )}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={9}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Verificar en el browser**

Run: `cd e-ovrt_experimental-setup/webconsole && make dev` (o el comando de arranque que use el proyecto — revisar `README.md`/`Makefile` de `webconsole/` si `make dev` no existe).

Con el media-plane y control-plane services corriendo (o mockeados), abrir la consola, ir a la lista de runs, y verificar:
1. Un run `running` NO tiene botón "Borrar".
2. Un run terminado sí lo tiene; al clickear aparece el `window.confirm`.
3. Cancelar el confirm no hace nada.
4. Confirmar borra el run y desaparece de la lista tras el refresh.

- [ ] **Step 3: Typecheck**

Run: `cd e-ovrt_experimental-setup/webconsole/frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/frontend/src/pages/RunsPage.tsx
git commit -m "feat: botón de borrado (con confirmación) en RunsPage"
```

---

## Task 7: Frontend — botón de borrado en `RunDetailPage.tsx`

**Files:**
- Modify: `e-ovrt_experimental-setup/webconsole/frontend/src/pages/RunDetailPage.tsx`

**Interfaces:**
- Consumes: `deleteRun` (Task 5), `useNavigate` de `react-router-dom`.

- [ ] **Step 1: Implementar el botón + confirmación + redirect**

En `RunDetailPage.tsx`:

1. Actualizar los imports (líneas 1-10 actuales):

```tsx
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { artifactUrl, deleteRun, getRun, stopRun } from '../api'
import EvalSection from '../components/EvalSection'
import Sparkline from '../components/Sparkline'
import TraceSection from '../components/TraceSection'
import { Badge, Card, DetChip, EmptyState, ErrorBanner, StatTile } from '../components/ui'
import { isLive, runStatusLabel, runStatusTone, topologyBadge } from '../runview'
import { useRunStream } from '../stream'
import type { RunDetail } from '../types'
```

2. Dentro de `RunDetailPage`, agregar después de la línea `const live = useRunStream(id, streamable)`:

```tsx
  const navigate = useNavigate()
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!window.confirm(`¿Borrar el run ${id}? No se puede deshacer.`)) return
    setDeleting(true)
    try {
      const result = await deleteRun(id)
      if (result?.errors) {
        setError(
          `Borrado parcial: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
        setDeleting(false)
        return
      }
      navigate('/runs')
    } catch (e) {
      setError(`No se pudo borrar: ${String(e)}`)
      setDeleting(false)
    }
  }
```

3. En el `<h2>` de cabecera (línea 73-86 actuales), agregar el botón junto al de "Detener" (visible solo cuando no está `running`, es decir el opuesto de `streamable`/`running`):

```tsx
      <h2 className="eo-inline">
        <span>{run.run_id}</span>
        <Badge tone={runStatusTone(run)}>{runStatusLabel(run)}</Badge>
        {topology && <Badge tone="neutral">{topology}</Badge>}
        {streamable && (
          <button
            onClick={() => {
              stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
            }}
          >
            ■ Detener
          </button>
        )}
        {!running && (
          <button type="button" disabled={deleting} onClick={() => void handleDelete()}>
            Borrar
          </button>
        )}
      </h2>
```

- [ ] **Step 2: Verificar en el browser**

Con el dev server corriendo (Task 6, Step 2), navegar al detalle de un run terminado, clickear "Borrar", confirmar, y verificar que redirige a `/runs` y el run ya no aparece en la lista.

- [ ] **Step 3: Typecheck**

Run: `cd e-ovrt_experimental-setup/webconsole/frontend && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
cd e-ovrt_experimental-setup
git add webconsole/frontend/src/pages/RunDetailPage.tsx
git commit -m "feat: botón de borrado (con confirmación) en RunDetailPage"
```

---

## Self-Review Notes

- **Spec coverage:** Alcance (hard delete, estados terminales) → Tasks 1/4. Arquitectura (orquestación BFF) → Task 4. Componente 1 (control-plane endpoint) → Task 1. Componente 2 (orquestador + idempotencia) → Task 4. Componente 3 (frontend, dos ubicaciones, confirmación) → Tasks 5/6/7. Testing (los tres niveles listados en el spec) → Tasks 1, 3, 4.
- **Placeholder scan:** sin TBD/TODO; todos los pasos traen código completo.
- **Type consistency:** `RunActive.detail: str` es consistente entre `run_backend.py` y `control_backend.py` (dos clases distintas, mismo shape, usadas con alias en el router). `deleteRun` en el frontend devuelve el mismo shape (`{ detail, errors } | undefined`) consumido igual en `RunsPage.tsx` y `RunDetailPage.tsx`.
