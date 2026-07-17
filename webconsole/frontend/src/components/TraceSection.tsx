import { useEffect, useState } from 'react'
import { artifactUrl, getTrace } from '../api'
import { Badge, Card, DetChip, EmptyState, ErrorBanner, StatTile } from './ui'
import { controlLabel, controlTone, frameHasActivity } from '../traceview'
import PreviewWithBoxes from './PreviewWithBoxes'
import type { TraceFrame, TracePage } from '../types'

export default function TraceSection({ runId }: { runId: string }) {
  const [trace, setTrace] = useState<TracePage | null>(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const [soloActividad, setSoloActividad] = useState(false)

  useEffect(() => {
    let alive = true
    getTrace(runId, page, 50)
      .then((t) => {
        if (alive) setTrace(t)
      })
      .catch((e) => {
        if (alive) setError(String(e))
      })
    return () => {
      alive = false
    }
  }, [runId, page])

  if (error) return <ErrorBanner>Error cargando la traza: {error}</ErrorBanner>
  if (!trace) return <p>Cargando traza…</p>

  const { totals } = trace
  const frames = soloActividad ? trace.frames.filter(frameHasActivity) : trace.frames
  const totalPages = Math.max(1, Math.ceil(trace.total / trace.page_size))
  const hasControl = trace.control_run_id !== null || !!trace.control_error

  return (
    <Card title="Evaluación del control-plane">
      <div className="eo-stats-row">
        <StatTile label="run de control" value={trace.control_run_id ?? '—'} />
        <StatTile label="alertas" value={totals.alerts} />
        {Object.entries(totals.dropped_by_reason).map(([reason, count]) => (
          <StatTile key={reason} label={controlLabel(`dropped:${reason}`)} value={count} />
        ))}
        {totals.not_received !== null && <StatTile label="no recibidos" value={totals.not_received} />}
      </div>
      {trace.topology === 'two_node' && <small>descartes internos n/d en two-node</small>}
      {trace.control_error && (
        <ErrorBanner>control-plane no disponible: {trace.control_error}</ErrorBanner>
      )}
      {trace.control_run_id === null && !trace.control_error && (
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
          {frames.map((f: TraceFrame) => (
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
                    {(f.frame_index !== null ? `#${f.frame_index}` : '') + (f.unit_id ?? '')}
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
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        pág. {trace.page} de {totalPages}{' '}
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          anterior
        </button>{' '}
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
          siguiente
        </button>
      </p>
    </Card>
  )
}
