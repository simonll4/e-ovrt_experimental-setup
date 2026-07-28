# Rediseño de la consola — Experimentos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin Experimentos (`ExperimentsPage.tsx`) and Detalle de experimento
(`ExperimentDetailPage.tsx`) on top of the existing foundation: glossary status labels,
condition names, the manifest list showing the fields it actually has (`group`/
`description`, not fabricated aggregates), and `Table`/`MonoCell`/`Button` density.

**Architecture:** Same additive approach as the three prior plans on this branch — no
backend changes, no new routing. Builds on the tokens, `Badge`/`Button`/`Table`/
`MonoCell` primitives, and `labels.ts` glossary module from the foundation plan, and the
`conditionLabel`/status-label glossary patterns established in the Detalle de corrida
and Comparar plans.

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom).
No new dependencies.

## Global Constraints

- No backend/BFF changes.
- The manifest list shows only fields `ExperimentManifestSummary` actually has (`slug`,
  `experiment_id`, `description`, `group`) — no invented status/count/date columns (that
  data doesn't exist in this endpoint; see the design spec's gap-resolution table).
- Identifiers (`slug`, `experiment_id`, `alert_id`, `media_run_id`, `control_run_id`)
  render in monospace.
- Condition codes (`CR-01`, `CR-02`) always show their readable name via `conditionLabel`,
  never bare.
- **Deliberately out of scope for this plan**: converting the two native `<select>`
  elements in `ExperimentsPage.tsx` (the launcher slug picker and the "basado en" picker
  in the derive form) to the custom `Select` primitive. One of this screen's own tests
  (`'espera la recarga de manifiestos antes de seleccionar el slug derivado'` in
  `ExperimentsPage.test.tsx`) depends on a genuine native-`<select>` browser behavior —
  when the bound `value` doesn't match any current `<option>`, the browser falls back to
  showing the first option, and that fallback is exactly the safety mechanism the test
  (and the code comment above it) documents. The custom `Select` primitive has no such
  native fallback today, and giving it one is a real, separate design decision, not a
  drop-in swap. Leave both `<select>`s as native elements in this plan.
- Run `npm test` (Vitest) and `npm run build` from `webconsole/frontend/` after every task.
- Never commit unless explicitly instructed — this plan's "Commit" steps commit locally
  to the current feature branch, but do not push.

---

### Task 1: glossary status labels for experiments

**Files:**
- Modify: `webconsole/frontend/src/experimentview.ts`
- Test: Modify `webconsole/frontend/src/__tests__/experimentview.test.ts`

**Interfaces:**
- `experimentStatusLabel`/`experimentStatusTone` keep their existing signatures —
  consumed unchanged by `ExperimentsPage.tsx` and `ExperimentDetailPage.tsx`.

- [ ] **Step 1: Update the failing test**

In `src/__tests__/experimentview.test.ts`, change:

```ts
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('corriendo')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallo')
    expect(experimentStatusLabel(null)).toBe('—')
  })
})
```

to:

```ts
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('en curso')
    expect(experimentStatusLabel({ status: 'succeeded' } as any)).toBe('completada')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallida')
    expect(experimentStatusLabel(null)).toBe('—')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/experimentview.test.ts`
Expected: FAIL — `experimentStatusLabel` still returns the old strings.

- [ ] **Step 3: Update `experimentStatusLabel` in `experimentview.ts`**

Change:

```ts
export function experimentStatusLabel(state: ExperimentRunState | null): string {
  if (state === null) return '—'
  if (state.status === 'running') return 'corriendo'
  if (state.status === 'succeeded' || state.ok === true) return 'OK'
  if (state.status === 'failed') return 'fallo'
  return state.status
}
```

to:

```ts
export function experimentStatusLabel(state: ExperimentRunState | null): string {
  if (state === null) return '—'
  if (state.status === 'running') return 'en curso'
  if (state.status === 'succeeded' || state.ok === true) return 'completada'
  if (state.status === 'failed') return 'fallida'
  return state.status
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/experimentview.test.ts`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS (no other test file asserts on the old `'corriendo'`/`'OK'`/`'fallo'`
strings — confirm this by grepping for them across `src/` before running, and report if
you find any other consumer).

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/experimentview.ts src/__tests__/experimentview.test.ts
git commit -m "design: glossary status labels for experiments (en curso/completada/fallida)"
```

---

### Task 2: condition names via the glossary

**Files:**
- Modify: `webconsole/frontend/src/pages/ExperimentDetailPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx`

**Interfaces:**
- Consumes: `conditionLabel` from `../labels` (existing).

- [ ] **Step 1: Write the failing tests**

Add `getControlCurrent: vi.fn()` to the existing `vi.mock('../api', ...)` list at the
top of `ExperimentDetailPage.test.tsx`:

```tsx
vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperiment: vi.fn(),
  getExperimentAlerts: vi.fn(),
  getExperimentReport: vi.fn(),
  getControlCurrent: vi.fn(),
}))
```

Add these two tests inside `describe('ExperimentDetailPage', ...)`:

```tsx
  it('la condición de una alerta muestra el nombre legible del glosario', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_5', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([
      { alert_id: 'al5', condition_id: 'CR-02', severity: 'high' } as any,
    ])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_5')
    await waitFor(() => expect(screen.getByText(/CR-02 — Presencia de persona sin chaleco/)).toBeTruthy())
  })

  it('un patrón de riesgo activo muestra el nombre legible de la condición', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_6', status: 'running' } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockRejectedValue(new api.ApiError(404, {}))
    vi.mocked(api.getControlCurrent).mockResolvedValue({
      patterns: [{ pattern_id: 'CR-01', condition_id: 'CR-01', severity: 'high', state: 'confirmed', active_ms: 5000 }],
    } as any)
    renderPage('exp_6')
    await waitFor(() => expect(screen.getByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy())
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx`
Expected: FAIL — the two new tests fail (condition codes still render bare).

- [ ] **Step 3: Implement the changes in `ExperimentDetailPage.tsx`**

Add the import: `import { conditionLabel } from '../labels'`

Change the `RiskActiveBanner`'s badge:

```tsx
<Badge tone={alertSeverityTone(p.severity)}>{p.condition_id}</Badge>
```

to:

```tsx
<Badge tone={alertSeverityTone(p.severity)}>{conditionLabel(p.condition_id)}</Badge>
```

Change the Alertas table's condition cell:

```tsx
<td>{a.condition_id}</td>
```

to:

```tsx
<td>{conditionLabel(a.condition_id)}</td>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ExperimentDetailPage.tsx src/__tests__/ExperimentDetailPage.test.tsx
git commit -m "design: condition names via glossary in Detalle de experimento"
```

---

### Task 3: Experimentos — manifest fields, dense table, Button primitive

**Files:**
- Modify: `webconsole/frontend/src/pages/ExperimentsPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ExperimentsPage.test.tsx`

**Interfaces:**
- Consumes: `Button`, `Table`, `MonoCell` from `../components/ui` (existing).

- [ ] **Step 1: Write the failing tests**

Add to `src/__tests__/ExperimentsPage.test.tsx`, inside `describe('ExperimentsPage', ...)`:

```tsx
  it('muestra grupo y descripción del manifiesto cuando vienen', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([
      { slug: 'd1', experiment_id: null, group: 'S1', description: 'set inicial' } as any,
    ])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('S1')).toBeTruthy())
    expect(screen.getByText('set inicial')).toBeTruthy()
  })

  it('sin grupo/descripción muestra guion en esas columnas', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd2', experiment_id: null } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d2').length).toBeGreaterThan(0))
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2)
  })

  it('el slug de un manifiesto en la tabla se muestra en monoespaciada', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1', experiment_id: null } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => {
      const cells = screen.getAllByText('d1')
      expect(cells.some((el) => el.className.includes('eo-mono'))).toBe(true)
    })
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentsPage.test.tsx`
Expected: FAIL — the 3 new tests fail (no group/description columns, no monospace slug
cell yet).

- [ ] **Step 3: Implement the changes in `ExperimentsPage.tsx`**

Change the import from `components/ui`:

```tsx
import { Badge, Card, ErrorBanner, EmptyState, Field } from '../components/ui'
```

to:

```tsx
import { Badge, Button, Card, ErrorBanner, EmptyState, Field, MonoCell, Table } from '../components/ui'
```

Change the "Lanzar experimento" button:

```tsx
<button onClick={trigger} disabled={busy || !slug || blocked}>
  {busy ? 'Lanzando…' : 'Lanzar experimento'}
