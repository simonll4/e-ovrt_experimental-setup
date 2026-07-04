import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { artifactUrl, getDetections, getRun, stopRun } from '../api'
import EvalSection from '../components/EvalSection'
import Sparkline from '../components/Sparkline'
import { useRunStream } from '../stream'
import type { DetectionsPage, RunDetail } from '../types'

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [detections, setDetections] = useState<DetectionsPage | null>(null)
  const [hasVideo, setHasVideo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const running = run?.status === 'running'
  const live = useRunStream(id, Boolean(running))

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
  useEffect(() => {
    if (run && !running) {
      getDetections(id, 1, 24).then(setDetections).catch(() => setDetections(null))
      fetch(artifactUrl(id, 'annotated.mp4'), { method: 'GET', headers: { range: 'bytes=0-0' } })
        .then((r) => setHasVideo(r.ok))
        .catch(() => setHasVideo(false))
    }
  }, [run?.status])

  if (error) return <p style={{ color: '#b00' }}>Error cargando el run {id}: {error}</p>
  if (!run) return <p>Cargando run {id}…</p>
  const summary = (run.summary ?? {}) as Record<string, any>
  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <h2>
        {run.run_id} — {run.status}{' '}
        {running && (
          <button
            onClick={() => {
              stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
            }}
          >
            ■ Detener
          </button>
        )}
      </h2>
      {running && (
        <section style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          <div>
            <b>FPS</b> {live.lastMetric?.fps ?? '—'}
            <Sparkline values={live.fpsHistory} />
          </div>
          <div>
            <b>Latencia/unidad (ms)</b> {live.lastMetric?.latency_total_ms ?? '—'}
            <Sparkline values={live.latencyHistory} />
          </div>
          <div><b>VRAM (MB)</b> {live.lastMetric?.gpu_memory_mb ?? '—'}</div>
          <div><b>Detecciones</b> {live.detectionsTotal}</div>
          <div style={{ width: '100%' }}>
            <b>Errores (tail)</b>
            <pre style={{ maxHeight: 140, overflow: 'auto', background: '#f6f6f6', padding: 8 }}>
              {live.errors.map((e) => `${e.unit_id ?? '?'} [${e.stage}] ${e.message}\n`)}
              {live.errors.length === 0 && 'sin errores'}
            </pre>
          </div>
          <small>p95 y detecciones-por-label se calculan al terminar (summary).</small>
        </section>
      )}
      {!running && run.summary && (
        <section>
          <h3>Summary</h3>
          <ul>
            <li>
              modelo: {summary.model_name ?? '—'} ({summary.device ?? '—'}) — prompts:{' '}
              {summary.prompt_set_id ?? '—'}
            </li>
            <li>
              unidades: {summary.units_processed ?? '—'} · detecciones: {summary.total_detections ?? '—'}
            </li>
            <li>
              FPS: {summary.fps_effective ?? '—'} · p95: {summary.p95_latency_ms ?? '—'} ms · dur:{' '}
              {summary.duration_seconds ?? '—'}s
            </li>
            <li>
              por label:{' '}
              {Object.entries(summary.detections_by_label ?? {})
                .map(([k, v]) => `${k}=${v}`)
                .join(', ') || '—'}
            </li>
          </ul>
          {hasVideo && (
            <video controls width={640} src={artifactUrl(id, 'annotated.mp4')} />
          )}
          {detections && (
            <>
              <h3>Detecciones (pág. 1 de {Math.ceil(detections.total / detections.page_size)})</h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {detections.items.map((d: any) => (
                  <figure key={d.unit_id} style={{ margin: 0 }}>
                    <img
                      src={artifactUrl(id, `previews/${d.unit_id}.preview.jpg`)}
                      alt={d.unit_id}
                      width={160}
                      onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
                    />
                    <figcaption><small>{d.unit_id} ({(d.detections ?? []).length})</small></figcaption>
                  </figure>
                ))}
              </div>
            </>
          )}
        </section>
      )}
      {!running && (
        <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
      )}
    </div>
  )
}
