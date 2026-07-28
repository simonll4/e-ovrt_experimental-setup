import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { deleteRun, getTrace, listRuns } from '../api'
import type { RunRow } from '../types'
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  InlineDeleteConfirm,
  MonoCell,
  NumCell,
  PageHeader,
  RowNameCell,
  SearchInput,
  SegmentedControl,
  SortableHeader,
  Table,
  type SortState,
} from '../components/ui'
import { createdAtMs, hace, isRunning, runStatusLabel, runStatusTone, sourceLabel } from '../runview'

const PAGE_SIZE = 25

const SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'stopped', label: 'Detenidas' },
  { value: 'failed', label: 'Fallidas' },
] as const
type Segment = (typeof SEGMENTS)[number]['value']

const dec = (v: number | null | undefined, digits = 1): string =>
  v == null ? '—' : v.toFixed(digits).replace('.', ',')

/** Orden estable con los nulos siempre al final, en cualquier dirección. */
function compare(a: RunRow, b: RunRow, key: string, dir: 'asc' | 'desc'): number {
  const pick = (r: RunRow): string | number | null => {
    switch (key) {
      case 'name': return (r.name ?? r.run_id).toLowerCase()
      case 'status': return r.status
      case 'model': return r.model ?? null
      case 'fps': return r.fps_effective ?? null
      case 'dets': return r.total_detections ?? null
      case 'dur': return r.duration_seconds ?? null
      default: return createdAtMs(r)
    }
  }
  const va = pick(a)
  const vb = pick(b)
  if (va == null && vb == null) return 0
  if (va == null) return 1
  if (vb == null) return -1
  const sign = va < vb ? -1 : va > vb ? 1 : 0
  return dir === 'asc' ? sign : -sign
}

