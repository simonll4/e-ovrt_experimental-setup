# Spec 44 C — Webconsole frontend: vistas de experimento (React)

> **EJECUTADO el 2026-07-11.** Las 5 tareas + 1 fix completas (webconsole/frontend **39→55 passed**,
> `tsc --noEmit` limpio; revisión final **LISTO PARA MERGE**, sin Critical/Important). Resultados:
> `docs/operacion/53` §9 (repo `docs`). Vistas de experimento (lista, disparo orquestado, alertas,
> reporte con badge no-temporal ADR-013), aditivas sobre el frontend existente. Gate discriminante
> por mutación. Fix del review: la columna de nombre de métrica leía el campo equivocado (`name`).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar al frontend React de la webconsole las **vistas de experimento** (spec 44 §5.2): navegación/lista de experimentos, **disparo orquestado** desde la UI, vista de detalle con **alertas** y **reporte** (con detección **no-temporal** ADR-013). Consume las rutas del backend B (`/api/experiments/*`). Sigue exactamente las convenciones del frontend existente (fetch + `request<T>`, `useEffect`+`useState` con guard `alive`, estilos inline, tests Vitest+RTL).

**Architecture:** `webconsole/frontend/` (React 18, Vite 5, TypeScript strict, react-router-dom v6 `HashRouter`). Cliente único `src/api.ts` (relative `/api/...`, proxy Vite → BFF). Data-loading por página con `useEffect`+`useState` (sin React Query/estado global). Estilos 100% inline `style={{}}` (sin CSS/Tailwind). Tipos centralizados en `src/types.ts`. Lógica pura en `src/*view.ts` (testeable en aislamiento, patrón `runview.ts`). **Todo es aditivo** — las páginas/tests existentes (8 files, 39 tests) no se tocan.

**Tech Stack:** React 18.3, TypeScript 5.5 (strict), Vite 5.4, Vitest 2.0 + @testing-library/react 16 + jsdom. Sin ESLint/Prettier (no hay). Sin nuevas dependencias.

## Global Constraints

- **Nunca commitear sin pedido explícito del usuario en ese turno.** Pasos "Commit" preparan; sólo si el usuario lo pide. Si no, `git add -A` sin `git commit`. SDD usa `git write-tree` (no es commit).
- **Nunca `Co-Authored-By`. Nada en GitHub sin pedido explícito** (los remotes existen; sólo se pushea a pedido).
- **Aditivo, no rompe lo existente.** Las 8 suites / 39 tests existentes NO se tocan ni fallan. No editar `api.test.ts`, `runview.ts`, las páginas de run (`RunsPage`/`RunDetailPage`/`ComposePage`/etc.) salvo `App.tsx` (agregar nav+rutas) y `src/types.ts`/`src/api.ts` (agregar, no modificar lo existente).
- **Colisión de nombres:** ya existe un tipo `Experiment` (catálogo de compose). Los tipos nuevos se llaman `ExperimentManifest`, `ExperimentRunState`, `ExperimentAlert`, `ExperimentReport` (NO `Experiment`).
- **Convenciones de test (obligatorias):**
  - `src/__tests__/`. Correr con **`npm test`** (= `vitest run`, desde `webconsole/frontend/`).
  - **NO existe `@testing-library/jest-dom`** → usar `.toBeTruthy()`/`.toBeNull()`/`.toBe(...)`, NUNCA `.toBeInTheDocument()`.
  - Tests de `api.ts`: `vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), {status})))` + `afterEach(() => vi.unstubAllGlobals())` (patrón `api.test.ts`).
  - Tests de páginas: `vi.mock('../api', async (importOriginal) => ({ ...(await importOriginal()), fn: vi.fn() }))` + `render(<Page/>)` de RTL + `vi.mocked(fn).mockResolvedValue(...)` + `waitFor`/`fireEvent`/`screen.getByRole`. `beforeEach(() => vi.clearAllMocks())`. Las páginas se renderizan **sin router wrapper** (usan `<Link>`, el warning "No routes matched" es benigno) — salvo que se use `useParams`, en cuyo caso envolver en `<MemoryRouter initialEntries={[...]}><Routes>...`.
- **Typecheck:** `npx tsc --noEmit` debe pasar (TypeScript strict; el build es `tsc && vite build`). Correr como gate de tipos además de `npm test`.
- **Estilos inline** con hex (`#b00` error, `#c80` warning, `#080` ok, `#f5f5f5` header, `#ddd` bordes); constantes `CELL`/`ROW` `CSSProperties` por archivo. Sin CSS files.
- Comentarios/strings de UI en español (con o sin tildes — es UI visible; imitar el vecino, que usa tildes en el texto visible: "Cargando…", "Nueva corrida"). En código/identificadores, sin tildes.
- **Baseline MEDIDA (2026-07-11):** `npm test` → **39 passed (8 files)**; `npx tsc --noEmit` → limpio.

