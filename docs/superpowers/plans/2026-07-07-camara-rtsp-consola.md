# Cámara RTSP desde la consola — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Habilitar en la consola web la ingesta desde una cámara RTSP (URL única), retirando el candado "MVP" que hoy la bloquea, con credenciales redactadas al persistir manifiestos.

**Architecture:** Cambios sólo en `webconsole/` (BFF FastAPI + SPA React). El media-plane ya soporta rtsp; no se toca. Se renombra el concepto `MVP_PLUGINS → SUPPORTED_PLUGINS` (campo de API `mvp_enabled → enabled`), se suma `rtsp` de forma permanente, se agrega validación de URL en el BFF, un campo de URL en el formulario, y redacción de credenciales en el camino de guardado (no en el de lanzamiento).

**Tech Stack:** Python 3.14 + FastAPI + pytest (backend `webconsole/backend/`), React 18 + TypeScript + Vite + Vitest (frontend `webconsole/frontend/`).

## Global Constraints

- **Política de commits del repo:** NUNCA commitear salvo que el usuario lo pida explícitamente en el turno. Cada tarea termina en verificación verde; el `git commit` lo hace el usuario. No agregar `Co-Authored-By`.
- **Rutas:** todas relativas a `e-ovrt_experimental-setup/webconsole/`. Correr los comandos desde ahí.
- **Comandos de test:**
  - Backend: `cd backend && .venv/bin/python -m pytest -q` (una sola: `... -q tests/test_x.py`)
  - Lint backend: `cd backend && .venv/bin/ruff check src tests`
  - Frontend: `cd frontend && npx vitest run` (uno: `... run src/__tests__/ComposePage.test.tsx`)
  - Todo junto: `make test` (desde la raíz del repo).
- **RTSP permanente, sin flag.** `oak_d` sigue fuera (hardware no disponible).
- **Separación de caminos:** `composition_to_run_request` manda la URL **real**; `composition_to_manifest` la escribe **redactada** (`rtsp://***:***@...`). Nunca cruzar estos dos.
- **Spec:** `docs/superpowers/specs/2026-07-07-camara-rtsp-consola-design.md`.

---

### Task 1: Backend — retirar "MVP", habilitar rtsp y validar su URL

**Files:**
- Modify: `backend/src/eovrt_webconsole/settings.py` (líneas 9-12, 33)
- Modify: `backend/src/eovrt_webconsole/routers/compose.py` (líneas 19-24, 39-50)
- Modify: `backend/src/eovrt_webconsole/routers/catalog.py` (líneas 37-42)
- Modify: `backend/src/eovrt_webconsole/__init__.py` (línea 1)
- Test: `backend/tests/test_settings.py` (línea 18)
- Test: `backend/tests/test_catalog_proxy.py` (todo `test_ingest_plugins_con_policy_mvp`)
- Test: `backend/tests/test_compose.py` (`test_plugin_fuera_del_mvp` + casos rtsp nuevos)

**Interfaces:**
- Consumes: nada de tareas previas.
- Produces:
  - `ConsoleSettings.supported_plugins: frozenset[str]` (default `SUPPORTED_PLUGINS = {"image_folder","video_file","rtsp"}`), reemplaza `mvp_plugins`/`MVP_PLUGINS`.
  - Campo de salida de `GET /api/catalog/ingest-plugins`: `enabled: bool` (reemplaza `mvp_enabled`).
  - `validate_composition`: para `plugin == "rtsp"` valida `config.url` (requerido, prefijo `rtsp://`), error en campo `ingest.config.url`.

- [ ] **Step 1: Actualizar tests de settings y catálogo (fallan primero)**

En `backend/tests/test_settings.py`, línea 18, reemplazar:

```python
    assert s.mvp_plugins == frozenset({"image_folder", "video_file"})
```

por:

```python
    assert s.supported_plugins == frozenset({"image_folder", "video_file", "rtsp"})
```

