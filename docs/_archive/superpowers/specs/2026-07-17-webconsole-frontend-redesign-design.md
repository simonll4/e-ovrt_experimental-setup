# Rediseño del frontend de la webconsole — Diseño

**Fecha**: 2026-07-17
**Estado**: aprobado en brainstorming; pendiente de plan de implementación
**Alcance**: `e-ovrt_experimental-setup/webconsole/` (frontend + un endpoint de lectura en el BFF)

## 1. Propósito

La webconsole se rediseña como **herramienta de trabajo diaria**, no como pieza de
demostración. La prioridad es densidad de información, menos clicks en las tareas
repetidas y jerarquía visual legible. La defensa de tesis no es el escenario que manda:
se acepta explícitamente que un tema oscuro proyecta mal en sala iluminada (§4.1).

## 2. Diagnóstico

### 2.1 El problema de fondo

**La navegación está organizada por recurso; el trabajo está organizado por loop.**

Los 7 links actuales son sustantivos del sistema (Runs, Prompts, Catálogos, Plataforma,
Experimentos). Los cuatro loops de trabajo reales son verbos: iterar prompts, comparar
corridas, vigilar una corrida en vivo, revisar histórico. Cada loop cruza varios
sustantivos —iterar un prompt recorre Prompts → Nueva corrida → Detalle— y por eso las
cuatro fricciones reportadas (jerarquía, navegación, densidad, clicks) aparecen juntas:
son síntomas del mismo desajuste, no cuatro problemas independientes.

### 2.2 Estado actual medido

- **Cero archivos `.css`** en todo el repo. 90 ocurrencias de `style={{}}` inline en 16
  archivos `.tsx`.
- Constantes `CELL` y `ROW` **duplicadas literalmente** en 6 archivos (`ComparePage`,
  `RunsPage`, `EvalSection`, `ExperimentDetailPage`, `ExperimentsPage`, `PlatformPage`).
- Paleta de hex sueltos: `#b00` error, `#c80` warning, `#080` ok, `#a60` skipped, `#ddd`
  bordes, `#f5f5f5` header de tabla. `experimentview.ts:alertSeverityColor` **replica esos
  hex en TypeScript** — el color de estado vive en dos lugares.
- Tipografía: dos tamaños en total (`h1: 20` y el default del browser). Sin escala.
- 3 `className` muertos sin hoja de estilos que los defina: `prompt-sets-page`,
  `badge badge-${status}`, `prompt-set-editor` (heredados del plan de prompt-strategy).
- `maxWidth: 1100` en el contenedor raíz: desperdicia pantalla en monitor ancho.
- Sin dark mode, sin design tokens, sin ESLint/Prettier.

### 2.3 Stack (se conserva)

React 18 + Vite 5 + TS strict + `react-router-dom` 6 (HashRouter). **3 dependencias de
runtime.** Vitest 2 + Testing Library + jsdom; 62 tests en 15 archivos. El BFF (FastAPI)
sirve la SPA compilada vía `StaticFiles`.

## 3. Decisiones cerradas

| # | Decisión | Razón |
|---|---|---|
| D1 | Enfoque B: fundamentos + shell + flujos, en dos tramos | Ataca las 4 fricciones; entrega visible al cerrar el tramo 1 |
| D2 | Sin dependencias nuevas (no Tailwind, no shadcn/Radix) | El repo tiene 3 deps de runtime; para 9 páginas el kit propio es menos código que la migración |
| D3 | Sidebar agrupado por **rol**, no por loop | Por rol cada destino aparece una sola vez; por verbo un mismo objeto cae en dos grupos (una corrida se ejecuta *y* se analiza) |
| D4 | "Nueva corrida" deja de ser destino y pasa a acción primaria | Es un verbo entre sustantivos; sacarlo deja 6 destinos que agrupan limpio |
| D5 | **Dark-only** | Herramienta técnica de uso diario. Se acepta el costo de proyección en sala iluminada |
| D6 | `GET /api/runs/{id}/composition` en el BFF | Sin esto "relanzar variando" es imposible (§5.1); va en backend porque el frontend no tiene parser YAML |
| D7 | La lógica de mapeo de errores por página **no se toca** | Es conocimiento de dominio ganado; solo cambia la presentación |

## 4. Diseño

### 4.1 Lenguaje visual

Un `tokens.css` con custom properties como única fuente de verdad. Todo lo demás lo
consume; ningún hex literal sobrevive en TSX ni en TS.

- **Superficies y texto**: `--surface`, `--surface-raised`, `--border`, `--text`,
  `--text-muted`. Hoy no existe "texto secundario", y por eso todo pesa igual.
- **Estado semántico**: `--status-live`, `--status-ok`, `--status-warn`, `--status-error`,
  `--status-neutral`. Consumidos por CSS **y por TS vía nombre de clase, no vía hex** —
  esto elimina la duplicación de `alertSeverityColor`.
