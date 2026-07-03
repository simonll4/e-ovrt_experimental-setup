# E-OVRT Web Console — Diseño (Spec B)

- **Fecha:** 2026-07-01 (reescrito tras el pivote a servicio) · **Revisión:** 2026-07-03
  (alineada contra el servicio Fase 1 **ya implementado**: telemetría real, fallback WS,
  proxy obligatorio sin CORS, `frozen` como convención del BFF, clave `config.dataset`)
- **Estado:** aprobado para escribir plan de implementación (Spec A Fase 1 implementada)
- **Repo:** `e-ovrt_experimental-setup` (monorepo) — la consola vive en `webconsole/`.
- **Depende de:** Spec A — `e-ovrt_media-plane/docs/superpowers/specs/2026-07-01-media-plane-service-design.md`
  (el media-plane es ahora un **servicio de inferencia**). La consola es **cliente** de ese servicio.

## 1. Propósito

Interfaz web experimental para la plataforma **E-OVRT-VDP**. Punto único desde el cual
**componer, lanzar, monitorear en vivo y explorar** corridas de detección
open-vocabulary. Es el germen del **control plane** de la plataforma.

La consola **no ejecuta el pipeline**: es un **BFF** (backend-for-frontend) que habla con
el/los servicio(s) media-plane por HTTP/WS, y que además resuelve las declaraciones
(`prompts/`, `experiments/`) que viven en su mismo repo. Al vivir junto a las
declaraciones, guardar un manifiesto es una escritura **in-repo** (commit atómico).

### Alcance

- **MVP (Fase 1):** componer corridas seleccionando plugin de ingesta + prompts + params
  contra **una instancia local del servicio** (un modelo cargado); lanzar sobre
  datasets/video; ver progreso + telemetría en vivo; explorar resultados; guardar
  manifiesto. Catálogos read-only. Un solo nodo/instancia.
- **Fuera del MVP (Fase 2+):** fuentes en vivo (RTSP con lifecycle), registro de cámaras,
  editor de manifiestos/prompt sets, evaluación BENCH + compare-runs, **multi-instancia /
  multi-nodo** (elegir modelo = targetear/lanzar la instancia con ese `MODEL_REF`),
  auth/multi-usuario.

## 2. Decisiones de diseño (cerradas)

| Decisión | Resolución |
|---|---|
| Rol de la consola | **BFF cliente** del servicio media-plane (no ejecuta el pipeline) |
| Integración | HTTP/REST + WebSocket contra el servicio. **Sin subprocess, sin tailing de archivos, sin `cwd` hacks** |
| Monitoreo en vivo | Progreso + telemetría por WebSocket (proxy del stream del servicio). Sin video en vivo |
| Stack | FastAPI (BFF) + SPA React/Vite/TypeScript |
| Definir corrida | Formulario compositor (ingesta + prompts + params) + guardar manifiesto in-repo |
| Modelo | **Fijo por instancia** (lo define el servicio). La UI muestra el modelo activo (`GET /api/model`); no hay dropdown de modelo en caliente en Fase 1 |
| Prompts | La consola resuelve el prompt set in-repo y lo envía **inline** al crear el run |
| Multi-nodo | Costura `RunBackend` = cliente de una instancia del servicio. Fase 1: una instancia local. Fase 2: varias instancias/nodos |
| Auth | Sin auth, localhost (Fase 1) |
| Ubicación | Monorepo `e-ovrt_experimental-setup`, consola en `webconsole/` |

## 3. Arquitectura

```
e-ovrt_experimental-setup/          (repo unificado)
├── prompts/            ← declarativo (raíz; ver §3.1)
├── experiments/        ← declarativo (raíz)
├── docs/
└── webconsole/
    ├── backend/        FastAPI (BFF) — cliente del servicio + acceso a prompts/experiments in-repo
    └── frontend/       React + Vite + TypeScript — SPA
```

```
Navegador (React SPA)
   │  REST + WebSocket (un solo origen)
   ▼
FastAPI BFF (webconsole/backend)
   ├─ CatalogService   proxya catálogos del servicio (ingest-plugins, datasets, /model) + lee prompts/ y experiments/ in-repo
   ├─ RunComposer      form → run request; resuelve prompt set in-repo → prompts inline; valida
   ├─ ManifestWriter   guarda manifiesto YAML in-repo (experiments/)
   ├─ RunBackend       cliente HTTP/WS del servicio (una instancia = un "node/target")
   │     ├─ crea run (POST /api/runs) · stop · estado
   │     ├─ proxya el WS de telemetría (/api/runs/{id}/stream)
   │     └─ proxya artefactos (annotated.mp4 con range, previews, detections)
   ▼
Servicio media-plane (Spec A)  ── GET /api/model, POST /api/runs, WS stream, artefactos ──
   ▼
runs/<run_id>/  (propiedad del servicio; la consola los consume por API)
```