export default function RunsPage() {
  const nav = useNavigate()
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<SortState>({ key: 'started_at', dir: 'desc' })
  const [liveAlerts, setLiveAlerts] = useState<number | null>(null)

  const refresh = () =>
    listRuns()
      .then((r) => {
        setRows(r)
        setError(null)
        return r
      })
      .catch((e) => {
        setError(String(e))
        return null
      })

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      refresh().then((r) => {
        // Refresco solo mientras hay actividad; el resto es historial estático.
        if (alive && r && r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
      })
    void tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const liveRun = rows?.find((r) => isRunning(r)) ?? null
  const liveRunId = liveRun?.run_id ?? null

  // Alertas de la corrida en vivo: un pedido liviano (page_size=1) solo por los
  // totales. Se omite si el motor de reglas no evaluó la corrida.
  useEffect(() => {
    if (!liveRunId) {
      setLiveAlerts(null)
      return
    }
    let alive = true
    getTrace(liveRunId, 1, 1)
      .then((t) => {
        if (alive) setLiveAlerts(t.control_run_id ? t.totals.alerts : null)
      })
      .catch(() => {
        if (alive) setLiveAlerts(null)
      })
    return () => {
      alive = false
    }
  }, [liveRunId])

  const filtered = useMemo(() => {
    if (!rows) return []
    const q = query.trim().toLowerCase()
    return rows
      .filter((r) => (segment === 'all' ? true : segment === 'running' ? isRunning(r) : r.status === segment))
      .filter((r) => !q || r.run_id.toLowerCase().includes(q) || (r.name ?? '').toLowerCase().includes(q))
      .slice()
      .sort((a, b) => compare(a, b, sort.key, sort.dir))
  }, [rows, query, segment, sort])

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const current = Math.min(page, pages)
  const visible = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE)

  const resetView = () => {
    setPage(1)
    setConfirmId(null)
  }

  const onSort = (key: string) => {
    setSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }))
    resetView()
  }

  const handleDelete = async (row: RunRow) => {
    setConfirmId(null)
    setDeletingId(row.run_id)
    setDeleteError(null)
    try {
      const result = await deleteRun(row.run_id)
      if (result?.errors) {
        setDeleteError(
          `Borrado parcial de ${row.run_id}: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
      }
    } catch (e) {
      setDeleteError(`No se pudo borrar ${row.run_id}: ${String(e)}`)
    } finally {
      setDeletingId(null)
      await refresh()
    }
  }

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const runningCount = rows.filter((r) => isRunning(r)).length

  return (
    <>
      <PageHeader
        title="Corridas"
        meta={
          <>
            <span>{rows.length} en total</span>
            {runningCount > 0 && (
              <>
                <span className="eo-sep">·</span>
                <span style={{ color: 'var(--live)' }}>{runningCount} en curso</span>
              </>
            )}
          </>
        }
        actions={<Button variant="primary" onClick={() => nav('/compose')}>Nueva corrida</Button>}
      />

      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}

      {liveRun && (
        <Banner
          tone="live"
          action={
            <Button onClick={() => nav(`/runs/${liveRun.run_id}`)}>Ver en vivo</Button>
          }
        >
          <b>{liveRun.name ?? liveRun.run_id}</b> está procesando ahora
          {liveRun.total_detections != null && ` — ${liveRun.total_detections} detecciones`}
          {liveAlerts != null && `, ${liveAlerts} alertas confirmadas`}
        </Banner>
      )}

      <div className="eo-toolbar">
        <SearchInput
          value={query}
          onChange={(v) => {
            setQuery(v)
            resetView()
          }}
          placeholder="Buscar por nombre o identificador"
          ariaLabel="Buscar corridas por nombre o identificador"
        />
        <SegmentedControl
          value={segment}
          options={SEGMENTS as unknown as Array<{ value: Segment; label: string }>}
          onChange={(v) => {
            setSegment(v)
            resetView()
          }}
        />
        <span className="eo-toolbar__count eo-mono">
          {filtered.length} de {rows.length}
        </span>
      </div>

      <Card flush>
        <Table>
          <thead>
            <tr>
              <SortableHeader label="Corrida" sortKey="name" sortState={sort} onSort={onSort} />
              <SortableHeader label="Estado" sortKey="status" sortState={sort} onSort={onSort} />
              <SortableHeader label="Modelo" sortKey="model" sortState={sort} onSort={onSort} />
              <th>Fuente</th>
              <th>Conjunto de prompts</th>
              <SortableHeader label="Cuadros/s" sortKey="fps" sortState={sort} onSort={onSort} numeric />
              <SortableHeader label="Detecciones" sortKey="dets" sortState={sort} onSort={onSort} numeric />
              <SortableHeader label="Duración" sortKey="dur" sortState={sort} onSort={onSort} numeric />
              <th>Creada</th>
              <th aria-label="Acciones" />
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.run_id} className={isRunning(r) ? 'eo-row--live' : undefined}>
                {/* RowNameCell no linkea: el enlace va dentro del título. */}
                <RowNameCell
                  title={<Link to={`/runs/${r.run_id}`}>{r.name ?? r.run_id}</Link>}
                  subtitle={r.name ? r.run_id : undefined}
                />
                <td>
                  <Badge tone={runStatusTone(r)} pulse={isRunning(r)}>
                    {runStatusLabel(r)}
                  </Badge>
                </td>
                <MonoCell>{r.model ?? '—'}</MonoCell>
                <td>{sourceLabel(r.source_type)}</td>
                <MonoCell>{r.prompt_set_id ?? '—'}</MonoCell>
                <NumCell>{dec(r.fps_effective, 2)}</NumCell>
                <NumCell>{r.total_detections ?? '—'}</NumCell>
                <NumCell>{r.duration_seconds != null ? `${dec(r.duration_seconds)} s` : '—'}</NumCell>
                <td className="eo-cell--muted">{hace(r)}</td>
                <td className="eo-cell--actions">
                  {!isRunning(r) &&
                    (confirmId === r.run_id ? (
                      <InlineDeleteConfirm
                        onConfirm={() => void handleDelete(r)}
                        onCancel={() => setConfirmId(null)}
                      />
                    ) : (
                      <Button
                        variant="ghost"
                        aria-label={`Borrar ${r.run_id}`}
                        disabled={deletingId === r.run_id}
                        onClick={() => setConfirmId(r.run_id)}
                      >
                        ×
                      </Button>
                    ))}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
        {rows.length === 0 && <EmptyState>Sin corridas todavía.</EmptyState>}
        {rows.length > 0 && filtered.length === 0 && (
          <EmptyState hint="Probá con otro texto o cambiá el filtro de estado.">
            Ninguna corrida coincide con la búsqueda
          </EmptyState>
        )}
      </Card>

      {pages > 1 && (
        <nav className="eo-pager" aria-label="Paginación de corridas">
          <Button disabled={current === 1} onClick={() => setPage(current - 1)}>
            Anterior
          </Button>
          <span className="eo-mono">
            Página {current} de {pages}
          </span>
          <Button disabled={current === pages} onClick={() => setPage(current + 1)}>
            Siguiente
          </Button>
        </nav>
      )}
    </>
  )
}
