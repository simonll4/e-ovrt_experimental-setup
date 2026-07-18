# Vista correlacionada media↔control (Pieza B) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Para un run terminado, `RunDetailPage` muestra el ciclo completo de cada frame: detecciones del media-plane, si llegó al control-plane (o por qué se descartó), progreso de patrones y alertas — vía un trace compuesto en el BFF.

**Architecture:** 2 endpoints de lectura en el control-plane (lookup por `media_run_id` + `received-units`), un módulo puro de composición + endpoint `trace` en el BFF (merge por `frame_index`, paginado), y una sección nueva en `RunDetailPage` con la tabla unificada. Todo aditivo.

**Tech Stack:** Python 3.11 + FastAPI + pytest (2 repos backend); React 18 + TS strict + Vitest (SPA). Cero dependencias nuevas en los tres repos.

**Spec:** `docs/superpowers/specs/2026-07-17-evaluation-trace-view-design.md`

## Global Constraints

- **MODO SIN COMMITS** en los tres repos (regla de `projects/CLAUDE.md`). Los pasos "Commit" son puntos de corte.
- **Aditivo estricto**: nada existente cambia de forma en ningún repo.
- Baselines: control-plane 242 passed + 1 fallo labs preexistente (numpy — NO es nuestro); experimental-setup backend 270+ / frontend 108; media-plane 604 (no se toca en este plan). Gate = cero fallos nuevos.
- Tests: control-plane `.venv/bin/python -m pytest tests/ -q`; BFF `cd webconsole/backend && .venv/bin/python -m pytest -q` (¡`python -m`, no pytest plano!); SPA `cd webconsole/frontend && npx vitest run` (fireEvent, NO user-event; toBeTruthy, NO jest-dom).
- SPA: ningún hex literal en TS/TSX; colores por tokens/clases `eo-*`; `BadgeTone` desde `types.ts`.
- **Desvío declarado del spec §7**: el cache LRU del trace se DIFIERE como follow-up (la paginación ya acota la respuesta; YAGNI hasta medir). El plan no lo implementa.

---

### Task 1: Endpoints de lectura en el control-plane

**Repo:** `/home/simonll4/projects/e-ovrt_control-plane/`
**Files:**
- Modify: `src/eovrt_control/service/run_manager.py`, `src/eovrt_control/service/routers/runs.py`
- Test: `tests/test_service_api.py` (append)

**Interfaces:**
- Produces: `GET /api/runs?media_run_id=` → `[{control_run_id, status, started_at, alerts_count, media_run_id}]` (más reciente primero); `GET /api/runs/{id}/received-units?limit=` → `[{unit_id}]`.
- Consumes: patrón de `RunManager.alerts()`/`pattern_progress()` (líneas ~179-230) y sus tests vecinos (`test_pattern_progress_endpoint_*` de la Pieza A: mismo armado de run_dir).

- [ ] **Step 1: Tests que fallan** — append a `tests/test_service_api.py`, replicando el armado de run_dir de los tests de pattern-progress del mismo archivo (escriben archivos en el runs_dir del settings del client):

```python
def test_list_runs_lookup_by_media_run_id(client, tmp_path) -> None:
    # armar DOS run_dirs con summary.json (copiar el mecanismo de los tests vecinos):
    #  - "ctrl-a": summary con media_run_id="media-1", status="succeeded",
    #              started_at="2026-07-17T00:00:00Z", alerts_count=1
    #  - "ctrl-b": summary con media_run_id="media-2", ...
    ...
    r = client.get("/api/runs?media_run_id=media-1")
    assert r.status_code == 200
    rows = r.json()
    assert [x["control_run_id"] for x in rows] == ["ctrl-a"]
    assert rows[0]["media_run_id"] == "media-1" and rows[0]["alerts_count"] == 1

    todo = client.get("/api/runs")
    assert {x["control_run_id"] for x in todo.json()} >= {"ctrl-a", "ctrl-b"}


def test_list_runs_skips_corrupt_summary(client, tmp_path) -> None:
    # un run_dir con summary.json ilegible NO rompe el listado (mismo criterio del servicio)
    ...
    assert client.get("/api/runs").status_code == 200


def test_received_units_serves_unit_ids(client, tmp_path) -> None:
    # run_dir con metrics.jsonl de 3 lineas {"unit_id": "u0"}, {"unit_id": "u1"}, {"unit_id": "u2"}
    ...
    r = client.get(f"/api/runs/{run_id}/received-units")
    assert r.status_code == 200
    assert [x["unit_id"] for x in r.json()] == ["u0", "u1", "u2"]
    limited = client.get(f"/api/runs/{run_id}/received-units?limit=2")
    assert len(limited.json()) == 2


def test_received_units_unknown_run_404_and_missing_file_empty(client, tmp_path) -> None:
    assert client.get("/api/runs/no-existe/received-units").status_code == 404
    # run_dir valido SIN metrics.jsonl -> 200 []
    ...
    assert client.get(f"/api/runs/{run_id}/received-units").json() == []
```