### 3.1 Invariante con el media-plane (two-root loader)

`prompts/` y `experiments/` **permanecen en la raíz del repo**; `webconsole/` es un
subdirectorio. Esto preserva la resolución del loader del media-plane y permite al BFF
leer/escribir las declaraciones por ruta relativa desde `webconsole/backend`.

### Settings del BFF (env / archivo)

- `SERVICE_URL` — URL base de la instancia del servicio media-plane (Fase 1: una local).
  Fase 2: **registro de instancias/nodos** (`{node_id → url, model}`).
- La raíz de las declaraciones (`prompts/`, `experiments/`) se resuelve relativa a
  `webconsole/` (no por env).
- `CONCURRENCY` de runs lo impone el **servicio** (un run activo); el BFF solo refleja el
  estado (`409 busy`).

## 4. Relación con el servicio y modelo de nodo

- Cada **instancia del servicio = un node/target** con **un modelo cargado**. `RunBackend`
  apunta a una instancia. El campo `node` existe en el modelo de datos y en la UI desde el
  MVP (un único nodo `local` en Fase 1).
- **Selección de modelo:** como el modelo es fijo por instancia, la UI **muestra** el
  modelo activo del target (`GET /api/model`) en lugar de ofrecer un dropdown libre. En
  Fase 2, elegir otro modelo = seleccionar/lanzar la instancia con ese `MODEL_REF`
  (routing en `RunBackend`).
- **Despliegue EBE (Fase 2):** la consola vive en Nodo A (edge) y apunta a la instancia del
  servicio en Nodo B (GPU) vía `SERVICE_URL` de ese nodo. La ingesta la hace el servicio
  (su adaptador de ingesta); la consola solo selecciona y observa.

## 5. Componentes del BFF

### 5.1 CatalogService
- Proxya del servicio: `GET /api/catalog/ingest-plugins`, `GET /api/catalog/datasets`,
  `GET /api/model` (modelo activo del target).
- Lee in-repo: `prompts/*.yaml` (sets + clases) y `experiments/**/*.yaml` (manifiestos
  como plantillas, **recorrido recursivo** — incluye la matriz `experiments/bench_v2/`,
  mostrada como grupo por subdirectorio).
- **`frozen`:** hoy **no existe** en ningún YAML ni en el schema `PromptSet` del
  media-plane (lo "congelado" es solo texto en descripciones), y la Fase 1 del media-plane
  cerró **sin** agregarlo. Para el MVP, "congelado" es una **convención del BFF**: una lista
  de `set_id` congelados en la config de la consola (p.ej. `cr01_cr02_bench_v2`) que el
  compositor trata como read-only. Extender el schema `PromptSet` del media-plane con un
  campo `frozen` queda como mejora opcional (PR chico) fuera del MVP; hasta entonces el dato
  no viaja en el request (los prompts se envían inline igual).
- Expone al frontend un catálogo unificado por target.

### 5.2 RunComposer
- Recibe la composición del form: `{ ingest: {plugin, config}, prompts: {set_id, active_ids},
  run: {stride, max_units, save_annotated_video, ...} }` (el modelo lo define el target).
  Nombres por capa (contrato canónico en Spec A §3.1): el form/BFF usa `set_id`; el
  request al servicio lleva `prompts.set_inline`; el manifiesto declarativo usa
  `prompts.ref`.
- **Resuelve el prompt set in-repo** y arma el request con **prompts inline**
  (`set_inline`) para el servicio. El request **nunca lleva sección `model`** (el
  servicio la rechaza con `422`).
- Valida la composición **contra el target**: `ingest.plugin` y los ids de dataset se
  chequean contra `GET /api/catalog/*` de esa instancia (los ids ya no son locales de la
  consola), y el prompt set contra el repo.
- Valida (esquema del request + validación del servicio) antes de lanzar.
- `POST /api/compose/validate` → errores a nivel de campo.
- `POST /api/runs` → delega en `RunBackend.launch` (que hace `POST` al servicio).

