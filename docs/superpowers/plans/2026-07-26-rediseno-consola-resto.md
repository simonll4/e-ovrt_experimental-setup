# Rediseño de la consola — Resto de pantallas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the visual reskin on the five remaining, lower-priority screens
(Conjuntos de prompts, Catálogos, Plataforma, Cámaras, Clips) — `Button`/`Table`
primitives and the couple of untranslated glossary terms still visible in these pages.
No functional changes, per the design spec's own scoping for this tier of screens.

**Architecture:** Same additive approach as the four prior plans on this branch — no
backend changes, no new routing, no new primitives (everything needed already exists:
`Button`, `Table` from the foundation plan). This plan is intentionally narrow: page-
level files only. Sub-components each page renders (`PromptSetEditor`,
`CameraPresetForm`, `LivePromptPanel`, `RecordPanel`, `TrimDialog`, `LiveViewer`) are
explicitly out of scope — they weren't named in the design's per-screen list, and
touching them would expand this plan well past "visual reskin."

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom).
No new dependencies.

## Global Constraints

- No backend/BFF changes.
- Only the five page-level files listed below are in scope. Their child components
  (`PromptSetEditor.tsx`, `CameraPresetForm.tsx`, `LivePromptPanel.tsx`,
  `RecordPanel.tsx`, `TrimDialog.tsx`, `LiveViewer.tsx`) are NOT touched by this plan.
- `Button`/`Table` primitives (from the foundation plan) replace raw `<button>`/
  `<table>` at the page level only — not inside the excluded child components.
- Run `npm test` (Vitest) and `npm run build` from `webconsole/frontend/` after every task.
- Never commit unless explicitly instructed — this plan's "Commit" steps commit locally
  to the current feature branch, but do not push.

---

### Task 1: Conjuntos de prompts — dense table, Button primitive, glossary status labels

**Files:**
- Modify: `webconsole/frontend/src/pages/PromptSetsPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/PromptSetsPage.test.tsx`

**Interfaces:**
- Consumes: `Button`, `Table` from `../components/ui` (existing).

- [ ] **Step 1: Update the existing test and add a new one**

The existing file `src/__tests__/PromptSetsPage.test.tsx` has a test
`'lista los sets con badge de estado'` that asserts on the CURRENT (untranslated)
status strings — it will break once Step 3's glossary fix lands, so update it now, in
the same step, as part of this task's failing-test change:

Change:

```tsx
  it('lista los sets con badge de estado', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('eind_v1')).toBeTruthy())
    expect(screen.getByText('frozen_pending_review')).toBeTruthy()
    expect(screen.getByText('frozen')).toBeTruthy()
  })
```

to:

```tsx
  it('lista los sets con badge de estado, traducido por el glosario', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('eind_v1')).toBeTruthy())
    expect(screen.getByText('congelado, pendiente de revisión')).toBeTruthy()
    expect(screen.getByText('congelado')).toBeTruthy()
  })
```

Then add a new test in the same `describe('PromptSetsPage', ...)` block:

```tsx
  it('el botón "Nuevo set" es el primitivo Button', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo set' }).className).toContain('eo-btn'))
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PromptSetsPage.test.tsx`
Expected: FAIL — the updated assertion doesn't match yet (still raw
`'frozen_pending_review'`/`'frozen'`), and the "Nuevo set" button doesn't yet have the
`eo-btn` class.

- [ ] **Step 3: Implement the changes in `PromptSetsPage.tsx`**

Change the import:

```tsx
import { Badge, EmptyState, ErrorBanner } from '../components/ui'
```

to:

```tsx
import { Badge, Button, EmptyState, ErrorBanner, Table } from '../components/ui'
```

Change the status glossary map:

```tsx
const STATUS_LABEL: Record<string, string> = {
  exploratory: 'exploratory',
  frozen_pending_review: 'frozen_pending_review',
  frozen: 'frozen',
}
```

to:

```tsx
const STATUS_LABEL: Record<string, string> = {
  exploratory: 'exploratorio',
  frozen_pending_review: 'congelado, pendiente de revisión',
  frozen: 'congelado',
}
```

