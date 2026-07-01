# E-OVRT Web Console — Diseño (spec)

- **Fecha:** 2026-07-01
- **Estado:** ⚠️ **PENDIENTE DE REESCRITURA (Spec B).** Superado por el pivote del
  2026-07-01: el media-plane deja de ser CLI y pasa a ser un **servicio de inferencia
  desplegado** (ver Spec A, `2026-07-01-media-plane-service-design.md`). Cuando Spec A
  cierre, este documento se reescribe: la consola pasa a ser **cliente del servicio**
  (se cae el subprocess, la correlación de `run_id`, el tailing de archivos y los hacks
  de `cwd`; el `RunBackend` se convierte en "cliente del servicio media-plane"). Las
  decisiones de UI/alcance/monitoreo de abajo siguen vigentes; cambia la capa de
  integración.
- **Repo:** `e-ovrt_experimental-setup` (monorepo) — la consola vive en `webconsole/`.
  Repos hermanos externos: `e-ovrt_media-plane`, `e-ovrt_datasets`.

## 1. Propósito

Interfaz web experimental para la plataforma **E-OVRT-VDP**. Punto único desde el
cual **componer, lanzar, monitorear en vivo y explorar** corridas del pipeline de
detección open-vocabulary, sobre datasets de imágenes/video (y, a futuro, fuentes en
vivo). Es el germen del **control plane** de la plataforma.

Hoy, definir y correr un experimento exige editar YAML a mano y ejecutar el CLI
`eovrt-media` desde la raíz del media-plane. La consola elimina ese dolor sin duplicar la
lógica del motor. Al vivir en el mismo repo que las declaraciones (`prompts/`,
`experiments/`), guardar un manifiesto es una escritura **in-repo** (commit atómico).

### Alcance

- **MVP (Fase 1):** consola de plataforma acotada pero extensible — componer corridas
  desde catálogos, lanzarlas sobre datasets/video, ver progreso + telemetría en vivo,
  explorar resultados. Catálogos en modo lectura. Un solo nodo de cómputo (local).
- **Explícitamente fuera del MVP (Fase 2+):** fuentes en vivo (RTSP/OAK-D) con
  lifecycle, registro de cámaras, editor de manifiestos/prompt sets, evaluación BENCH +
  compare-runs, despliegue multi-nodo, auth/multi-usuario.

## 2. Decisiones de diseño (cerradas)

| Decisión | Resolución |
|---|---|
| Alcance | Consola de plataforma, MVP extensible |
| Monitoreo en vivo | Progreso + telemetría por WebSocket (sin video en vivo) |
| Stack | FastAPI (backend) + subprocess + SPA React/Vite/TypeScript |
| Integración con el motor | Subprocess `eovrt-media run` para ejecutar; import de `eovrt_media.config` **solo** para parsear/validar |
| Fuentes en vivo | Datasets/video ahora; RTSP/OAK-D como *plugin-slot* (Fase 2). Modelo de datos ya las contempla |
| Definir corrida | Formulario compositor + opción de guardar manifiesto (in-repo) |
| Multi-nodo | Costura `RunBackend` desde el día 1; solo `LocalRunBackend` implementado en MVP |
| Auth | Sin auth, localhost (Fase 1). Auth → Fase 2 |
| Ubicación | Monorepo `e-ovrt_experimental-setup`, consola en `webconsole/` |

## 3. Arquitectura

Monorepo unificado. Los artefactos declarativos permanecen en la **raíz** del repo; la
consola vive en un subdirectorio. Esto preserva el contrato con el media-plane (ver
§3.1).

```
e-ovrt_experimental-setup/          (repo unificado)
├── prompts/            ← se mantienen en la raíz
├── experiments/        ← se mantienen en la raíz
├── docs/
└── webconsole/
    ├── backend/        FastAPI (Python) — orquesta y lee artefactos
    └── frontend/       React + Vite + TypeScript — SPA
```

**Principio rector:** el backend **nunca importa GPU ni corre el pipeline en su
proceso**. Ejecuta `eovrt-media run` como **subproceso** con `cwd = <raíz media-plane>`
(para resolver las rutas relativas `../e-ovrt_datasets/...`) usando el **Python del venv
del media-plane**. Importa `eovrt_media.config` **solo para parsear/validar** configs,
manteniendo una única fuente de verdad de los schemas Pydantic (sin duplicarlos).

```
Navegador (React SPA)
   │  REST + WebSocket
   ▼
FastAPI backend  ── importa eovrt_media.config (solo validar) ──▶ schemas Pydantic
   ├─ CatalogService   lee ../prompts + ../experiments (in-repo) + configs/ del media-plane (externo)
   ├─ RunComposer      form → RunConfig YAML → valida con loader → (opcional) guarda manifiesto in-repo
   ├─ RunManager       ── usa ──▶ RunBackend
   ├─ TelemetryTailer  ── usa ──▶ RunBackend
   └─ ResultsService   ── usa ──▶ RunBackend
                                    │
                                    ├─ LocalRunBackend (MVP): subprocess + FS local
                                    └─ RemoteNodeBackend (Fase 2): node-agent por HTTP
   ▼
e-ovrt_media-plane/runs/<run_id>/  (detections/metrics/errors.jsonl, annotated.mp4, previews/, summary.json)
```

