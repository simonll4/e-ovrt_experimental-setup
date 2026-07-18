# Visibilidad read-only de runs two-node en la consola — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que los runs two-node (EBE, `infra/twonode/`) aparezcan en la consola web con estado fiable (`running` → `succeeded`/`failed`), sin que la consola toque Docker.

**Architecture:** Tres fixes en `e-ovrt_media-plane` (finalización garantizada de `run_node_b`, disk-scan que reporta `running`+`live`, regla de ownership en la reconciliación de huérfanos) + propagación del campo en el BFF y badge/guarda WS en el frontend de `e-ovrt_experimental-setup/webconsole`. Spec: `docs/superpowers/specs/2026-07-06-webconsole-twonode-visibility-design.md` (en este repo).

**Tech Stack:** Python 3.11 (media-plane, venv en `.venv/`), FastAPI/httpx (BFF), React+Vite+TS/vitest (frontend).

## Global Constraints

- **NUNCA commitear**: regla del workspace — todo queda en working tree; el usuario commitea cuando lo pide explícitamente. Los pasos de este plan NO incluyen `git commit` a propósito.
- media-plane: correr tests/lint con `.venv/bin/python -m pytest -q` y `.venv/bin/python -m ruff check src tests` desde `/home/simonll4/projects/e-ovrt_media-plane`.
- webconsole backend: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && python -m pytest -q` (usar su venv si existe).
- webconsole frontend: `cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && npx vitest run`.
- Nombres exactos cross-task: campo **`live: bool`** (respuestas de `get()`/`list_runs()` del servicio), campo **`topology: str | None`** (filas del BFF), helpers frontend **`isLive()`** / **`topologyBadge()`**.

---

### Task 1: `run_node_b()` — finalización siempre completa (media-plane)

**Files:**
- Modify: `src/eovrt_media/runtime/two_node.py` (función `run_node_b`, líneas ~86-146, e imports)
- Test: `tests/test_two_node.py`

**Interfaces:**
- Produces: `summary.json` de cualquier run two-node siempre contiene `status: "succeeded"|"failed"` y `error: str|null`; `run_manifest.json` y `run_provenance.json` siempre presentes al salir del proceso. La excepción original se re-lanza tras escribir (así `tools/run_node.py` conserva su `SystemExit(1)`).

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_two_node.py` (agregar `import pytest` arriba si no está):

```python
def test_node_b_ante_fallo_escribe_summary_failed(tmp_path, monkeypatch):
    """Spec 2026-07-06 §3.1: un run two-node que falla debe dejar summary.json
    con status=failed + error, y manifest/provenance igual presentes."""
    images = tmp_path / "imgs"
    _images(images, 2)

    cfg = load_run_config(CONFIGS_DIR / "runs" / "mock.yaml")
    cfg.model.adapter = "mock"
    cfg.source.path = str(images)
    cfg.topology.mode = "two_node"
    cfg.transport.backend = "network"
    cfg.transport.endpoint = _loopback_endpoint()
    cfg.transport.heartbeat_endpoint = _loopback_endpoint()
    cfg.outputs.base_dir = str(tmp_path / "runs")
    cfg.outputs.run_dir = str(tmp_path / "runs")
    cfg.outputs.save_previews = False

    def _boom(*args, **kwargs):
        raise RuntimeError("Nodo A no respondió en 10000 ms")

    monkeypatch.setattr("eovrt_media.runtime.two_node.run_consumer_loop", _boom)

    with pytest.raises(RuntimeError, match="no respondió"):
        run_node_b(cfg)

    run_dirs = [d for d in (tmp_path / "runs").iterdir() if d.is_dir()]
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "summary.json").read_text())
    assert summary["status"] == "failed"
    assert "no respondió" in summary["error"]
    assert (run_dirs[0] / "run_manifest.json").exists()
    assert (run_dirs[0] / "run_provenance.json").exists()
```

También extender el test existente `test_two_node_loopback_produces_detections` con asserts del camino feliz (después del assert de `len(events) == 4`):

```python
    summary = json.loads((Path(cfg.outputs.base_dir) / run_id / "summary.json").read_text())
    assert summary["status"] == "succeeded"
    assert summary["error"] is None
```