Los `...` son el armado de run_dir a COPIAR de los tests vecinos de pattern-progress/alerts del mismo archivo (no inventar mecanismos).

- [ ] **Step 2: Verificar que fallan** — `.venv/bin/python -m pytest tests/test_service_api.py -q` → FAIL.

- [ ] **Step 3: Implementar.**

(a) `run_manager.py` — dos métodos debajo de `pattern_progress()`. Nota: para el listado hace falta el directorio raíz de runs; **mirá cómo lo obtiene `_run_dir()` en el archivo real y usá el mismo atributo** (el código abajo asume `self._runs_dir`; si el nombre real difiere, usá el real):

```python
    def list_runs(self, media_run_id: str | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self._runs_dir.is_dir():
            return rows
        for run_dir in self._runs_dir.iterdir():
            summary_path = run_dir / "summary.json"
            if not summary_path.is_file():
                continue
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("summary ilegible en %s: %s", run_dir.name, exc)
                continue
            if media_run_id is not None and summary.get("media_run_id") != media_run_id:
                continue
            rows.append(
                {
                    "control_run_id": run_dir.name,
                    "status": summary.get("status"),
                    "started_at": summary.get("started_at"),
                    "alerts_count": summary.get("alerts_count"),
                    "media_run_id": summary.get("media_run_id"),
                }
            )
        rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
        return rows

    def received_units(self, run_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            raise UnknownRunError(run_id)
        path = run_dir / "metrics.jsonl"
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    sample = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("metrica ilegible en %s linea %d: %s", run_id, line_no, exc)
                    continue
                unit_id = sample.get("unit_id")
                if unit_id is not None:
                    rows.append({"unit_id": unit_id})
        if limit is not None:
            rows = rows[: max(limit, 0)]
        return rows
```

(b) `routers/runs.py` — dos endpoints. `GET /runs` (listado) puede ir junto a `POST /runs`; `received-units` debajo de `pattern-progress`, copiando su wrapper de errores:

```python
@router.get("/runs")
def list_runs(request: Request, media_run_id: str | None = Query(default=None)):
    return _manager(request).list_runs(media_run_id=media_run_id)


@router.get("/runs/{run_id}/received-units")
def get_run_received_units(
    run_id: str, request: Request, limit: int | None = Query(default=None, ge=0)
):
    # copiar el wrapper require_valid_run_id + UnknownRunError->404 del endpoint de pattern-progress
    ...
```

- [ ] **Step 4: Verificar que pasan** — `tests/test_service_api.py -q` → PASS; suite completa → cero fallos nuevos (el de labs es baseline).
- [ ] **Step 5: Punto de corte (sin commit).**

---

### Task 2: Clientes y fakes del BFF

**Repo:** `/home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend/`
**Files:**
- Modify: `src/eovrt_webconsole/experiment/control_backend.py`, `src/eovrt_webconsole/run_backend.py`, `tests/fake_control_service.py`, `tests/fake_service.py`
- Test: `tests/test_run_backend.py` (append; si los métodos de control se testean en otro archivo, seguir ese patrón)

**Interfaces:**
- Produces: `ControlPlaneBackend.list_runs(media_run_id=None)`, `.pattern_progress(control_run_id)`, `.received_units(control_run_id)`; `RunBackend.dropped(run_id, page, page_size)`. Fakes: `FakeControlState.runs_index` (lookup), `.pattern_progress`, `.received_units`; `FakeState.dropped`.
- Consumes: `_get_json` de ambos clientes (ya existen, control_backend.py:41-51 / run_backend.py:48-58).

- [ ] **Step 1: Tests que fallan** — append al archivo de tests que hoy cubre los métodos de `RunBackend` (`tests/test_run_backend.py`), siguiendo su patrón de transporte ASGI contra el fake:

