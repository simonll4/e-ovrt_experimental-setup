import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, Button, EmptyState, ErrorBanner, Select, Table, MonoCell, NumCell } from '../components/ui'
import type { SelectOption } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['corrida', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)', '']

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'failed', label: 'Fallidas' },
]

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('all')

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

  const handleDelete = async (row: RunRow) => {
    if (!window.confirm(`¿Borrar el run ${row.run_id}? No se puede deshacer.`)) return
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

  const visibleRows = useMemo(() => {
    if (!rows) return rows
    if (statusFilter === 'all') return rows
    return rows.filter((r) => r.status === statusFilter)
  }, [rows, statusFilter])

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <div className="eo-clips__head">
        <Select value={statusFilter} options={STATUS_OPTIONS} onChange={setStatusFilter} />
      </div>
      <Table>
        <thead>
          <tr>{HEADERS.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {visibleRows!.map((r) => (
            <tr key={r.run_id}>
              <MonoCell title={r.run_id}>
                <Link to={`/runs/${r.run_id}`}>{r.name || r.run_id}</Link>
                {r.name && <><br /><small>{r.run_id}</small></>}
              </MonoCell>
              <td>
                <Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge>
                {r.topology === 'two_node' ? <small> two-node</small> : null}
              </td>
              <td>{r.model ?? '—'}</td>
              <td>{r.source_type ?? '—'}</td>
              <td>{r.prompt_set_id ?? '—'}</td>
              <NumCell>{r.fps_effective ?? '—'}</NumCell>
              <NumCell>{r.total_detections ?? '—'}</NumCell>
              <NumCell>{r.duration_seconds ?? '—'}</NumCell>
              <td>
                {!isRunning(r) && (
                  <Button
                    variant="danger"
                    disabled={deletingId === r.run_id}
                    onClick={() => void handleDelete(r)}
                  >
                    Borrar
                  </Button>
                )}
              </td>
            </tr>
          ))}
          {visibleRows!.length === 0 && (
            <tr><td colSpan={9}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </Table>
    </div>
  )
}
