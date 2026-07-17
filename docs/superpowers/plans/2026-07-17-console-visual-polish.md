# Pulido visual de la consola + trace enriquecido — Spec-plan combinado

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Alcance chico: spec y plan en un solo doc.

**Fecha**: 2026-07-17 · **Estado**: aprobado (alcance "ambas" elegido por el usuario)
**Repos**: `e-ovrt_experimental-setup` (SPA + un passthrough en BFF)

**Goal:** (1) cerrar la deuda visual anotada del rediseño (tramo 1); (2) que la vista del trace *muestre*: bboxes sobre los previews, filas con alerta resaltadas, preview ampliable.

## Global Constraints
- MODO SIN COMMITS. Cero dependencias nuevas. Ningún hex nuevo en TS/TSX (colores por tokens o `SERIES_COLORS`, la paleta de datos ya validada). fireEvent/toBeTruthy. Baselines: BFF 291 · SPA 119 — cero fallos nuevos.

---

### Task 1: Pulido de consistencia (SPA)

**Files:** Modify: `src/pages/{ComparePage,ExperimentsPage,PlatformPage,ExperimentDetailPage,RunDetailPage,CatalogPage,ComposePage}.tsx`, `src/components/GroupedBars.tsx`, `src/styles/{ui,tokens}.css`.

- [ ] Los `<p>Cargando…</p>` pelados (5 páginas: Compare, Experiments, Platform, ExperimentDetail, RunDetail) → `<p className="eo-empty">Cargando…</p>` (el patrón que RunsPage ya usa). El TEXTO no cambia — los tests existentes que lo matchean siguen verdes sin tocarse.
- [ ] Espaciados crudos de layout → tokens: en los `style={{}}` de grid/flex que sobrevivieron, `gap: 16` → `gap: 'var(--space-4)'`, `gap: 20` → `'var(--space-5)'`, `gap: 12` → `'var(--space-3)'`, `gap: 4` → `'var(--space-1)'`, `gap: 32` → `'var(--space-6)'`. El `fontSize: 12` del legend de `GroupedBars` → `'var(--text-sm)'`. (Los `maxWidth`/`cursor` quedan.)
- [ ] `ui.css`: `.eo-sidebar__action { color: #fff }` (x2) → `var(--text)`; borrar el comentario de andamiaje "Se puebla en Tasks 2-4" de la línea 1.
- [ ] `tokens.css`: comentario en `--status-serious` — "reserva de la paleta de status validada (dataviz); sin consumidor aún".
- [ ] Verificación: `npx vitest run` (119, cero cambios de tests), `npx tsc --noEmit`, `npm run build`, y grep: `grep -rnE "gap: [0-9]+" src/ --include=*.tsx` → solo casos justificados si quedan.

### Task 2: bbox_norm en el trace (BFF + tipos)

**Files:** Modify: `webconsole/backend/src/eovrt_webconsole/trace.py`, `tests/test_trace.py`, `frontend/src/types.ts`.

- [ ] `compose_trace`: las detecciones del frame pasan de `{label, confidence}` a `{label, confidence, bbox_norm_xyxy}` — passthrough de `d.get("bbox_norm_xyxy")` (nullable; el DetectionEvent real siempre lo trae).
- [ ] Test: un assert en un unit existente de que `bbox_norm_xyxy` viaja (`[0.1, 0.2, 0.5, 0.9]` in → out).
- [ ] `types.ts`: `TraceDetection` gana `bbox_norm_xyxy?: number[] | null`.
- [ ] Verificación: BFF `python -m pytest -q` (291+, cero fallos nuevos); SPA `tsc --noEmit`.

### Task 3: Trace que muestra (SPA)

**Files:** Create: `src/components/PreviewWithBoxes.tsx`. Modify: `src/components/TraceSection.tsx`, `src/traceview.ts`, `src/styles/ui.css`. Test: `src/__tests__/PreviewWithBoxes.test.tsx` + append a `TraceSection.test.tsx`.

- [ ] **`PreviewWithBoxes`** (`{ src, detections, width=80 }`): contenedor `position:relative` clase `eo-preview`; `<img>` con `onError` que oculta TODO el contenedor; un `<div className="eo-preview__box">` por detección con `bbox_norm_xyxy` no nulo, posicionado `left/top/width/height` en % (`x1*100%`, `(x2-x1)*100%`...), `borderColor` por label vía `labelColor(label)`.
- [ ] **`labelColor(label: string): string`** en `traceview.ts`: hash determinista del label → índice en `SERIES_COLORS` (importada de `./components/GroupedBars` — es la excepción de paleta de datos declarada en el tramo 1; mismo label = mismo color SIEMPRE, regla dataviz "el color sigue a la entidad"). Test puro: mismo label → mismo color; labels distintos pueden repetir (hash módulo 8, ok).
- [ ] **CSS** (`ui.css`): `.eo-preview { position:relative; display:inline-block; }`, `.eo-preview__box { position:absolute; border:1.5px solid; pointer-events:none; }`, hover-zoom puro CSS: `.eo-preview:hover { transform: scale(2.2); transform-origin: left center; z-index: 10; position: relative; transition: transform .12s; }`, y resaltado de fila: `.eo-row--alert > td { background: color-mix(in srgb, var(--status-error) 8%, transparent); }`.
- [ ] **`TraceSection`**: la celda de preview usa `PreviewWithBoxes` con las detecciones del frame; `<tr className={f.alert.length ? 'eo-row--alert' : undefined}>`.
- [ ] Tests: `PreviewWithBoxes` — N cajas para N bboxes, 0 cajas si bbox null, estilos % correctos en una caja conocida; `TraceSection` — fila con alerta lleva la clase, fila sin alerta no; `labelColor` determinista.
- [ ] Verificación: `npx vitest run` (cero fallos nuevos), `tsc`, `build`.

### Gate
- [ ] Suites BFF + SPA verdes; rebuild servido en :8090; pasada visual del usuario sobre el run smoke.
