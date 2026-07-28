# Rediseño de la consola — Comparar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin the Comparar screen (`ComparePage.tsx`) on top of the existing
foundation: add the bench_split-mismatch warning and condition-name glossary wording the
design spec calls for (both use data the screen already loads — no backend gap), and
apply the `Table`/`MonoCell` density primitives.

**Architecture:** Same additive approach as the prior two plans on this branch — no
backend changes, no new routing. Builds on the tokens, `Badge`/`Table`/`MonoCell`
primitives, and `labels.ts` glossary module from
`docs/superpowers/plans/2026-07-26-rediseno-consola-fundacion-corridas.md`, and the
condition-name usage pattern established in
`docs/superpowers/plans/2026-07-26-rediseno-consola-detalle-corrida.md`'s `EvalSection`
wording (`${conditionLabel('CR-01')} (exhaustividad: …)`).

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom).
No new dependencies.

## Global Constraints

- No backend/BFF changes.
- The bench_split-mismatch warning uses `CompareRunEntry.bench_split` (already loaded by
  this screen via `getCompare()` — confirmed in `types.ts`, no API gap).
- Every status/warning still pairs an icon/glyph with text, never color alone.
- Identifiers (`run_id`) render in monospace via the `eo-mono` class or `MonoCell`.
- `SERIES_COLORS` in `GroupedBars.tsx` (the categorical dataviz palette) is validated
  for colorblind-safety and must NOT be touched by this plan — it's a separate,
  deliberately distinct palette from the status-color tokens.
- Run `npm test` (Vitest) and `npm run build` from `webconsole/frontend/` after every task.
- Never commit unless explicitly instructed — this plan's "Commit" steps commit locally
  to the current feature branch, but do not push.

---

### Task 1: bench_split mismatch warning + CR-01 glossary wording

**Files:**
- Modify: `webconsole/frontend/src/pages/ComparePage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ComparePage.test.tsx`

**Interfaces:**
- Consumes: `conditionLabel` from `../labels` (existing, from the foundation plan).
- No new exports — `bestPerRow` and `ComparePage`'s default export are unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `src/__tests__/ComparePage.test.tsx`, inside the existing `describe('ComparePage', ...)`
block:

```tsx
  it('corridas con distinto bench_split muestran aviso', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue({
      ...COMPARE,
      runs: [
        { ...COMPARE.runs[0], bench_split: 'bench_v2_test' },
        { ...COMPARE.runs[1], bench_split: 'bench_v3' },
      ],
    })
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText(/run_a/)).toBeTruthy())
    fireEvent.click(screen.getByRole('checkbox', { name: /run_a/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /run_b/ }))
    await waitFor(() => expect(screen.getByText(/conjuntos de evaluación distintos/i)).toBeTruthy())
  })

  it('corridas con el mismo bench_split no muestran aviso', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText(/run_a/)).toBeTruthy())
    fireEvent.click(screen.getByRole('checkbox', { name: /run_a/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /run_b/ }))
    await waitFor(() => expect(screen.getAllByText('gdino · bench_v2_test').length).toBeGreaterThan(0))
    expect(screen.queryByText(/conjuntos de evaluación distintos/i)).toBeNull()
  })

  it('la fila de CR-01 usa el nombre legible del glosario', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText(/run_a/)).toBeTruthy())
    fireEvent.click(screen.getByRole('checkbox', { name: /run_a/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /run_b/ }))
    await waitFor(() => expect(screen.getByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy())
  })
```

Note: `COMPARE.runs[0].bench_split` and `COMPARE.runs[1].bench_split` are both
`'bench_v2_test'` in the existing fixture (see the top of the test file) — that's what
makes the "same bench_split" test pass unmodified and the "distinto" test need an
override via spread.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: FAIL — the 3 new tests fail (no warning text exists, no glossary wording on
the CR-01 row yet).

- [ ] **Step 3: Implement the changes in `ComparePage.tsx`**

Add the import:

```tsx
import { conditionLabel } from '../labels'
```

Add this block right after the `{result.skipped.length > 0 && (...)}` block and before
the `<table className="eo-table">`:

```tsx
{(() => {
  const splits = new Set(
    result.runs.map((r) => r.bench_split).filter((b): b is string => b !== null),
  )
  return splits.size > 1 ? (
    <p className="eo-note--warn">
      ⚠ Estás comparando corridas sobre conjuntos de evaluación distintos (
      {result.runs.map((r) => r.bench_split ?? 'sin dato').join(' vs. ')}).
    </p>
  ) : null
})()}
```

Change the `CR-01 recall` row:

```tsx
<MetricRow
  name="CR-01 recall"
  values={result.runs.map((r) => r.cr01_detection_recall)}
/>
```

to:

```tsx
<MetricRow
  name={`${conditionLabel('CR-01')} (exhaustividad)`}
  values={result.runs.map((r) => r.cr01_detection_recall)}
/>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: PASS (all tests, old and new).

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ComparePage.tsx src/__tests__/ComparePage.test.tsx
git commit -m "design: Comparar — bench_split mismatch warning + CR-01 glossary wording"
```

---

### Task 2: dense table + monospace run ids

**Files:**
- Modify: `webconsole/frontend/src/pages/ComparePage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ComparePage.test.tsx`

**Interfaces:**
- Consumes: `Table` from `../components/ui` (existing, from the foundation plan) —
  replaces the raw `<table className="eo-table">` element. `MetricRow`'s own manual
  `className={i === best ? 'eo-num eo-best' : 'eo-num'}` logic is untouched (it already
  produces the correct dense/tabular-nums styling via the existing `.eo-num` CSS rule —
  no `NumCell` swap needed here since `NumCell` doesn't yet accept an extra className
  for the `eo-best` highlight, and adding that isn't in this task's scope).

- [ ] **Step 1: Write the failing test**

Add to `src/__tests__/ComparePage.test.tsx`:

```tsx
  it('el id de una corrida en el selector se muestra en monoespaciada', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText('run_a').className).toContain('eo-mono'))
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: FAIL — `run_a` isn't currently wrapped in an element with the `eo-mono` class.

- [ ] **Step 3: Implement the changes in `ComparePage.tsx`**

Add `Table` and `MonoCell` to the existing `components/ui` import:

```tsx
import { Badge, EmptyState, ErrorBanner, MonoCell, Table } from '../components/ui'
```

Change the run-picker label:

```tsx
{r.run_id} — {r.model ?? '—'} · {r.bench_split ?? '—'}
```

to:

```tsx
<span className="eo-mono">{r.run_id}</span> — {r.model ?? '—'} · {r.bench_split ?? '—'}
```

Change the skipped-runs badge to show its id in monospace too:

```tsx
{result.skipped.map((id) => (
  <Badge key={id} tone="warn">
    {id}
  </Badge>
))}
```

to:

```tsx
{result.skipped.map((id) => (
  <Badge key={id} tone="warn">
    <span className="eo-mono">{id}</span>
  </Badge>
))}
```

Change the results table wrapper from `<table className="eo-table">` / `</table>` to
`<Table>` / `</Table>` (keep the `<thead>`/`<tbody>` contents exactly as they are —
`Table` renders a `<table>` with both `eo-table` and `eo-table--dense` classes, a
superset of what's there today).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 6: Commit**

```bash
cd webconsole/frontend
git add src/pages/ComparePage.tsx src/__tests__/ComparePage.test.tsx
git commit -m "design: Comparar — dense table + monospace run ids"
```

---

## After this plan

Next in priority order: Experimentos + Detalle de experimento, then the lower-priority
rest (Prompt sets, Catálogos, Plataforma, Cámaras, Clips).

Still-parked items, carried forward again (none were load-bearing for Comparar
specifically, so none were addressed here): condition codes are not rendered in
monospace within `conditionLabel`'s combined "CODE — Name" string (a Minor, twice-parked
item — worth a deliberate decision, e.g. a small JSX-returning glossary helper, next time
a screen's *primary* content is condition codes rather than a single row label); the
15%/40% status fill/border variant system is still only partially built (just the Run
Detail row band); `Select`'s missing accessible-label prop (not used on this screen
either); `Table`'s missing header-row helpers; the dead `--sidebar-width-collapsed`
token; `RunsPage`'s empty-state text not distinguishing "no data" from "filter matched
nothing."