- **Escala tipográfica**: 4–5 pasos. Es lo que produce la jerarquía ausente.
- **Espaciado**: `--space-1..6`, reemplaza los `padding: '4px 10px'` y `gap: 4` a ojo.

Tema único oscuro (D5). Los tokens se estructuran de modo que un light futuro sea un
archivo de overrides, pero **no se construye ni se verifica light ahora**.

Los dos gráficos SVG hechos a mano (`Sparkline`, `GroupedBars`) se conservan y solo se
retematizan contra los tokens. Al elegir colores de serie, cargar la skill `dataviz`
antes de escribir el código.

### 4.2 Kit de componentes

Siete componentes, cada uno justificado por duplicación existente:

| Componente | Qué elimina |
|---|---|
| `Table` | Las `CELL` duplicadas en 6 archivos |
| `Badge` | Los hex de estado y los 3 `className` muertos de prompt sets |
| `Field` | Las `ROW` del compositor (13 `style=` en `ComposePage`) |
| `Card` | Secciones ad-hoc |
| `StatTile` | Métricas legibles de un vistazo (densidad del detalle) |
| `EmptyState` | Estados vacíos ad-hoc |
| `ErrorBanner` | Texto rojo `#b00` armado a mano en cada página |

### 4.3 Shell y arquitectura de información

Sidebar (~200px) con tres grupos por rol, acción primaria persistente, y píldora de
corrida viva:

```
┌──────────────────┬─────────────────────────────────┐
│ E-OVRT           │  Corridas           [● mock ✓]  │
│                  │                                 │
│ [+ Nueva corrida]│  ┌───────────────────────────┐  │
│                  │  │ run_id  estado    modelo  │  │
│ TRABAJO          │  ├───────────────────────────┤  │
│  ▸ Corridas      │  │ r_204   ● vivo    gdino   │  │
│    Experimentos  │  │ r_203   ✓ ok      gdino   │  │
│    Comparar      │  │ r_202   ✗ error   yoloe   │  │
│                  │  └───────────────────────────┘  │
│ DEFINICIONES     │                                 │
│    Prompt sets   │                                 │
│    Catálogos     │                                 │
│                  │                                 │
│ SISTEMA          │                                 │
│    Plataforma    │                                 │
│                  │                                 │
│ ─────────────    │                                 │
│ ● r_204 vivo     │                                 │
│   42 fps · 18ms  │                                 │
└──────────────────┴─────────────────────────────────┘
```

- **Trabajo**: Corridas (`/`), Experimentos (`/experiments`), Comparar (`/compare`)
- **Definiciones**: Prompt sets (`/prompts`), Catálogos (`/catalog`)
- **Sistema**: Plataforma (`/platform`)
- **Acción primaria**: `+ Nueva corrida` → `/compose` (D4)
- **`TargetBadge`**: se conserva, va en el header del contenido
- **Píldora de corrida viva**: fps + latencia, clickeable al detalle. Fuente: el campo
  `live` que `listRuns` ya devuelve, polleado a 5000 ms (mismo patrón que `useTarget`)
- **Breadcrumbs** en rutas de detalle (`/runs/:id`, `/experiments/:id`)
- **`maxWidth`**: 1100 → ~1600

Las rutas **no cambian**. Es reagrupación de navegación y layout, no re-ruteo.

### 4.4 Flujos

Cada flujo ataca un loop:

| Loop | Flujo | Superficie |
|---|---|---|
| Iterar prompts | **Relanzar variando** desde el detalle → precarga el compositor | BFF (§5.1) + prefill existente |
| Comparar | **Checkboxes** en la tabla → botón Comparar | Frontend (`/compare?runs=` ya existe) |
| Vigilar en vivo | **Píldora** en sidebar + fila de `StatTile` en el detalle | Frontend (`listRuns.live`) |
| Revisar histórico | **Filtro y búsqueda** en Corridas (modelo, prompt set, estado) | Frontend (filtrado en cliente) |

Tres de cuatro son frontend puro. El filtrado es en cliente: `listRuns` ya trae todo y el
volumen de corridas no justifica paginación de servidor.

## 5. El endpoint de composición

### 5.1 Por qué es necesario

`GET /api/runs/{id}` devuelve un **resumen**, no una composición. Reconstruir el payload de
`POST /api/runs` desde ahí es imposible:

| Campo de `Composition` | ¿Está en `GET /api/runs/{id}`? |
|---|---|
| `prompts.set_id` | **Sí** (`summary.prompt_set_id`) |
| `run.stride` | **Sí** (`summary.run_descriptor.rate_control.stride`) |
| `ingest.plugin` | No — solo `source_type`, mapeo lossy en `video`/`video_frame` |
| `ingest.config.dataset` / `.path` / `.url` | **No** — la fuente concreta se pierde |
| `prompts.active_ids` | No — inferible de `detections_by_prompt_id`, pero solo lista lo que detectó algo: no fiable |
| `run.max_units`, `save_*`, `name` | No |
| `manifest_model_ref` | No — `summary.model_name` es el nombre (`grounding_dino`), no el ref (`grounding-dino/gdino-tiny`) |

