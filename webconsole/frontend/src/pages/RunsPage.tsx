import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, EmptyState, ErrorBanner } from '../components/ui'
import { runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)']

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      listRuns()
        .then((r) => {
          if (!alive) return
          setRows(r)
          setError(null)
          // refresco solo mientras hay actividad (el resto es historial estático)
          if (r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
        })
        .catch((e) => alive && setError(String(e)))
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  if (error) return <ErrorBanner>Error listando runs: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
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
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={8}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
