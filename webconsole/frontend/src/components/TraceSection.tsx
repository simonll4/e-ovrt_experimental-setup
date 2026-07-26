import { useEffect, useState } from 'react'
import { artifactUrl, getTrace } from '../api'
import { Badge, Card, ConditionName, DetChip, EmptyState, ErrorBanner, StatTile } from './ui'
import { controlLabel, controlLabelIsRaw, controlTone, frameHasActivity } from '../traceview'
import { alertSeverityTone } from '../experimentview'
import PreviewWithBoxes from './PreviewWithBoxes'
import TraceTimeline from './TraceTimeline'
import type { TraceFrame, TracePage } from '../types'

type TraceMeta = Omit<TracePage, 'frames'>

const MAX_PAGES = 20

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
        first = await getTrace(runId, 1, 1000)
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
      if (totalPages > MAX_PAGES) {
        setPartialError(
          'línea de tiempo incompleta: la corrida tiene más cuadros de los que se pueden cargar de una vez',
        )
        return
      }
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
      <TraceTimeline frames={visibleFrames} />
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
            <tr
              key={f.unit_id ?? f.frame_index}
              id={`frame-${f.unit_id ?? f.frame_index}`}
              className={f.alert.length > 0 ? 'eo-row--alert' : undefined}
            >
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
                  <Badge tone={controlTone(f.control)}>
                    <span className={controlLabelIsRaw(f.control) ? 'eo-mono' : undefined}>
                      {controlLabel(f.control)}
                    </span>
                  </Badge>
                </td>
              )}
              {hasControl && (
                <td>
                  {f.progress.map((p, i) => (
                    <div className="eo-patternrow" key={i}>
                      <span className="eo-patternrow__id"><ConditionName code={p.condition_id} /></span>
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
                    <Badge key={i} tone="alert">
                      ALERTA <ConditionName code={a.condition_id} />
                    </Badge>
                  ))}
                  {(f.active_patterns ?? []).map((p, i) => (
                    <div className="eo-patternrow" key={`active-${i}`}>
                      <Badge tone={alertSeverityTone(p.severity)}><ConditionName code={p.condition_id} /></Badge>
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
