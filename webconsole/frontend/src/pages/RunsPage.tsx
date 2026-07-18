import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, EmptyState, ErrorBanner } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)', '']

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

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

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <table className="eo-table">
        <thead>
          <tr>{HEADERS.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id}>
              <td><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
              <td>
                <Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge>
                {r.topology === 'two_node' ? <small> two-node</small> : null}
              </td>
              <td>{r.model ?? '—'}</td>
              <td>{r.source_type ?? '—'}</td>
              <td>{r.prompt_set_id ?? '—'}</td>
              <td className="eo-num">{r.fps_effective ?? '—'}</td>
              <td className="eo-num">{r.total_detections ?? '—'}</td>
              <td className="eo-num">{r.duration_seconds ?? '—'}</td>
              <td>
                {!isRunning(r) && (
                  <button
                    type="button"
                    disabled={deletingId === r.run_id}
                    onClick={() => void handleDelete(r)}
                  >
                    Borrar
                  </button>
                )}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={9}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