### 3.1 Invariante con el media-plane (two-root loader)

El *two-root loader* del media-plane descubre la "raíz del experimento" **subiendo desde
el manifiesto hasta el directorio que contiene `prompts/`**. Por eso `prompts/` y
`experiments/` **deben permanecer en la raíz del repo**; agregar `webconsole/` como
subdirectorio no altera esa resolución. `prompts.ref` resuelve contra la raíz del repo;
`model.ref` y `source.ref` resuelven contra los catálogos del media-plane (externo).

### Settings del backend (env / archivo)

`MEDIA_PLANE_ROOT`, `DATASETS_ROOT` (hermanos externos), `PYTHON_BIN` (venv del
media-plane), `RUNS_DIR`, `CONCURRENCY` (default 1, GPU serie). La raíz de
`experimental-setup` (donde viven `prompts/`, `experiments/`) es el propio repo — se
resuelve relativa a `webconsole/`, no por env. Al arrancar, el backend valida que
`PYTHON_BIN` existe y que `eovrt-media` es invocable (el venv del media-plane se rompe si
el repo se mueve; hay que detectarlo temprano).

## 4. La costura `RunBackend` (control plane)

Toda interacción con "dónde y cómo se ejecuta" pasa por una interfaz. Ni la API REST ni
el frontend asumen ejecución local ni filesystem local.

```
RunBackend (interfaz)
  launch(run_config, node) -> job_handle
  stream_telemetry(job_handle) -> iterador de eventos
  stop(job_handle) -> None
  list_runs(node) -> [RunSummaryRef]
  get_result(node, run_id) -> RunResult
  open_artifact(node, run_id, rel_path) -> stream de bytes
```

- **MVP → `LocalRunBackend`:** subprocess + tail del FS local. Único implementado.
- **Fase 2 → `RemoteNodeBackend`:** habla con un **node-agent** (daemon liviano, mismo
  contrato) en cada nodo de cómputo; artefactos por HTTP o volumen compartido.

**Modelo de datos con `node`/`target`:** cada job y cada run se atribuyen a un nodo. En
MVP hay un único nodo implícito (`local`), pero el campo existe en API y UI.

### Despliegue objetivo EBE (Fase 2, registrado — no se construye aún)

La web console se despliega en **Nodo A (edge)**, junto al punto de ingesta (posee la
conexión con la fuente de video), compone la config y la **envía a Nodo B (GPU)**, que
queda como target de inferencia headless. Calza con el split existente del media-plane
(`run-producer` en A / `run-consumer` en B vía ZeroMQ): el `RemoteNodeBackend` orquesta
ambos. Como en EBE los sinks corren en B, la console en A obtiene telemetría y artefactos
de B a través de la costura `RunBackend` (node-agent o volumen compartido). El modelo
`node` + `RunBackend` no impide este escenario; el MVP simplemente no lo implementa.

## 5. Componentes del backend

### 5.1 CatalogService (read-only)
Parsea los YAML declarativos (in-repo: `prompts/`, `experiments/`) y los catálogos del
media-plane (externo: `configs/`), y expone:
- `GET /api/catalog/models` — refs de modelo (family/variant, adapter, device default, thresholds).
- `GET /api/catalog/datasets` — refs de dataset (type, path, bounded vs live).
- `GET /api/catalog/prompt-sets` — sets con clases, backends de phrasing, flag `frozen`.
- `GET /api/catalog/manifests` — manifiestos existentes (plantillas de corrida).
- `GET /api/catalog/source-plugins` — registro de tipos de fuente (`image_folder`,
  `video_file`, `rtsp`, `oak_d`) con flag de disponibilidad. MVP: `rtsp`=*fase 2*,
  `oak_d`=*no disponible*.

### 5.2 RunComposer
Recibe la composición del form (source ref, model ref, prompt set + `active_ids`,
overrides: `stride`, `device`, thresholds, `save_annotated_video`), arma el `RunConfig`,
lo **valida con `load_run_config`** (mismos errores que el CLI, mapeados a nivel de
campo) y opcionalmente lo **persiste como manifiesto** in-repo en `experiments/`
(escritura atómica; respeta los sets congelados y la estructura existente).
- `POST /api/runs/validate` → errores de validación.
- `POST /api/runs` → lanza (via RunManager).
- `POST /api/manifests` → guarda manifiesto YAML in-repo.

### 5.3 RunManager
Estado del job (`queued/running/succeeded/failed/stopped`, node, run_id, exit code, log),
**cola en serie** (`CONCURRENCY`, default 1 por GPU), **stop** (termina el proceso vía
`RunBackend`), captura de stdout/stderr a log.
- **Correlación job ↔ run dir:** el `run_id` lo genera el media-plane en runtime
  (timestamp + name). El `LocalRunBackend` detecta el directorio nuevo bajo `RUNS_DIR`
  cuyo nombre matchea el `run.name`, creado tras el launch. **Riesgo / mitigación:** si
  resulta frágil (colisión de nombres, concurrencia), se agrega una opción mínima al CLI
  del media-plane (`--print-run-dir` o `--run-id`). Autorizado como fallback.

