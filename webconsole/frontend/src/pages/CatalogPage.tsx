import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Badge, Button, Card, EmptyState, ErrorBanner, LoadingState, MonoCell, PageHeader, StaleNotice,
  Table, TableScroll,
} from '../components/ui'
import { useTargetQuery } from '../api/queries/platform'
import { useCatalogPromptSets, useDatasets, useIngestPlugins } from '../api/queries/catalog'
import { sourceLabel } from '../runview'
import type { PromptSet } from '../types'

/** Nombre legible de cada umbral del modelo. Las claves son de la API. */
const UMBRAL_LABEL: Record<string, string> = {
  confidence: 'Confianza mínima',
  iou: 'Solapamiento máximo',
  box: 'Umbral de caja',
  text: 'Umbral de texto',
}

/** Una fuente acotada termina sola; una en vivo no. */
const KIND_LABEL: Record<string, string> = {
  bounded: 'Acotado',
  live: 'En vivo',
}

/** Cuántas clases se muestran de entrada en cada conjunto. */
const CLASES_VISIBLES = 4

const dec2 = (v: number): string => v.toFixed(2).replace('.', ',')

type Consulta = { isPending: boolean; error: unknown; data: unknown; isFetching: boolean; refetch: () => unknown }

/** Carga y fallo de UN catálogo, en su propia tarjeta: que falle uno no se
 *  presenta como que los otros están vacíos. */
function EstadoCatalogo({ q, que }: { q: Consulta; que: string }): ReactNode {
  if (q.isPending && !q.data) return <LoadingState lines={3}>Cargando {que}…</LoadingState>
  if (q.error && !q.data) {
    return (
      <ErrorBanner detail={String(q.error)} onRetry={() => void q.refetch()} retrying={q.isFetching}>
        No se pudo leer {que}.
      </ErrorBanner>
    )
  }
  if (q.error) return <StaleNotice what={que} onRetry={() => void q.refetch()} retrying={q.isFetching} />
  return null
}

/** Las clases de un conjunto: las primeras a la vista y el resto a un click.
 *  Todas están: plegar no recorta la lista, sólo el alto de la fila. */
function ClasesDelConjunto({ set }: { set: PromptSet }) {
  const [todas, setTodas] = useState(false)
  const ids = set.classes.map((c) => c.id)
  const visibles = todas ? ids : ids.slice(0, CLASES_VISIBLES)
  const listaId = `clases-${set.id}`
  return (
    <div>
      <span className="eo-mono" id={listaId}>{visibles.join(', ')}</span>
      {ids.length > CLASES_VISIBLES && (
        <>
          {!todas && <span className="eo-cell--muted"> … </span>}
          <Button
            variant="ghost"
            aria-expanded={todas}
            aria-controls={listaId}
            onClick={() => setTodas((v) => !v)}
          >
            {todas ? 'Ver menos' : `Ver las ${ids.length} clases`}
          </Button>
        </>
      )}
    </div>
  )
}

