import { Fragment } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getArchivedRun, getEvidenceIndex, getEvidenceResult } from '../api'
import { Badge, Button, Card, EmptyState, ErrorBanner, PageHeader, StatTile, Table } from '../components/ui'
import type { ArchivedRun } from '../types'
import './EvidencePage.css'

const resultUrl = (id: string) => `/evidencia/resultado?${new URLSearchParams({ id })}`
const runUrl = (run: ArchivedRun, id: string) =>
  `/evidencia/run?${new URLSearchParams({ plane: run.plane, run_id: run.run_id, id })}`

export default function EvidencePage() {
  const { pathname } = useLocation()
  const [params, setParams] = useSearchParams()
  const id = params.get('id') ?? ''
  const plane = params.get('plane') ?? ''
  const runId = params.get('run_id') ?? ''
  const requestedPage = Number(params.get('page') ?? '1')
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1
  const level = pathname === '/evidencia/run' ? 'run' : pathname === '/evidencia/resultado' ? 'result' : 'index'
  const index = useQuery({
    queryKey: ['evidencia', 'index'], queryFn: getEvidenceIndex, enabled: level === 'index',
  })
  const result = useQuery({
    queryKey: ['evidencia', 'result', id, page],
    queryFn: () => getEvidenceResult(id, page), enabled: level === 'result',
  })
  const run = useQuery({
    queryKey: ['evidencia', 'run', plane, runId],
    queryFn: () => getArchivedRun(plane, runId), enabled: level === 'run',
  })
  const active = level === 'index' ? index : level === 'result' ? result : run
  if (active.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (active.error) return <ErrorBanner>No se pudo leer esta evidencia. Comprobá la referencia y la copia local del archivo.</ErrorBanner>
  if (active.data?.available === false) return <>
    <PageHeader title="Evidencia" />
    <EmptyState hint={active.data.message}>Archivo de evidencia no disponible</EmptyState>
  </>

  if (level === 'index' && index.data) {
    const groups = index.data.collections
    const total = groups.reduce((n, group) => n + group.n_results, 0)
    return <div className="eo-evidence">
      <PageHeader title="Evidencia" meta={`${total} resultados · ${groups.length} índices`} />
      <p className="eo-note">Resultados del informe y sus corridas de respaldo. Lectura del archivo curado, sin consultar los servicios.</p>
      {groups.length === 0 && <EmptyState>No hay resultados en el registro de evidencia.</EmptyState>}
      <div className="eo-evidence__indices">
        {groups.map((group) => <Card key={group.id} title={group.id} meta={`${group.n_results} resultados`}>
          <p className="eo-note">results/{group.id}/ · {group.n_rows} relaciones registradas</p>
          <Table aria-label={`Resultados de ${group.id}`}>
            <thead><tr><th>Resultado</th><th className="eo-num">Corridas</th></tr></thead>
            <tbody>{group.results.map((row) => <tr key={row.result_id}>
              <td><Link to={resultUrl(row.result_id)}>{row.titulo || row.etiqueta}</Link></td>
              <td className="eo-num">{row.n_runs}</td>
            </tr>)}</tbody>
          </Table>
        </Card>)}
      </div>
    </div>
  }
  if (level === 'result' && result.data?.result) {
    const data = result.data
    const info = result.data.result
    const pages = Math.max(1, Math.ceil(data.total / data.page_size))
    const changePage = (next: number) => setParams({ id, page: String(next) })
    return <div className="eo-evidence">
      <PageHeader title={info.titulo || info.etiqueta} meta={`${info.n_runs} corridas · ${info.index}`} />
      <p className="eo-note">{info.result_id} · results/{info.index}/</p>
      <Card title="Procedencia">
        {info.documents.map((doc) => <p className="eo-mono" key={doc}>{doc}</p>)}
        <details><summary>Fuentes registradas ({info.source_refs.length})</summary>
          <ul>{info.source_refs.map((ref) => <li key={ref} className="eo-mono">{ref}</li>)}</ul>
        </details>
      </Card>
      <div className="eo-stats-row">{Object.entries(info.roles).map(([role, count]) =>
        <StatTile key={role} label={role} value={count} />)}</div>
      <Card title="Corridas por rol" meta={`${data.items.length} de ${data.total}`}>
        <Table aria-label="Corridas de evidencia">
          <thead><tr><th>Corrida</th><th>Plano</th><th>Conservación</th><th>Fuente</th></tr></thead>
          <tbody>{data.items.map((row, i) => <Fragment key={`${row.plane}/${row.run_id}/${row.role}/${row.source_ref}`}>
            {(i === 0 || data.items[i - 1].role !== row.role) && <tr><th colSpan={4}>{row.role}</th></tr>}
            <tr>
              <td><Link to={runUrl(row, id)} className="eo-mono">{row.run_id}</Link></td>
              <td>{row.plane === 'media-plane' ? 'Medios' : 'Control'}</td>
              <td><Badge tone="neutral">{row.status === 'archived_only' ? 'Sólo archivo' : 'Copia curada'}</Badge>
                {row.reason && <p className="eo-note">{row.reason}</p>}</td>
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
  if (level === 'run' && run.data?.run) {
    const data = run.data
    const info = run.data.run
    const values = Object.entries(data.summary ?? {}).filter(([, value]) => value === null || typeof value !== 'object')
    return <div className="eo-evidence">
      <PageHeader title="Corrida de evidencia" meta={info.plane === 'media-plane' ? 'Medios' : 'Control'} />
      <p className="eo-mono">{info.run_id}</p>
      <Badge tone="neutral">{info.status === 'archived_only' ? 'Sólo archivo' : 'Copia curada'}</Badge>
      {info.reason && <p>{info.reason}</p>}
      {!info.tiene_detalle_vivo && <p className="eo-note">La evidencia se conserva en el archivo; no hay un detalle vivo disponible.</p>}
      {info.tiene_detalle_vivo && info.plane === 'media-plane' && <p><Link to={`/runs/${encodeURIComponent(info.run_id)}`}>Abrir detalle vivo</Link> · requiere el servicio de medios.</p>}
      {info.tiene_detalle_vivo && info.plane === 'control-plane' && <p className="eo-note">El directorio original de control está disponible. Esta consola no tiene una vista viva de control.</p>}
      <Card title="Procedencia"><p className="eo-mono">{info.source_ref}</p>
        <p className="eo-note">Rol: {info.role}</p>
        {data.relations?.map((relation) => <p key={`${relation.result_id}/${relation.role}/${relation.source_ref}`}>
          <Link to={resultUrl(relation.result_id)}>{relation.result_id}</Link> · {relation.role}
        </p>)}
      </Card>
      {data.notice && <p className="eo-note">{data.notice}</p>}
      {data.summary && <Card title="Summary congelado">
        {data.summary_source && <p className="eo-note">Conservado en {data.summary_source}</p>}
        <Table aria-label="Summary congelado"><thead><tr><th>Campo</th><th>Valor</th></tr></thead>
          <tbody>{values.map(([key, value]) => <tr key={key}><td>{key}</td><td>{value === null ? '—' : String(value)}</td></tr>)}</tbody>
        </Table>
        <details><summary>Summary completo</summary><pre>{JSON.stringify(data.summary, null, 2)}</pre></details>
      </Card>}
      {data.substitutes.map((artifact) => <Card key={artifact.name} title={artifact.name}>
        <details open={!data.summary}><summary>Artefacto sustituto preservado</summary><pre>{JSON.stringify(artifact.data, null, 2)}</pre></details>
      </Card>)}
    </div>
  }
  return <EmptyState>No se encontró evidencia para esta referencia.</EmptyState>
}
