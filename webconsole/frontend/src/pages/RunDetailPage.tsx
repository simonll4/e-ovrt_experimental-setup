import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { artifactUrl, deleteRun, getRun, stopRun } from '../api'
import EvalSection from '../components/EvalSection'
import RunKpiStrip from '../components/RunKpiStrip'
import RunTimeline from '../components/RunTimeline'
import TraceSection from '../components/TraceSection'
import {
  Badge,
  Banner,
  Button,
  Card,
  DetChip,
  ErrorBanner,
  InlineDeleteConfirm,
} from '../components/ui'
import { isLive, runStatusLabel, runStatusTone, sourceLabel, topologyBadge } from '../runview'
import { buildRunSeries } from '../runseries'
import { useFullTrace } from '../useFullTrace'
import type { RunDetail } from '../types'

type Tab = 'trace' | 'summary' | 'eval' | 'files'

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

const dec = (v: number | null, digits = 1) => (v == null ? '—' : v.toFixed(digits).replace('.', ','))

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [hasVideo, setHasVideo] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('trace')
  const [selected, setSelected] = useState<number | null>(null)

  const running = run?.status === 'running'
  const streamable = Boolean(run && isLive(run))

  // Una sola lectura de la traza para toda la pantalla: la comparten la línea de
  // tiempo y la lista de cuadros.
  const trace = useFullTrace(id, Boolean(run) && !running)
  const series = useMemo(() => buildRunSeries(trace.frames), [trace.frames])

  const refresh = () =>
    getRun(id)
      .then((r) => {
        setRun(r)
        setError(null)
      })
      .catch((e) => setError(String(e)))

  useEffect(() => {
    void refresh()
  }, [id])

  // Corrida externa (dos equipos) en curso: sin WS, el estado se re-hidrata por polling.
  useEffect(() => {
    if (!running) return
    const timer = setInterval(refresh, 4000)
    return () => clearInterval(timer)
  }, [running])

  useEffect(() => {
    if (run && !running) {
      fetch(artifactUrl(id, 'annotated.mp4'), { method: 'GET', headers: { range: 'bytes=0-0' } })
        .then((r) => setHasVideo(r.ok))
        .catch(() => setHasVideo(false))
    }
  }, [run?.status])

  const handleDelete = async () => {
    setConfirmDelete(false)
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

  if (error) return <ErrorBanner>Error cargando la corrida {id}: {error}</ErrorBanner>
  if (!run) return <p className="eo-empty">Cargando la corrida {id}…</p>

  const summary = run.summary
  const topology = topologyBadge(summary)
  // `name` viaja top-level mientras la corrida está viva y dentro de summary una
  // vez terminada (persistido).
  const runName = run.name || (summary?.name as string | undefined)
  const duration = num(summary, 'duration_seconds')

  return (
    <>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}

      <div className="eo-runhead">
        <div>
          <h1>{runName || run.run_id}</h1>
          <div className="eo-runhead__meta">
            <Badge tone={runStatusTone(run)} pulse={running}>
              {runStatusLabel(run)}
            </Badge>
            {topology && <Badge tone="neutral">{topology}</Badge>}
            {runName && (
              <>
                <span className="eo-mono">{run.run_id}</span>
                <span className="eo-sep">·</span>
              </>
            )}
            <span>{sourceLabel(str(summary, 'source_type'))}</span>
            {duration != null && (
              <>
                <span className="eo-sep">·</span>
                <span className="eo-mono">{dec(duration)} s</span>
              </>
            )}
          </div>
        </div>
        <div className="eo-runhead__acts">
          {streamable && (
            <Button
              onClick={() => {
                stopRun(id).catch((e) => setError(`No se pudo detener: ${String(e)}`))
              }}
            >
              Detener
            </Button>
          )}
          {!running &&
            (confirmDelete ? (
              <InlineDeleteConfirm
                onConfirm={() => void handleDelete()}
                onCancel={() => setConfirmDelete(false)}
              />
            ) : (
              <Button variant="ghost" disabled={deleting} onClick={() => setConfirmDelete(true)}>
                Borrar
              </Button>
            ))}
        </div>
      </div>

      <RunKpiStrip
        summary={summary}
        series={series}
        live={running}
        alerts={trace.totals?.alerts ?? null}
      />

      {!running && (
        <RunTimeline
          frames={trace.frames}
          selected={selected}
          truncated={trace.truncated}
          loading={trace.loading}
          onSelect={(_frameIndex, position) => setSelected(position)}
        />
      )}

      {trace.error && <ErrorBanner>{trace.error}</ErrorBanner>}
      {trace.controlError && (
        <Banner tone="warn">
          El motor de reglas no pudo evaluar esta corrida: {trace.controlError}
        </Banner>
      )}

      {!running && (
        <>
          <nav className="eo-tabs" role="tablist">
            <button role="tab" aria-selected={tab === 'trace'} onClick={() => setTab('trace')}>
              Traza <span className="eo-tabs__count eo-mono">{trace.frames.length}</span>
            </button>
            <button role="tab" aria-selected={tab === 'summary'} onClick={() => setTab('summary')}>
              Resumen
            </button>
            <button role="tab" aria-selected={tab === 'eval'} onClick={() => setTab('eval')}>
              Evaluación
            </button>
            <button role="tab" aria-selected={tab === 'files'} onClick={() => setTab('files')}>
              Archivos
            </button>
          </nav>

          {tab === 'trace' && (
            <TraceSection
              key={id}
              runId={id}
              frames={trace.frames}
              totals={trace.totals}
              selected={selected}
              onSelect={setSelected}
            />
          )}

          {tab === 'summary' && (
            <Card title="Resumen de la corrida">
              <dl className="eo-deflist">
                <div>
                  <dt>Modelo</dt>
                  <dd className="eo-mono">
                    {str(summary, 'model_name') ?? '—'} ({str(summary, 'device') ?? '—'})
                  </dd>
                </div>
                <div>
                  <dt>Conjunto de prompts</dt>
                  <dd className="eo-mono">{str(summary, 'prompt_set_id') ?? '—'}</dd>
                </div>
                <div>
                  <dt>Cuadros procesados</dt>
                  <dd className="eo-mono">{num(summary, 'units_processed') ?? '—'}</dd>
                </div>
                <div>
                  <dt>Latencia (percentil 95)</dt>
                  <dd className="eo-mono">{dec(num(summary, 'p95_latency_ms'), 0)} ms</dd>
                </div>
                <div>
                  <dt>Detecciones por clase</dt>
                  <dd>
                    {labelCounts(summary).length > 0 ? (
                      <span className="eo-detchips">
                        {labelCounts(summary).map(([k, v]) => (
                          <DetChip key={k} label={k} count={v} />
                        ))}
                      </span>
                    ) : (
                      '—'
                    )}
                  </dd>
                </div>
              </dl>
            </Card>
          )}

          {tab === 'eval' && (
            <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
          )}

          {tab === 'files' && (
            <Card title="Archivos generados">
              {hasVideo ? (
                <video controls className="eo-video" src={artifactUrl(id, 'annotated.mp4')} />
              ) : (
                <p className="eo-cap">
                  Esta corrida no generó video anotado. Los artefactos de texto viven en{' '}
                  <span className="eo-mono">runs/{id}/</span>.
                </p>
              )}
            </Card>
          )}
        </>
      )}
    </>
  )
}
