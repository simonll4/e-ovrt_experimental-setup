import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, getTrace, listRuns } from '../api'
import type { RunRow } from '../types'
import {
  Badge, Banner, Button, EmptyState, ErrorBanner, InlineDeleteConfirm,
  PageHeader, RowNameCell, SearchInput, SegmentedControl, SortableHeader,
  Table, NumCell,
} from '../components/ui'
import type { SortState } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel, sourceLabel } from '../runview'

const SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'stopped', label: 'Detenidas' },
  { value: 'failed', label: 'Fallidas' },
] as const
type Segment = (typeof SEGMENTS)[number]['value']

// hace(): antigüedad legible cuando la fila no tiene nombre.
function hace(startedAt: string | null | undefined): string {
  if (!startedAt) return '—'
  const min = Math.floor((Date.now() - new Date(startedAt).getTime()) / 60000)
  if (min < 1) return 'recién'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `hace ${h} h`
  return `hace ${Math.floor(h / 24)} d`
}

function numOrNull(v: number | null | undefined): number {
  return v == null ? -Infinity : v
}

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [sort, setSort] = useState<SortState | null>(null)
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
        // refresco solo mientras hay actividad (el resto es historial estático)
        if (alive && r && r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
      })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const liveRun = rows?.find((r) => r.status === 'running') ?? null

  // Resumen de la corrida en vivo: totals.alerts de la traza, un pedido liviano
  // (page_size=1) — se omite si control_run_id es null (no evaluada por el motor de reglas).
  useEffect(() => {
    if (!liveRun) {
      setLiveAlerts(null)
      return
    }
    let alive = true
    getTrace(liveRun.run_id, 1, 1)
      .then((t) => {
        if (alive) setLiveAlerts(t.control_run_id ? t.totals.alerts : null)
      })
      .catch(() => {
        if (alive) setLiveAlerts(null)
      })
    return () => {
      alive = false
    }
  }, [liveRun?.run_id])

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
      } else {
        setDeleteError(null)
      }
    } catch (e) {
      setDeleteError(`No se pudo borrar ${row.run_id}: ${String(e)}`)
    } finally {
      setDeletingId(null)
      await refresh()
    }
  }

  const filtered = useMemo(() => {
    if (!rows) return null
    const q = query.trim().toLowerCase()
    return rows.filter((r) => {
      if (segment !== 'all') {
        if (segment === 'failed' ? !['failed', 'error'].includes(r.status) : r.status !== segment) return false
      }
      if (q && !`${r.name ?? ''} ${r.run_id}`.toLowerCase().includes(q)) return false
      return true
    })
  }, [rows, query, segment])

  const sorted = useMemo(() => {
    if (!filtered) return filtered
    if (!sort) return filtered
    const dir = sort.dir === 'asc' ? 1 : -1
    const key = sort.key as keyof RunRow
    return [...filtered].sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' || typeof bv === 'number') {
        return (numOrNull(av as number) - numOrNull(bv as number)) * dir
      }
      return String(av ?? '').localeCompare(String(bv ?? '')) * dir
    })
  }, [filtered, sort])

  const onSort = (key: string) => {
    setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))
  }

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const runningCount = rows.filter((r) => r.status === 'running').length

  return (
    <div>
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
        actions={
          <Link to="/compose" className="eo-btn eo-btn--primary">
            ▶ Nueva corrida
          </Link>
        }
      />
      {liveRun && (
        <Banner
          tone="live"
          action={
            <Link to={`/runs/${liveRun.run_id}`} className="eo-btn eo-btn--secondary">
              Ver en vivo
            </Link>
          }
        >
          <b>{liveRun.name || liveRun.run_id}</b> está procesando ahora
          {liveAlerts !== null ? ` — ${liveAlerts} alertas confirmadas.` : '.'}
        </Banner>
      )}
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <div className="eo-toolbar2">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Buscar por nombre o identificador"
          ariaLabel="Buscar corridas"
        />
        <SegmentedControl value={segment} options={[...SEGMENTS]} onChange={setSegment} />
        <span className="eo-toolbar2__count">{sorted!.length} de {rows.length}</span>
      </div>
      <Table>
        <thead>
          <tr>
            <SortableHeader label="Corrida" sortKey="name" sortState={sort} onSort={onSort} />
            <SortableHeader label="Estado" sortKey="status" sortState={sort} onSort={onSort} />
            <th>Modelo</th>
            <th>Fuente</th>
            <th>Conjunto de prompts</th>
            <SortableHeader label="Cuadros/s" sortKey="fps_effective" sortState={sort} onSort={onSort} numeric />
            <SortableHeader label="Detecciones" sortKey="total_detections" sortState={sort} onSort={onSort} numeric />
            <SortableHeader label="Duración" sortKey="duration_seconds" sortState={sort} onSort={onSort} numeric />
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sorted!.map((r) => (
            <tr key={r.run_id} className="eo-row--clickable">
              <RowNameCell
                title={<Link to={`/runs/${r.run_id}`}>{r.name || r.run_id}</Link>}
                subtitle={r.name ? r.run_id : hace(r.started_at)}
              />
              <td>
                <Badge tone={runStatusTone(r)} pulse={isRunning(r)}>{runStatusLabel(r)}</Badge>
              </td>
              <td className={r.model ? 'eo-mono' : undefined}>{r.model ?? '—'}</td>
              <td>{sourceLabel(r.source_type)}</td>
              <td className={r.prompt_set_id ? 'eo-mono' : undefined}>{r.prompt_set_id ?? '—'}</td>
              <NumCell>{r.fps_effective ?? '—'}</NumCell>
              <NumCell>{r.total_detections ?? '—'}</NumCell>
              <NumCell>{r.duration_seconds != null ? `${r.duration_seconds} s` : '—'}</NumCell>
              <td className="eo-cell--actions">
                {confirmId === r.run_id ? (
                  <InlineDeleteConfirm
                    onConfirm={() => void handleDelete(r)}
                    onCancel={() => setConfirmId(null)}
                  />
                ) : (
                  !isRunning(r) && (
                    <Button
                      variant="ghost"
                      disabled={deletingId === r.run_id}
                      onClick={() => setConfirmId(r.run_id)}
                    >
                      Borrar
                    </Button>
                  )
                )}
              </td>
            </tr>
          ))}
          {sorted!.length === 0 && (
            <tr>
              <td colSpan={9}>
                {query || segment !== 'all' ? (
                  <EmptyState hint="Probá con otro texto o volvé a «Todas».">
                    Ninguna corrida coincide con el filtro.
                  </EmptyState>
                ) : (
                  <EmptyState hint="Empezá por elegir una fuente y un conjunto de prompts.">
                    Todavía no lanzaste ninguna corrida.
                  </EmptyState>
                )}
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </div>
  )
}