</button>
```

to:

```tsx
<Button variant="primary" onClick={trigger} disabled={busy || !slug || blocked}>
  {busy ? 'Lanzando…' : 'Lanzar experimento'}
</Button>
```

Change the manifest table's header, body, and the "Derivar" button:

```tsx
<table className="eo-table">
  <thead>
    <tr>
      {['slug', 'experimento', ''].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  <tbody>
    {rows.map((r) => (
      <tr key={r.slug}>
        <td>{r.slug}</td>
        <td>
          {r.experiment_id ? (
            <Link to={`/experiments/${r.experiment_id}`}>{r.experiment_id}</Link>
          ) : '—'}
        </td>
        <td>
          <button onClick={() => setFormMode({ source: r.slug, selectable: false })}>
            Derivar
          </button>
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

to:

```tsx
<Table>
  <thead>
    <tr>
      {['slug', 'grupo', 'descripción', 'experimento', ''].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  <tbody>
    {rows.map((r) => (
      <tr key={r.slug}>
        <MonoCell>{r.slug}</MonoCell>
        <td>{r.group ?? '—'}</td>
        <td>{r.description ?? '—'}</td>
        <td>
          {r.experiment_id ? (
            <Link to={`/experiments/${r.experiment_id}`}>
              <span className="eo-mono">{r.experiment_id}</span>
            </Link>
          ) : '—'}
        </td>
        <td>
          <Button variant="secondary" onClick={() => setFormMode({ source: r.slug, selectable: false })}>
            Derivar
          </Button>
        </td>
      </tr>
    ))}
  </tbody>
</Table>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentsPage.test.tsx`
Expected: PASS (all tests, old and new — the existing tests query by button role/name
and by row text, both unaffected by the `Table`/`Button`/`MonoCell` swap).

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ExperimentsPage.tsx src/__tests__/ExperimentsPage.test.tsx
git commit -m "design: Experimentos — manifest group/description columns, dense table, Button primitive"
```

---

### Task 4: Detalle de experimento — dense tables, monospace identifiers

**Files:**
- Modify: `webconsole/frontend/src/pages/ExperimentDetailPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ExperimentDetailPage.test.tsx`

**Interfaces:**
- Consumes: `Table`, `MonoCell` from `../components/ui` (existing).

- [ ] **Step 1: Write the failing test**

Add to `src/__tests__/ExperimentDetailPage.test.tsx`:

```tsx
  it('el experiment_id del encabezado y el alert_id de la tabla se muestran en monoespaciada', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_7', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([
      { alert_id: 'al7', condition_id: 'CR-01', severity: 'high' } as any,
    ])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_7')
    await waitFor(() => expect(screen.getByText('exp_7').className).toContain('eo-mono'))
    expect(screen.getByText('al7').className).toContain('eo-mono')
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx`
Expected: FAIL — neither `exp_7` nor `al7` currently render in an element with the
`eo-mono` class.

- [ ] **Step 3: Implement the changes in `ExperimentDetailPage.tsx`**

Update the import from `components/ui`:

```tsx
import { Badge, Card, EmptyState, ErrorBanner } from '../components/ui'
```

to:

```tsx
import { Badge, Card, EmptyState, ErrorBanner, MonoCell, Table } from '../components/ui'
```

Change the header:

```tsx
<h2>
  {experiment.experiment_id} — <Badge tone={experimentStatusTone(experiment)}>{experimentStatusLabel(experiment)}</Badge>
</h2>
<p>
  media run: {experiment.media_run_id ?? '—'} · control run: {experiment.control_run_id ?? '—'}
</p>
```

to:

```tsx
<h2>
  <span className="eo-mono">{experiment.experiment_id}</span>{' '}
  — <Badge tone={experimentStatusTone(experiment)}>{experimentStatusLabel(experiment)}</Badge>
</h2>
<p>
  media run: <span className="eo-mono">{experiment.media_run_id ?? '—'}</span>
  {' '}· control run: <span className="eo-mono">{experiment.control_run_id ?? '—'}</span>
</p>
```

Change the Alertas table (`<table className="eo-table">` → `<Table>`, `alert_id` cell →
`MonoCell`):

```tsx
<table className="eo-table">
  <thead>
    <tr>
      {['alerta', 'condicion', 'severidad', 'ts (ms)'].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  <tbody>
    {alerts.map((a) => (
      <tr key={a.alert_id}>
        <td>{a.alert_id}</td>
        <td>{conditionLabel(a.condition_id)}</td>
        <td>
          <Badge tone={alertSeverityTone(a.severity)}>{a.severity}</Badge>
        </td>
        <td className="eo-num">{a.timestamp_ms ?? '—'}</td>
      </tr>
    ))}
  </tbody>
</table>
```

to:

```tsx
<Table>
  <thead>
    <tr>
      {['alerta', 'condicion', 'severidad', 'ts (ms)'].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  <tbody>
    {alerts.map((a) => (
      <tr key={a.alert_id}>
        <MonoCell>{a.alert_id}</MonoCell>
        <td>{conditionLabel(a.condition_id)}</td>
        <td>
          <Badge tone={alertSeverityTone(a.severity)}>{a.severity}</Badge>
        </td>
        <td className="eo-num">{a.timestamp_ms ?? '—'}</td>
      </tr>
    ))}
  </tbody>
</Table>
```

(This table already has `conditionLabel(a.condition_id)` from Task 2 — don't
reintroduce the bare `{a.condition_id}`.)

Change the Reporte table (`<table className="eo-table">` → `<Table>`, contents
unchanged):

```tsx
<table className="eo-table">
  <thead>
    <tr>
      {['metrica', 'status', 'causa'].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  ...
</table>
```

to:

```tsx
<Table>
  <thead>
    <tr>
      {['metrica', 'status', 'causa'].map((h) => (
        <th key={h}>{h}</th>
      ))}
    </tr>
  </thead>
  ...
</Table>
```

(Keep the `<tbody>` contents exactly as they are — this is only the wrapper-element
swap, same as done in the Comparar and Detalle de corrida plans.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx`
Expected: PASS (all tests, old and new).

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ExperimentDetailPage.tsx src/__tests__/ExperimentDetailPage.test.tsx
git commit -m "design: Detalle de experimento — dense tables, monospace identifiers"
```

---

## After this plan

Next in priority order: the lower-priority rest (Prompt sets, Catálogos, Plataforma,
Cámaras, Clips) — visual reskin only, per the design doc, since they already work fine
with current data.

Still-parked items, carried forward again: converting the two native `<select>`
elements in `ExperimentsPage.tsx`/`DeriveExperimentForm.tsx` to the custom `Select`
primitive (blocked on giving `Select` a native-fallback-compatible behavior first, or a
deliberate decision to accept different semantics and rewrite the dependent test);
condition codes still not rendered in monospace inside `conditionLabel`'s combined
string (now shipped a fourth time — this is the last screen in the priority list that
leans on condition codes this heavily; recommend deciding before starting the "resto"
screens, since after this there's no more forcing function); the bench_split
mismatch-warning null-blindness bug found in the Comparar plan's final review (not
touched by this plan — `ComparePage.tsx` isn't in this plan's file list); the 15%/40%
status fill/border variant system (still only the Run Detail row band); `Table`'s
missing header-row helpers; the dead `--sidebar-width-collapsed` token; `RunsPage`'s
empty-state text not distinguishing "no data" from "filter matched nothing"; no shared
Vitest `cleanup`/`setupFiles` (several test files render more than once per file without
`afterEach(cleanup)` and pass only by luck of query specificity).