```python
# RunBackend.dropped: passthrough paginado (mismo shape que detections)
async def test_dropped_passthrough(...):
    # sembrar fake_state.dropped = {"run-1": [{...3 registros...}]}
    ...
    result = await backend.dropped("run-1", page=1, page_size=2)
    assert result["total"] == 3 and len(result["items"]) == 2

# ControlPlaneBackend: lookup + progress + received-units contra el fake de control
async def test_control_lookup_and_readers(...):
    ...
    runs = await control.list_runs(media_run_id="media-1")
    assert runs[0]["control_run_id"] == "ctrl-a"
    prog = await control.pattern_progress("ctrl-a")
    assert prog[0]["progress"] == 0.5
    units = await control.received_units("ctrl-a")
    assert [u["unit_id"] for u in units] == ["u0", "u1"]
```

(los `...` = fixtures/patrón del archivo real; copiarlos de los tests vecinos, no inventar).

- [ ] **Step 2: FAIL** → **Step 3: Implementar.**

(a) `control_backend.py` — tres métodos junto a `alerts()` (mismo estilo `_get_json`):

```python
    async def list_runs(self, media_run_id: str | None = None) -> list[dict]:
        params = {"media_run_id": media_run_id} if media_run_id else {}
        return await self._get_json("/api/runs", **params)

    async def pattern_progress(self, control_run_id: str) -> list[dict]:
        return await self._get_json(f"/api/runs/{control_run_id}/pattern-progress")

    async def received_units(self, control_run_id: str) -> list[dict]:
        return await self._get_json(f"/api/runs/{control_run_id}/received-units")
```

(b) `run_backend.py` — junto a `detections()`:

```python
    async def dropped(self, run_id: str, page: int = 1, page_size: int = 100) -> dict:
        return await self._get_json(
            f"/api/runs/{run_id}/dropped", page=page, page_size=page_size
        )
```

(c) Fakes: en `fake_service.py`, endpoint `GET /api/runs/{run_id}/dropped` que sirve `state.dropped.get(run_id, [])` paginado con el shape `{page, page_size, total, items}` (espejo del de detections del fake). En `fake_control_service.py`: `GET /api/runs` (filtra `state.runs_index` por `media_run_id`), `GET /api/runs/{id}/pattern-progress` (`state.pattern_progress.get(id, [])`), `GET /api/runs/{id}/received-units` (`state.received_units.get(id, [])`), con 404 para run desconocido siguiendo el criterio de los endpoints ya presentes en el fake.

- [ ] **Step 4: PASS** — tests del archivo + suite backend completa sin fallos nuevos.
- [ ] **Step 5: Punto de corte (sin commit).**

---

### Task 3: Composición y endpoint `trace` en el BFF

**Repo:** `webconsole/backend/`
**Files:**
- Create: `src/eovrt_webconsole/trace.py` (módulo puro de composición)
- Modify: `src/eovrt_webconsole/routers/runs.py`
- Test: `tests/test_trace.py` (nuevo)

**Interfaces:**
- Produces: `compose_trace(...) -> dict` (puro, testeable sin HTTP) y `GET /api/runs/{run_id}/trace?page&page_size&control_run_id`. Contrato de respuesta = spec §4, verbatim.
- Consumes: Task 2 (clientes), `two_plane_client` + `FakeState`/`FakeControlState` (conftest.py:110-121).

- [ ] **Step 1: Tests que fallan** — `tests/test_trace.py`. Dos niveles:

(1) **Unit del merge puro** (sin HTTP):

