# Spec 44 B — Webconsole backend: cliente del control-plane, orquestación y alertas

> **EJECUTADO el 2026-07-11.** Las 5 tareas + 3 fixes completas (webconsole/backend **236 passed**,
> ruff limpio; revisión final **LISTO PARA MERGE**, sin Critical/Important). Resultados y deuda:
> `docs/operacion/53-experimental-setup-runner-y-reporte.md` §7 (repo `docs`). Defectos corregidos:
> YAMLError→500 en el listado; test de slot-free-on-crash faltante; **path traversal HIGH** en
> `/report` (`%2e%2e` escapaba `runs/`) — guard + containment. Concurrencia (one-active,
> slot-free-on-crash) y el disparo orquestado verificados discriminantes por mutación.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el BFF de la webconsole (hoy mono-plano: sólo media-plane :8080) en la **superficie de gestión de la plataforma** (spec 44 §5): un **segundo backend** hacia el control-plane :8081, **CRUD del manifiesto paraguas** `experiment.manifest.v1`, **disparo orquestado** de un experimento (la misma secuencia del runner A1, en background), y la **vista de alertas** (proxy a `GET /api/runs/{id}/alerts` del control-plane) + lectura del **reporte consolidado**. Reusa todo lo de A1/A2 (`ControlPlaneBackend`, `run_experiment`, `ExperimentManifest`, `write_report`).

**Architecture:** `webconsole/backend/`, package `eovrt_webconsole`, FastAPI BFF. El BFF sigue siendo el único origen para el navegador (sin ZeroMQ en la consola: polling). El wiring es **puramente aditivo** — el media-plane y sus 204 tests quedan intactos. Los handlers leen `request.app.state.{backend,control_backend,settings}`. `run_experiment` es async y **hace polling hasta terminal** (bloquea), así que el disparo orquestado corre en una **tarea de fondo** (`asyncio.Task`) gestionada por un `ExperimentRunManager` (un experimento activo por vez, patrón del `RunManager` del media-plane). Las funciones sync de A2 (`consolidate_experiment`/`write_report`) las invoca `run_experiment` internamente.

**Tech Stack:** Python 3.11+, FastAPI, httpx async, Pydantic v2, pyyaml, pytest + pytest-asyncio, ruff. Sin nuevas dependencias.

## Global Constraints

- **Nunca commitear sin pedido explícito del usuario en ese turno.** Pasos "Commit" preparan; sólo si el usuario lo pide. Si no, `git add -A` sin `git commit`. SDD usa `git write-tree` (no es commit).
- **Nunca `Co-Authored-By`. Nada en GitHub; todo local.**
- **Aditivo, no rompe el mono-plano.** Los 204 tests existentes NO deben tocarse ni fallar. El media-plane (`app.state.backend`, `RunBackend`, `fake_service.py`) queda intacto. El segundo backend y las rutas nuevas son adición.
- **No editar `fake_service.py` ni `run_backend.py`** (pre-existentes del media-plane). Sí se puede editar `app.py`, `settings.py`, `conftest.py`, y crear routers/módulos nuevos.
- **Sin bloquear el event loop:** `run_experiment` corre en `asyncio.Task` de fondo (no se `await` inline en el handler); las funciones sync de A2 se invocan dentro de `run_experiment`. El handler de disparo devuelve 202/201 con `experiment_id` y el estado se consulta por polling.
- **Un experimento activo por vez** (como el media-plane): `POST` de disparo con uno activo ⇒ 409 con el `experiment_id` activo.
- **El BFF es cliente HTTP de ambos planos** — no consume el bus. La vista de alertas lee `GET /api/runs/{id}/alerts` del control-plane por polling.
- `ruff` line-length 100. Comentarios/docstrings en español, sin tildes ni ñ dentro del código.
- **Entorno/tests:** desde `webconsole/backend/`, `.venv/bin/python -m pytest -q` (asyncio_mode=auto), `.venv/bin/python -m ruff check src tests`.
- **Baseline MEDIDA (2026-07-11):** `pytest -q` → **204 passed** (A1+A2 incluidos).