En `backend/tests/test_catalog_proxy.py`, reemplazar `test_ingest_plugins_con_policy_mvp` completo por:

```python
def test_ingest_plugins_con_policy_soporte(client):
    plugins = {p["id"]: p for p in client.get("/api/catalog/ingest-plugins").json()}
    assert set(plugins) == {"image_folder", "video_file", "rtsp", "oak_d"}
    assert plugins["image_folder"]["enabled"] is True
    assert plugins["video_file"]["enabled"] is True
    # rtsp: fuente viva soportada de forma permanente por la consola
    assert plugins["rtsp"]["available"] is True
    assert plugins["rtsp"]["enabled"] is True
    # oak_d: available=False en el servicio (sin hardware) -> no soportado
    assert plugins["oak_d"]["enabled"] is False
```

- [ ] **Step 2: Actualizar/agregar tests de compose (fallan primero)**

En `backend/tests/test_compose.py`, reemplazar `test_plugin_fuera_del_mvp` (líneas 17-20) por estos tests:

```python
def test_plugin_no_soportado(client):
    # oak_d no está soportado por la consola (available=False en el servicio).
    r = client.post("/api/compose/validate", json=_body(ingest={"plugin": "oak_d", "config": {}}))
    errors = r.json()["errors"]
    assert any(e["field"] == "ingest.plugin" for e in errors)


def test_rtsp_sin_url(client):
    r = client.post("/api/compose/validate", json=_body(ingest={"plugin": "rtsp", "config": {}}))
    errors = r.json()["errors"]
    assert any(e["field"] == "ingest.config.url" for e in errors)


def test_rtsp_url_con_prefijo_invalido(client):
    body = _body(ingest={"plugin": "rtsp", "config": {"url": "http://cam/stream"}})
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert any(e["field"] == "ingest.config.url" for e in errors)


def test_rtsp_url_valida(client):
    body = _body(ingest={"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}})
    errors = client.post("/api/compose/validate", json=body).json()["errors"]
    assert not any(e["field"].startswith("ingest.config") for e in errors)
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `cd backend && .venv/bin/python -m pytest tests/test_settings.py tests/test_catalog_proxy.py tests/test_compose.py -q`
Expected: FAIL (AttributeError `supported_plugins` / KeyError `enabled` / los casos rtsp no encuentran `ingest.config.url`).

- [ ] **Step 4: Renombrar en `settings.py` y sumar rtsp**

Reemplazar líneas 9-12:

```python
DEFAULT_FROZEN_SETS = frozenset({"cr01_cr02_bench_v2"})
# Policy MVP (Spec B §6): RTSP/oak_d quedan fuera por decisión de la consola,
# no del catálogo del servicio (que marca rtsp como disponible).
MVP_PLUGINS = frozenset({"image_folder", "video_file"})
```

por:

```python
DEFAULT_FROZEN_SETS = frozenset({"cr01_cr02_bench_v2"})
# Fuentes de ingesta que la consola sabe lanzar (decisión 2026-07-07: rtsp queda
# habilitado de forma permanente; supersede la restricción "MVP" de
# 2026-07-01-webconsole-design.md §6). oak_d queda fuera hasta tener hardware
# (el servicio lo marca available=False).
SUPPORTED_PLUGINS = frozenset({"image_folder", "video_file", "rtsp"})
```

Reemplazar línea 33 (dentro del dataclass):

```python
    mvp_plugins: frozenset[str] = MVP_PLUGINS
```

por:

```python
    supported_plugins: frozenset[str] = SUPPORTED_PLUGINS
```

- [ ] **Step 5: Renombrar en `catalog.py`**

Reemplazar líneas 37-42:

```python
    # mvp_enabled es policy de la CONSOLA (Spec B §6): el catálogo del servicio marca
    # rtsp como disponible, pero el MVP solo lanza fuentes acotadas.
    return [
        {**p, "mvp_enabled": p["id"] in settings.mvp_plugins and p.get("available", False)}
        for p in plugins
    ]