---

## Task 1: Tipos + funciones de API para experimentos

**Files:**
- Modify: `src/types.ts` (tipos nuevos), `src/api.ts` (funciones nuevas)
- Test: `src/__tests__/experiment-api.test.ts`

**Interfaces:**
- Produces (en `types.ts`): `ExperimentManifestSummary { slug: string; experiment_id?: string | null; ... }`; `ExperimentRunState { experiment_id: string; status: string; ok?: boolean; media_run_id?: string; control_run_id?: string; ... }`; `ExperimentAlert { alert_id: string; condition_id: string; severity: string; timestamp_ms?: number | null; ... }`; `ExperimentReport { non_temporal: boolean; resultados?: unknown[]; identificacion?: Record<string, unknown>; ... }` (campos laxos; el reporte es un dict grande — tipar lo que la UI usa).
- Produces (en `api.ts`): `getExperimentManifests() -> ExperimentManifestSummary[]` (`GET /api/experiments/manifests`); `runExperiment(body: {slug: string}) -> {experiment_id: string}` (`POST /api/experiments/run`); `getCurrentExperiment() -> ExperimentRunState | null` (`GET /api/experiments/current`, 404 ⇒ null); `getExperiment(id) -> ExperimentRunState` (`GET /api/experiments/{id}`); `getExperimentAlerts(id) -> ExperimentAlert[]` (`GET /api/experiments/{id}/alerts`); `getExperimentReport(id) -> ExperimentReport` (`GET /api/experiments/{id}/report`). Usar `encodeURIComponent` en el id (patrón `getRun`).

- [ ] **Step 1: Escribir el test que falla** (`experiment-api.test.ts`, patrón `api.test.ts` con `vi.stubGlobal('fetch', ...)`):

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getExperiment, runExperiment, getCurrentExperiment, getExperimentAlerts } from '../api'

afterEach(() => vi.unstubAllGlobals())

function stub(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })))
}

describe('experiment api', () => {
  it('runExperiment postea a /api/experiments/run y devuelve el id', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ experiment_id: 'exp_1' }), { status: 202 }))
    vi.stubGlobal('fetch', fetchMock)
    const r = await runExperiment({ slug: 'd1' })
    expect(r.experiment_id).toBe('exp_1')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/experiments/run')
    expect((init as RequestInit).method).toBe('POST')
  })
  it('getExperiment encodea el id en la URL', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ experiment_id: 'a b', status: 'succeeded' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await getExperiment('a b')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/experiments/a%20b')
  })
  it('getCurrentExperiment devuelve null en 404', async () => {
    stub(404, { detail: 'no hay run activo' })
    expect(await getCurrentExperiment()).toBeNull()
  })
  it('getExperimentAlerts devuelve la lista', async () => {
    stub(200, [{ alert_id: 'al1', condition_id: 'CR-01', severity: 'high' }])
    const a = await getExperimentAlerts('exp_1')
    expect(a[0].alert_id).toBe('al1')
  })
})
```

- [ ] **Step 2: Correr — falla** — Run: `cd webconsole/frontend && npm test` — Expected: FAIL (funciones no existen / TS error).

- [ ] **Step 3: Implementación** — agregar los tipos a `types.ts` y las funciones a `api.ts` siguiendo el patrón one-liner `request<T>`. `getCurrentExperiment` maneja el 404 devolviendo `null` (try/catch sobre `ApiError` con `status === 404`).

- [ ] **Step 4-5:** correr (pasan) + `npx tsc --noEmit` limpio + `npm test` (Expected: 39 + 4 nuevos, todo verde).
- [ ] **Step 6: Commit (sólo si el usuario lo pidió).**

---

## Task 2: Helpers de vista puros (`experimentview.ts`)

**Files:**
- Create: `src/experimentview.ts`
- Test: `src/__tests__/experimentview.test.ts`

**Interfaces:**
- Produces: `isNonTemporal(report: ExperimentReport | null): boolean` (lee `report.non_temporal`); `alertSeverityColor(severity: string): string` (`high`→`#b00`, `medium`→`#c80`, otro→`#080`); `experimentStatusLabel(state: ExperimentRunState | null): string` (`running`→"corriendo", `succeeded`/`ok`→"OK", `failed`→"fallo", null→"—").