---

## Task 1: Segundo backend — `control_service_url` + `app.state.control_backend`

**Files:**
- Modify: `src/eovrt_webconsole/settings.py` (campo `control_service_url`)
- Modify: `src/eovrt_webconsole/app.py` (`create_app` gana `control_transport`; `_lifespan` construye `app.state.control_backend`)
- Modify: `tests/conftest.py` (fixture que inyecta AMBOS fakes)
- Test: `tests/test_control_backend_wiring.py`

**Interfaces:**
- Consumes: `ControlPlaneBackend` (A1), `make_fake_control_service`/`FakeControlState` (A1 tests).
- Produces: `ConsoleSettings.control_service_url: str = "http://localhost:8081"` (+ `from_env` línea `EOVRT_CONSOLE_CONTROL_SERVICE_URL`); `create_app(settings, service_transport=None, compose_runner=None, control_transport=None)`; `app.state.control_http` + `app.state.control_backend = ControlPlaneBackend(...)`, cerrado en teardown; un fixture `two_plane_client` en conftest que inyecta media+control fakes.

- [ ] **Step 1: Escribir el test que falla** — un test que crea la app con ambos fakes inyectados (`two_plane_client`) y verifica que `app.state.control_backend` existe y responde (p.ej. una ruta smoke `/api/experiments/health` que llame `control_backend.config()` o directamente asserta que `create_app(..., control_transport=t).state` tiene `control_backend`). Simplest: instanciar `create_app(settings, control_transport=transport)` y con `TestClient` verificar que `app.state.control_backend` es un `ControlPlaneBackend`.

- [ ] **Step 2: Correr — falla** (AttributeError: control_backend / TypeError: control_transport).

- [ ] **Step 3: Implementación** (los seams del §1 del mapa): agregar el campo defaulted a `ConsoleSettings` (no rompe los 2 sitios de construcción en conftest); `from_env` con `EOVRT_CONSOLE_CONTROL_SERVICE_URL`; en `_lifespan` (modo estático) construir `app.state.control_http = httpx.AsyncClient(base_url=settings.control_service_url, transport=control_transport, timeout=30.0)` y `app.state.control_backend = ControlPlaneBackend(app.state.control_http)`, y `await app.state.control_http.aclose()` en teardown. En conftest, agregar el fixture `two_plane_client` que inyecta `service_transport` (media) + `control_transport` (control) — SIN tocar `client`/`live_client` existentes.

- [ ] **Step 4-5:** correr nuevo (pasa) + suite completa (Expected: 204 + N; los 204 verdes).
- [ ] **Step 6: Commit (sólo si el usuario lo pidió).**

---

## Task 2: CRUD del manifiesto paraguas `experiment.manifest.v1`

**Files:**
- Create: `src/eovrt_webconsole/routers/experiments.py` (`APIRouter(prefix="/api/experiments")`)
- Modify: `src/eovrt_webconsole/app.py` (registrar el router antes del mount de la SPA)
- Test: `tests/test_experiments_manifests.py`

**Interfaces:**
- Consumes: `ExperimentManifest`/`load_manifest` (A1), `write_manifest` (dict-agnóstico), `settings.experiments_dir`.
- Produces: `POST /api/experiments/manifests` (body `experiment.manifest.v1` → valida con `ExperimentManifest.model_validate` → `write_manifest(experiments_dir, name=slug, group=None, manifest=model.model_dump(mode="json"), overwrite=...)` → 201; 422 inválido; 409 existe sin overwrite); `GET /api/experiments/manifests` (lista los YAML de `experiments_dir` que tengan `schema_version: experiment.manifest.v1`, vía `load_manifest`, tolerando los single-plane viejos); `GET /api/experiments/manifests/{slug}` (200 el manifiesto o 404).