```python
from eovrt_webconsole.trace import compose_trace


def _det(fi, uid, labels):  # DetectionEvent minimo del lado media
    return {"unit_id": uid, "source": {"frame_index": fi, "timestamp_ms": float(fi) * 100},
            "detections": [{"label": l, "confidence": 0.9} for l in labels]}


def test_merge_interleaves_processed_and_dropped_ordered():
    frames = compose_trace(
        detections=[_det(0, "u0", ["person"]), _det(2, "u2", ["person"])],
        dropped=[{"frame_index": 1, "unit_id": "u1", "reason": "rate_gate"}],
        progress=[], alerts=[], received_unit_ids={"u0", "u2"},
        control_run_id="ctrl-a", topology="single_host", control_error=None,
    )["frames"]
    assert [f["frame_index"] for f in frames] == [0, 1, 2]
    assert frames[1]["control"] == "dropped:rate_gate" and frames[1]["detections"] is None
    assert frames[0]["control"] == "received"


def test_not_received_via_set_difference():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"]), _det(1, "u1", ["person"])],
        dropped=[], progress=[], alerts=[], received_unit_ids={"u0"},
        control_run_id="ctrl-a", topology="single_host", control_error=None,
    )
    assert out["frames"][1]["control"] == "not_received"
    assert out["totals"]["not_received"] == 1


def test_progress_and_alert_attached_by_frame():
    out = compose_trace(
        detections=[_det(3, "u3", ["person"]), _det(4, "u4", ["person"])],
        dropped=[],
        progress=[{"frame_index": 3, "condition_id": "CR-01", "progress": 0.5,
                   "elapsed_ms": 500.0, "threshold_ms": 1000.0, "mode": "time"}],
        alerts=[{"frame_index": 4, "condition_id": "CR-01", "severity": "high"}],
        received_unit_ids={"u3", "u4"},
        control_run_id="ctrl-a", topology="single_host", control_error=None,
    )
    assert out["frames"][0]["progress"][0]["progress"] == 0.5
    assert out["frames"][1]["alert"][0]["condition_id"] == "CR-01"


def test_no_control_run_all_nd():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])], dropped=[], progress=[], alerts=[],
        received_unit_ids=None, control_run_id=None, topology="single_host",
        control_error=None,
    )
    assert out["frames"][0]["control"] == "n/d"
    assert out["totals"]["received"] is None
```

(2) **Endpoint vía `two_plane_client`**: sembrar `fake_state` (run terminado con detections + dropped) y `control_state` (runs_index apuntando al media_run_id, progress, received_units, alerts); `GET /api/runs/{id}/trace` → 200 con `control_run_id` resuelto por lookup automático, frames merged y paginación (`page_size=2` → 2 frames, `total` correcto). Más: control caído (apagar el fake / usar `client` de un solo plano) → 200 con `control: "n/d"` en frames y campo `control_error` poblado; `?control_run_id=` override respetado.

- [ ] **Step 2: FAIL** → **Step 3: Implementar.**

(a) `trace.py` — funciones puras. `compose_trace(detections, dropped, progress, alerts, received_unit_ids, control_run_id, topology, control_error)`:
- indexar progress/alerts por `frame_index` (listas por frame);
- eje = filas de detections (`frame_index` de `source.frame_index`) + filas de dropped, ordenado por `frame_index`;
- `control` por frame según la semántica del spec §4 (dropped → `dropped:<reason>`; con `received_unit_ids` set: `received`/`not_received`; `received_unit_ids is None` → `n/d`);
- `totals`: frames, detections (suma), `dropped_by_reason` (Counter), alerts, `received`/`not_received` (None si no hay control);
- devuelve `{control_run_id, topology, totals, frames}`; la paginación la hace el endpoint sobre `frames`.

(b) Endpoint en `routers/runs.py`, patrón de `detections` + `experiments.py:193-200` para el lado control:

```python
@router.get("/{run_id}/trace")
async def trace(
    run_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    control_run_id: str | None = Query(default=None),
) -> dict:
    backend = request.app.state.backend
    control = request.app.state.control_backend
    try:
        summary = await backend.status(run_id)
    except UnknownRun as exc:
        raise HTTPException(status_code=404, detail=f"Run desconocido: {run_id}") from exc
    except ServiceUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # traer TODAS las paginas de detections y dropped (page_size=1000, loop hasta total)
    detections = await _fetch_all(backend.detections, run_id)
    dropped = await _fetch_all(backend.dropped, run_id)
    # lado control: best-effort (degradacion del spec §6)
    progress, alerts, received, control_error = [], [], None, None
    try:
        if control_run_id is None:
            candidates = await control.list_runs(media_run_id=run_id)
            control_run_id = candidates[0]["control_run_id"] if candidates else None
        if control_run_id is not None:
            progress = await control.pattern_progress(control_run_id)
            alerts = await control.alerts(control_run_id)
            received = {u["unit_id"] for u in await control.received_units(control_run_id)}
    except ControlServiceUnavailable as exc:
        control_error = str(exc)
        control_run_id, progress, alerts, received = None, [], [], None
    topology = ((summary.get("summary") or {}).get("run_descriptor") or {}).get("topology")
    composed = compose_trace(
        detections=detections, dropped=dropped, progress=progress, alerts=alerts,
        received_unit_ids=received, control_run_id=control_run_id,
        topology=topology, control_error=control_error,
    )
    frames = composed.pop("frames")
    start = (page - 1) * page_size
    return {
        "media_run_id": run_id, **composed, "control_error": control_error,
        "page": page, "page_size": page_size, "total": len(frames),
        "frames": frames[start : start + page_size],
    }
```

