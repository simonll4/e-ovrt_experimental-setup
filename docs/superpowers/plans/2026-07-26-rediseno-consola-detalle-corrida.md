# Rediseño de la consola — Detalle de corrida Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin the Detalle de corrida screen (`RunDetailPage.tsx` + `TraceSection.tsx`)
on top of the tokens/primitives/glossary/Shell foundation from the prior plan: replace
the paginated trace view with a full-run activity index (fetched once, all pages, per
the design's chosen adaptation), add a compact clickable timeline strip, and finish the
glossary/token consistency pass this screen needs (condition names, monospace fallback
for unrecognized control-drop-reason codes, and the "alerta confirmada" tone actually
used for confirmed-risk rows instead of the generic error tone).

**Architecture:** Same additive approach as the prior plan — no backend changes, no new
routing. This plan builds on the tokens, `Badge`/`Button`/`Table`/`MonoCell`/`Select`
primitives, `labels.ts` glossary module, and responsive `Shell` from
`docs/superpowers/plans/2026-07-26-rediseno-consola-fundacion-corridas.md` (already
merged on this branch).

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom),
react-router-dom v6. No new dependencies.

## Global Constraints

- No backend/BFF changes of any kind.
- Dark-only theme, off-white text (`#f2f1ed`), never pure white.
- Never encode state with color alone — status always pairs icon/glyph with text.
- Identifiers (`run_id`, unit ids) and condition codes (`CR-01`, `CR-02`) are never
  translated and always render in monospace. An **unrecognized** `control` drop-reason
  code is not an identifier by convention elsewhere in this codebase, but per the design
  spec it must still render in monospace when it falls back to the raw code (since at
  that point it IS effectively an untranslated literal, same as an id) — see Task 3.
- The trace timeline is built by fetching all `/trace` pages on open (already decided,
  not re-litigated here) and assembling the complete per-frame index client-side. A
  partial-fetch failure (a later page fails after the first succeeded) must not blank
  the screen — show a banner and keep whatever loaded.
- No server-side pagination/filtering added — all in-memory, client-side.
- Follow the existing `eo-*` CSS class naming convention; reuse the `Button`/`Badge`
  primitives from the prior plan rather than raw `<button>`/inline status colors.
- Every changed page/component keeps or extends its existing Vitest test file — never
  rewritten from scratch conceptually, though `TraceSection.test.tsx`'s pagination-era
  tests are replaced with fetch-all-era equivalents (that IS the intended behavior
  change, not test rot).
- Run `npm test` (Vitest) and `npm run build` from `webconsole/frontend/` after every task.
- Never commit unless explicitly instructed — this plan's "Commit" steps commit locally
  to the current feature branch as part of the working pattern, but do not push.

---

### Task 1: `TraceSection` — fetch the full run's trace, replace pagination

**Files:**
- Modify: `webconsole/frontend/src/components/TraceSection.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/TraceSection.test.tsx`

**Interfaces:**
- Consumes: `getTrace(id, page, pageSize, controlRunId?): Promise<TracePage>` from
  `api.ts` (unchanged signature) — called in a loop instead of once.
- Produces: no new exports; `TraceSection` keeps its existing `{ runId: string }` props,
  so `RunDetailPage.tsx` (which renders `<TraceSection key={id} runId={id} />`) needs no
  change for this task.

- [ ] **Step 1: Replace the full contents of `TraceSection.tsx`**