- [ ] **Step 1: Escribir el test que falla** — POST un `experiment.manifest.v1` válido → 201 y el archivo aparece en `experiments_dir`; GET lista lo incluye y NO incluye los manifiestos single-plane viejos; GET por slug lo devuelve; POST inválido (schema roto) → 422; POST duplicado sin overwrite → 409. Usar el `repo`/`settings` fixtures.

- [ ] **Step 2-6:** falla → impl (router leyendo `request.app.state.settings`; mapear `ManifestExistsError`→409, `ProtectedManifestError`→409, `ValueError`/`ValidationError`→422) → pasan → suite → commit guarded. Registrar el router en `app.py`.

---

## Task 3: `ExperimentRunManager` + disparo orquestado (background, un activo)

**Files:**
- Create: `src/eovrt_webconsole/experiment/run_manager.py`
- Modify: `src/eovrt_webconsole/routers/experiments.py` (rutas de disparo/estado), `app.py` (crear el manager en `_lifespan`)
- Test: `tests/test_experiment_orchestration.py`

**Interfaces:**
- Consumes: `run_experiment` (A1, async, polls to terminal), `ExperimentManifest`, `app.state.{backend,control_backend}`.
- Produces: `ExperimentRunManager` — `start(manifest) -> experiment_id` (crea un `asyncio.Task` que corre `run_experiment(manifest, media_backend=..., control_backend=..., now=...)`; 1 activo por vez, `ExperimentBusy(active_experiment_id)` si ya hay uno); `current() -> dict | None` (estado del activo: `experiment_id`, `running`/`ok`/`failed`); `get(experiment_id) -> dict | None` (resultado: incluye `ExperimentResult` si terminó); limpieza del slot en `finally`. `POST /api/experiments/run` (body `{slug}` o `{manifest}` → carga el manifiesto de `experiments_dir/{slug}.yaml`, genera experiment_id, `manager.start(...)` → 202 `{experiment_id}`; 409 `{active_experiment_id}`; 422 manifiesto inválido/inexistente). `GET /api/experiments/current` (200 el activo o 404). `GET /api/experiments/{experiment_id}` (200 estado/resultado o 404).

- [ ] **Step 1: Escribir el test que falla** — con `two_plane_client` (ambos fakes, corridas rápidas): `POST /api/experiments/run` con un slug de un manifiesto `live`/`replay` → 202 + `experiment_id`; poll `GET /api/experiments/{id}` hasta `ok`; asserta que terminó OK y (vía los fakes) que el orden fue el correcto. Un `POST` con otro ya activo → 409 con `active_experiment_id`. **SIGABRT/threads:** el manager usa `asyncio.Task` (mismo loop), no hilos — no hay cierre de sockets cross-thread.

- [ ] **Step 2-6:** falla → impl (el manager arranca el task, trackea estado, limpia el slot en `finally`; el handler NO awaitea `run_experiment` inline — deja correr el task y devuelve 202) → pasan → suite → commit guarded.

**Nota de concurrencia:** un experimento activo por vez. El manager guarda el `asyncio.Task` y el estado; `current()`/`get()` reflejan `running`→`ok`/`failed`. El slot se libera pase lo que pase (incluye excepción del task).

---

## Task 4: Vista de alertas + lectura del reporte consolidado

**Files:**
- Modify: `src/eovrt_webconsole/routers/experiments.py`
- Test: `tests/test_experiment_alerts_report.py`

**Interfaces:**
- Consumes: `control_backend.alerts(control_run_id)` (A1), el dir consolidado / `report/report.json` (A2), el estado del manager (para resolver `experiment_id → control_run_id`).
- Produces: `GET /api/experiments/{experiment_id}/alerts` (resuelve el `control_run_id` desde el resultado del manager o desde el `report.json`/`summary` consolidado, luego proxya `control_backend.alerts` → 200 lista; 404 si no hay control_run_id; 502 `ServiceUnavailable`); `GET /api/experiments/{experiment_id}/report` (lee `runs/<experiment_id>/report/report.json` del dir consolidado → 200 el reporte; 404 si no consolidado). Detección ADR-013: si el `report.json` marca la corrida no-temporal (`source_clock: none`), la respuesta incluye un flag `non_temporal: true` para que el frontend deshabilite los controles temporales.