Se pierde justo lo mínimo indispensable: **qué fuente usó la corrida**.

Tampoco sirve el manifiesto: **no hay ningún identificador que una un manifiesto con las
corridas lanzadas desde él**. El slug nunca viaja en el launch, `run_manifest.json` tiene
`config_file: null`, y `run.name` se persiste `null`. Arreglar eso de raíz toca el
media-plane y queda **fuera de alcance** (se ofreció y se descartó).

### 5.2 La salida

`effective_config.yaml` se escribe en cada run y **contiene todo**: `source{type, ref,
dataset_id, path, url, split, ...}`, `prompts{ref, active_ids, set_inline}`,
`rate_control{stride}`, `run{name, max_units}`, `outputs{save_annotated_video,
save_previews}`, `model{ref, ...}`. Ya es alcanzable por HTTP: el media-plane lo sirve en
`GET /api/runs/{id}/artifacts/effective_config.yaml` y el BFF lo proxea.

Y su forma es **casi 1:1** con la del manifiesto que `ComposePage` ya sabe precargar vía
`?from=` (`source` / `prompts` / `rate_control` / `run` / `outputs` / `model`).

### 5.3 Contrato

`GET /api/runs/{id}/composition` → lee `effective_config.yaml` del run dir, devuelve JSON
**con forma de manifiesto** para reusar el prefill existente casi sin código nuevo.

- **200**: manifiesto
- **404**: run inexistente, o run sin `effective_config.yaml`

Frontend: `/compose?fromRun=<id>` reusa el mecanismo de `?from=` — mismo patrón (query
param → traer objeto → setear form), incluido el guard `lastPrefilledFrom` que evita pisar
ediciones del usuario en un re-fetch.

**Caso borde obligatorio**: `prompts.ref` puede venir `null` cuando el set viaja inline
(`set_inline`); en ese caso el id sale de `resolved_prompt_set`.

## 6. Errores

La lógica de mapeo por página se conserva intacta (D7): 409 (ya hay experimento activo),
422 (validación), 502 (target caído). Cambia solo la presentación: `ErrorBanner` con
`--status-error` en vez de texto rojo inline. `ApiError` (`status` + `payload`) no se toca.

## 7. Testing

Los 62 tests actuales chequean texto y presencia (`.toBeTruthy()` / `.toBeNull()`), no
estilos: **el retema no debería romperlos**. Cobertura nueva:

- **Shell y nav** — `App.tsx` hoy no tiene ningún test. Con nav agrupada, breadcrumbs y
  píldora, necesita: grupos renderizados, link activo, píldora visible solo con run vivo.
- **Flujos** — selección→comparar (checkboxes producen el `?runs=` correcto); prefill
  desde corrida (`?fromRun=` puebla el form).
- **Endpoint** — pytest: 200 con forma de manifiesto, 404 sin `effective_config.yaml`, y
  el caso `prompts.ref: null` → `resolved_prompt_set`.

**Riesgo anotado**: `spec44c_gate.test.tsx` (3 tests) y `GroupedBars.test.tsx` (4 tests)
podrían asertar estructura o atributos SVG. Si el retema los rompe, se arreglan — pero es
una decisión consciente, no una sorpresa.

## 8. Tramos

**Tramo 1 — fundamentos + shell**
`tokens.css`, kit de 7 componentes, shell con sidebar agrupado + breadcrumbs + píldora,
migración de las 9 páginas a los componentes. Elimina `CELL`/`ROW` duplicadas, los hex en
TS y los 3 `className` muertos. Resultado visible y usable al cerrar.

**Tramo 2 — flujos**
Endpoint `GET /api/runs/{id}/composition` + `?fromRun=`; checkboxes→comparar; filtros en
Corridas; `StatTile` en el detalle.

## 9. Fuera de alcance

- Light mode (tokens quedan listos; no se construye)
- Tailwind / shadcn / cualquier dependencia nueva
- Persistir el link manifiesto↔run en el media-plane (§5.1) — ofrecido y descartado
- ESLint / Prettier
- Re-ruteo: las rutas se conservan
- Reescritura de la §4 de Spec B (ya marcada superseded por el doc de twonode-visibility)

## 10. Criterios de éxito

1. Ningún hex de color literal en `.tsx` / `.ts`; todos los colores salen de tokens.
2. `CELL` y `ROW` no existen más en ningún archivo.
3. Los 3 `className` muertos tienen CSS real o desaparecen.
4. Los 6 destinos están agrupados en 3 grupos; "Nueva corrida" es acción, no destino.
5. Comparar dos corridas no requiere tipear ids.
6. Relanzar variando una corrida existente: un click al compositor precargado.
7. La corrida viva es visible desde cualquier pantalla.
8. Los 62 tests siguen verdes (o su ruptura fue una decisión registrada), más los nuevos.