### 5.3 ManifestWriter
- `POST /api/manifests` → guarda la composición como manifiesto YAML **in-repo** en
  `experiments/` (escritura atómica; respeta sets congelados y estructura existente).
  **As-built:** ver "Notas as-built" al final — "respeta sets congelados" no se implementó
  como enforcement de `frozen`; lo que sí se implementó (endurecimiento posterior) es
  protección de manifiestos curados vía `protected_groups`.
- **Formato guardado = formato declarativo actual** (`source.ref`, `model.ref`,
  `rate_control.stride`, `outputs.save_annotated_video`, `prompts.ref`): un solo formato
  en disco, coherente con los 19 manifiestos existentes y la matriz BENCH. El BFF es el
  **dueño único de la traducción bidireccional** manifiesto ↔ run request (tabla canónica
  en Spec A §3.1), centralizada en un módulo con tests de ida y vuelta. Al guardar,
  `model.ref` se completa con el modelo del target.

### 5.4 Manifiestos existentes como plantillas (migración)

Los manifiestos actuales cargan directo como plantillas del compositor con esta
traducción (dueño: BFF):

| Manifiesto (disco) | Run request (servicio) |
|---|---|
| `source: {ref: X}` | `ingest: {plugin, config: {dataset: X}}` — la ref del dataset viaja como `config.dataset`; el servicio la retraduce a `source: {ref}` (ver `service/run_request.py:to_raw_run_config`) |
| `prompts: {ref, active_ids}` | `prompts: {set_inline, active_ids}` — resuelto in-repo |
| `rate_control: {stride}` | `run: {stride}` |
| `outputs: {save_annotated_video}` | `run: {save_annotated_video}` |
| `model: {ref}` | **no viaja** — ver política abajo |

**Política `model.ref` ≠ modelo del target:** el compositor lo detecta contra
`GET /api/model` y **bloquea el lanzamiento** con mensaje claro; el usuario puede
continuar explícitamente ("usar el modelo del target"). El request no lleva modelo en
ningún caso. Sin confirmación no se lanza: evita correr un manifiesto BENCH contra la
instancia equivocada en silencio.

### 5.5 RunBackend (la costura de control plane)
Cliente del servicio. Interfaz estable independiente de "qué/dónde":
```
RunBackend
  launch(run_request, node) -> run_id            # POST {service}/api/runs
  stop(node, run_id)                             # POST {service}/api/runs/{id}/stop
  status(node, run_id) -> RunStatus              # GET  {service}/api/runs/{id}
  stream(node, run_id) -> eventos                # WS   {service}/api/runs/{id}/stream (proxy)
  list_runs(node) -> [...]                        # GET  {service}/api/runs
  open_artifact(node, run_id, rel) -> bytes      # GET  {service}/api/runs/{id}/artifacts/...
```
- **Fase 1:** un único target `local` (`SERVICE_URL`).
- **Fase 2:** varios targets (registro de nodos); `launch` rutea al target del modelo pedido.

### 5.6 TelemetryProxy / ResultsProxy
- **Telemetry:** el BFF se suscribe al WS del servicio y lo reexpone al SPA
  (`WS /api/runs/{id}/stream`), manteniendo un solo origen. Los eventos reales del servicio
  son `metric` (`fps`, `latency_total_ms`, `detections_count`, `gpu_memory_mb` por unidad),
  `detection` (`{unit_id, count}`), `error` (`{unit_id, stage, message}`) y `state`
  (`{status, error}` final). p95 y detecciones-por-label **no** son eventos en vivo (viven en
  `summary.json` al terminar). **Fallback WS caído:** el mecanismo primario es **reconectar
  el WS** (el broadcaster del servicio admite N suscriptores y sólo el run activo es
  suscribible); `GET /api/runs/{id}` sirve **sólo para re-hidratar el estado** (para un run
  activo devuelve `{run_id, status, started_at, model}`, sin summary ni métricas parciales),
  no la telemetría. **Backpressure:** el proxy coalesce métricas (último estado gana) sobre
  cola acotada con drop-oldest — espejo de la política del servicio (Spec A §3.1); un SPA
  lento nunca acumula memoria en el BFF.
- **Results:** proxya `summary`, `detections` paginadas, `annotated.mp4` (con range
  requests) y `previews/` desde el servicio, en **streaming pass-through** (sin
  bufferizar el archivo en memoria del BFF).