- [ ] **Step 2: Verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_two_node.py -v`
Expected: `test_node_b_ante_fallo_escribe_summary_failed` FAIL (no existe `summary.json`: `FileNotFoundError` o assert de status); el loopback FAIL por `KeyError: 'status'`.

- [ ] **Step 3: Implementar**

En `src/eovrt_media/runtime/two_node.py`, agregar imports:

```python
import json
from pathlib import Path

from eovrt_media.sinks.jsonl_sink import atomic_write_json
```

Agregar helper a nivel módulo:

```python
def _finalize_summary_status(summary_path: Path, *, status: str, error: str | None) -> None:
    """Read-modify-write del summary, mismo patrón que RunManager._finalize():
    write_summary() no conoce status/error (son del ciclo de vida, no del pipeline)."""
    try:
        summary = json.loads(summary_path.read_text())
    except (OSError, json.JSONDecodeError):
        summary = {}
    summary["status"] = status
    summary["error"] = error
    atomic_write_json(summary_path, summary)
```

Reestructurar el final de `run_node_b()` — reemplazar desde el `try:` que envuelve `adapter.load()` hasta el `return`:

```python
    failure: Exception | None = None
    try:
        try:
            artifact_writer.write_debug_event(node="B", stage="model", event="model.load_start")
            adapter.load()
            artifact_writer.write_debug_event(node="B", stage="model", event="model.load_end")
            run_consumer_loop(
                transport,
                adapter,
                normalizer,
                artifact_writer,
                run_context,
                tracker,
                config,
                plan,
                prompt_set_id,
                timings={},
                progress=None,
                task=None,
                drain_errors=False,
            )
        finally:
            transport.shutdown()
            adapter.close()
            artifact_writer.close()
    except Exception as exc:  # noqa: BLE001 — el status failed captura la causa (como RunManager._execute)
        failure = exc

    run_context.gpu_memory_peak_mb = get_gpu_memory_peak_mb()
    run_context.finish()
    artifact_writer.write_summary(tracker)
    artifact_writer.write_provenance()
    artifact_writer.write_manifest()
    _finalize_summary_status(
        run_context.run_dir / "summary.json",
        status="failed" if failure is not None else "succeeded",
        error=str(failure) if failure is not None else None,
    )
    if failure is not None:
        raise failure
    return run_context.run_id
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_two_node.py tests/test_run_node_tool.py -v`
Expected: todo PASS (incluye `test_run_node_tool.py`: el `SystemExit(1)` ante fallo se preserva porque la excepción se re-lanza).

---

### Task 2: `RunManager.get()`/`list_runs()` — runs en curso visibles + campo `live` (media-plane)

**Files:**
- Modify: `src/eovrt_media/service/run_manager.py` (`get()` líneas ~148-175, `list_runs()` líneas ~177-218)
- Test: `tests/test_run_manager.py`

**Interfaces:**
- Produces: `get()` y `list_runs()` incluyen `"live": True` solo en el run activo en memoria; los runs detectados por disco llevan `"live": False`. Un directorio con `effective_config.yaml` y sin `summary.json` se reporta `status: "running"` (antes: omitido/`UnknownRunError`). Un directorio sin ninguno de los dos sigue siendo desconocido.
- Consumes: nada de Task 1 (independiente), pero su semántica "running = genuinamente en curso" depende de que Task 1 esté aplicada.

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_run_manager.py`:

```python
def test_run_externo_en_curso_es_visible_como_running(manager, tmp_path):
    """Spec 2026-07-06 §3.2: dir con effective_config.yaml y sin summary.json
    (p.ej. un run two-node en vuelo) se reporta running con live=False."""
    d = tmp_path / "runs" / "run_20260706_000000_ebe_mock_abc123"
    d.mkdir(parents=True)
    (d / "effective_config.yaml").write_text("topology:\n  mode: two_node\n")

    info = manager.get(d.name)
    assert info["status"] == "running"
    assert info["live"] is False

    listed = {r["run_id"]: r for r in manager.list_runs()}
    assert listed[d.name]["status"] == "running"
    assert listed[d.name]["live"] is False


def test_dir_sin_effective_config_sigue_siendo_desconocido(manager, tmp_path):
    d = tmp_path / "runs" / "run_basura"
    d.mkdir(parents=True)
    with pytest.raises(UnknownRunError):
        manager.get("run_basura")
    assert all(r["run_id"] != "run_basura" for r in manager.list_runs())


def test_live_true_solo_para_el_run_activo_propio(manager, tmp_path):
    run_id = manager.start_run(_request(_images(tmp_path)))
    assert manager.get(run_id)["live"] is True
    _wait_final(manager, run_id)
    assert manager.get(run_id)["live"] is False
```

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_run_manager.py -v -k "externo or basura or live_true"`
Expected: los 3 FAIL (`UnknownRunError` en el primero, `KeyError: 'live'` en el tercero; el segundo puede pasar ya — si pasa, dejarlo como regresión).

- [ ] **Step 3: Implementar**

En `get()`: agregar `"live": True` al dict del branch del run activo; agregar `"live": False` al dict del branch con summary; y entre ambos, reemplazar el `raise UnknownRunError` inmediato por:

```python
        summary_path = self._settings.runs_dir / run_id / "summary.json"
        if not summary_path.exists():
            # Sin summary pero con effective_config: run en curso de otro proceso
            # (p.ej. two-node) que comparte runs_dir — visible como running.
            if (self._settings.runs_dir / run_id / "effective_config.yaml").exists():
                return {
                    "run_id": run_id,
                    "status": "running",
                    "live": False,
                    **bench_metadata(self._settings.runs_dir / run_id),
                }
            raise UnknownRunError(run_id)
```

En `list_runs()`: agregar `"live": True` a la fila del activo y `"live": False` a las filas con summary; y donde hoy el loop hace `if summary_path.exists():` (y omite el resto), agregar la rama:

```python
                elif (d / "effective_config.yaml").exists():
                    runs.append(
                        {
                            "run_id": d.name,
                            "status": "running",
                            "live": False,
                            **bench_metadata(d),
                        }
                    )
```

- [ ] **Step 4: Verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_run_manager.py tests/test_service_events.py -v`
Expected: todo PASS. Nota: `routers/stream.py` NO se toca (spec §3.4: su degradación state+close ya es correcta); `DELETE` tampoco (el 409 sobre `running` externo es el comportamiento querido, spec §4).

---

### Task 3: `reconcile_orphan_runs()` — regla de ownership two-node (media-plane)

**Files:**
- Modify: `src/eovrt_media/service/retention.py` (función `reconcile_orphan_runs`, líneas ~50-97, e imports)
- Test: `tests/test_retention.py`

**Interfaces:**
- Produces: un dir huérfano cuyo `effective_config.yaml` declara `topology.mode: two_node` NO se estampa `interrupted` (se saltea). Huérfanos single-host o sin/`effective_config.yaml` ilegible: comportamiento actual intacto.
- Consumes: nada de tasks previas.

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_retention.py`, siguiendo la construcción de `settings` que ya usan los tests `test_reconcile_*` existentes en ese archivo (reusar su helper/fixture local; si construyen settings inline, copiar ese patrón):

```python
def test_reconcile_saltea_huerfano_two_node(tmp_path):
    """Spec 2026-07-06 §3.3: el servicio no es dueño de los runs two-node;
    un huérfano two-node puede estar vivo y no debe estamparse interrupted."""
    runs = tmp_path / "runs"
    d = runs / "run_ebe_huerfano"
    d.mkdir(parents=True)
    (d / "effective_config.yaml").write_text("topology:\n  mode: two_node\n")
    settings = _settings(tmp_path)  # <- usar el mismo helper/patrón de settings del archivo

    assert reconcile_orphan_runs(settings) == []
    assert not (d / "summary.json").exists()


def test_reconcile_sigue_marcando_huerfano_single_host(tmp_path):
    runs = tmp_path / "runs"
    d = runs / "run_dbe_huerfano"
    d.mkdir(parents=True)
    (d / "effective_config.yaml").write_text("topology:\n  mode: single_host\n")
    settings = _settings(tmp_path)

    assert reconcile_orphan_runs(settings) == ["run_dbe_huerfano"]
    assert json.loads((d / "summary.json").read_text())["status"] == "interrupted"