Detalles obligatorios: importar las excepciones del control con alias (`from eovrt_webconsole.experiment.control_backend import ServiceUnavailable as ControlServiceUnavailable, UnknownRun as ControlUnknownRun`) — son clases DISTINTAS de las homónimas de `run_backend` (¡no mezclarlas!). `_fetch_all` es un helper local del router (loop de páginas con `page_size=1000` acumulando `items` hasta `total`). Las filas de alerts del control traen `frame_index` (confirmado en `control.alert.v1`, `contracts/alerts.py`). `ControlUnknownRun` en el lookup/lecturas se trata como "sin control run" (degradación), no como 404 del trace.

- [ ] **Step 4: PASS** — `tests/test_trace.py` + suite backend completa.
- [ ] **Step 5: Punto de corte (sin commit).**

---

### Task 4: SPA — api, tipos y `traceview.ts`

**Repo:** `webconsole/frontend/`
**Files:**
- Modify: `src/api.ts`, `src/types.ts`
- Create: `src/traceview.ts`
- Test: `src/__tests__/traceview.test.ts` (nuevo)

**Interfaces:**
- Produces: `getTrace(id, page, pageSize, controlRunId?)` → `request<TracePage>`; tipos `TraceFrame`/`TracePage` espejando el contrato del BFF; `traceview.ts`: `controlTone(control: string): BadgeTone`, `controlLabel(control: string): string`, `frameHasActivity(f: TraceFrame): boolean`.
- Consumes: patrón `request<T>` (api.ts:17-33), `BadgeTone` de `types.ts`.

- [ ] **Step 1: Tests que fallan** — `src/__tests__/traceview.test.ts` (lógica pura, sin render):

```ts
import { describe, expect, it } from 'vitest'
import { controlTone, controlLabel, frameHasActivity } from '../traceview'

describe('controlTone', () => {
  it('received ok, dropped warn, not_received error, n/d neutral', () => {
    expect(controlTone('received')).toBe('ok')
    expect(controlTone('dropped:rate_gate')).toBe('warn')
    expect(controlTone('dropped:queue_full')).toBe('warn')
    expect(controlTone('not_received')).toBe('error')
    expect(controlTone('n/d')).toBe('neutral')
  })
})

describe('controlLabel', () => {
  it('extrae el reason del dropped', () => {
    expect(controlLabel('dropped:rate_gate')).toBe('rate_gate')
    expect(controlLabel('received')).toBe('recibido')
    expect(controlLabel('not_received')).toBe('no recibido')
    expect(controlLabel('n/d')).toBe('n/d')
  })
})

describe('frameHasActivity', () => {
  const base = { frame_index: 0, unit_id: 'u0', timestamp_ms: null, detections: [], control: 'received', progress: [], alert: [] }
  it('sin nada es inactivo', () => expect(frameHasActivity(base as any)).toBe(false))
  it('deteccion, descarte, progreso o alerta activan', () => {
    expect(frameHasActivity({ ...base, detections: [{ label: 'p', confidence: 1 }] } as any)).toBe(true)
    expect(frameHasActivity({ ...base, control: 'dropped:rate_gate' } as any)).toBe(true)
    expect(frameHasActivity({ ...base, progress: [{ condition_id: 'CR-01', progress: 0.1 }] } as any)).toBe(true)
    expect(frameHasActivity({ ...base, alert: [{ condition_id: 'CR-01', severity: 'high' }] } as any)).toBe(true)
  })
})
```

- [ ] **Step 2: FAIL** → **Step 3: Implementar** (tipos espejo del contrato; `getTrace` con query params; `traceview.ts` puro importando `BadgeTone` de `./types`). `frameHasActivity`: detections no vacío || control empieza con `dropped:` || `not_received` || progress no vacío || alert no vacío.
- [ ] **Step 4: PASS** — `npx vitest run` completo, cero fallos nuevos.
- [ ] **Step 5: Punto de corte (sin commit).**

---

### Task 5: SPA — la sección en RunDetailPage