## 6. Frontend (pantallas)

- **Runs (home):** tabla de corridas (activa + historial vía servicio) con estado, nodo,
  modelo activo, plugin de ingesta, métricas clave; botón *Nueva corrida*. Nota: el servicio
  lista runs como `[{run_id, status}]`; el resto de columnas las hidrata el BFF con un
  `GET /api/runs/{id}` por fila (N+1 aceptable en MVP; los summaries son locales al servicio).
- **Nueva corrida (compositor):** target/nodo (Fase 1: `local`, muestra su modelo) →
  plugin de ingesta (dataset/video) + su config → prompt set con toggles de clases activas
  → overrides (`stride`, `max_units`, `save_annotated_video`, `save_previews`). Los
  **thresholds son del modelo** (fijos por instancia, cargados al startup): **no** son
  overrides del compositor — se muestran **read-only** desde `GET /api/model`. Validación en
  vivo. Botones *Lanzar* y *Guardar como manifiesto*. Puede partir de un manifiesto existente.
  **As-built:** no se implementó como validación en vivo — ver "Notas as-built" al final.
- **Detalle de corrida (vivo):** barra de progreso (derivada de `unit_id`/`max_units` en el
  BFF cuando la fuente es acotada) + gráficos de telemetría alimentados por los eventos WS
  reales (`metric`: FPS, latencia total por unidad, conteo de detecciones, VRAM; `detection`:
  conteo por unidad; `error`: tail de errores como "consola de log"). **p95** y
  **detecciones-por-label** son de `summary.json` (post-run), no eventos en vivo: en vivo se
  muestra latencia por unidad (o p95 rolling calculado client-side). Al terminar: player del
  `annotated.mp4`, galería de previews, tabla de detecciones, summary (p95/p99 y por-label) y
  config efectiva.
- **Catálogos (read-only):** modelo activo del target, plugins de ingesta con badges de
  disponibilidad, datasets, prompt sets. La disponibilidad de **OAK-D** viene del catálogo
  del servicio (`available: false`); el servicio **sí acepta RTSP hoy**, así que la exclusión
  de RTSP en el MVP es **policy del BFF** (allowlist de plugins acotados
  `image_folder`/`video_file`), no un dato del catálogo.

## 7. Flujo de datos

```
form → POST /api/compose/validate → POST /api/runs (BFF) → RunBackend.launch → POST {service}/api/runs
   → el servicio ingiere+infiere y escribe runs/<id>/ → WS del servicio → BFF proxya WS → SPA en vivo
   → al terminar, ResultsProxy sirve artefactos desde el servicio
```

## 8. Manejo de errores

- **Validación:** errores del request (esquema BFF) + validación del servicio (`422`)
  mapeados a campos del compositor **usando la misma tabla de traducción de §5.4** (los
  paths de campo del servicio no coinciden con los del form; el mapeo es responsabilidad
  del BFF).
- **Manifiesto con `model.ref` ≠ modelo del target:** bloqueo con confirmación explícita
  (§5.4).
- **Servicio no disponible / no `ready`:** el BFF detecta `GET /healthz`/`/readyz` del
  target y muestra estado; los lanzamientos se bloquean con mensaje claro.
- **`409 busy`:** ya hay un run activo en el target; la UI lo informa y ofrece ver el run
  activo.
- **Errores de runtime:** el servicio los expone (contador + tail vía WS/summary); la UI
  los muestra.
- **WS caído:** fallback primario = **reconectar el WS** (el run activo sigue siendo
  suscribible); `GET /api/runs/{id}` re-hidrata **sólo el estado** (no hay summary ni
  métricas parciales para un run activo — ver §5.6).
- **Plugin live/OAK-D pedido en MVP:** el servicio lo rechaza; la UI lo muestra
  deshabilitado con badge.

## 9. Testing

- **Backend BFF (pytest):** contra un **servicio fake** (o el servicio real con detector
  `mock`): compose → validate → launch → proxy de WS emite telemetría → results legibles;
  resolución de prompt set in-repo → inline; escritura de manifiesto in-repo;
  **traducción manifiesto ↔ run request con tests de ida y vuelta sobre los manifiestos
  reales del repo (incluido `bench_v2/`)** y política `model.ref` ≠ target; `RunBackend`
  contra fake HTTP/WS; manejo de `409`/servicio no `ready`.
