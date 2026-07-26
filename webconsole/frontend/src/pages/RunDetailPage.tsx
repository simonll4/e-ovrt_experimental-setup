import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { artifactUrl, deleteRun, getRun, stopRun } from '../api'
import EvalSection from '../components/EvalSection'
import Sparkline from '../components/Sparkline'
import TraceSection from '../components/TraceSection'
import { Badge, Button, Card, DetChip, EmptyState, ErrorBanner, StatTile } from '../components/ui'
import { isLive, runStatusLabel, runStatusTone, topologyBadge } from '../runview'
import { useRunStream } from '../stream'
import type { RunDetail } from '../types'

function num(summary: Record<string, unknown> | undefined, key: string): number | null {
  const v = summary?.[key]
  return typeof v === 'number' ? v : null
}

function str(summary: Record<string, unknown> | undefined, key: string): string | null {
  const v = summary?.[key]
  return typeof v === 'string' ? v : null
}

function labelCounts(summary: Record<string, unknown> | undefined): Array<[string, number]> {
  const v = summary?.detections_by_label
  if (!v || typeof v !== 'object') return []
  return Object.entries(v as Record<string, unknown>).filter(
    (entry): entry is [string, number] => typeof entry[1] === 'number',
  )
}

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [hasVideo, setHasVideo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const running = run?.status === 'running'
  const streamable = Boolean(run && isLive(run))
  const live = useRunStream(id, streamable)
  const navigate = useNavigate()
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleDelete = async () => {
    if (!window.confirm(`¿Borrar la corrida ${id}? No se puede deshacer.`)) return
    setDeleting(true)
    setDeleteError(null)
    try {
      const result = await deleteRun(id)
      if (result?.errors) {
        setDeleteError(
          `Borrado parcial: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
        setDeleting(false)
        return
      }
      navigate('/runs')
    } catch (e) {
      setDeleteError(`No se pudo borrar: ${String(e)}`)
      setDeleting(false)
    }
  }

  const refresh = () =>
    getRun(id)
      .then((r) => {
        setRun(r)
        setError(null)
      })
      .catch((e) => setError(String(e)))
  useEffect(() => {
    refresh()
  }, [id])
  // El evento `state` marca el fin: re-hidratar estado+summary desde el BFF.
  useEffect(() => {
    if (live.finalState) refresh()
  }, [live.finalState])
  // Run externo (two-node) en curso: sin WS, el estado se re-hidrata por polling.
  useEffect(() => {
    if (!running || streamable) return
    const timer = setInterval(refresh, 4000)
    return () => clearInterval(timer)
  }, [running, streamable])
  useEffect(() => {
    if (run && !running) {
      fetch(artifactUrl(id, 'annotated.mp4'), { method: 'GET', headers: { range: 'bytes=0-0' } })
        .then((r) => setHasVideo(r.ok))
        .catch(() => setHasVideo(false))
    }
  }, [run?.status])

  if (error) return <ErrorBanner>Error cargando la corrida {id}: {error}</ErrorBanner>
  if (!run) return <p className="eo-empty">Cargando la corrida {id}…</p>
  const summary = run.summary
  const topology = topologyBadge(summary)
  // "name" viaja top-level mientras el run está vivo (RunManager.get() lee la
  // config en memoria) y dentro de summary una vez terminado (persistido).
  const runName = run.name || (summary?.name as string | undefined)
  return (
    <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <h2 className="eo-inline">
        <span className="eo-mono" title={run.run_id}>{runName || run.run_id}</span>
        {runName && <small>{run.run_id}</small>}
        <Badge tone={runStatusTone(run)}>{runStatusLabel(run)}</Badge>
        {topology && <Badge tone="neutral">{topology}</Badge>}
        {streamable && (
          <Button
            variant="secondary"
            onClick={() => {
              stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
            }}
          >
            ■ Detener
          </Button>
        )}
        {!running && (
          <Button variant="danger" disabled={deleting} onClick={() => void handleDelete()}>
            Borrar
          </Button>
        )}
      </h2>
      {streamable && (
        <section>
          <div className="eo-stats-row">
            <StatTile label="Cuadros por segundo" value={live.lastMetric?.fps ?? '—'} />
            <StatTile label="Latencia/unidad" value={live.lastMetric?.latency_total_ms ?? '—'} unit="ms" />
            <StatTile label="Memoria de GPU" value={live.lastMetric?.gpu_memory_mb ?? '—'} unit="MB" />
            <StatTile label="Detecciones" value={live.detectionsTotal} />
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
            <div>
              <b>Cuadros por segundo</b>
              <Sparkline values={live.fpsHistory} />
            </div>
            <div>
              <b>Latencia/unidad (ms)</b>
              <Sparkline values={live.latencyHistory} />
            </div>
          </div>
          {live.errors.length > 0 ? (
            <ErrorBanner>
              {live.errors.map((e, i) => (
                <div key={i}>{e.unit_id ?? '?'} [{e.stage}] {e.message}</div>
              ))}
            </ErrorBanner>
          ) : (
            <EmptyState>sin errores</EmptyState>
          )}
          <small>
            La latencia (percentil 95) y las detecciones por clase se calculan al terminar la corrida.
          </small>
        </section>
      )}
      {!running && run.summary && (
        <Card title="Resumen">
          <div className="eo-stats-row">
            <StatTile label="Cuadros por segundo" value={num(summary, 'fps_effective') ?? '—'} />
            <StatTile label="Latencia (mediana)" value={num(summary, 'p50_latency_ms') ?? '—'} unit="ms" />
            <StatTile label="Detecciones" value={num(summary, 'total_detections') ?? '—'} />
            <StatTile label="Duración" value={num(summary, 'duration_seconds') ?? '—'} unit="s" />
          </div>
          <dl className="eo-deflist">
            <div>
              <dt>modelo</dt>
              <dd>
                {str(summary, 'model_name') ?? '—'} ({str(summary, 'device') ?? '—'})
              </dd>
            </div>
            <div>
              <dt>prompts</dt>
              <dd>{str(summary, 'prompt_set_id') ?? '—'}</dd>
            </div>
            <div>
              <dt>unidades</dt>
              <dd>{num(summary, 'units_processed') ?? '—'}</dd>
            </div>
            <div>
              <dt>latencia (percentil 95)</dt>
              <dd>{num(summary, 'p95_latency_ms') ?? '—'} ms</dd>
            </div>
            <div>
              <dt>por clase</dt>
              <dd>
                {labelCounts(summary).length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
                    {labelCounts(summary).map(([k, v]) => (
                      <DetChip key={k} label={k} count={v} />
                    ))}
                  </div>
                ) : (
                  '—'
                )}
              </dd>
            </div>
          </dl>
        </Card>
      )}
      {!running && run.summary && hasVideo && (
        <Card title="Archivos generados">
          <video controls className="eo-video" src={artifactUrl(id, 'annotated.mp4')} />
        </Card>
      )}
      {/* key={id}: remonta la sección al navegar run→run — sin esto el `page`
          interno quedaría apuntando a una página que el run nuevo quizás no tiene */}
      {!running && <TraceSection key={id} runId={id} />}
      {!running && (
        <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
      )}
    </div>
  )
}