- [ ] **Step 1: Escribir el test que falla** (patrón `runview.test.ts`, lógica pura):

```ts
import { describe, expect, it } from 'vitest'
import { isNonTemporal, alertSeverityColor, experimentStatusLabel } from '../experimentview'

describe('isNonTemporal', () => {
  it('true cuando el reporte marca non_temporal', () => {
    expect(isNonTemporal({ non_temporal: true } as any)).toBe(true)
    expect(isNonTemporal({ non_temporal: false } as any)).toBe(false)
    expect(isNonTemporal(null)).toBe(false)
  })
})
describe('alertSeverityColor', () => {
  it('high rojo, medium ambar, otro verde', () => {
    expect(alertSeverityColor('high')).toBe('#b00')
    expect(alertSeverityColor('medium')).toBe('#c80')
    expect(alertSeverityColor('low')).toBe('#080')
  })
})
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('corriendo')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallo')
    expect(experimentStatusLabel(null)).toBe('—')
  })
})
```

- [ ] **Step 2-6:** falla → impl (funciones puras) → pasan → `tsc --noEmit` + `npm test` verde → commit guarded.

---

## Task 3: `ExperimentsPage` — lista + disparo orquestado

**Files:**
- Create: `src/pages/ExperimentsPage.tsx`
- Modify: `src/App.tsx` (nav `<Link to="/experiments">Experimentos</Link>` + `<Route path="/experiments" element={<ExperimentsPage/>}/>`)
- Test: `src/__tests__/ExperimentsPage.test.tsx`

**Interfaces:**
- Consumes: `getExperimentManifests`, `runExperiment`, `getCurrentExperiment`, `experimentStatusLabel`.
- Produces: una página que lista los manifiestos paraguas (tabla, patrón `RunsPage`), muestra el experimento activo (banner, poll `getCurrentExperiment` cada 4s mientras `status === "running"`), y un control de **disparo**: elegir un slug → botón "Ejecutar experimento" → `runExperiment({slug})` → al 202 `navigate('/experiments/'+experiment_id)`. Mapear `ApiError` por status (409 "ya hay un experimento activo"→ mostrar el `active_experiment_id`; 422 "manifiesto inválido"; 502 "servicio no disponible") con un `errorMessage()` local (patrón `PlatformPage`).

- [ ] **Step 1: Escribir el test que falla** (patrón `ComparePage.test.tsx`: `vi.mock('../api')` + RTL):

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ExperimentsPage from '../pages/ExperimentsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperimentManifests: vi.fn(), getCurrentExperiment: vi.fn(), runExperiment: vi.fn(),
}))
beforeEach(() => vi.clearAllMocks())

it('lista manifiestos y dispara un experimento', async () => {
  vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1', experiment_id: null } as any])
  vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
  vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_9' })
  render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('d1')).toBeTruthy())
  // seleccionar el slug y disparar (ajustar al control real: select/boton)
  fireEvent.click(screen.getByRole('button', { name: /ejecutar/i }))
  await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
})