- **Frontend (Vitest):** componentes + integración contra BFF stub.

## 10. Plan de fases

- **Fase 1 (MVP):** BFF cliente de **una instancia local** del servicio; catálogos
  read-only (proxy + in-repo); compositor (ingesta + prompts + params) + guardar manifiesto
  in-repo; lanzar sobre datasets/video; telemetría en vivo (proxy WS); detalle + resultados;
  lista de runs; costura `RunBackend` + modelo `node`.
- **Fase 2:** RTSP en vivo (lifecycle); registro de cámaras; **multi-instancia/multi-nodo**
  (elegir modelo = targetear/lanzar instancia); editor de manifiestos/prompt sets;
  evaluación BENCH + compare-runs; auth/multi-usuario.

## 11. Riesgos

1. **Proxy de WebSocket/HTTP en el BFF** — mantener el stream del servicio hacia el SPA sin
   introducir latencia/backpressure. La alternativa (SPA directo al servicio) **no es viable
   en Fase 1**: el servicio media-plane **no expone CORS** (`app.py` no monta
   `CORSMiddleware`), por lo que un navegador en otro origen sería bloqueado. El proxy BFF de
   **único origen es obligatorio**, no una simplificación opcional. Política concreta de
   coalescing + drop-oldest en §5.6. (Agregar CORS al servicio quedaría fuera del alcance de
   Fase 1 y tocaría el media-plane.)
2. **Streaming de artefactos grandes** (`annotated.mp4`) — resuelto por decisión: range
   requests con stream pass-through, sin bufferizar en el BFF (§5.6).
3. **Selección de modelo por instancia** — en Fase 1 el modelo es el del target; cambiarlo
   exige otra instancia (Fase 2). La UI debe dejar esto claro (muestra modelo activo).
4. **Sincronía de catálogos** — datasets/plugins vienen del servicio y prompts del repo;
   evitar estados incoherentes: la validación al componer es **contra los catálogos del
   target** (§5.2), no contra copias locales.
5. **Divergencia guardar↔lanzar** — se guarda formato declarativo y se lanza formato de
   servicio; mitigado centralizando la traducción en un único módulo del BFF (§5.3/§5.4)
   con tests de ida y vuelta sobre los manifiestos reales.
6. **Sin auth entre consola y servicio** — aceptado en Fase 1 (localhost). En Fase 2
   (multi-nodo, el API cruza la red) mínimo token estático compartido, alineado con
   Spec A §11.6.

## Notas as-built (2026-07-03)

Brechas conocidas entre esta spec y la implementación ejecutada
(`docs/superpowers/plans/2026-07-03-webconsole-mvp.md`, código en `webconsole/`):

- **§5.2/§6 "Validación en vivo"**: no se implementó. El endpoint
  `POST /api/compose/validate` existe en el BFF (`routers/compose.py`) y está testeado
  (`tests/test_compose.py`), pero el frontend no lo llama — `frontend/src/api.ts` define
  `validateComposition()` sin ningún consumidor en `ComposePage.tsx`. La validación real
  ocurre **on-submit**: `ComposePage` llama `launchRun()` y captura el `422` del servicio
  (ver `frontend/src/pages/ComposePage.tsx`). El endpoint queda disponible, sin cablear, para
  una futura validación en vivo (Fase 2).
- **§5.3 "ManifestWriter respeta sets congelados"**: `frozen` (`settings.frozen_set_ids`,
  default `cr01_cr02_bench_v2`) es únicamente un **badge de UI** en el selector de prompt
  sets del compositor (`ComposePage.tsx`: `{s.frozen ? ' ❄' : ''}`) — no hay enforcement en
  el write-path de `manifest_writer.py`, y de hecho los prompt sets no se escriben/sobrescriben
  vía la API (solo se leen). Lo que sí se implementó, como endurecimiento posterior no
  previsto en esta spec, es la protección de **manifiestos curados**:
  `EOVRT_CONSOLE_PROTECTED_GROUPS` (default `bench_v2`, `settings.protected_groups`) hace que
  `write_manifest()` (`manifest_writer.py`) responda `409`/`ProtectedManifestError` si el
  grupo destino está protegido y el manifiesto ya existe — **independiente** del flag
  `overwrite`. Resumen del estado real: `frozen` = badge informativo; protección de
  manifiestos curados = `protected_groups`, mecanismos separados y no intercambiables.