**Repo:** `webconsole/frontend/`
**Files:**
- Modify: `src/pages/RunDetailPage.tsx` (sección nueva entre la Card de Artefactos, cierra ~L182, y `EvalSection` ~L183), `src/styles/ui.css` (clase `.eo-progressbar`)
- Test: `src/__tests__/RunDetailPage.test.tsx` (append) o `src/__tests__/TraceSection.test.tsx` si se extrae componente

**Interfaces:**
- Consumes: `getTrace` + `traceview.ts` (Task 4); kit (`Card`, `Badge`, `StatTile`, `EmptyState`, `ErrorBanner`, `.eo-table`, `.eo-num`, `.eo-stats-row`); `artifactUrl` para previews.
- Produces: componente `TraceSection` (archivo propio `src/components/TraceSection.tsx` — RunDetailPage ya es la página más grande; extraer mantiene los archivos enfocados) montado con `{!running && <TraceSection runId={id} />}`.

- [ ] **Step 1: Tests que fallan** — sobre `TraceSection` con `getTrace` mockeado (patrón `vi.mock('../api', importOriginal)` del repo). Casos:
  1. trace con 3 frames (uno con detección+progreso 0.5, uno dropped, uno con alerta) → renderiza tiles (alertas=1, descartes rate_gate=1), la tabla con badges correctos (`eo-badge--ok`/`--warn`) y la barra con `width: 50%`.
  2. `control_run_id: null` + frames solo-media → muestra "no evaluado por el control-plane" (EmptyState) y la tabla sin columnas de control.
  3. `control_error` poblado → ErrorBanner visible, tabla presente.
  4. filtro "solo frames con actividad" (fireEvent.click en el checkbox) → la fila inactiva desaparece.
  5. paginación: botón "siguiente" dispara `getTrace(id, 2, ...)` (assert sobre el mock).
- [ ] **Step 2: FAIL** → **Step 3: Implementar.**
  - `.eo-progressbar` en `ui.css`: contenedor `height: 6px; background: var(--surface-sunken); border-radius: 999px; overflow: hidden` + hijo `.eo-progressbar__fill { height: 100%; background: var(--status-warn); }` y modificador `--alert { background: var(--status-error); }`. El ancho va inline por dato: `style={{ width: `${p.progress * 100}%` }}` (geometría por dato = excepción legítima, como los SVG).
  - `TraceSection`: estado `trace/page/error/soloActividad`; efecto de carga con guard `alive` (patrón del repo); tiles; tabla `.eo-table` con columnas del mock aprobado (preview vía `artifactUrl(runId, `previews/${unit_id}.preview.jpg`)` con `onError` que oculta, igual que la tabla de artefactos); badges con `controlTone`/`controlLabel`; barra por cada entrada de `progress`; badge `ALERTA` (tone error) por cada entrada de `alert`; checkbox del filtro aplicando `frameHasActivity`; paginación anterior/siguiente.
  - Nota two-node (spec §6): si `trace.topology === 'two_node'`, mostrar junto a los tiles un `<small>` con "descartes internos n/d en two-node" — el ledger no se escribe en esa topología (A2 §8) y un cero silencioso mentiría.
  - Montaje en `RunDetailPage`: `{!running && <TraceSection runId={id} />}` entre Artefactos y EvalSection.
- [ ] **Step 4: PASS** — suite vitest completa; `npx tsc --noEmit`; `npm run build`.
- [ ] **Step 5: Punto de corte (sin commit).**

---

### Task 6: Gate final + smoke real end-to-end

- [ ] **Step 1: Suites de los tres repos** — control-plane (cero fallos nuevos sobre baseline), BFF backend, SPA. Todos verdes.
- [ ] **Step 2: Smoke real DBE** (los servicios levantados: media :8080 mock, control :8081, BFF :8090):
  1. Disparar un run de medios con `stride>1` (mock, image_folder) → terminar.
  2. Disparar un replay del control sobre el `detections.jsonl` de ese run (config replay con `input.path` apuntando al artefacto; el `media_run_id` viaja en los eventos).
  3. `curl :8090/api/runs/<media_run_id>/trace` → verificar: `control_run_id` resuelto SIN pasarlo (lookup automático), frames intercalados procesado/descartado ordenados, `received` en los procesados, y si el pattern set aplica, progreso/alertas adjuntos.
  4. Abrir la consola y verificar la sección a ojo (tiles + tabla + filtro).
- [ ] **Step 3: No-regresión** — `git status` en los tres repos: solo los archivos declarados por este plan.
- [ ] **Step 4: Punto de corte (sin commit).**
