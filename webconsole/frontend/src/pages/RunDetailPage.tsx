import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { artifactUrl } from '../api'
import {
  useArtifacts, useDeleteRun, useRun, useRunComparison, useStopRun, useTraceIndex,
} from '../api/queries/runs'
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
  EmptyState,
  ErrorBanner,
  IconDownload,
  InlineDeleteConfirm,
  MonoCell,
  NumCell,
  Table,
} from '../components/ui'
import { isLive, runStatusLabel, runStatusTone, sourceLabel, topologyBadge } from '../runview'
import { buildRunSeries } from '../runseries'
import type { RunSummary, TraceFrame, TraceIndex } from '../types'

/** `buildRunSeries` trabaja sobre cuadros; el índice trae solo los conteos.
 *  Se rearma lo mínimo que las series necesitan (cantidad de detecciones y
 *  marca de tiempo), sin las cajas ni el progreso de condiciones. */
function seriesFrames(index: TraceIndex | null): TraceFrame[] {
  if (!index) return []
  return index.detections.map((n, i) => ({
    frame_index: index.frame_index[i],
    unit_id: index.unit_id[i],
    timestamp_ms: index.timestamp_ms[i],
    detections: new Array(n).fill(null) as TraceFrame['detections'],
    control: index.control_state[i] === 'unknown' ? 'n/d' : index.control_state[i],
    progress: [],
    alert: [],
  }))
}

type Tab = 'trace' | 'summary' | 'eval' | 'files'

/** Con `RunSummary` tipado, esto es un `Object.entries` y nada más: antes hacía
 *  falta filtrar a mano los valores que no fueran número. */
function labelCounts(summary: RunSummary | undefined): Array<[string, number]> {
  return Object.entries(summary?.detections_by_label ?? {})
}

const dec = (v: number | null, digits = 1) => (v == null ? '—' : v.toFixed(digits).replace('.', ','))

/** Tamaño legible. Los artefactos van de cero bytes (errors.jsonl vacío) a
 *  decenas de MB (previews/), así que la unidad se elige por magnitud. */
function tamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${dec(bytes / 1024)} KB`
  return `${dec(bytes / (1024 * 1024))} MB`
}

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [stopError, setStopError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('trace')
  const [selected, setSelected] = useState<number | null>(null)

  // Mientras la corrida está viva la query se repregunta sola (caso de dos
  // equipos: no hay WS y el estado se re-hidrata por reloj). Al terminar, para.
  const { data: run = null, error: loadError } = useRun(id)
  const running = run?.status === 'running'
  const streamable = Boolean(run && isLive(run))

  // La línea de tiempo se alimenta del índice (la corrida completa en una sola
  // petición); la lista de cuadros trae su propia página. Antes las dos
  // compartían una traza entera descargada de a 500 cuadros por vez.
  // También mientras corre: es el estado que más se mira, y ocultar la traza y
  // los indicadores dejaba la pantalla casi vacía justo en ese momento.
  const indice = useTraceIndex(id, Boolean(run), running)
  const trace = indice.data ?? null
  const series = useMemo(() => buildRunSeries(seriesFrames(trace)), [trace])

  const borrado = useDeleteRun()
  const detener = useStopRun(id)

  const artifacts = useArtifacts(id, Boolean(run) && !running).data ?? []
  // El inventario ya dice si el video está, así que no hace falta la sonda con
  // Range de un byte que había antes: una petición menos y una fuente de verdad
  // sola en vez de dos que podían discrepar.
  const hasVideo = artifacts.some((a) => a.name === 'annotated.mp4')
  const comparison = useRunComparison(id, Boolean(run) && !running).data ?? null

  const handleDelete = async () => {
    setConfirmDelete(false)
    setDeleteError(null)
    try {
      const result = await borrado.mutateAsync(id)
      if (result?.errors) {
        // Borrado parcial (207): la corrida sigue existiendo en un plano, así
        // que no se navega — hay que quedarse y decir qué quedó a medias.
        setDeleteError(
          `Borrado parcial: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
        return
      }
      navigate('/')
    } catch (e) {
      setDeleteError(`No se pudo borrar: ${String(e)}`)
    }
  }

  const deleting = borrado.isPending

  if (loadError) return <ErrorBanner>Error cargando la corrida {id}: {String(loadError)}</ErrorBanner>
  if (!run) return <p className="eo-empty">Cargando la corrida {id}…</p>

  const summary = run.summary
  const topology = topologyBadge(summary)
  // `name` viaja top-level mientras la corrida está viva y dentro de summary una
  // vez terminada (persistido).
  const runName = run.name || (summary?.name as string | undefined)
  const duration = summary?.duration_seconds ?? null

  return (
    <>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      {/* Que falle el "Detener" no debe borrar la pantalla: la corrida sigue
          ahí y el operador necesita seguir viéndola para reintentar. */}
      {stopError && <ErrorBanner>{stopError}</ErrorBanner>}

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
            <span>{sourceLabel(summary?.source_type)}</span>
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
                detener
                  .mutateAsync()
                  .catch((e: unknown) => setStopError(`No se pudo detener: ${String(e)}`))
              }}
            >
              Detener
            </Button>
          )}
          {/* Atajo a los archivos generados: es la acción más frecuente sobre
              una corrida terminada y estaba a dos clicks, escondida en una
              pestaña. */}
          {!running && artifacts.length > 0 && (
            <Button onClick={() => setTab('files')}>
              <IconDownload />
              Archivos
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
        alerts={trace?.totals?.alerts ?? null}
        comparison={comparison}
      />

      <RunTimeline
        index={trace}
        selected={selected}
        loading={indice.isPending}
        onSelect={(_frameIndex, position) => setSelected(position)}
      />

      {indice.error && (
        <ErrorBanner>No se pudo leer la traza: {String(indice.error)}</ErrorBanner>
      )}
      {trace?.control_error && (
        <Banner tone="warn">
          El motor de reglas no pudo evaluar esta corrida: {trace.control_error}
        </Banner>
      )}

      <nav className="eo-tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'trace'} onClick={() => setTab('trace')}>
          Traza <span className="eo-tabs__count eo-mono">{trace?.total ?? 0}</span>
        </button>
        <button role="tab" aria-selected={tab === 'summary'} onClick={() => setTab('summary')}>
          Resumen
        </button>
        <button role="tab" aria-selected={tab === 'eval'} onClick={() => setTab('eval')}>
          Evaluación
        </button>
        <button role="tab" aria-selected={tab === 'files'} onClick={() => setTab('files')}>
          Archivos{' '}
          {artifacts.length > 0 && (
            <span className="eo-tabs__count eo-mono">{artifacts.length}</span>
          )}
        </button>
      </nav>

      {tab === 'trace' && (
        <TraceSection
          key={id}
          runId={id}
          totals={trace?.totals ?? null}
          enabled={Boolean(run)}
          jumpTo={selected}
        />
      )}

      {/* Dos tarjetas y no una lista mezclada: la configuración es lo que se
          pidió y el rendimiento es lo que salió. Juntas obligaban a separar
          a ojo la causa del efecto. */}
      {tab === 'summary' && (
        <div className="eo-summary">
          <Card title="Configuración">
            <dl className="eo-deflist">
              <div>
                <dt>Modelo</dt>
                <dd className="eo-mono">
                  {summary?.model_name ?? '—'} ({summary?.device ?? '—'})
                </dd>
              </div>
              <div>
                <dt>Conjunto de prompts</dt>
                <dd className="eo-mono">{summary?.prompt_set_id ?? '—'}</dd>
              </div>
              <div>
                <dt>Fuente</dt>
                <dd>{sourceLabel(summary?.source_type)}</dd>
              </div>
            </dl>
          </Card>

          <Card title="Rendimiento">
            <dl className="eo-deflist">
              <div>
                <dt>Cuadros procesados</dt>
                <dd className="eo-mono">{summary?.units_processed ?? '—'}</dd>
              </div>
              <div>
                <dt>Cuadros por segundo</dt>
                <dd className="eo-mono">{dec(summary?.fps_effective ?? null, 2)}</dd>
              </div>
              <div>
                <dt>Latencia (percentil 95)</dt>
                <dd className="eo-mono">{dec(summary?.p95_latency_ms ?? null, 0)} ms</dd>
              </div>
              <div>
                <dt>Duración</dt>
                <dd className="eo-mono">{duration != null ? `${dec(duration)} s` : '—'}</dd>
              </div>
            </dl>
          </Card>

          <Card title="Detecciones por clase" className="eo-summary__wide">
            {labelCounts(summary).length > 0 ? (
              <span className="eo-detchips">
                {labelCounts(summary).map(([k, v]) => (
                  <DetChip key={k} label={k} count={v} />
                ))}
              </span>
            ) : (
              <p className="eo-cap">
                {running
                  ? 'Todavía no hay detecciones consolidadas: se cuentan al terminar.'
                  : 'Esta corrida no detectó nada.'}
              </p>
            )}
          </Card>
        </div>
      )}

      {tab === 'eval' && (
        <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
      )}

      {tab === 'files' && (
        <>
          <Card title="Video anotado">
            {hasVideo ? (
              <video controls className="eo-video" src={artifactUrl(id, 'annotated.mp4')} />
            ) : (
              <p className="eo-cap">
                Esta corrida no generó video anotado. Se genera solo si se pide al lanzarla.
              </p>
            )}
          </Card>
          <Card title="Archivos generados" meta={`${artifacts.length}`} flush>
            {artifacts.length === 0 ? (
              <EmptyState hint="Los archivos quedan disponibles al terminar la corrida.">
                Sin archivos
              </EmptyState>
            ) : (
              <Table>
                <thead>
                  <tr>
                    <th>Archivo</th>
                    <th>Contenido</th>
                    <th className="eo-num">Tamaño</th>
                    <th aria-label="Descargar" />
                  </tr>
                </thead>
                <tbody>
                  {artifacts.map((a) => (
                    <tr key={a.path}>
                      <MonoCell>{a.name}</MonoCell>
                      <td>{a.description ?? '—'}</td>
                      <NumCell>{tamano(a.size_bytes)}</NumCell>
                      <td className="eo-cell--actions">
                        {/* Un directorio (previews/) no se descarga como
                            archivo: se ofrece solo lo que se puede servir. */}
                        {a.n_files === null && (
                          <a
                            className="eo-btn eo-btn--ghost"
                            href={artifactUrl(id, a.path)}
                            download
                            aria-label={`Descargar ${a.name}`}
                          >
                            Descargar
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card>
        </>
      )}
    </>
  )
}