Change the "Nuevo set" button:

```tsx
<button type="button" onClick={() => setCreating(true)}>Nuevo set</button>
```

to:

```tsx
<Button variant="primary" onClick={() => setCreating(true)}>Nuevo set</Button>
```

Change the table wrapper (`<table className="eo-table">` → `<Table>`, contents
unchanged):

```tsx
<table className="eo-table">
  <thead>
    <tr><th>id</th><th>estado</th><th>track</th><th>clases</th><th>frases</th><th>deriva de</th></tr>
  </thead>
  ...
</table>
```

to:

```tsx
<Table>
  <thead>
    <tr><th>id</th><th>estado</th><th>track</th><th>clases</th><th>frases</th><th>deriva de</th></tr>
  </thead>
  ...
</Table>
```

(Keep `<tbody>` contents byte-for-byte unchanged — the `"← Prompt sets"` and per-row
`eo-linklike` buttons are deliberately left as-is; those aren't primary actions and the
`Button` primitive isn't meant for link-style affordances.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PromptSetsPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/PromptSetsPage.tsx src/__tests__/PromptSetsPage.test.tsx
git commit -m "design: Conjuntos de prompts — dense table, Button primitive, translated status labels"
```

---

### Task 2: Catálogos — dense tables

**Files:**
- Modify: `webconsole/frontend/src/pages/CatalogPage.tsx`
- Test: Create `webconsole/frontend/src/__tests__/CatalogPage.test.tsx` (this page has
  no existing test file)

**Interfaces:**
- Consumes: `Table` from `../components/ui` (existing). This page has no primary
  action buttons — it's read-only — so `Button` doesn't apply here.
- Consumes: `useTarget` from `../useTarget` — `CatalogPage` calls this hook on mount;
  mock it the same way `useTarget`-consuming tests elsewhere in this codebase do (check
  `src/__tests__/` for an existing example, e.g. any test file importing from
  `'../useTarget'`, to match the mock shape exactly).

- [ ] **Step 1: Write the failing test**

Create `src/__tests__/CatalogPage.test.tsx`:

```tsx
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CatalogPage from '../pages/CatalogPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getDatasets: vi.fn(),
  getIngestPlugins: vi.fn(),
  getPromptSets: vi.fn(),
}))

