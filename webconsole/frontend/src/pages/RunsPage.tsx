import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api'
import type { RunRow } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

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
  if (error) return <p style={{ color: '#b00' }}>Error listando runs: {error}</p>
  if (!rows) return <p>Cargando…</p>
  return (
    <div>
      <p><Link to="/compose">➕ Nueva corrida</Link></p>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            {['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)'].map((h) => (
              <th key={h} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id}>
              <td style={CELL}><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
              <td style={CELL}>
                {r.status === 'running' ? '🟢 running' : r.status}
                {r.topology === 'two_node' ? ' · two-node' : ''}
              </td>
              <td style={CELL}>{r.model ?? '—'}</td>
              <td style={CELL}>{r.source_type ?? '—'}</td>
              <td style={CELL}>{r.prompt_set_id ?? '—'}</td>
              <td style={CELL}>{r.fps_effective ?? '—'}</td>
              <td style={CELL}>{r.total_detections ?? '—'}</td>
              <td style={CELL}>{r.duration_seconds ?? '—'}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td style={CELL} colSpan={8}>Sin corridas todavía.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
