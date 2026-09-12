import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getArchivedRun, getEvidenceRecorrido } from '../api'
import { Badge, Card, EmptyState, ErrorBanner, PageHeader, Table } from '../components/ui'
import Entrada from './evidencia/Entrada'
import Paso, { TablaResultados } from './evidencia/Paso'
import Resultado from './evidencia/Resultado'
import './EvidencePage.css'

const resultUrl = (id: string) => `/evidencia/resultado?${new URLSearchParams({ id })}`

/** El respaldo instrumental reusa la tabla de un paso, pero se sirve inline:
 *  no tiene ruta propia en la API (su desglose viaja en la respuesta de
 *  `/api/evidencia`, dentro de `respaldo.resultados`), así que extraerlo como
 *  pantalla propia sería inventar una fuente de datos que no existe. */
function Respaldo() {
  const q = useQuery({ queryKey: ['evidencia', 'recorrido'], queryFn: getEvidenceRecorrido })
  if (q.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (q.error) return <ErrorBanner>No se pudo leer el archivo de evidencia.</ErrorBanner>
  if (q.data.available === false) return <>
    <PageHeader title="Evidencia" />
    <EmptyState hint={q.data.message}>Archivo de evidencia no disponible</EmptyState>
  </>
  const respaldo = q.data.respaldo
  if (!respaldo) return <EmptyState>No hay respaldo instrumental registrado.</EmptyState>
  return <div className="eo-evidence">
    <PageHeader title={respaldo.titulo} meta={`${respaldo.resultados.length} resultados`} />
    <p className="eo-note">{respaldo.claim}</p>
    <Card title="Las mediciones de respaldo" flush>
      <TablaResultados resultados={respaldo.resultados} caption="Mediciones de respaldo instrumental" />
    </Card>
  </div>
}

/** Despacha por pathname entre los niveles del recorrido de evidencia.
 *  Entrada, Paso, Respaldo y Resultado (nivel de resultado, con su agregado y
 *  su desglose — ver `evidencia/Resultado.tsx`) tienen pantalla propia y hacen
 *  su propia consulta. El nivel de corrida (`/evidencia/run`) se queda acá:
 *  es el único que todavía no justifica un archivo propio. */
export default function EvidencePage() {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const plane = params.get('plane') ?? ''
  const runId = params.get('run_id') ?? ''
  const level = pathname === '/evidencia/run' ? 'run'
    : pathname === '/evidencia/resultado' ? 'result'
    : pathname === '/evidencia/paso' ? 'paso'
    : pathname === '/evidencia/respaldo' ? 'respaldo'
    : 'entrada'
  const run = useQuery({
    queryKey: ['evidencia', 'run', plane, runId],
    queryFn: () => getArchivedRun(plane, runId), enabled: level === 'run',
  })
  if (level === 'entrada') return <Entrada />
  if (level === 'paso') return <Paso />
  if (level === 'respaldo') return <Respaldo />
  if (level === 'result') return <Resultado />

  if (run.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (run.error) return <ErrorBanner>No se pudo leer esta evidencia. Comprobá la referencia y la copia local del archivo.</ErrorBanner>
  if (run.data?.available === false) return <>
    <PageHeader title="Evidencia" />
    <EmptyState hint={run.data.message}>Archivo de evidencia no disponible</EmptyState>
  </>

  if (run.data?.run) {
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