vi.mock('../useTarget', () => ({
  useTarget: () => null,
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('CatalogPage', () => {
  it('las tablas usan la clase de densidad de consola', async () => {
    vi.mocked(api.getIngestPlugins).mockResolvedValue([
      { id: 'p1', kind: 'file', description: 'desc', available: true, enabled: true } as any,
    ])
    vi.mocked(api.getDatasets).mockResolvedValue([])
    vi.mocked(api.getPromptSets).mockResolvedValue([])
    render(<CatalogPage />)
    await waitFor(() => expect(screen.getByText('p1')).toBeTruthy())
    const table = document.querySelector('.eo-table')
    expect(table?.className).toContain('eo-table--dense')
  })
})
```

If `useTarget` is mocked differently elsewhere in this codebase (e.g. returning an
object with a different shape, or the hook lives under a different mock path), match
that existing convention instead of the stub above — grep `src/__tests__/` for
`useTarget` first and follow whatever pattern already exists.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/CatalogPage.test.tsx`
Expected: FAIL — no element has the `eo-table--dense` class yet.

- [ ] **Step 3: Implement the changes in `CatalogPage.tsx`**

Add `Table` to the import:

```tsx
import { Card, EmptyState } from '../components/ui'
```

to:

```tsx
import { Card, EmptyState, Table } from '../components/ui'
```

Replace all four occurrences of `<table className="eo-table">` / `</table>` with
`<Table>` / `</Table>` — the "Modelo del target" table, the "Plugins de ingesta" table,
the "Datasets" table, and the "Prompt sets (in-repo)" table. Leave every `<thead>`/
`<tbody>` exactly as they are; this is a wrapper-only change repeated four times in the
same file.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/CatalogPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/CatalogPage.tsx src/__tests__/CatalogPage.test.tsx
git commit -m "design: Catálogos — dense tables"
```

---

### Task 3: Plataforma — dense table, Button primitive, glossary "ready" header

**Files:**
- Modify: `webconsole/frontend/src/pages/PlatformPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/PlatformPage.test.tsx`

**Interfaces:**
- Consumes: `Button`, `Table` from `../components/ui` (existing).

- [ ] **Step 1: Write the failing tests**

Read `src/__tests__/PlatformPage.test.tsx` first for its existing mock/render pattern.
Add:

```tsx
  it('la columna se llama "operativa", no "ready"', async () => {
    vi.mocked(api.getInstances).mockResolvedValue([
      { name: 'inst_1', model_ref: 'gdino', state: 'ready', ready: true, is_target: true } as any,
    ])
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText('operativa')).toBeTruthy())
    expect(screen.queryByText('ready')).toBeNull()
  })

  it('"Apagar" es el primitivo Button', async () => {
    vi.mocked(api.getInstances).mockResolvedValue([
      { name: 'inst_1', model_ref: 'gdino', state: 'ready', ready: true, is_target: true } as any,
    ])
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Apagar' }).className).toContain('eo-btn'))
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PlatformPage.test.tsx`
Expected: FAIL — the header still says `'ready'`, and the "Apagar" button doesn't yet
have the `eo-btn` class.

- [ ] **Step 3: Implement the changes in `PlatformPage.tsx`**

Change the import:

```tsx
import { Badge, ErrorBanner } from '../components/ui'
```

to:

```tsx
import { Badge, Button, ErrorBanner, Table } from '../components/ui'
```

Change the header array:

```tsx
{['instancia', 'modelo', 'estado', 'ready', '', ''].map((h, i) => (
```

to:

```tsx
{['instancia', 'modelo', 'estado', 'operativa', '', ''].map((h, i) => (
```

Change the table wrapper:

```tsx
<table className="eo-table" style={{ maxWidth: 760 }}>
```

to:

```tsx
<Table style={{ maxWidth: 760 }}>
```

(and its closing `</table>` to `</Table>`).

Change the two action buttons:

```tsx
<button onClick={() => activate(r.name)} disabled={busy !== null}>
  {busy === r.name ? 'Activando…' : 'Activar'}
</button>
```

to:

```tsx
<Button variant="primary" onClick={() => activate(r.name)} disabled={busy !== null}>
  {busy === r.name ? 'Activando…' : 'Activar'}
</Button>
```

and:

```tsx
<button onClick={stop} disabled={busy !== null}>Apagar</button>
```

to:

```tsx
<Button variant="danger" onClick={stop} disabled={busy !== null}>Apagar</Button>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/PlatformPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/PlatformPage.tsx src/__tests__/PlatformPage.test.tsx
git commit -m "design: Plataforma — dense table, Button primitive, glosario (operativa)"
```

---

### Task 4: Cámaras — Button primitive on page-level actions

**Files:**
- Modify: `webconsole/frontend/src/pages/CamerasPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/CamerasPage.test.tsx`

**Interfaces:**
- Consumes: `Button` from `../components/ui` (existing). This page has no page-level
  `<table>`, so `Table` doesn't apply here. `CameraPresetForm`/`RecordPanel`/
  `LivePromptPanel`/`LiveViewer` are separate components NOT touched by this task —
  only the buttons rendered directly by `CamerasPage.tsx` itself are in scope.

- [ ] **Step 1: Write the failing test**

`src/__tests__/CamerasPage.test.tsx` mocks the API via a `vi.hoisted(() => ({ ... }))`
object called `mocks` (not `vi.mocked(api.foo)`), and its `beforeEach` already sets
`mocks.listCameras.mockResolvedValue([{ id: 'oak_d_lab', name: 'OAK-D laboratorio',
plugin: 'oak_d', config: {} }])` plus `mocks.getPreview`/`mocks.usePreviewStream`
defaults — read the top of the file to confirm before writing this test, then add,
inside the existing `describe('CamerasPage', ...)` block:

```tsx
  it('"Nuevo preset" es el primitivo Button', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo preset' }).className).toContain('eo-btn'))
  })
```

(No new mock setup needed — the file's existing `beforeEach` default preset list
already gets `CamerasPage` to a rendered state where "Nuevo preset" is visible, and
`renderPage()` is the existing helper function already defined in this file.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/CamerasPage.test.tsx`
Expected: FAIL — "Nuevo preset" doesn't yet have the `eo-btn` class.

- [ ] **Step 3: Implement the changes in `CamerasPage.tsx`**

Add `Button` to the import:

```tsx
import { Badge, Card, DetChip, EmptyState, ErrorBanner } from '../components/ui'
```

to:

```tsx
import { Badge, Button, Card, DetChip, EmptyState, ErrorBanner } from '../components/ui'
```

Convert each of these page-level buttons (leave everything else — including the
`<CameraPresetForm>`/`<RecordPanel>`/`<LivePromptPanel>`/`<LiveViewer>` children —
untouched):

```tsx
<button type="button" onClick={recheck}>Reintentar</button>
```
→
```tsx
<Button variant="secondary" onClick={recheck}>Reintentar</Button>
```

```tsx
<button type="button" onClick={resume}>Retomar stream</button>
```
→
```tsx
<Button variant="secondary" onClick={resume}>Retomar stream</Button>
```

```tsx
<button type="button" onClick={() => void disconnect()}>Detener</button>
```
(the one inside the `resumable` paragraph)
→
```tsx
<Button variant="secondary" onClick={() => void disconnect()}>Detener</Button>
```

```tsx
<button type="button" onClick={() => void disconnect()}>Desconectar</button>
```
(the one inside the Viewer card, a different call site than the one above — both exist
in the file)
→
```tsx
<Button variant="secondary" onClick={() => void disconnect()}>Desconectar</Button>
```

```tsx
<button type="button" onClick={() => setEditing('new')}>Nuevo preset</button>
```
→
```tsx
<Button variant="primary" onClick={() => setEditing('new')}>Nuevo preset</Button>
```

```tsx
<button
  type="button"
  disabled={Boolean(busy) || needsPromptSet}
  onClick={() => void connect(p)}
>
  Conectar
</button>
```
→
```tsx
<Button
  variant="primary"
  disabled={Boolean(busy) || needsPromptSet}
  onClick={() => void connect(p)}
>
  Conectar
</Button>
```

```tsx
<button type="button" onClick={() => setEditing(p)}>Editar</button>
```
→
```tsx
<Button variant="secondary" onClick={() => setEditing(p)}>Editar</Button>
```

```tsx
<button
  type="button"
  className="eo-btn--danger"
  onClick={() => {
    if (!window.confirm(`¿Borrar el preset ${p.id}?`)) return
    void deleteCamera(p.id).then(() => {
      // Sin esto queda una cámara fantasma en el panel de
      // grabación: el botón sigue habilitado sobre un
      // preset que ya no existe y falla recién al grabar.
      setLastChosen((prev) => (prev?.id === p.id ? null : prev))
      return refreshPresets()
    })
  }}
>
  Eliminar
</button>
```
→
```tsx
<Button
  variant="danger"
  onClick={() => {
    if (!window.confirm(`¿Borrar el preset ${p.id}?`)) return
    void deleteCamera(p.id).then(() => {
      // Sin esto queda una cámara fantasma en el panel de
      // grabación: el botón sigue habilitado sobre un
      // preset que ya no existe y falla recién al grabar.
      setLastChosen((prev) => (prev?.id === p.id ? null : prev))
      return refreshPresets()
    })
  }}
>
  Eliminar
</Button>
```

(Dropping the manual `className="eo-btn--danger"` in favor of the `Button` component's
own `variant="danger"` — same visual result, now via the primitive.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/CamerasPage.test.tsx`
Expected: PASS (all tests, old and new — every existing query in this test file that
targets these buttons by role/name keeps working, since `Button` renders a native
`<button>` with the same children).

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/CamerasPage.tsx src/__tests__/CamerasPage.test.tsx
git commit -m "design: Cámaras — Button primitive on page-level actions"
```

---

### Task 5: Clips — Button primitive on page-level actions

**Files:**
- Modify: `webconsole/frontend/src/pages/ClipsPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ClipsPage.test.tsx`

**Interfaces:**
- Consumes: `Button` from `../components/ui` (existing). `TrimDialog` is a separate
  component NOT touched by this task. The row-pick `<button className="eo-row__pick">`
  elements (the whole clip row acting as a click target) are deliberately left as raw
  buttons — they're a full-row affordance styled by `.eo-row__pick`, not a case the
  `Button` primitive (built for a fixed-height, padded action button) fits.

- [ ] **Step 1: Write the failing test**

`src/__tests__/ClipsPage.test.tsx` mocks `getMasters`/`getClips` as named imports
(`vi.mocked(getMasters)`, not `vi.mocked(api.getMasters)`) and already has a `MASTERS`
fixture array at the top of the file with entries shaped like `{ name, scenario,
size_bytes, duration_ms, readable, clips }`. Add, inside the existing
`describe('ClipsPage', ...)` block, reusing that existing `MASTERS` fixture:

```tsx
  it('"Recortar" es el primitivo Button', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('P1-a-take1.mp4')).toBeTruthy())
    const boton = screen.getAllByText('Recortar')[0].closest('button') as HTMLButtonElement
    expect(boton.className).toContain('eo-btn')
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ClipsPage.test.tsx`
Expected: FAIL — "Recortar" doesn't yet have the `eo-btn` class.

- [ ] **Step 3: Implement the changes in `ClipsPage.tsx`**

Add `Button` to the import:

```tsx
import { Card, EmptyState, ErrorBanner } from '../components/ui'
```

to:

```tsx
import { Button, Card, EmptyState, ErrorBanner } from '../components/ui'
```

Change the "Recortar" button:

```tsx
<button
  type="button"
  disabled={!m.readable}
  onClick={() => setPanel({ kind: 'trim', master: m })}
>
  Recortar
</button>
```

to:

```tsx
<Button
  variant="secondary"
  disabled={!m.readable}
  onClick={() => setPanel({ kind: 'trim', master: m })}
>
  Recortar
</Button>
```

Change the "Cerrar" button:

```tsx
<button type="button" onClick={() => setPanel(null)}>
  Cerrar
</button>
```

to:

```tsx
<Button variant="secondary" onClick={() => setPanel(null)}>
  Cerrar
</Button>
```

Leave the `eo-row__pick` button (the clickable clip row) exactly as it is.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ClipsPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ClipsPage.tsx src/__tests__/ClipsPage.test.tsx
git commit -m "design: Clips — Button primitive on page-level actions"
```

---

## After this plan

This is the last plan in the redesign's priority order — all 11 screens will have been
visually re-skinned on the shared foundation (tokens, glossary, `Button`/`Select`/
`Table`/`MonoCell` primitives, responsive `Shell`).

Still-parked items, none addressed by this plan (all pre-existing, none load-bearing for
these five screens specifically): the bench_split mismatch-warning null-blindness bug in
`ComparePage.tsx`; the 15%/40% status fill/border variant system (only the Run Detail
row band exists); `LiveRunPill.tsx`'s own hardcoded `'corriendo'` string (now the sole
glossary inconsistency after the Experimentos plan's fix); `.eo-mono`'s hardcoded
`font-size` making identifiers look small inside headings; no shared Vitest `cleanup`/
`setupFiles`; converting the native `<select>` elements in `ExperimentsPage.tsx`/
`DeriveExperimentForm.tsx` to the custom `Select` primitive (blocked on a native-
fallback-compatible `Select` behavior). These are all candidates for a dedicated
cleanup pass, not urgent enough to justify another full plan on their own.