```

(Si el archivo no tiene helper `_settings`, construirlo igual que el fixture `manager` de `tests/test_run_manager.py`: `ServiceSettings.from_env({"EOVRT_MODEL_REF": "mock", "EOVRT_RUNS_DIR": str(tmp_path / "runs")})`.)

- [ ] **Step 2: Verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_retention.py -v`
Expected: `test_reconcile_saltea_huerfano_two_node` FAIL (reconcilia y devuelve el nombre); el single-host PASS ya (es el comportamiento actual — confirma que no rompemos nada).

- [ ] **Step 3: Implementar**

En `retention.py`, agregar `import yaml` a los imports y el helper:

```python
def _owned_by_two_node(run_dir: Path) -> bool:
    """effective_config.yaml con topology.mode: two_node ⇒ el dueño del run es
    un proceso run_node_b externo, no este servicio — puede estar vivo (spec
    2026-07-06 §3.3). Ilegible/ausente ⇒ False (se reconcilia como siempre)."""
    cfg_path = run_dir / "effective_config.yaml"
    if not cfg_path.exists():
        return False
    try:
        cfg = yaml.safe_load(cfg_path.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return False
    return (cfg.get("topology") or {}).get("mode") == "two_node"
```

En el loop de `reconcile_orphan_runs()`, después del `if summary_path.exists(): continue`:

```python
        if _owned_by_two_node(d):
            logger.info("Run huérfano %s pertenece a two-node: no se reconcilia", d.name)
            continue
```

- [ ] **Step 4: Verificar que pasa + suite completa del repo**

Run: `.venv/bin/python -m pytest -q && .venv/bin/python -m ruff check src tests`
Expected: suite completa verde (428 + los nuevos), lint limpio. **NO commitear.**

---

### Task 4: BFF — propagar `live` y `topology` en las filas (webconsole backend)

**Files:**
- Modify: `webconsole/backend/src/eovrt_webconsole/routers/runs.py` (`_row()` líneas ~21-36 y las filas fallback de `list_runs()`)
- Modify: `webconsole/backend/tests/fake_service.py` (shapes de `list_runs`/`status`)
- Test: `webconsole/backend/tests/test_runs_router.py`

**Interfaces:**
- Consumes: campo `live: bool` de las respuestas del servicio (Task 2). `GET /api/runs/{id}` del BFF ya proxya la respuesta del servicio verbatim (`backend.status()`), así que `live` llega al detalle sin cambios.
- Produces: filas de `GET /api/runs` del BFF con `live: bool` y `topology: str | None` (de `summary.run_descriptor.topology`).

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_runs_router.py`, siguiendo el patrón de los tests existentes del listado (usan el fake service de `fake_service.py`):

```python
def test_listado_incluye_live_y_topology(client):
    rows = client.get("/api/runs").json()
    by_id = {r["run_id"]: r for r in rows}
    # el fake declara un run terminado con run_descriptor two_node (Step 3)
    assert by_id["run_done_1"]["live"] is False
    assert by_id["run_done_1"]["topology"] == "two_node"
```

(Adaptar el nombre del fixture `client` al que ya usa ese archivo.)

- [ ] **Step 2: Verificar que falla**

Run: `cd webconsole/backend && python -m pytest tests/test_runs_router.py -v`
Expected: FAIL con `KeyError: 'live'`.

- [ ] **Step 3: Implementar**

1. `fake_service.py`: en `SUMMARY_FINISHED` agregar `"run_descriptor": {"topology": "two_node"}`; en las respuestas de `list_runs()`/`status()` agregar `"live": True` para el run activo del fake y `"live": False` para los terminados (espejo del shape real de Task 2).
2. `routers/runs.py` — `_row()`: agregar dos claves:

```python
        "live": info.get("live", False),
        "topology": (summary.get("run_descriptor") or {}).get("topology"),