```

por:

```python
    # `enabled` es policy de la CONSOLA: un plugin se ofrece si está soportado por la
    # consola Y disponible en el servicio (decisión 2026-07-07, rtsp habilitado).
    return [
        {**p, "enabled": p["id"] in settings.supported_plugins and p.get("available", False)}
        for p in plugins
    ]
```

- [ ] **Step 6: Renombrar el gate y agregar validación rtsp en `compose.py`**

Reemplazar líneas 19-24:

```python
    if comp.ingest.plugin not in settings.mvp_plugins:
        errors.append({
            "field": "ingest.plugin",
            "message": f"Plugin '{comp.ingest.plugin}' fuera del MVP "
                       f"(permitidos: {sorted(settings.mvp_plugins)})",
        })
```

por:

```python
    if comp.ingest.plugin not in settings.supported_plugins:
        errors.append({
            "field": "ingest.plugin",
            "message": f"Plugin '{comp.ingest.plugin}' no soportado por la consola "
                       f"(soportados: {sorted(settings.supported_plugins)})",
        })
```

Reemplazar el bloque de validación de fuente (líneas 39-50):

```python
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
```

por:

```python
    if comp.ingest.plugin == "rtsp":
        url = comp.ingest.config.get("url")
        if not url:
            errors.append({"field": "ingest.config.url",
                           "message": "Se requiere 'url' de la cámara (rtsp://...)"})
        elif not str(url).startswith("rtsp://"):
            errors.append({"field": "ingest.config.url",
                           "message": "La URL debe empezar con 'rtsp://'"})
    else:
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
```

- [ ] **Step 7: Actualizar docstring de `__init__.py`**

Reemplazar línea 1:

```python
"""BFF de la consola web E-OVRT (Spec B, MVP) — cliente del servicio media-plane."""
```

por:

```python
"""BFF de la consola web E-OVRT (Spec B) — cliente del servicio media-plane."""
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `cd backend && .venv/bin/python -m pytest tests/test_settings.py tests/test_catalog_proxy.py tests/test_compose.py -q`
Expected: PASS.

- [ ] **Step 9: Verificación de la tarea (suite + lint)**