```tsx
import { useEffect, useState } from 'react'
import { artifactUrl, getTrace } from '../api'
import { Badge, Card, DetChip, EmptyState, ErrorBanner, StatTile } from './ui'
import { controlLabel, controlTone, frameHasActivity } from '../traceview'
import { alertSeverityTone } from '../experimentview'
import PreviewWithBoxes from './PreviewWithBoxes'
import type { TraceFrame, TracePage } from '../types'

type TraceMeta = Omit<TracePage, 'frames'>

export default function TraceSection({ runId }: { runId: string }) {
  const [meta, setMeta] = useState<TraceMeta | null>(null)
  const [frames, setFrames] = useState<TraceFrame[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [partialError, setPartialError] = useState<string | null>(null)
  const [soloActividad, setSoloActividad] = useState(false)

  useEffect(() => {
    let alive = true
    setMeta(null)
    setFrames(null)
    setError(null)
    setPartialError(null)

    async function loadAll() {
      let first: TracePage
      try {
        first = await getTrace(runId, 1, 50)
      } catch (e) {
        if (alive) setError(String(e))
        return
      }
      if (!alive) return
      const { frames: firstFrames, ...firstMeta } = first
      setMeta(firstMeta)
      let acc = firstFrames
      setFrames(acc)
      const totalPages = Math.max(1, Math.ceil(first.total / first.page_size))
      for (let p = 2; p <= totalPages; p++) {
        if (!alive) return
        try {
          const next = await getTrace(runId, p, first.page_size)
          if (!alive) return
          acc = acc.concat(next.frames)
          setFrames(acc)
        } catch (e) {
          if (alive) {
            setPartialError(
              `línea de tiempo incompleta: no se pudieron cargar todos los cuadros (${String(e)})`,
            )
          }
          return
        }
      }
    }

    loadAll()
    return () => {
      alive = false
    }
  }, [runId])

  if (error) return <ErrorBanner>Error cargando la traza: {error}</ErrorBanner>
  if (!meta || !frames) return <p>Cargando traza…</p>

  const { totals } = meta
  const visibleFrames = soloActividad ? frames.filter(frameHasActivity) : frames
  const hasControl = meta.control_run_id !== null || !!meta.control_error

  return (
    <Card title="Evaluación del control-plane">
      {partialError && <ErrorBanner>{partialError}</ErrorBanner>}
      <div className="eo-stats-row">
        <StatTile label="run de control" value={meta.control_run_id ?? '—'} />
        <StatTile label="alertas" value={totals.alerts} />
        {Object.entries(totals.dropped_by_reason).map(([reason, count]) => (
          <StatTile key={reason} label={controlLabel(`dropped:${reason}`)} value={count} />
        ))}
        {totals.not_received !== null && <StatTile label="no recibidos" value={totals.not_received} />}
      </div>
      {meta.topology === 'two_node' && <small>descartes internos n/d en two-node</small>}
      {meta.control_error && (
        <ErrorBanner>control-plane no disponible: {meta.control_error}</ErrorBanner>
      )}
      {meta.control_run_id === null && !meta.control_error && (
        <EmptyState>no evaluado por el control-plane</EmptyState>
      )}
      <label>
        <input
          type="checkbox"
          checked={soloActividad}
          onChange={(e) => setSoloActividad(e.target.checked)}
        />{' '}
        solo frames con actividad
      </label>
      <table className="eo-table">
        <thead>
          <tr>
            <th>frame</th>
            <th>detecciones</th>
            {hasControl && <th>control</th>}
            {hasControl && <th>patrón</th>}
          </tr>
        </thead>
        <tbody>
          {visibleFrames.map((f: TraceFrame) => (
            <tr key={f.unit_id ?? f.frame_index} className={f.alert.length > 0 ? 'eo-row--alert' : undefined}>
              <td>
                <div className="eo-framecell">
                  {f.unit_id !== null && (
                    <PreviewWithBoxes
                      src={artifactUrl(runId, `previews/${f.unit_id}.preview.jpg`)}
                      alt={f.unit_id}
                      detections={f.detections ?? []}
                    />
                  )}
                  <span className="eo-framecell__id">
                    {[f.frame_index !== null ? `#${f.frame_index}` : null, f.unit_id]
                      .filter((x) => x !== null && x !== '')
                      .join(' · ')}
                  </span>
                </div>
              </td>
              <td>
                {f.detections === null || f.detections.length === 0 ? (
                  '—'
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', alignItems: 'flex-start' }}>
                    {f.detections.map((d, i) => (
                      <DetChip key={i} label={d.label} confidence={d.confidence} />
                    ))}
                  </div>
                )}
              </td>
              {hasControl && (
                <td>
                  <Badge tone={controlTone(f.control)}>{controlLabel(f.control)}</Badge>
                </td>
              )}
              {hasControl && (
                <td>
                  {f.progress.map((p, i) => (
                    <div className="eo-patternrow" key={i}>
                      <span className="eo-patternrow__id">{p.condition_id}</span>
                      <div className="eo-progressbar">
                        <div
                          className={`eo-progressbar__fill${f.alert.some((a) => a.condition_id === p.condition_id) ? ' eo-progressbar__fill--alert' : ''}`}
                          style={{ width: `${p.progress * 100}%` }}
                        />
                      </div>
                      <span className="eo-patternrow__pct">{Math.round(p.progress * 100)}%</span>
                    </div>
                  ))}
                  {f.alert.map((a, i) => (
                    <Badge key={i} tone="error">
                      ALERTA {a.condition_id}
                    </Badge>
                  ))}
                  {(f.active_patterns ?? []).map((p, i) => (
                    <div className="eo-patternrow" key={`active-${i}`}>
                      <Badge tone={alertSeverityTone(p.severity)}>{p.condition_id}</Badge>
                      <span>riesgo activo</span>
                    </div>
                  ))}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
```

Note: the "pág. X de Y anterior/siguiente" footer is gone entirely — there is no more
pagination UI, since the whole run's trace is now loaded and rendered at once. Condition
codes (`{p.condition_id}`, `{a.condition_id}`) and the `tone="error"` on the ALERTA badge
are deliberately left unchanged in this task — that's Task 3's job.

- [ ] **Step 2: Replace the full contents of `TraceSection.test.tsx`**

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import TraceSection from '../components/TraceSection'
import * as api from '../api'
import type { TracePage } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTrace: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

function basePage(overrides: Partial<TracePage> = {}): TracePage {
  return {
    media_run_id: 'r_1',
    control_run_id: 'ctrl_1',
    topology: 'one_node',
    control_error: null,
    totals: {
      frames: 3,
      detections: 1,
      dropped_by_reason: { rate_gate: 1 },
      alerts: 1,
      received: 1,
      not_received: 0,
    },
    page: 1,
    page_size: 50,
    total: 3,
    frames: [
      {
        frame_index: 0,
        unit_id: 'u0',
        timestamp_ms: 0,
        detections: [{ label: 'person', confidence: 0.91 }],
        control: 'received',
        progress: [{ condition_id: 'CR-01', progress: 0.5 }],
        alert: [],
      },
      {
        frame_index: 1,
        unit_id: 'u1',
        timestamp_ms: 100,
        detections: null,
        control: 'dropped:rate_gate',
        progress: [],
        alert: [],
      },
      {
        frame_index: 2,
        unit_id: null,
        timestamp_ms: 200,
        detections: [],
        control: 'received',
        progress: [],
        alert: [{ condition_id: 'CR-02', severity: 'high' }],
      },
    ],
    ...overrides,
  }
}

describe('TraceSection', () => {
  it('renderiza tiles, badges y la barra de progreso', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(screen.getAllByText('1', { selector: '.eo-stat__value' }).length).toBe(2)
    expect(screen.getAllByText('recibido')[0].className).toContain('eo-badge--ok')
    expect(screen.getByText('límite de tasa', { selector: '.eo-badge' }).className).toContain('eo-badge--warn')
    const fill = document.querySelector('.eo-progressbar__fill') as HTMLElement
    expect(fill.style.width).toBe('50%')
  })

  it('frame_index null (corrida image_folder) muestra el unit_id en vez de "#null"', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: null,
            unit_id: 'img_000002',
            timestamp_ms: null,
            detections: [{ label: 'helmet', confidence: 0.8 }],
            control: 'received',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('img_000002')).toBeTruthy())
  })

  it('sin control_run_id muestra EmptyState', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        control_run_id: null,
        control_error: null,
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [{ label: 'person', confidence: 0.9 }],
            control: 'n/d',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('no evaluado por el control-plane')).toBeTruthy())
    expect(screen.queryByText('control')).toBeNull()
    expect(screen.queryByText('patrón')).toBeNull()
  })

  it('control_error muestra ErrorBanner y la tabla sigue presente', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({ control_error: 'control-plane no responde' }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() =>
      expect(screen.getByText(/control-plane no disponible/)).toBeTruthy(),
    )
    expect(document.querySelector('.eo-table')).toBeTruthy()
  })

  it('filtro solo frames con actividad oculta la fila inactiva', async () => {
    const page = basePage()
    page.frames.push({
      frame_index: 3,
      unit_id: 'u3',
      timestamp_ms: 300,
      detections: [],
      control: 'received',
      progress: [],
      alert: [],
    })
    vi.mocked(api.getTrace).mockResolvedValue(page)
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#3 · u3')).toBeTruthy())
    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)
    await waitFor(() => expect(screen.queryByText('#3 · u3')).toBeFalsy())
  })

  it('solo pinta --alert en la barra cuya condition_id coincide con la alerta', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [{ label: 'person', confidence: 0.91 }],
            control: 'received',
            progress: [
              { condition_id: 'CR-01', progress: 0.5 },
              { condition_id: 'CR-02', progress: 0.3 },
            ],
            alert: [{ condition_id: 'CR-02', severity: 'high' }],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    const fills = document.querySelectorAll('.eo-progressbar__fill')
    expect(fills.length).toBe(2)
    expect((fills[0] as HTMLElement).className).not.toContain('--alert')
    expect((fills[1] as HTMLElement).className).toContain('--alert')
  })

  it('un frame sin alerta/progreso propios pero con active_patterns muestra "activo" (el bug real: frame_000456)', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 456,
            unit_id: 'u456',
            timestamp_ms: 15400,
            detections: [{ label: 'person', confidence: 0.9 }],
            control: 'received',
            progress: [],
            alert: [],
            active_patterns: [
              { pattern_id: 'CR-01', condition_id: 'CR-01', severity: 'high', subject_key: 'k1' },
            ],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText(/activo/i)).toBeTruthy())
    expect(screen.getByText('CR-01', { selector: '.eo-badge' })).toBeTruthy()
  })

  it('un frame sin active_patterns no muestra "activo"', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(screen.queryByText(/riesgo activo/i)).toBeNull()
  })

  it('la fila con alerta lleva eo-row--alert, la fila sin alerta no', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    const rows = document.querySelectorAll('.eo-table tbody tr')
    // frame 0: alert=[] -> sin clase; frame 2: alert=[CR-02] -> con clase
    expect(rows[0].className).not.toContain('eo-row--alert')
    expect(rows[2].className).toContain('eo-row--alert')
  })

  it('trae todas las páginas y acumula los frames de cada una', async () => {
    const page1 = basePage({
      total: 4,
      page: 1,
      page_size: 2,
      frames: [
        { frame_index: 0, unit_id: 'u0', timestamp_ms: 0, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 1, unit_id: 'u1', timestamp_ms: 100, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    const page2 = basePage({
      total: 4,
      page: 2,
      page_size: 2,
      frames: [
        { frame_index: 2, unit_id: 'u2', timestamp_ms: 200, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 3, unit_id: 'u3', timestamp_ms: 300, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    vi.mocked(api.getTrace).mockResolvedValueOnce(page1).mockResolvedValueOnce(page2)
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#3 · u3')).toBeTruthy())
    expect(api.getTrace).toHaveBeenNthCalledWith(1, 'r_1', 1, 50)
    expect(api.getTrace).toHaveBeenNthCalledWith(2, 'r_1', 2, 2)
    expect(screen.getByText('#0 · u0')).toBeTruthy()
    expect(screen.getByText('#1 · u1')).toBeTruthy()
    expect(screen.getByText('#2 · u2')).toBeTruthy()
  })

  it('si falla una página intermedia, muestra banner de traza incompleta pero mantiene lo ya cargado', async () => {
    const page1 = basePage({
      total: 4,
      page: 1,
      page_size: 2,
      frames: [
        { frame_index: 0, unit_id: 'u0', timestamp_ms: 0, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 1, unit_id: 'u1', timestamp_ms: 100, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    vi.mocked(api.getTrace).mockResolvedValueOnce(page1).mockRejectedValueOnce(new Error('timeout'))
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#1 · u1')).toBeTruthy())
    await waitFor(() => expect(screen.getByText(/línea de tiempo incompleta/)).toBeTruthy())
    expect(screen.getByText('#0 · u0')).toBeTruthy()
  })
})
```

The old "el botón siguiente dispara getTrace con la página siguiente" test is gone — there
is no more "siguiente" button. Its replacement is the new "trae todas las páginas…" test
above, which verifies the same underlying mechanism (calling `getTrace` with an
incrementing page number) but for the new fetch-all behavior instead of a user-triggered
one.

- [ ] **Step 3: Run the test file to confirm it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceSection.test.tsx`
Expected: PASS (11 tests).

- [ ] **Step 4: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds. `RunDetailPage.test.tsx`'s `getTrace` mock already
returns `total: 0` (see that file), which makes `totalPages = 1`, so it needs no changes
— confirm this by checking its result stays green.

- [ ] **Step 5: Commit**

```bash
cd webconsole/frontend
git add src/components/TraceSection.tsx src/__tests__/TraceSection.test.tsx
git commit -m "design: TraceSection fetches the full run's trace instead of paginating"
```

---

### Task 2: `TraceTimeline` — compact clickable activity strip

**Files:**
- Create: `webconsole/frontend/src/components/TraceTimeline.tsx`
- Modify: `webconsole/frontend/src/components/TraceSection.tsx`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/TraceTimeline.test.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/TraceSection.test.tsx`

**Interfaces:**
- Produces: `TraceTimeline({ frames: TraceFrame[] }): JSX.Element | null`, default
  export. Renders one clickable tick per frame; clicking a tick scrolls the
  corresponding table row (rendered by `TraceSection`) into view. Frame rows get a new
  `id={`frame-${f.unit_id ?? f.frame_index}`}` attribute so the timeline can target them.
- Consumes: `controlTone` from `traceview.ts` (existing) to color ticks by delivery
  status, overridden to the `alert` tone when the frame has a confirmed alert.

- [ ] **Step 1: Write the failing test for `TraceTimeline`**

Create `src/__tests__/TraceTimeline.test.tsx`:

```tsx
import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import TraceTimeline from '../components/TraceTimeline'
import type { TraceFrame } from '../types'

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})
afterEach(() => cleanup())

function frame(overrides: Partial<TraceFrame> = {}): TraceFrame {
  return {
    frame_index: 0,
    unit_id: 'u0',
    timestamp_ms: 0,
    detections: [],
    control: 'received',
    progress: [],
    alert: [],
    ...overrides,
  }
}

describe('TraceTimeline', () => {
  it('sin frames no renderiza nada', () => {
    const { container } = render(<TraceTimeline frames={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renderiza un tick por frame', () => {
    render(
      <TraceTimeline
        frames={[frame({ frame_index: 0, unit_id: 'u0' }), frame({ frame_index: 1, unit_id: 'u1' })]}
      />,
    )
    expect(document.querySelectorAll('.eo-timeline__tick').length).toBe(2)
  })

  it('un frame con alerta confirmada lleva el modificador --alert', () => {
    render(
      <TraceTimeline
        frames={[
          frame({ frame_index: 0, unit_id: 'u0' }),
          frame({ frame_index: 1, unit_id: 'u1', alert: [{ condition_id: 'CR-02', severity: 'high' }] }),
        ]}
      />,
    )
    const ticks = document.querySelectorAll('.eo-timeline__tick')
    expect(ticks[0].className).not.toContain('--alert')
    expect(ticks[1].className).toContain('--alert')
  })

  it('clickear un tick hace scrollIntoView sobre la fila del frame correspondiente', () => {
    render(<TraceTimeline frames={[frame({ frame_index: 5, unit_id: 'u5' })]} />)
    const target = document.createElement('tr')
    target.id = 'frame-u5'
    document.body.appendChild(target)
    fireEvent.click(screen.getByRole('listitem'))
    expect(target.scrollIntoView).toHaveBeenCalled()
    document.body.removeChild(target)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceTimeline.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `TraceTimeline.tsx`**

```tsx
import { controlTone } from '../traceview'
import type { TraceFrame } from '../types'

function frameKey(f: TraceFrame): string {
  return String(f.unit_id ?? f.frame_index)
}

function frameLabel(f: TraceFrame): string {
  return [f.frame_index !== null ? `#${f.frame_index}` : null, f.unit_id]
    .filter((x) => x !== null && x !== '')
    .join(' · ')
}

const TONE_VAR: Record<string, string> = {
  live: 'var(--status-live)',
  ok: 'var(--status-ok)',
  warn: 'var(--status-warn)',
  alert: 'var(--status-alert)',
  error: 'var(--status-error)',
  neutral: 'var(--status-neutral)',
}

export default function TraceTimeline({ frames }: { frames: TraceFrame[] }) {
  if (frames.length === 0) return null

  return (
    <div className="eo-timeline" role="list" aria-label="línea de tiempo de la corrida">
      {frames.map((f) => {
        const key = frameKey(f)
        const hasAlert = f.alert.length > 0
        const tone = hasAlert ? 'alert' : controlTone(f.control)
        return (
          <button
            key={key}
            type="button"
            role="listitem"
            className={`eo-timeline__tick${hasAlert ? ' eo-timeline__tick--alert' : ''}`}
            style={{ background: TONE_VAR[tone] }}
            title={frameLabel(f)}
            onClick={() => document.getElementById(`frame-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
          />
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Add the CSS**

Add to `styles/ui.css`, near the `.eo-progressbar` section:

```css
/* Línea de tiempo — franja compacta de actividad de toda la corrida, clickeable. */
.eo-timeline {
  display: flex;
  gap: 1px;
  overflow-x: auto;
  padding: var(--space-2);
  background: var(--surface-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: var(--space-3);
}
.eo-timeline__tick {
  flex: 0 0 4px;
  height: 24px;
  border: none;
  border-radius: 1px;
  cursor: pointer;
  padding: 0;
}
.eo-timeline__tick--alert {
  outline: 2px solid var(--status-alert);
  outline-offset: -1px;
}
```

- [ ] **Step 5: Wire `TraceTimeline` into `TraceSection`**

In `src/components/TraceSection.tsx`:
1. Add the import: `import TraceTimeline from './TraceTimeline'`
2. Render `<TraceTimeline frames={frames} />` immediately above the `<table className="eo-table">`.
3. Add `id={`frame-${f.unit_id ?? f.frame_index}`}` to the `<tr>` inside the `.map`, so
   the timeline's `scrollIntoView` target exists — the `<tr>` line becomes:
   ```tsx
   <tr
     key={f.unit_id ?? f.frame_index}
     id={`frame-${f.unit_id ?? f.frame_index}`}
     className={f.alert.length > 0 ? 'eo-row--alert' : undefined}
   >
   ```

- [ ] **Step 6: Add one integration assertion to `TraceSection.test.tsx`**

Add to the existing `describe('TraceSection', ...)` block:

```tsx
  it('muestra la línea de tiempo con un tick por frame', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(document.querySelectorAll('.eo-timeline__tick').length).toBe(3)
  })
```

- [ ] **Step 7: Run tests to verify everything passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceTimeline.test.tsx src/__tests__/TraceSection.test.tsx`
Expected: all PASS.

- [ ] **Step 8: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 9: Commit**

```bash
cd webconsole/frontend
git add src/components/TraceTimeline.tsx src/components/TraceSection.tsx src/styles/ui.css src/__tests__/TraceTimeline.test.tsx src/__tests__/TraceSection.test.tsx
git commit -m "design: add TraceTimeline (clickable full-run activity strip)"
```

---

### Task 3: Glossary & token consistency pass — condition names, monospace fallback, alert tone

**Files:**
- Modify: `webconsole/frontend/src/traceview.ts` (new helper)
- Modify: `webconsole/frontend/src/components/TraceSection.tsx`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Modify: `webconsole/frontend/src/components/EvalSection.tsx`
- Modify: `webconsole/frontend/src/pages/RunDetailPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/traceview.test.ts`
- Test: Modify `webconsole/frontend/src/__tests__/TraceSection.test.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/EvalSection.test.tsx`

**Interfaces:**
- Consumes: `conditionLabel` from `labels.ts` (built in the prior plan).
- Produces: `controlLabelIsRaw(control: string): boolean` from `traceview.ts` — true
  when `controlLabel` is about to return an untranslated raw code (i.e. an unrecognized
  `dropped:*` reason), used by `TraceSection` to render that specific badge text in
  monospace.

This task addresses two items the final review of the prior plan explicitly parked for
this next plan: (1) the "alerta confirmada" status color (`--status-alert`) wasn't yet
used anywhere — it's needed exactly for the confirmed-alert row band and badge in this
screen; (2) an unrecognized `control` drop-reason must fall back to the raw code **in
monospace** (today it falls back to the raw code correctly, per the prior plan, but not
in monospace).

- [ ] **Step 1: Write the failing test for `controlLabelIsRaw`**

Add to `src/__tests__/traceview.test.ts`, a new `describe` block:

```ts
describe('controlLabelIsRaw', () => {
  it('es true para un motivo de descarte no reconocido', () => {
    expect(controlLabelIsRaw('dropped:queue_full')).toBe(true)
  })
  it('es false para un motivo de descarte conocido', () => {
    expect(controlLabelIsRaw('dropped:rate_gate')).toBe(false)
    expect(controlLabelIsRaw('dropped:overload')).toBe(false)
  })
  it('es false para recibido/no recibido/n-d (no son "dropped")', () => {
    expect(controlLabelIsRaw('received')).toBe(false)
    expect(controlLabelIsRaw('not_received')).toBe(false)
    expect(controlLabelIsRaw('n/d')).toBe(false)
  })
})
```

Update the import line at the top of `traceview.test.ts` to include the new function:

```ts
import { controlTone, controlLabel, controlLabelIsRaw, frameHasActivity, labelColor } from '../traceview'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/traceview.test.ts`
Expected: FAIL — `controlLabelIsRaw` is not exported.

- [ ] **Step 3: Implement `controlLabelIsRaw` in `traceview.ts`**

Add this function to `src/traceview.ts` (near `controlLabel`), and update the import at
the top of the file to also bring in `CONTROL_DROP_REASONS` (it's already imported from
the prior plan's Task 6 — check before adding a duplicate import):

```ts
export function controlLabelIsRaw(control: string): boolean {
  if (!control.startsWith('dropped:')) return false
  const reason = control.slice('dropped:'.length)
  return !(reason in CONTROL_DROP_REASONS)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/traceview.test.ts`
Expected: PASS.

- [ ] **Step 5: Use `conditionLabel` and `controlLabelIsRaw` in `TraceSection.tsx`, and switch confirmed-alert coloring to the `alert` tone**

In `src/components/TraceSection.tsx`:

1. Update the import line to add `conditionLabel` and `controlLabelIsRaw`:
   ```tsx
   import { controlLabel, controlLabelIsRaw, controlTone, frameHasActivity } from '../traceview'
   import { conditionLabel } from '../labels'
   ```

2. Change the control badge to render its text in monospace only when it's an
   unrecognized raw fallback:
   ```tsx
   <Badge tone={controlTone(f.control)}>
     <span className={controlLabelIsRaw(f.control) ? 'eo-mono' : undefined}>
       {controlLabel(f.control)}
     </span>
   </Badge>
   ```

3. Change the progress row's condition id to show the readable name:
   ```tsx
   <span className="eo-patternrow__id">{conditionLabel(p.condition_id)}</span>
   ```

4. Change the ALERTA badge to use the `alert` tone (not `error`) and the readable name:
   ```tsx
   {f.alert.map((a, i) => (
     <Badge key={i} tone="alert">
       ALERTA {conditionLabel(a.condition_id)}
     </Badge>
   ))}
   ```

5. Change the active-pattern badge to use the readable name (its tone already comes from
   `alertSeverityTone`, which is a different, existing severity-based mapping — leave
   that call as-is):
   ```tsx
   <Badge tone={alertSeverityTone(p.severity)}>{conditionLabel(p.condition_id)}</Badge>
   ```

- [ ] **Step 6: Update `.eo-row--alert` and `.eo-progressbar__fill--alert` to use the `alert` tone instead of `error`**

In `src/styles/ui.css`, find and change:

```css
.eo-row--alert > td { background: color-mix(in srgb, var(--status-error) 8%, transparent); }
```

to:

```css
.eo-row--alert > td { background: color-mix(in srgb, var(--status-alert) 15%, transparent); }
```

(This also brings the row band up to the spec's stated 15% fill for status bands,
instead of the ad-hoc 8% it had before.)

Find and change:

```css
.eo-progressbar__fill--alert { background: var(--status-error); }
```

to:

```css
.eo-progressbar__fill--alert { background: var(--status-alert); }
```

- [ ] **Step 7: Update `TraceSection.test.tsx` assertions affected by the condition-name and tone changes**

The existing test `'un frame sin alerta/progreso propios pero con active_patterns muestra "activo"...'`
asserts `screen.getByText('CR-01', { selector: '.eo-badge' })` — this must become:

```tsx
expect(screen.getByText('CR-01 — Presencia de persona sin casco', { selector: '.eo-badge' })).toBeTruthy()
```

Add one new test verifying the monospace fallback and the `alert` tone:

```tsx
  it('un motivo de descarte no reconocido se muestra crudo y en monoespaciada', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [],
            control: 'dropped:queue_full',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('queue_full')).toBeTruthy())
    expect(screen.getByText('queue_full').className).toContain('eo-mono')
  })

  it('la fila con alerta confirmada usa el tono alert, no error', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText(/ALERTA/)).toBeTruthy())
    expect(screen.getByText(/ALERTA/).closest('.eo-badge')?.className).toContain('eo-badge--alert')
  })
```

- [ ] **Step 8: Run the affected test files to verify they pass**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceSection.test.tsx src/__tests__/traceview.test.ts`
Expected: all PASS.

- [ ] **Step 9: Update `EvalSection.tsx`'s "CR-01 recall" wording to use the glossary**

In `src/components/EvalSection.tsx`:

1. Add the import: `import { conditionLabel } from '../labels'`
2. Change:
   ```tsx
   <b>mAP@0.5: {fmt(result.mAP50)}</b> · CR-01 recall: {fmt(result.cr01_detection_recall)}
   {' '}· IoU ≥ {result.iou_threshold}
   ```
   to:
   ```tsx
   <b>mAP@0.5: {fmt(result.mAP50)}</b> · {conditionLabel('CR-01')} (exhaustividad: {fmt(result.cr01_detection_recall)})
   {' '}· IoU ≥ {result.iou_threshold}
   ```

Check `src/__tests__/EvalSection.test.tsx` for any assertion on the literal string
`'CR-01 recall'` and update it to match the new wording (`'CR-01 — Presencia de persona
sin casco'` and `'exhaustividad'` as separate text, since they're no longer adjacent in
one literal string — use `screen.getByText(/exhaustividad/)` or similar substring
matching rather than an exact string, following the existing style in that test file).

- [ ] **Step 10: Run `EvalSection.test.tsx` to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/EvalSection.test.tsx`
Expected: PASS.

- [ ] **Step 11: Polish `RunDetailPage.tsx` — monospace run_id, `Button` primitive for Detener/Borrar**

In `src/pages/RunDetailPage.tsx`:

1. Add the import: `import { Badge, Button, Card, DetChip, EmptyState, ErrorBanner, StatTile } from '../components/ui'`
   (adding `Button` to the existing import from `'../components/ui'`).
2. Change `<span title={run.run_id}>{runName || run.run_id}</span>` to
   `<span className="eo-mono" title={run.run_id}>{runName || run.run_id}</span>`.
3. Change the "■ Detener" button:
   ```tsx
   <button
     onClick={() => {
       stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
     }}
   >
     ■ Detener
   </button>
   ```
   to:
   ```tsx
   <Button
     variant="secondary"
     onClick={() => {
       stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
     }}
   >
     ■ Detener
   </Button>
   ```
4. Change the "Borrar" button:
   ```tsx
   <button type="button" disabled={deleting} onClick={() => void handleDelete()}>
     Borrar
   </button>
   ```
   to:
   ```tsx
   <Button variant="danger" disabled={deleting} onClick={() => void handleDelete()}>
     Borrar
   </Button>
   ```

`RunDetailPage.test.tsx` queries these by `getByRole('button', { name: 'Borrar' })` and
similar — `Button` renders a native `<button>` with its children as text, so these
queries keep working unchanged; no test file edit should be needed here, but run the
suite to confirm.

- [ ] **Step 12: Run the full suite and build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: all PASS, build succeeds.

- [ ] **Step 13: Commit**

```bash
cd webconsole/frontend
git add src/traceview.ts src/components/TraceSection.tsx src/styles/ui.css src/components/EvalSection.tsx src/pages/RunDetailPage.tsx src/__tests__/traceview.test.ts src/__tests__/TraceSection.test.tsx src/__tests__/EvalSection.test.tsx
git commit -m "design: glossary/token consistency pass on Run Detail (condition names, alert tone, mono fallback)"
```

---

## After this plan

Detalle de corrida is now fully re-skinned. The remaining screens, in the priority
order confirmed in the design doc, each get their own follow-up plan: Comparar next,
then Experimentos + Detalle de experimento, then the lower-priority rest (Prompt sets,
Catálogos, Plataforma, Cámaras, Clips).

Still-parked items from the prior plan's final review that remain undecided (not
addressed by this plan, since they weren't load-bearing for Run Detail specifically):
a general UI-term dictionary in `labels.ts` beyond condition names and drop reasons;
`Select`'s missing accessible-label prop; `Table`'s missing header-row helpers (`thead`/
`tr` are still hand-rolled per screen); the dead `--sidebar-width-collapsed` token; and
`RunsPage`'s empty-state text not distinguishing "no data" from "filter matched
nothing." Worth a deliberate decision in whichever follow-up plan next touches each of
these areas.