```

3. Las dos filas fallback de `list_runs()` (except y cola post-hydration-limit): agregar `"live": item.get("live", False)` (sin `topology`: no hay summary ahí).

- [ ] **Step 4: Verificar que pasa**

Run: `cd webconsole/backend && python -m pytest -q`
Expected: suite backend completa verde.

---

### Task 5: Frontend — helpers, badge de topología y guarda del WS (webconsole frontend)

**Files:**
- Create: `webconsole/frontend/src/runview.ts`
- Modify: `webconsole/frontend/src/types.ts` (interfaces `RunRow`, `RunDetail`)
- Modify: `webconsole/frontend/src/pages/RunDetailPage.tsx`
- Modify: `webconsole/frontend/src/pages/RunsPage.tsx`
- Test: `webconsole/frontend/src/__tests__/runview.test.ts`

**Interfaces:**
- Consumes: `live` y `topology` de las filas del BFF (Task 4); `live` en el detalle (proxy verbatim).
- Produces: `isLive(run)` y `topologyBadge(summary)` en `runview.ts`.

- [ ] **Step 1: Escribir los tests que fallan**

`webconsole/frontend/src/__tests__/runview.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import { isLive, topologyBadge } from '../runview'

describe('isLive', () => {
  it('true solo cuando running y live', () => {
    expect(isLive({ status: 'running', live: true })).toBe(true)
  })
  it('false para running externo (two-node): evita el reconnect-loop del WS', () => {
    expect(isLive({ status: 'running', live: false })).toBe(false)
    expect(isLive({ status: 'running' })).toBe(false) // live ausente = servicio viejo
  })
  it('false cuando no está running', () => {
    expect(isLive({ status: 'succeeded', live: true })).toBe(false)
  })
})

describe('topologyBadge', () => {
  it('two_node → two-node', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'two_node' } })).toBe('two-node')
  })
  it('single_host → single-host', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'single_host' } })).toBe('single-host')
  })
  it('sin descriptor → null', () => {
    expect(topologyBadge({})).toBeNull()
    expect(topologyBadge(undefined)).toBeNull()
  })
})
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runview.test.ts`
Expected: FAIL (módulo `../runview` no existe).

- [ ] **Step 3: Implementar helpers y tipos**

`webconsole/frontend/src/runview.ts`:

```typescript
export function isLive(run: { status: string; live?: boolean }): boolean {
  // live=true solo lo emite el servicio para SU run activo en memoria — el único
  // suscribible por WS. Un running externo (two-node) con WS abierto entra en
  // reconnect-loop infinito (spec 2026-07-06 §3.4).
  return run.status === 'running' && run.live === true
}

export function topologyBadge(summary: Record<string, unknown> | undefined): string | null {
  const desc = summary?.run_descriptor as Record<string, unknown> | undefined
  const topo = desc?.topology
  if (topo === 'two_node') return 'two-node'
  if (topo === 'single_host') return 'single-host'
  return null
}
```

`types.ts`: agregar `live?: boolean` y `topology?: string | null` a `RunRow`; agregar `live?: boolean` a `RunDetail`.

- [ ] **Step 4: Verificar que los tests de helpers pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runview.test.ts`
Expected: PASS.

- [ ] **Step 5: Cablear las páginas**

`RunDetailPage.tsx`:
1. `import { isLive, topologyBadge } from '../runview'`
2. Reemplazar `const live = useRunStream(id, Boolean(running))` por:

```typescript
  const streamable = Boolean(run && isLive(run))
  const live = useRunStream(id, streamable)
```

3. El botón `■ Detener` y la sección de telemetría en vivo: condicionarlos a `streamable` en vez de `running` (el stop de un run externo daría 404 — es read-only por spec §6).
4. Polling para runs externos en curso (sin WS no hay `finalState` que dispare `refresh()` — sin esto la página queda clavada en running): agregar después del useEffect de `live.finalState`:

```typescript
  // Run externo (two-node) en curso: sin WS, el estado se re-hidrata por polling.
  useEffect(() => {
    if (!running || streamable) return
    const timer = setInterval(refresh, 4000)
    return () => clearInterval(timer)
  }, [running, streamable])
```

5. Badge en el `<h2>` junto al status:

```typescript
  {topologyBadge(summary) && (
    <span style={{ fontSize: 14, background: '#eef', borderRadius: 4, padding: '2px 8px' }}>
      {topologyBadge(summary)}
    </span>
  )}
```

`RunsPage.tsx`: en la celda de estado, mostrar el badge cuando la fila lo trae:

```typescript
  <td style={CELL}>
    {r.status === 'running' ? '🟢 running' : r.status}
    {r.topology === 'two_node' ? ' · two-node' : ''}
  </td>
```

- [ ] **Step 6: Verificar suite frontend completa + build**

Run: `cd webconsole/frontend && npx vitest run && npx tsc --noEmit`
Expected: vitest verde, sin errores de tipos.

---

### Task 6: Smoke manual E2E (criterio de aceptación)

**Files:** ninguno (verificación operativa; requiere Docker activo y las imágenes de `infra/twonode/` ya construidas — verificadas 2026-07-06).

**Nota previa:** las imágenes Docker del fleet y de twonode contienen el código de media-plane **al momento del build** — para que este smoke ejercite los fixes de Tasks 1-3 hay que rebuildar: `cd /home/simonll4/projects/e-ovrt_media-plane/infra/twonode && docker compose build` (y rebuild del servicio del fleet si el smoke usa la plataforma completa).

- [ ] **Step 1: Consola + servicio arriba** — levantar la plataforma (`e-ovrt_experimental-setup/infra/platform/`) o el BFF local apuntando a un servicio mock, según lo que esté disponible.
- [ ] **Step 2: Run two-node feliz** — `cd e-ovrt_media-plane/infra/twonode && docker compose up --abort-on-container-exit`. En la consola: el run aparece `🟢 running · (sin badge aún)` durante la corrida, y al terminar pasa a `succeeded` con badge `two-node`, sin telemetría en vivo y sin loop de reconexión WS (verificar en la pestaña Network del browser que NO hay conexiones WS repetidas).
- [ ] **Step 3: Run two-node fallido** — subir `max_units` a 200 en ambas configs de `infra/twonode/configs/`, `docker compose up -d`, `docker compose kill -s SIGKILL node-a`. En la consola: el run pasa de `running` a `failed` en ~15s con `error` con el mensaje de timeout. Restaurar `max_units: 20`.
- [ ] **Step 4: Reconciliación no interfiere** — con un run two-node en curso (max_units 200 de nuevo, sin kill), reiniciar el contenedor del servicio del fleet (`docker compose restart <instancia>` en infra/platform). El run two-node NO debe aparecer `interrupted`; debe terminar `succeeded`. Restaurar configs.
- [ ] **Step 5: Registrar el resultado** — anotar el resultado del smoke en la sección "Ejecutado y verificado" de `infra/twonode/README.md` (media-plane) con fecha. **NO commitear** (ni en media-plane ni en experimental-setup); avisar al usuario que ambos working trees quedan listos para su revisión/commit.

---

## Self-review (hecho al escribir el plan)

- **Cobertura del spec**: §3.1→Task 1; §3.2 (running + live)→Task 2; §3.3 (ownership reconcile)→Task 3; §3.4 (badge + guarda WS)→Tasks 4-5; §5 testing→tests TDD de cada task + smoke Task 6 (incluye el caso nuevo de reconciliación en Step 4); §4/§6 (límites y exclusiones) no requieren código — verificado que stream.py, DELETE y stop no se tocan.
- **Consistencia de tipos**: `live` (bool) mismo nombre servicio→BFF→frontend; `topology` solo BFF→frontend (el servicio lo emite dentro de `summary.run_descriptor`); `isLive`/`topologyBadge` definidos en Task 5 Step 3 y usados en Step 5.
- **Placeholders**: el único punto delegado es el helper `_settings` de `test_retention.py` (Task 3) y el fixture `client` de `test_runs_router.py` (Task 4) — ambos con instrucción explícita de qué patrón existente copiar y un fallback concreto. No hay TBDs.
- **Riesgo conocido**: los conteos de tests esperados no se fijan (la suite media-plane era 428 al escribir esto); el invariante es "suite completa verde".