Run: `cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: PASS + sin errores de ruff. (No commitear; marcar la tarea hecha para revisión.)

---

### Task 2: Backend — round-trip rtsp y redacción de credenciales al guardar

**Files:**
- Modify: `backend/src/eovrt_webconsole/translation.py` (líneas 8-19, 92, 119-153)
- Test: `backend/tests/test_translation.py` (tests nuevos)
- Test: `backend/tests/test_manifest_writer.py` (`test_endpoint_plugin_no_soportado_422`, líneas 137-151)

**Interfaces:**
- Consumes: `SUPPORTED_PLUGINS` de Task 1 (no directamente; independiente).
- Produces:
  - `_SOURCE_TYPE_TO_PLUGIN` y `_PLUGIN_TO_SOURCE_TYPE` incluyen `"rtsp": "rtsp"`.
  - `_redact_rtsp_credentials(url: str) -> str` en `translation.py`.
  - `composition_to_manifest`: para `source.type == "rtsp"`, la `url` sale redactada.
  - `composition_to_run_request`: sin cambios (URL real).

- [ ] **Step 1: Escribir los tests de traducción rtsp (fallan primero)**

Agregar al final de `backend/tests/test_translation.py`:

```python
def test_run_request_rtsp_lleva_url_real(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}})
    raw = composition_to_run_request(comp, repo / "prompts")
    assert raw["ingest"] == {"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}}


def test_manifest_rtsp_redacta_credenciales(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://u:p@10.0.0.5:554/s"}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["type"] == "rtsp"
    assert manifest["source"]["url"] == "rtsp://***:***@10.0.0.5:554/s"


def test_manifest_rtsp_sin_credenciales_no_cambia(repo):
    comp = _composition(ingest={"plugin": "rtsp", "config": {"url": "rtsp://10.0.0.5:554/s"}})
    manifest = composition_to_manifest(comp, target_model_ref="t/t")
    assert manifest["source"]["url"] == "rtsp://10.0.0.5:554/s"


def test_round_trip_manifiesto_rtsp_redactado():
    manifest = {
        "run": {"scenario": "DBE"},
        "source": {"type": "rtsp", "url": "rtsp://***:***@10.0.0.5:554/s"},
        "prompts": {"ref": "frozen_set"},
        "model": {"ref": "yoloe/yoloe-26l"},
    }
    comp = manifest_to_composition(manifest)
    assert comp.ingest.plugin == "rtsp"
    assert comp.ingest.config == {"url": "rtsp://***:***@10.0.0.5:554/s"}
    regenerated = composition_to_manifest(comp, target_model_ref="ignored/target")
    assert regenerated["source"]["type"] == "rtsp"
    assert regenerated["source"]["url"] == "rtsp://***:***@10.0.0.5:554/s"
```

- [ ] **Step 2: Migrar el test de "plugin no soportado al guardar" a oak_d (falla primero)**

En `backend/tests/test_manifest_writer.py`, reemplazar `test_endpoint_plugin_no_soportado_422` (líneas 137-151) por:

```python
def test_endpoint_plugin_no_soportado_422(client):
    # Schema-válido (Composition acepta cualquier str en ingest.plugin) pero sin mapeo
    # en _PLUGIN_TO_SOURCE_TYPE y sin "dataset" (no toma el camino source.ref): antes
    # del fix, composition_to_manifest hacía un KeyError sin capturar -> 500. Debe dar
    # 422, no 500. (rtsp ya está soportado; usamos oak_d, que sigue fuera del mapeo.)
    body = {
        "name": "oak_d_no_soportado",
        "composition": {
            "ingest": {"plugin": "oak_d", "config": {}},
            "prompts": {"set_id": "demo_set", "active_ids": None},
        },
    }
    r = client.post("/api/manifests", json=body)
    assert r.status_code == 422
    assert r.status_code != 500
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `cd backend && .venv/bin/python -m pytest tests/test_translation.py tests/test_manifest_writer.py -q`
Expected: FAIL (rtsp aún no mapea; `oak_d` con config vacía todavía no está garantizado; no existe la redacción).

- [ ] **Step 4: Agregar mapeos rtsp y el helper de redacción en `translation.py`**

Reemplazar líneas 8-19:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eovrt_webconsole.repo_catalog import get_prompt_set

_SOURCE_TYPE_TO_PLUGIN = {"image_folder": "image_folder", "video_file": "video_file",
                          "video": "video_file", "video_frame": "video_file"}
_PLUGIN_TO_SOURCE_TYPE = {"image_folder": "image_folder", "video_file": "video_file"}
```

por:

```python
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eovrt_webconsole.repo_catalog import get_prompt_set

_SOURCE_TYPE_TO_PLUGIN = {"image_folder": "image_folder", "video_file": "video_file",
                          "video": "video_file", "video_frame": "video_file",
                          "rtsp": "rtsp"}
_PLUGIN_TO_SOURCE_TYPE = {"image_folder": "image_folder", "video_file": "video_file",
                          "rtsp": "rtsp"}

# user[:pass] entre "rtsp://" y el primer "/" (o fin de host). Redacta el userinfo
# para no escribir credenciales a disco al guardar un manifiesto.
_RTSP_USERINFO = re.compile(r"(rtsp://)[^/@]+@")


def _redact_rtsp_credentials(url: str) -> str:
    return _RTSP_USERINFO.sub(r"\1***:***@", url)
```

- [ ] **Step 5: Redactar la url en `composition_to_manifest`**

En `composition_to_manifest`, reemplazar el bloque que arma `source` para el camino sin dataset (líneas 129-138):

```python
    else:
        # Preferir el source.type original (round-trip sin pérdida); si la
        # composición viene del formulario (sin source_type), derivarlo del plugin.
        plugin_type = comp.ingest.source_type or _PLUGIN_TO_SOURCE_TYPE.get(comp.ingest.plugin)
        if plugin_type is None:
            raise ValueError(
                f"Plugin no soportado para guardar manifiesto: {comp.ingest.plugin!r} "
                f"(soportados: {sorted(_PLUGIN_TO_SOURCE_TYPE)})"
            )
        source = {"type": plugin_type, **{k: v for k, v in comp.ingest.config.items()}}
```

por:

```python
    else:
        # Preferir el source.type original (round-trip sin pérdida); si la
        # composición viene del formulario (sin source_type), derivarlo del plugin.
        plugin_type = comp.ingest.source_type or _PLUGIN_TO_SOURCE_TYPE.get(comp.ingest.plugin)
        if plugin_type is None:
            raise ValueError(
                f"Plugin no soportado para guardar manifiesto: {comp.ingest.plugin!r} "
                f"(soportados: {sorted(_PLUGIN_TO_SOURCE_TYPE)})"
            )
        source = {"type": plugin_type, **{k: v for k, v in comp.ingest.config.items()}}
        # Nunca escribir credenciales de cámara a disco: el run activo usa la url real
        # (composition_to_run_request), el manifiesto guardado va redactado.
        if plugin_type == "rtsp" and isinstance(source.get("url"), str):
            source["url"] = _redact_rtsp_credentials(source["url"])
```

- [ ] **Step 6: Actualizar el mensaje de error de `manifest_to_composition`**

Reemplazar línea 92:

```python
            raise ValueError(f"source.type fuera del MVP: {source_type!r}")
```

por:

```python
            raise ValueError(f"source.type no soportado: {source_type!r}")
```

- [ ] **Step 7: Correr los tests y verificar que pasan**

Run: `cd backend && .venv/bin/python -m pytest tests/test_translation.py tests/test_manifest_writer.py -q`
Expected: PASS.

- [ ] **Step 8: Verificación de la tarea (suite + lint)**

Run: `cd backend && .venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: PASS + sin errores de ruff.

---

### Task 3: Frontend — campo URL RTSP en el formulario y rename `enabled`

**Files:**
- Modify: `frontend/src/types.ts` (línea 38)
- Modify: `frontend/src/pages/ComposePage.tsx` (estado, prefill, composición, render de fuente y dropdown)
- Modify: `frontend/src/pages/CatalogPage.tsx` (línea 50)
- Test: `frontend/src/__tests__/ComposePage.test.tsx` (fixtures + test nuevo)

**Interfaces:**
- Consumes: campo de API `enabled` (Task 1); `config: { url }` para rtsp (Task 1/2).
- Produces: composición del formulario con `ingest.plugin === "rtsp"` y `ingest.config === { url }`.

- [ ] **Step 1: Escribir el test de selección rtsp (falla primero)**

En `frontend/src/__tests__/ComposePage.test.tsx`:

(a) En el mock de `getIngestPlugins` (líneas 17-19), renombrar `mvp_enabled → enabled` y agregar rtsp:

```javascript
  getIngestPlugins: vi.fn(async () => [
    { id: 'image_folder', kind: 'bounded', available: true, description: '', enabled: true },
    { id: 'rtsp', kind: 'live', available: true, description: '', enabled: true },
  ]),
```

(b) Agregar un nuevo `describe` al final del archivo:

```javascript
describe('ComposePage fuente RTSP', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('al elegir rtsp muestra el campo URL y arma config { url }', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Esperar a que carguen los plugins (aparece el <select> de plugin poblado).
    const pluginSelect = await screen.findByLabelText<HTMLSelectElement>(/Plugin de ingesta/i)
    fireEvent.change(pluginSelect, { target: { value: 'rtsp' } })

    const urlInput = await screen.findByPlaceholderText<HTMLInputElement>(/^rtsp:\/\//)
    fireEvent.change(urlInput, { target: { value: 'rtsp://u:p@10.0.0.5:554/s' } })

    // Elegir prompt set para no bloquear el lanzamiento por campos ajenos.
    const setSelect = await screen.findByLabelText<HTMLSelectElement>(/Prompt set/i)
    fireEvent.change(setSelect, { target: { value: 'demo_set' } })

    fireEvent.click(screen.getByText('Lanzar'))

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('rtsp')
    expect(comp.ingest.config).toEqual({ url: 'rtsp://u:p@10.0.0.5:554/s' })
  })
})
```

> Nota: los `<label>` de `ComposePage` no están asociados por `htmlFor`; `findByLabelText` funciona porque el `<select>`/`<input>` es hijo del contenedor con el `<label>`. Si la query por label fallara por el layout, usar `screen.findByRole('combobox')` ordenados por aparición. Verificar al correr el test.

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd frontend && npx vitest run src/__tests__/ComposePage.test.tsx`
Expected: FAIL (no existe el campo URL; `enabled` no lo lee el componente todavía).

- [ ] **Step 3: Renombrar el tipo en `types.ts`**

Reemplazar línea 38:

```typescript
  mvp_enabled: boolean
```

por:

```typescript
  enabled: boolean
```

- [ ] **Step 4: Agregar estado `rtspUrl` en `ComposePage.tsx`**

Después de la línea 29 (`const [path, setPath] = useState('')`), agregar:

```typescript
  const [rtspUrl, setRtspUrl] = useState('')
```

- [ ] **Step 5: Prefill de rtsp desde manifiesto**

En el efecto de prefill, dentro de la rama `else if (source.type)` (líneas 88-92), reemplazar:

```typescript
    } else if (source.type) {
      setPlugin(source.type.includes('video') ? 'video_file' : source.type)
      setPath(source.path ?? '')
      setSourceType(source.type) // preserva el string exacto para el round-trip
    }
```

por:

```typescript
    } else if (source.type) {
      setPlugin(source.type.includes('video') ? 'video_file' : source.type)
      setPath(source.path ?? '')
      setRtspUrl(source.type === 'rtsp' ? (source.url ?? '') : '')
      setSourceType(source.type) // preserva el string exacto para el round-trip
    }
