import { Fragment } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getEvidenceResult } from '../../api'
import {
  Badge, Button, Card, EmptyState, ErrorBanner, PageHeader, StatTile, Table,
} from '../../components/ui'
import type { ArchivedRun } from '../../types'
import { fmt } from './Paso'
import Desglose from './Desglose'

const runUrl = (run: ArchivedRun, id: string) =>
  `/evidencia/run?${new URLSearchParams({ plane: run.plane, run_id: run.run_id, id })}`

/** Agrupa el motivo de conservación de la página actual de corridas: un motivo
 *  compartido por varias filas (típico de un lote archivado en bloque) se
 *  cuenta una vez, no se repite por fila — la misma regla de "declarar, no
 *  repetir" que rige las filas sin dato de un desglose. Sólo cubre la página
 *  cargada (no las 68 corridas si hay más de una página): se rotula "en esta
 *  página" para no implicar un conteo que no se leyó. */
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
 *  la procedencia y las corridas que lo respaldan. Extraído de EvidencePage.tsx
 *  (que conserva el nivel de corrida inline). */
export default function Resultado() {
  const [params, setParams] = useSearchParams()
  const id = params.get('id') ?? ''
  const requestedPage = Number(params.get('page') ?? '1')
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1
  const result = useQuery({
    queryKey: ['evidencia', 'result', id, page],
    queryFn: () => getEvidenceResult(id, page),
  })
  if (result.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (result.error) return <ErrorBanner>No se pudo leer esta evidencia. Comprobá la referencia y la copia local del archivo.</ErrorBanner>
  if (result.data?.available === false) return <>
    <PageHeader title="Evidencia" />
    <EmptyState hint={result.data.message}>Archivo de evidencia no disponible</EmptyState>
  </>
  if (!result.data?.result) return <EmptyState>No se encontró evidencia para esta referencia.</EmptyState>

  const data = result.data
  const info = result.data.result
  const metricas = info.metricas
  const pages = Math.max(1, Math.ceil(data.total / data.page_size))
  const changePage = (next: number) => setParams({ id, page: String(next) })
  const motivos = motivosDe(data.items)

  return <div className="eo-evidence">
    <PageHeader
      title={info.titulo || info.etiqueta}
      meta={<>
        <span className="eo-mono">{info.result_id}</span>
        <span className="eo-sep">·</span>{info.n_runs} corridas
        <span className="eo-sep">·</span>{info.index}
      </>}
      actions={<Badge tone="neutral">Resultado</Badge>}
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
      {info.documents.map((doc) => <p className="eo-mono" key={doc}>{doc}</p>)}
      <details><summary>Fuentes registradas ({info.source_refs.length})</summary>
        <ul>{info.source_refs.map((ref) => <li key={ref} className="eo-mono">{ref}</li>)}</ul>
      </details>
    </Card>

    <div className="eo-stats-row">{Object.entries(info.roles).map(([role, count]) =>
      <StatTile key={role} label={role} value={count} />)}</div>

    {motivos.length > 0 && (
      <Card title="Corridas plegadas" meta={`${data.items.length} en esta página`}>
        <details className="eo-adv">
          <summary>{motivos.length === 1 ? '1 motivo de conservación' : `${motivos.length} motivos de conservación`}</summary>
          <div className="eo-adv__body">
            <ul className="eo-mini__list">
              {motivos.map(([motivo, count]) => <li key={motivo}><b>{count}</b> {motivo}</li>)}
            </ul>
          </div>
        </details>
      </Card>
    )}

    <Card title="Corridas por rol" meta={`${data.items.length} de ${data.total}`}>
      <Table aria-label="Corridas de evidencia">
        <thead><tr><th>Corrida</th><th>Plano</th><th>Conservación</th><th>Fuente</th></tr></thead>
        <tbody>{data.items.map((row, i) => <Fragment key={`${row.plane}/${row.run_id}/${row.role}/${row.source_ref}`}>
          {(i === 0 || data.items[i - 1].role !== row.role) && <tr><th colSpan={4}>{row.role}</th></tr>}
          <tr>
            <td><Link to={runUrl(row, id)} className="eo-mono">{row.run_id}</Link></td>
            <td>{row.plane === 'media-plane' ? 'Medios' : 'Control'}</td>
            <td><Badge tone="neutral">{row.status === 'archived_only' ? 'Sólo archivo' : 'Copia curada'}</Badge></td>
            <td className="eo-mono">{row.source_ref}</td>
          </tr>
        </Fragment>)}</tbody>
      </Table>
      {data.items.length === 0 && <EmptyState>No hay corridas en esta página.</EmptyState>}
    </Card>
    <div className="eo-toolbar" aria-label="Paginación de evidencia">
      <Button variant="ghost" disabled={page <= 1} onClick={() => changePage(page - 1)}>Anterior</Button>
      <span>Página {page} de {pages}</span>
      <Button variant="ghost" disabled={page >= pages} onClick={() => changePage(page + 1)}>Siguiente</Button>
    </div>
  </div>
}