### 5.4 TelemetryTailer
Cuando conoce el run dir (vía `RunBackend`), sigue `metrics.jsonl` y `detections.jsonl`,
lee `summary.json` al cerrar, y emite por **WebSocket** (`/api/runs/{id}/ws`):
progreso (units hechas/total), FPS efectivo, latencia p95, GPU mem, detecciones por
label, contador de errores y tail del log.
- **Total de units:** para fuentes bounded sale del tamaño del dataset (nº de imágenes o
  frames/stride del video). Para fuentes live (Fase 2) el progreso es indefinido.
- **Fallback:** si el WebSocket cae, la UI hace polling de `GET /api/runs/{id}` y
  re-hidrata desde `summary.json` al reconectar.

### 5.5 ResultsService
Para runs terminados, a través de `RunBackend.open_artifact`:
- `GET /api/runs/{id}` — summary + effective_config + estado.
- `GET /api/runs/{id}/detections?page=` — detections.jsonl paginado.
- `GET /api/runs/{id}/artifacts/annotated.mp4` — con **range requests** para el player.
- `GET /api/runs/{id}/artifacts/previews/*` — galería de previews.

## 6. Frontend (pantallas)

- **Runs (home):** tabla de corridas (jobs vivos + `runs/` existentes) con estado,
  nodo, modelo, dataset, métricas clave; botón *Nueva corrida*.
- **Nueva corrida (compositor):** form fuente (dataset/video) → modelo → prompt set con
  toggles de clases activas → overrides. Validación en vivo (`/validate`). Botones
  *Lanzar* y *Guardar como manifiesto*. Puede partir de un manifiesto existente como
  plantilla.
- **Detalle de corrida (vivo):** barra de progreso + gráficos de telemetría (FPS, p95,
  GPU mem, detecciones-por-label) + consola de log en streaming. Al terminar: player del
  `annotated.mp4`, galería de previews, tabla de detecciones, summary y config efectiva.
- **Catálogos (read-only):** modelos, datasets, prompt sets, plugins de fuente (badges de
  disponibilidad).

## 7. Flujo de datos

```
form → POST /validate → POST /runs → RunManager → RunBackend.launch → subprocess eovrt-media
   → media-plane escribe runs/<id>/*.jsonl → TelemetryTailer (RunBackend) sigue archivos
   → WebSocket → UI en vivo → al cerrar, ResultsService (RunBackend.open_artifact) sirve artefactos
```

## 8. Manejo de errores

- **Validación de config:** errores del loader del media-plane mapeados a campos del
  compositor.
- **Fallo de launch** (venv/pesos faltantes): job `failed` + stderr visible. El backend
  valida `PYTHON_BIN`/`eovrt-media` al arrancar.
- **Errores de runtime:** el media-plane escribe `errors.jsonl` sin frenar; la UI muestra
  contador + tail. Exit code ≠ 0 → `failed`.
- **WebSocket caído:** la UI cae a polling y re-hidrata desde `summary.json`.
- **Fuente live/OAK-D pedida en MVP:** el backend la rechaza con mensaje claro; la UI la
  muestra deshabilitada con badge.

## 9. Testing

- **Backend (pytest):** e2e con el detector `mock` sobre `demo_v2` (sin GPU) —
  compose → validate → launch → tailer emite telemetría → results legibles. Unit:
  parsing de catálogos, composer→YAML, correlación de run dir, agregación del tailer,
  contrato `RunBackend` (fake in-memory).
- **Frontend (Vitest):** tests de componentes + integración contra backend stub.

## 10. Plan de fases

- **Fase 1 (MVP):** catálogos read-only; compositor + guardar manifiesto in-repo; lanzar
  mock/GDINO/YOLOE sobre datasets+video; telemetría en vivo; detalle + resultados; lista
  de runs; `LocalRunBackend`; costura `RunBackend` + modelo `node` en su lugar.
- **Fase 2:** RTSP en vivo (lifecycle start/stop, corrida sin fin); registro de cámaras;
  editor de manifiestos/prompt sets; evaluación BENCH + compare-runs; `RemoteNodeBackend`
  + node-agent (despliegue EBE Nodo A/Nodo B); auth/multi-usuario.

## 11. Riesgos e integración

1. **Correlación job ↔ run dir** — mitigado con opción de CLI si hace falta (§5.3).
2. **Venv del media-plane** — se rompe si el repo se mueve; validar al arranque.
3. **Ejecutar desde la raíz del media-plane** — requisito de rutas relativas; el
   `LocalRunBackend` fija `cwd` siempre.
4. **Invariante del two-root loader** — `prompts/` y `experiments/` deben quedar en la
   raíz del repo (§3.1); el subdir `webconsole/` no debe moverlos.
5. **Toolchain mixto** — el repo suma dependencias Python (web) y Node; aislar bajo
   `webconsole/` y no contaminar la capa declarativa.