```

- [ ] **Step 6: Armar `config` de rtsp en `composition()`**

Reemplazar el objeto `ingest` de `composition()` (líneas 102-107):

```typescript
    ingest: {
      plugin,
      config: dataset ? { dataset } : path ? { path } : {},
      // Solo relevante para fuentes por `path` (video); en dataset ref queda null.
      source_type: dataset ? null : sourceType,
    },
```

por:

```typescript
    ingest: {
      plugin,
      config:
        plugin === 'rtsp'
          ? (rtspUrl ? { url: rtspUrl } : {})
          : dataset ? { dataset } : path ? { path } : {},
      // Solo relevante para fuentes por `path` (video); rtsp deriva el type en el BFF.
      source_type: plugin === 'rtsp' ? null : dataset ? null : sourceType,
    },
```

- [ ] **Step 7: Dropdown de plugin — leer `enabled` y texto "(no soportado)"**

Reemplazar líneas 168-172:

```typescript
          {plugins.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.mvp_enabled}>
              {p.id}{!p.mvp_enabled ? ' (no disponible en MVP)' : ''}
            </option>
          ))}
```

por:

```typescript
          {plugins.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.enabled}>
              {p.id}{!p.enabled ? ' (no soportado)' : ''}
            </option>
          ))}
```

- [ ] **Step 8: Render condicional de la fuente (URL rtsp vs dataset/path)**

Reemplazar el bloque completo de la fila de fuente (líneas 176-194):

```typescript
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
```

por:

```typescript
      {plugin === 'rtsp' ? (
        <div style={ROW}>
          <label>URL RTSP de la cámara</label>
          <input placeholder="rtsp://usuario:clave@192.168.1.50:554/stream1" value={rtspUrl}
                 onChange={(e) => setRtspUrl(e.target.value)} />
          <FieldMsg errors={errors} field="ingest.config.url" />
          {rtspUrl.includes('***') && (
            <small style={{ color: '#c80' }}>Recompletá las credenciales antes de lanzar.</small>
          )}
        </div>
      ) : (
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
      )}
