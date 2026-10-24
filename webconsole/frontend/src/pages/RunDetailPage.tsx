import { useCallback, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { artifactUrl } from '../api'
import {
  useArtifacts, useDeleteRun, useRun, useRunComparison, useStopRun, useTraceIndex,
} from '../api/queries/runs'
import EvalSection from '../components/EvalSection'
import RunKpiStrip from '../components/RunKpiStrip'
import RunTimeline from '../components/RunTimeline'
import TraceSection, { type TraceJump } from '../components/TraceSection'
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
  LoadingState,
  MonoCell,
  NumCell,
  PageHeader,
  TabPanel,
  Table,
  TableScroll,
  Tabs,
  Tag,
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

/** Posición de un cuadro en el índice completo, para mover el cursor de la
 *  línea de tiempo al cuadro que eligió la lista. Se busca por `unit_id`
 *  (único) y, en una traza vieja sin él, por `frame_index`. */
function usePosicionEnIndice(index: TraceIndex | null) {
  return useMemo(() => {
    const porUnidad = new Map<string, number>()
    const porCuadro = new Map<number, number>()
    index?.unit_id.forEach((u, i) => { if (u != null) porUnidad.set(u, i) })
    index?.frame_index.forEach((f, i) => { if (f != null) porCuadro.set(f, i) })
    return (frame: TraceFrame | null): number | null => {
      if (!frame) return null
      if (frame.unit_id != null && porUnidad.has(frame.unit_id)) return porUnidad.get(frame.unit_id)!
      if (frame.frame_index != null && porCuadro.has(frame.frame_index)) return porCuadro.get(frame.frame_index)!
      return null
    }
  }, [index])
}

export default function RunDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [stopError, setStopError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('trace')
  // El cursor de la línea de tiempo sigue al cuadro elegido en la lista; el
  // pedido de salto (lo que se tocó en la línea de tiempo) lleva la lista a
  // ese cuadro. Mientras la lista no llegó, el cursor muestra el pedido.
  const [cuadroElegido, setCuadroElegido] = useState<TraceFrame | null>(null)
  const [cursorPedido, setCursorPedido] = useState<number | null>(null)
  const [salto, setSalto] = useState<TraceJump | null>(null)

  // Mientras la corrida está viva la query se repregunta sola (caso de dos
  // equipos: no hay WS y el estado se re-hidrata por reloj). Al terminar, para.
  const consultaCorrida = useRun(id)
  const { data: run = null, error: loadError } = consultaCorrida
  const running = run?.status === 'running'
  const streamable = Boolean(run && isLive(run))

  // La línea de tiempo se alimenta del índice (la corrida completa en una sola
  // petición); la lista de cuadros trae su propia página.
  const indice = useTraceIndex(id, Boolean(run), running)
  const trace = indice.data ?? null
  const series = useMemo(() => buildRunSeries(seriesFrames(trace)), [trace])
  const posicionDe = usePosicionEnIndice(trace)
  // Derivado y no guardado: si el índice llega después que la lista, el
  // cursor aparece igual en el cuadro elegido.
  const cursor = cursorPedido ?? posicionDe(cuadroElegido)
  const alCambiarCuadro = useCallback((frame: TraceFrame | null) => {
    setCuadroElegido(frame)
    setCursorPedido(null)
  }, [])

  const borrado = useDeleteRun()
  const detener = useStopRun(id)

  const artifactsQuery = useArtifacts(id, Boolean(run) && !running)
  const artifacts = artifactsQuery.data?.items ?? []
  // El inventario ya dice si el video está, así que no hace falta una sonda
  // aparte: una fuente de verdad sola en vez de dos que podían discrepar.
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

  // Sin la corrida todavía: la cabecera queda en su lugar con el identificador
  // pedido, y sólo el contenido espera o explica el fallo.
  if (!run) {
    return (
      <>
        <PageHeader title={id} meta={loadError ? 'No se pudo leer la corrida' : 'Cargando la corrida…'} />
        {loadError ? (
          <ErrorBanner
            detail={String(loadError)}
            onRetry={() => void consultaCorrida.refetch()}
            retrying={consultaCorrida.isFetching}
          >
            Error cargando la corrida {id}: el motor de detección no devolvió su detalle.
          </ErrorBanner>
        ) : (
          <LoadingState lines={4}>Cargando la corrida {id}…</LoadingState>
        )}
      </>
    )
  }

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

      <PageHeader
        title={runName || run.run_id}
        meta={
          <>
            <Badge tone={runStatusTone(run)} pulse={running}>
              {runStatusLabel(run)}
            </Badge>
            {topology && <Tag>{topology}</Tag>}
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
          </>
        }
        actions={
          <>
            {streamable && (
              <Button
                disabled={detener.isPending}
                aria-busy={detener.isPending || undefined}
                onClick={() => {
                  if (detener.isPending) return
                  setStopError(null)
                  detener
                    .mutateAsync()
                    .catch((e: unknown) => setStopError(`No se pudo detener: ${String(e)}`))
                }}
              >
                {detener.isPending ? 'Deteniendo…' : 'Detener'}
              </Button>
            )}
            {/* Atajo a los archivos generados: es la acción más frecuente sobre
                una corrida terminada. Selecciona la pestaña Archivos. */}
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
                  {deleting ? 'Borrando…' : 'Borrar'}
                </Button>
              ))}
          </>
        }
      />

      <Tabs<Tab>
        idBase="corrida"
        label="Secciones de la corrida"
        value={tab}
        onChange={setTab}
        items={[
          { id: 'trace', label: 'Traza', count: trace?.total ?? (indice.isPending ? '…' : 0) },
          { id: 'summary', label: 'Resumen' },
          { id: 'eval', label: 'Evaluación' },
          { id: 'files', label: 'Archivos', count: artifacts.length > 0 ? artifacts.length : undefined },
        ]}
      />

      {tab === 'trace' && (
        <TabPanel idBase="corrida" id="trace">
          <RunTimeline
            index={trace}
            selected={cursor}
            loading={indice.isPending}
            error={indice.error}
            onRetry={() => void indice.refetch()}
            retrying={indice.isFetching}
            onSelect={(_frameIndex, position) => {
              setCursorPedido(position)
              setSalto((prev) => ({ pos: position, seq: (prev?.seq ?? 0) + 1 }))
            }}
          />
          {trace?.control_error && (
            <Banner tone="warn">
              El motor de reglas no pudo evaluar esta corrida: {trace.control_error}
            </Banner>
          )}
          <TraceSection
            key={id}
            runId={id}
            totals={trace?.totals ?? null}
            enabled={Boolean(run)}
            running={running}
            jumpTo={salto}
            onFrameChange={alCambiarCuadro}
          />
        </TabPanel>
      )}

      {/* Indicadores, configuración (lo que se pidió) y procesamiento (lo que
          salió). Lo que la tira de indicadores ya muestra no se repite en las
          tarjetas: sólo quedan los datos que la tira no tiene en ese estado. */}
      {tab === 'summary' && (
        <TabPanel idBase="corrida" id="summary">
          <RunKpiStrip
            summary={summary}
            series={series}
            live={running}
            alerts={trace?.totals?.alerts ?? null}
            comparison={comparison}
          />
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

            <Card title="Procesamiento">
              <dl className="eo-deflist">
                <div>
                  <dt>Cuadros procesados</dt>
                  <dd className="eo-mono">{summary?.units_processed ?? '—'}</dd>
                </div>
                {/* En curso la tira no muestra el percentil 95 ni la duración
                    (todavía no son estables): se conservan acá. */}
                {running && (
                  <>
                    <div>
                      <dt>Latencia (percentil 95)</dt>
                      <dd className="eo-mono">{dec(summary?.p95_latency_ms ?? null, 0)} ms</dd>
                    </div>
                    <div>
                      <dt>Duración</dt>
                      <dd className="eo-mono">{duration != null ? `${dec(duration)} s` : '—'}</dd>
                    </div>
                  </>
                )}
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
        </TabPanel>
      )}

      {tab === 'eval' && (
        <TabPanel idBase="corrida" id="eval">
          {run.bench_split ? (
            <EvalSection runId={id} benchSplit={run.bench_split} evaluated={run.evaluated} />
          ) : (
            // La pestaña sigue disponible y dice por qué no hay nada que
            // evaluar, en vez de abrirse en blanco.
            <Card title="Evaluación">
              <EmptyState hint="Sólo se evalúan las corridas hechas sobre un conjunto anotado del BENCH: ahí hay detecciones de referencia contra las que medir. Las corridas sobre video o cámara no tienen ese conjunto.">
                Esta corrida no tiene un conjunto de evaluación asociado
              </EmptyState>
            </Card>
          )}
        </TabPanel>
      )}

      {tab === 'files' && (
        <TabPanel idBase="corrida" id="files">
          {artifactsQuery.error && (
            <ErrorBanner
              detail={String(artifactsQuery.error)}
              onRetry={() => void artifactsQuery.refetch()}
              retrying={artifactsQuery.isFetching}
            >
              No se pudo consultar el inventario de archivos.
            </ErrorBanner>
          )}
          {artifactsQuery.data?.complete === false && (
            <Banner tone="warn">{artifactsQuery.data.notice}</Banner>
          )}
          <Card title="Archivos generados" meta={artifactsQuery.data ? `${artifacts.length}` : undefined} flush>
            {running ? (
              <EmptyState hint="Los archivos quedan disponibles al terminar la corrida.">
                La corrida sigue en curso
              </EmptyState>
            ) : artifactsQuery.isPending ? (
              <LoadingState lines={3}>Leyendo el inventario de archivos…</LoadingState>
            ) : artifactsQuery.error && !artifactsQuery.data ? null : artifacts.length === 0 ? (
              <EmptyState hint="Los archivos quedan disponibles al terminar la corrida.">
                Sin archivos
              </EmptyState>
            ) : (
              <TableScroll label="Archivos generados">
                <Table aria-label="Archivos generados">
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
                              <IconDownload />
                              Descargar
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </TableScroll>
            )}
          </Card>
          <Card title="Video anotado">
            {hasVideo ? (
              <video controls className="eo-video" src={artifactUrl(id, 'annotated.mp4')} />
            ) : (
              <p className="eo-cap">
                {artifactsQuery.data
                  ? 'Esta corrida no generó video anotado. Se genera solo si se pide al lanzarla.'
                  : 'El video anotado se ofrece cuando el inventario de archivos lo confirma.'}
              </p>
            )}
          </Card>
        </TabPanel>
      )}
    </>
  )
}