it('muestra 409 con el experimento activo', async () => {
  vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
  vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
  const err = new api.ApiError(409, { active_experiment_id: 'exp_prev' })
  vi.mocked(api.runExperiment).mockRejectedValue(err)
  render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('d1')).toBeTruthy())
  fireEvent.click(screen.getByRole('button', { name: /ejecutar/i }))
  await waitFor(() => expect(screen.getByText(/exp_prev/)).toBeTruthy())
})
```

- [ ] **Step 2-6:** falla → impl (copiar el esqueleto de `RunsPage`; agregar el select de slug + botón + estado `busy`/`error`; `navigate` de `useNavigate`) → pasan → `tsc --noEmit` + `npm test` verde → wiring en `App.tsx` → commit guarded.

---

## Task 4: `ExperimentDetailPage` — estado + alertas + reporte (no-temporal)

**Files:**
- Create: `src/pages/ExperimentDetailPage.tsx`
- Modify: `src/App.tsx` (`<Route path="/experiments/:id" element={<ExperimentDetailPage/>}/>`)
- Test: `src/__tests__/ExperimentDetailPage.test.tsx`

**Interfaces:**
- Consumes: `getExperiment`, `getExperimentAlerts`, `getExperimentReport`, `isNonTemporal`, `alertSeverityColor`, `experimentStatusLabel`.
- Produces: página con `useParams` para el `id`; poll `getExperiment(id)` mientras `status === "running"`; una **tabla de alertas** (idiom de `EvalSection`: `CELL` const + header `.map` + filas; badge de severidad con `alertSeverityColor`); una **vista de reporte** que muestra los `resultados` (métrica + status + cause) y, si `isNonTemporal(report)`, un badge "diagnóstico espacial / no-temporal" y deshabilita/oculta los controles temporales. Manejar 404 (experimento/reporte inexistente) con un mensaje, no crash.

- [ ] **Step 1: Escribir el test que falla** (RTL + `vi.mock('../api')`, envolver en `MemoryRouter initialEntries={['/experiments/exp_1']}` + `Routes`/`Route path="/experiments/:id"` para que `useParams` funcione):

```tsx
// ... mock api: getExperiment, getExperimentAlerts, getExperimentReport ...
it('muestra alertas y marca no-temporal', async () => {
  vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'succeeded', ok: true } as any)
  vi.mocked(api.getExperimentAlerts).mockResolvedValue([{ alert_id: 'al1', condition_id: 'CR-01', severity: 'high' } as any])
  vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: true, resultados: [] } as any)
  render(<MemoryRouter initialEntries={['/experiments/exp_1']}><Routes>
    <Route path="/experiments/:id" element={<ExperimentDetailPage />} /></Routes></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('al1')).toBeTruthy())
  expect(screen.getByText(/no.?temporal/i)).toBeTruthy()   // badge ADR-013
})
```

- [ ] **Step 2-6:** falla → impl (copiar la estructura de `RunDetailPage`; sub-fetch de alertas + reporte en `useEffect`s; la tabla de alertas y el bloque de reporte) → pasan → `tsc --noEmit` + `npm test` verde → wiring de la ruta → commit guarded.

---

## Task 5: **Gate** — flujo por la UI + verificación por mutación (donde aplica)

**Files:**
- Test: `src/__tests__/spec44c_gate.test.tsx`

- [ ] **Step 1: Escribir el gate** — un test de integración (RTL, api mockeada) que ejercita el flujo: render `ExperimentsPage` → lista un manifiesto → dispara `runExperiment` (POST) → assert que se llamó y navegó; y un render de `ExperimentDetailPage` con un reporte `non_temporal: true` → assert que el badge no-temporal aparece Y que un reporte `non_temporal: false` NO lo muestra. Aserciones concretas.

- [ ] **Step 2: Correr el gate** — Run: `cd webconsole/frontend && npm test` — Expected: PASS.

- [ ] **Step 3: Verificar significancia (mutación) — obligatorio (sobre los helpers puros, que es donde la mutación es limpia).** Dos mutaciones, una por vez, salida literal:
  1. En `experimentview.ts`, hacer `isNonTemporal` devolver siempre `false`. Esperado: **falla** el gate (el badge no-temporal no aparece con `non_temporal: true`) o el test de Task 2. Revertí.
  2. En `ExperimentsPage`, no llamar `runExperiment` en el botón (o no navegar). Esperado: **falla** la aserción de disparo del gate. Revertí.
  Si alguna no hace fallar el gate, es vacuo: arreglalo.

- [ ] **Step 4: Suite completa + typecheck (final)** — Run: `npm test && npx tsc --noEmit` — Expected: 39 + tests nuevos, todo verde; typecheck limpio.
- [ ] **Step 5: Commit (sólo si el usuario lo pidió).**

---

## Cierre

- [ ] **Registrar la deuda:** el rediseño UX completo (§5.2) es declarado *sacrificable* — esta entrega da las vistas funcionales mínimas (lista, disparo, alertas, reporte, no-temporal). Estilos inline básicos; sin dashboard rico. Los números reales del reporte llegan con el GT (spec 43, diferido). El polling es simple (`setTimeout`); una corrida larga podría querer WS (patrón `stream.ts`) más adelante.
- [ ] **Actualizar el doc de resultados** (`docs/operacion/53` §7 o un cierre nuevo) con el frontend hecho. Banner EJECUTADO en este plan.
- [ ] **Verificación final:** pegar `npm test` (verde), `npx tsc --noEmit` (limpio), la salida de las dos mutaciones del gate.

## Alineación con spec 44 §5.2 (self-review)

| Requisito §5.2 | Task |
|---|---|
| Navegación por experimento | 3, 4 |
| Disparo orquestado desde la UI (secuencia del runner) | 3 |
| Vista de alertas (lee `/api/experiments/{id}/alerts`) | 4 |
| Vista de reporte (lee `/api/experiments/{id}/report`) | 4 |
| Detección de fuente no temporal (ADR-013) | 2, 4 |
| Rediseño UX rico | **deuda** (declarado sacrificable) |