- [ ] **Step 1: Escribir el test que falla** — tras una corrida orquestada (o con un dir consolidado sintético + un manager con un resultado que mapee experiment_id→control_run_id): `GET .../alerts` devuelve las alertas del fake control; `GET .../report` devuelve el `report.json` con sus estados de aplicabilidad; el caso imágenes marca `non_temporal: true`. 404 cuando no existe.

- [ ] **Step 2-6:** falla → impl (leer del dir consolidado con `Path`; el proxy de alertas mapea las excepciones del `control_backend` a HTTP; las lecturas sync de archivos van bien en el handler o con `run_in_threadpool` si son pesadas) → pasan → suite → commit guarded.

---

## Task 5: **Gate** — e2e por el BFF (TestClient, dos fakes) + verificación por mutación

**Files:**
- Test: `tests/test_spec44b_gate.py`

- [ ] **Step 1: Escribir el gate** — con `two_plane_client` (media+control fakes): (1) `POST /api/experiments/manifests` crea un manifiesto paraguas; (2) `POST /api/experiments/run` lo dispara → 202; (3) poll `GET /api/experiments/{id}` hasta OK; (4) `GET /api/experiments/{id}/alerts` devuelve las alertas del control fake; (5) `GET /api/experiments/{id}/report` devuelve el reporte. Aserciones concretas en cada paso; y que un segundo `run` mientras hay uno activo da 409.

- [ ] **Step 2: Correr el gate** — Expected: PASS.

- [ ] **Step 3: Verificar que el gate es significativo (mutación) — obligatorio.** Dos mutaciones, una por vez, salida literal:
  1. En el `ExperimentRunManager`, NO chequear el slot activo (permitir 2 concurrentes). Esperado: **falla** la aserción de 409 del gate. Revertí.
  2. En la ruta de alertas, devolver `[]` en vez de proxyar el control-plane. Esperado: **falla** la aserción de que las alertas del control fake aparecen. Revertí.
  Si alguna no hace fallar el gate, es vacuo: arreglalo.

- [ ] **Step 4: Suite completa + lint** — Expected: 204 + tests nuevos, todo verde; `All checks passed!`.
- [ ] **Step 5: Commit (sólo si el usuario lo pidió).**

---

## Cierre

- [ ] **Registrar la deuda:** el frontend React (Plan C) consume estas rutas (navegación por experimento, vista de alertas, disparo orquestado, detección no-temporal). El `GET /api/config` shape del control-plane real (deuda de A1) se alinea si alguna ruta lee config del control vivo. La orquestación por docker-compose (fleet, `platform` router) es ortogonal a este disparo por-experimento.
- [ ] **Escribir/actualizar el doc de resultados** (`docs/operacion/`, con A1/A2/B o un doc nuevo de la serie 50-). Banner EJECUTADO en este plan.
- [ ] **Verificación final:** pegar `pytest -q` (verde), `ruff check` (limpio), la salida de las dos mutaciones del gate.

## Alineación con spec 44 §5.1 (self-review)

| Requisito §5.1 | Task |
|---|---|
| Segundo `RunBackend` → control-plane :8081 (mismo patrón cliente-HTTP) | 1 |
| CRUD de configs: el BFF escribe el árbol versionado (manifiesto paraguas) | 2 |
| Disparo orquestado = la secuencia del runner (§3) | 3 |
| Vista de alertas: lee `GET /api/runs/{id}/alerts` (polling, sin ZeroMQ) | 4 |
| Agrupación/lectura desde el dir consolidado `runs/<experiment_id>/` | 4 |
| Detección de fuente no temporal (ADR-013) | 4 |
| Rediseño UX React (declarado sacrificable §5.2) | **Plan C** |