```

- [ ] **Step 9: Renombrar en `CatalogPage.tsx`**

Reemplazar línea 50:

```typescript
              {p.available && !p.mvp_enabled && <em>[fuera del MVP]</em>}
```

por:

```typescript
              {p.available && !p.enabled && <em>[no soportado]</em>}
```

- [ ] **Step 10: Correr el test y verificar que pasa**

Run: `cd frontend && npx vitest run src/__tests__/ComposePage.test.tsx`
Expected: PASS.

- [ ] **Step 11: Verificación de la tarea (suite frontend + build de tipos)**

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: PASS + sin errores de TypeScript (confirma que no quedó ningún `mvp_enabled`).

---

### Task 4: Docs — README y nota operativa de fuentes vivas

**Files:**
- Modify: `webconsole/README.md` (si menciona fuentes soportadas / MVP)
- Verify: comentarios de código ya actualizados en Tasks 1-2.

**Interfaces:**
- Consumes: nada.
- Produces: documentación alineada (rtsp soportado, runs vivos se detienen manualmente).

- [ ] **Step 1: Revisar menciones de MVP/fuentes en el README**

Run: `cd .. && grep -rniE "mvp|fuentes|image_folder|video_file|rtsp" webconsole/README.md`
Expected: lista de líneas a revisar (puede estar vacía).

- [ ] **Step 2: Actualizar el README**

Si el README enumera las fuentes soportadas, incluir `rtsp` y agregar una nota:

```markdown
### Fuentes de ingesta