export default function CatalogPage() {
  const targetQ = useTargetQuery()
  const target = targetQ.data ?? null
  // Los catálogos llevan la referencia del modelo en su clave de caché, así que
  // se recargan solos si el servicio reinicia con otro modelo.
  const pluginsQ = useIngestPlugins()
  const datasetsQ = useDatasets()
  const setsQ = useCatalogPromptSets()
  const plugins = pluginsQ.data ?? []
  const datasets = datasetsQ.data ?? []
  const sets = setsQ.data ?? []
  return (
    <>
      <PageHeader
        title="Catálogos"
        meta="Lo que la instancia activa ofrece hoy — solo lectura"
      />

      {/* Tarjeta destacada y no una tabla de una fila: el modelo en uso es el
          contexto de todo lo demás de la pantalla, no un registro más. */}
      {target?.model ? (
        <section className="eo-target" aria-labelledby="modelo-en-uso">
          <div className="eo-target__label" id="modelo-en-uso">Modelo en uso</div>
          <div className="eo-target__name">{target.model.ref}</div>
          <dl className="eo-params eo-target__foot">
            <div>
              <dt>Adaptador</dt>
              <dd>{target.model.adapter ?? '—'}</dd>
            </div>
            <div>
              <dt>Dispositivo</dt>
              <dd>{target.model.device ?? '—'}</dd>
            </div>
            {Object.entries(target.model.thresholds)
              .filter(([, v]) => v != null)
              .map(([k, v]) => (
                <div key={k}>
                  <dt>{UMBRAL_LABEL[k] ?? k}</dt>
                  <dd>{dec2(Number(v))}</dd>
                </div>
              ))}
          </dl>
          <p className="eo-cap">
            Estos valores son fijos por instancia. Para usar otro modelo hay que activar otra
            instancia desde <Link to="/platform">Plataforma</Link>.
          </p>
        </section>
      ) : (
        <Card title="Modelo en uso" flush>
          {targetQ.isPending && !target ? (
            <LoadingState lines={2}>Verificando el motor de detección…</LoadingState>
          ) : targetQ.error && !target ? (
            <ErrorBanner detail={String(targetQ.error)} onRetry={() => void targetQ.refetch()} retrying={targetQ.isFetching}>
              No se pudo consultar el motor de detección.
            </ErrorBanner>
          ) : (
            <EmptyState
              hint={<>El motor de detección respondió sin un modelo cargado. Se elige desde <Link to="/platform">Plataforma</Link>.</>}
            >
              Servicio no listo
            </EmptyState>
          )}
        </Card>
      )}

      <Card
        title="Orígenes de imágenes"
        meta={pluginsQ.data ? `${plugins.filter((p) => p.enabled).length} de ${plugins.length} disponibles` : undefined}
        flush
      >
        <EstadoCatalogo q={pluginsQ} que="los orígenes de imágenes" />
        {pluginsQ.data && (plugins.length === 0 ? (
          <EmptyState>Sin orígenes de imágenes</EmptyState>
        ) : (
          <TableScroll label="Orígenes de imágenes">
            <Table aria-label="Orígenes de imágenes">
              <thead>
                <tr>
                  <th>Origen</th>
                  <th>Tipo</th>
                  <th>Disponibilidad</th>
                  <th>Por qué</th>
                </tr>
              </thead>
              <tbody>
                {plugins.map((p) => (
                  <tr key={p.id}>
                    <td>{sourceLabel(p.id)}</td>
                    <td>{KIND_LABEL[p.kind] ?? p.kind}</td>
                    <td>
                      {!p.available ? (
                        <Badge tone="neutral">No disponible</Badge>
                      ) : !p.enabled ? (
                        <Badge tone="warn">No habilitada</Badge>
                      ) : (
                        <Badge tone="ok">Disponible</Badge>
                      )}
                    </td>
                    {/* El motivo del backend gana sobre la descripción genérica:
                        dice por qué NO se puede usar, que es lo que se busca acá. */}
                    <td className="eo-cell--wrap">{p.disabled_reason ?? p.description}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        ))}
      </Card>

      <Card title="Conjuntos de imágenes" meta={datasetsQ.data ? `${datasets.length}` : undefined} flush>
        <EstadoCatalogo q={datasetsQ} que="los conjuntos de imágenes" />
        {datasetsQ.data && (datasets.length === 0 ? (
          <EmptyState>Sin conjuntos de imágenes</EmptyState>
        ) : (
          <TableScroll label="Conjuntos de imágenes">
            <Table aria-label="Conjuntos de imágenes">
              <thead>
                <tr>
                  <th>Conjunto</th>
                  <th>Por qué</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <MonoCell>{d.id}</MonoCell>
                    <td className="eo-cell--wrap">{d.description}</td>
                    <td>
                      {d.available ? (
                        <Badge tone="ok">Montado</Badge>
                      ) : (
                        <Badge tone="neutral">No montado</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        ))}
      </Card>

      <Card title="Conjuntos de prompts del repositorio" meta={setsQ.data ? `${sets.length}` : undefined} flush>
        <EstadoCatalogo q={setsQ} que="los conjuntos de prompts" />
        {setsQ.data && (sets.length === 0 ? (
          <EmptyState>Sin conjuntos de prompts</EmptyState>
        ) : (
          <TableScroll label="Conjuntos de prompts del repositorio">
            <Table aria-label="Conjuntos de prompts del repositorio">
              <thead>
                <tr>
                  <th>Conjunto</th>
                  <th>Estado</th>
                  <th className="eo-th--numeric">Clases</th>
                  <th>Clases que define</th>
                </tr>
              </thead>
              <tbody>
                {sets.map((s) => (
                  <tr key={s.id}>
                    <MonoCell>{s.id}</MonoCell>
                    <td>
                      {s.frozen ? <Badge tone="ok">Congelado</Badge> : <Badge tone="neutral">Abierto</Badge>}
                    </td>
                    <td className="eo-num">{s.classes.length}</td>
                    <td className="eo-cell--wrap"><ClasesDelConjunto set={s} /></td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        ))}
      </Card>
    </>
  )
}
