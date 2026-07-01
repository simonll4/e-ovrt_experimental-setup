# E-OVRT Web Console — Diseño (Spec B)

- **Fecha:** 2026-07-01 (reescrito tras el pivote a servicio)
- **Estado:** aprobado para escribir plan de implementación (tras Spec A)
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
- Lee in-repo: `prompts/*.yaml` (sets + clases + `frozen`) y `experiments/*.yaml`
  (manifiestos como plantillas).
- Expone al frontend un catálogo unificado por target.

### 5.2 RunComposer
- Recibe la composición del form: `{ ingest: {plugin, config}, prompts: {set_id, active_ids},
  run: {stride, max_units, save_annotated_video, ...} }` (el modelo lo define el target).
- **Resuelve el prompt set in-repo** y arma el request con **prompts inline** para el
  servicio.
- Valida (esquema del request + validación del servicio) antes de lanzar.
- `POST /api/compose/validate` → errores a nivel de campo.
- `POST /api/runs` → delega en `RunBackend.launch` (que hace `POST` al servicio).

### 5.3 ManifestWriter
- `POST /api/manifests` → guarda la composición como manifiesto YAML **in-repo** en
  `experiments/` (escritura atómica; respeta sets congelados y estructura existente).

### 5.4 RunBackend (la costura de control plane)
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

### 5.5 TelemetryProxy / ResultsProxy
- **Telemetry:** el BFF se suscribe al WS del servicio y lo reexpone al SPA
  (`WS /api/runs/{id}/stream`), manteniendo un solo origen. Si el WS cae, el SPA hace
  polling de `GET /api/runs/{id}` y re-hidrata.
- **Results:** proxya `summary`, `detections` paginadas, `annotated.mp4` (con range
  requests) y `previews/` desde el servicio.

## 6. Frontend (pantallas)

- **Runs (home):** tabla de corridas (activa + historial vía servicio) con estado, nodo,
  modelo activo, plugin de ingesta, métricas clave; botón *Nueva corrida*.
- **Nueva corrida (compositor):** target/nodo (Fase 1: `local`, muestra su modelo) →
  plugin de ingesta (dataset/video) + su config → prompt set con toggles de clases activas
  → overrides (stride, thresholds, save_annotated_video). Validación en vivo. Botones
  *Lanzar* y *Guardar como manifiesto*. Puede partir de un manifiesto existente.
- **Detalle de corrida (vivo):** barra de progreso + gráficos de telemetría (FPS, p95, GPU
  mem, detecciones-por-label) + consola de log en streaming (WS). Al terminar: player del
  `annotated.mp4`, galería de previews, tabla de detecciones, summary y config efectiva.
- **Catálogos (read-only):** modelo activo del target, plugins de ingesta (badges de
  disponibilidad: RTSP=fase 2, OAK-D=no disponible), datasets, prompt sets.

## 7. Flujo de datos

```
form → POST /api/compose/validate → POST /api/runs (BFF) → RunBackend.launch → POST {service}/api/runs
   → el servicio ingiere+infiere y escribe runs/<id>/ → WS del servicio → BFF proxya WS → SPA en vivo
   → al terminar, ResultsProxy sirve artefactos desde el servicio
```

## 8. Manejo de errores

- **Validación:** errores del request (esquema BFF) + validación del servicio (`422`)
  mapeados a campos del compositor.
- **Servicio no disponible / no `ready`:** el BFF detecta `GET /healthz`/`/readyz` del
  target y muestra estado; los lanzamientos se bloquean con mensaje claro.
- **`409 busy`:** ya hay un run activo en el target; la UI lo informa y ofrece ver el run
  activo.
- **Errores de runtime:** el servicio los expone (contador + tail vía WS/summary); la UI
  los muestra.
- **WS caído:** fallback a polling; re-hidrata desde `summary`.
- **Plugin live/OAK-D pedido en MVP:** el servicio lo rechaza; la UI lo muestra
  deshabilitado con badge.

## 9. Testing

- **Backend BFF (pytest):** contra un **servicio fake** (o el servicio real con detector
  `mock`): compose → validate → launch → proxy de WS emite telemetría → results legibles;
  resolución de prompt set in-repo → inline; escritura de manifiesto in-repo; `RunBackend`
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

1. **Proxy de WebSocket en el BFF** — mantener el stream del servicio hacia el SPA sin
   introducir latencia/backpressure; alternativa: que el SPA se conecte directo al WS del
   servicio (se pierde el único-origen). Decisión Fase 1: proxy en el BFF por simplicidad
   de origen/routing.
2. **Streaming de artefactos grandes** (`annotated.mp4`) — proxyar con range requests sin
   bufferizar en memoria (stream pass-through).
3. **Selección de modelo por instancia** — en Fase 1 el modelo es el del target; cambiarlo
   exige otra instancia (Fase 2). La UI debe dejar esto claro (muestra modelo activo).
4. **Sincronía de catálogos** — datasets/plugins vienen del servicio y prompts del repo;
   evitar estados incoherentes (validar contra el target al componer).