La consola lanza runs desde: carpetas de imágenes (`image_folder`), archivos de
video (`video_file`) y cámaras IP por RTSP (`rtsp`). Las fuentes vivas (rtsp)
generan runs **infinitos**: se detienen manualmente desde la vista de run
("■ Detener"). Al guardar un manifiesto con una cámara RTSP, las credenciales
de la URL se escriben redactadas (`rtsp://***:***@...`); recompletá usuario y
clave al re-lanzar. `oak_d` no está soportado hasta contar con el hardware.
```

(Si el README no toca el tema, agregar esta sección donde documente el uso del formulario "Nueva corrida".)

- [ ] **Step 3: Verificación final de todo el repo**

Run: `make test`
Expected: PASS (pytest + ruff + vitest). Confirmar que no quedó ninguna referencia a `mvp_enabled`/`MVP_PLUGINS`:

Run: `cd .. && grep -rniE "mvp_enabled|mvp_plugins|MVP_PLUGINS" webconsole/backend/src webconsole/frontend/src`
Expected: sin resultados.

---

## Self-Review (cobertura del spec)

- **Habilitar rtsp permanente + retirar MVP** → Task 1 (settings/compose/catalog/__init__) + Task 3 (frontend types/pages). ✔
- **Validación URL rtsp en BFF** → Task 1 Step 6. ✔
- **Round-trip manifiesto rtsp** → Task 2 Steps 4-6. ✔
- **Redacción de credenciales al guardar, URL real al lanzar** → Task 2 Steps 4-5 + test `test_run_request_rtsp_lleva_url_real`. ✔
- **Campo URL única en el formulario + prefill + hint de `***`** → Task 3 Steps 4-8. ✔
- **Rename `mvp_enabled → enabled` coordinado backend+frontend** → Task 1 Step 5 + Task 3 Steps 3/7/9. ✔
- **oak_d sigue fuera** → cubierto en tests (`test_plugin_no_soportado`, `test_endpoint_plugin_no_soportado_422`). ✔
- **Docs / nota de runs vivos** → Task 4. ✔
- **Media-plane sin cambios** → ningún task lo toca. ✔
