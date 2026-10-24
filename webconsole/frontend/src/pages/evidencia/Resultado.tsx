import { Fragment } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getEvidenceResult } from '../../api'
import {
  Badge, Button, Card, Disclosure, EmptyState, PageHeader, StatTile, Table, TableScroll, Tag,
} from '../../components/ui'
import type { ArchivedRun } from '../../types'
import { fmt } from './Paso'
import Desglose from './Desglose'
import { ArchivoAusente, EstadoDeLectura, Evidencia, Rol, ROL_LABEL } from './comun'

/** El enlace a una corrida archivada lleva el contexto de la navegación —el
 *  resultado y, si se vino de un paso, el paso— sin inventar uno que no vino. */
const runUrl = (run: ArchivedRun, id: string, paso: string | null) =>
  `/evidencia/run?${new URLSearchParams({
    plane: run.plane, run_id: run.run_id, id, ...(paso ? { paso } : {}),
  })}`

/** Agrupa el motivo de conservación de la página actual de corridas: un motivo
 *  compartido por varias filas (típico de un lote archivado en bloque) se
 *  cuenta una vez, no se repite por fila. Sólo cubre la página cargada: se
 *  rotula "en esta página" para no implicar un conteo que no se leyó. */
function motivosDe(items: ArchivedRun[]): Array<[string, number]> {
  const porMotivo = new Map<string, number>()
  for (const item of items) {
    if (!item.reason) continue
    porMotivo.set(item.reason, (porMotivo.get(item.reason) ?? 0) + 1)
  }
  return [...porMotivo.entries()]
}

/** El nivel de resultado: el agregado (StatTile por `metricas.cabecera`) Y su
 *  desglose (`metricas.desgloses`, nunca sólo el agregado — limitación L5),
 *  la procedencia y las corridas que lo respaldan. */
export default function Resultado() {
  const [params, setParams] = useSearchParams()
  const id = params.get('id') ?? ''
  const paso = params.get('paso')
  const requestedPage = Number(params.get('page') ?? '1')
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1
  const result = useQuery({
    queryKey: ['evidencia', 'result', id, page],
    queryFn: () => getEvidenceResult(id, page),
  })
  if (result.isPending || result.error) return <EstadoDeLectura titulo={id || 'Resultado'} q={result} />
  if (result.data?.available === false) return <ArchivoAusente message={result.data.message} />
  if (!result.data?.result) {
    return <Evidencia>
      <PageHeader title={id || 'Resultado'} />
      <EmptyState>No se encontró evidencia para esta referencia.</EmptyState>
    </Evidencia>
  }

  const data = result.data
  const info = result.data.result
  const metricas = info.metricas
  const pages = Math.max(1, Math.ceil(data.total / data.page_size))
  // Cambiar de página toca SÓLO la página: `id`, `paso` y cualquier otro
  // parámetro de la navegación quedan como estaban.
  const changePage = (next: number) =>
    setParams((prev) => {
      const nuevos = new URLSearchParams(prev)
      nuevos.set('page', String(next))
      return nuevos
    })
  const motivos = motivosDe(data.items)

  return <Evidencia>
    <PageHeader
      title={info.titulo || info.etiqueta}
      meta={<>
        <span className="eo-mono">{info.result_id}</span>
        <span className="eo-sep">·</span>{info.n_runs} corridas
        <span className="eo-sep">·</span>{info.index}
      </>}
      actions={<Tag>Resultado</Tag>}
    />
    {info.reclamo && <p className="eo-note">{info.reclamo}</p>}

    {metricas && metricas.cabecera.length > 0 && (
      <div className="eo-stats-row">
        {metricas.cabecera.map((c) => (
          <StatTile key={c.label} label={c.label} value={fmt(c.valor, c.entero)} unit={c.nota} />
        ))}
      </div>
    )}
    {!metricas && <p className="eo-note">Sin metrics.json leído para este resultado.</p>}

    {metricas && metricas.desgloses.length > 0 && (
      <div className="eo-cols">
        {metricas.desgloses.map((d) => <Desglose key={d.id} esquema={metricas.esquema} desglose={d} />)}
      </div>
    )}

    <Card title="Procedencia">
      {/* Los documentos que lo citan, a la vista; las fuentes registradas,
          completas, a un click — no en un `title`. */}
      {info.documents.length > 0 ? (
        <ul className="eo-mini__list">
          {info.documents.map((doc) => <li key={doc} className="eo-mono">{doc}</li>)}
        </ul>
      ) : (
        <p className="eo-note">Ningún documento declarado.</p>
      )}
      <Disclosure summary={`Fuentes registradas (${info.source_refs.length})`}>
        <ul className="eo-mini__list">{info.source_refs.map((ref) => <li key={ref} className="eo-mono">{ref}</li>)}</ul>
      </Disclosure>
    </Card>

    <div className="eo-stats-row">{Object.entries(info.roles).map(([role, count]) =>
      <StatTile key={role} label={ROL_LABEL[role] ?? role} value={count} unit={ROL_LABEL[role] ? role : undefined} />)}</div>

    {motivos.length > 0 && (
      <Card title="Corridas plegadas" meta={`${data.items.length} en esta página`}>
        <Disclosure summary={motivos.length === 1 ? '1 motivo de conservación' : `${motivos.length} motivos de conservación`}>
          <ul className="eo-mini__list">
            {motivos.map(([motivo, count]) => <li key={motivo}><b>{count}</b> {motivo}</li>)}
          </ul>
        </Disclosure>
      </Card>
    )}

    <Card title="Corridas por rol" meta={`${data.items.length} de ${data.total}`} flush>
      <TableScroll label="Corridas de evidencia">
        <Table aria-label="Corridas de evidencia">
          <thead><tr><th>Corrida</th><th>Plano</th><th>Conservación</th><th>Fuente</th></tr></thead>
          <tbody>{data.items.map((row, i) => <Fragment key={`${row.plane}/${row.run_id}/${row.role}/${row.source_ref}`}>
            {(i === 0 || data.items[i - 1].role !== row.role) && (
              <tr><th colSpan={4} scope="colgroup"><Rol role={row.role} /></th></tr>
            )}
            <tr>
              <td><Link to={runUrl(row, id, paso)} className="eo-mono">{row.run_id}</Link></td>
              <td>{row.plane === 'media-plane' ? 'Medios' : 'Control'}</td>
              <td><Badge tone="neutral">{row.status === 'archived_only' ? 'Sólo archivo' : 'Copia curada'}</Badge></td>
              <td className="eo-mono">{row.source_ref}</td>
            </tr>
          </Fragment>)}</tbody>
        </Table>
      </TableScroll>
      {data.items.length === 0 && <EmptyState>No hay corridas en esta página.</EmptyState>}
    </Card>
    <nav className="eo-pager" aria-label="Paginación de evidencia">
      <Button disabled={page <= 1} onClick={() => changePage(page - 1)}>Anterior</Button>
      <span aria-live="polite">Página {page} de {pages}</span>
      <Button disabled={page >= pages} onClick={() => changePage(page + 1)}>Siguiente</Button>
    </nav>
  </Evidencia>
}
