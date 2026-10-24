import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getArchivedRun, getEvidenceRecorrido } from '../api'
import { Badge, Card, Disclosure, EmptyState, PageHeader, Table, TableScroll } from '../components/ui'
import Entrada from './evidencia/Entrada'
import Paso, { TablaResultados } from './evidencia/Paso'
import Resultado from './evidencia/Resultado'
import { ArchivoAusente, EstadoDeLectura, Evidencia, Rol } from './evidencia/comun'
import './EvidencePage.css'

/** El enlace a un resultado conserva el paso de origen si la navegación lo
 *  trajo; nunca inventa uno. */
const resultUrl = (id: string, paso: string | null) =>
  `/evidencia/resultado?${new URLSearchParams(paso ? { id, paso } : { id })}`

/** El respaldo instrumental reusa la tabla de un paso, pero se sirve inline:
 *  no tiene ruta propia en la API (su desglose viaja en la respuesta de
 *  `/api/evidencia`, dentro de `respaldo.resultados`). */
function Respaldo() {
  const q = useQuery({ queryKey: ['evidencia', 'recorrido'], queryFn: getEvidenceRecorrido })
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Respaldo instrumental" q={q} />
  if (q.data.available === false) return <ArchivoAusente message={q.data.message} />
  const respaldo = q.data.respaldo
  if (!respaldo) {
    return <Evidencia>
      <PageHeader title="Respaldo instrumental" />
      <EmptyState>No hay respaldo instrumental registrado.</EmptyState>
    </Evidencia>
  }
  return <Evidencia>
    <PageHeader title={respaldo.titulo} meta={`${respaldo.resultados.length} resultados`} />
    <p className="eo-note">{respaldo.claim}</p>
    <Card title="Las mediciones de respaldo" flush>
      <TablaResultados resultados={respaldo.resultados} caption="Mediciones de respaldo instrumental" />
    </Card>
  </Evidencia>
}

/** Valor de un campo del summary congelado, legible. */
const valor = (v: unknown) => (v === null || v === undefined ? '—' : String(v))

/** Despacha por pathname entre los niveles del recorrido de evidencia.
 *  Entrada, Paso, Respaldo y Resultado tienen pantalla propia y hacen su
 *  propia consulta. El nivel de corrida (`/evidencia/run`) se queda acá. */
export default function EvidencePage() {
  const { pathname } = useLocation()
  const [params] = useSearchParams()
  const plane = params.get('plane') ?? ''
  const runId = params.get('run_id') ?? ''
  const paso = params.get('paso')
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

  if (run.isPending || run.error) return <EstadoDeLectura titulo={runId || 'Corrida de evidencia'} q={run} />
  if (run.data?.available === false) return <ArchivoAusente message={run.data.message} />

  if (run.data?.run) {
    const data = run.data
    const info = run.data.run
    // Los campos principales del summary, legibles; el objeto entero (con lo
    // anidado) queda bajo «Datos originales», sin recortar.
    const values = Object.entries(data.summary ?? {}).filter(([, value]) => value === null || typeof value !== 'object')
    return <Evidencia>
      <PageHeader
        title="Corrida de evidencia"
        meta={<>
          <span className="eo-mono">{info.run_id}</span>
          <span className="eo-sep">·</span>
          <span>{info.plane === 'media-plane' ? 'Medios' : 'Control'}</span>
          <Badge tone="neutral">{info.status === 'archived_only' ? 'Sólo archivo' : 'Copia curada'}</Badge>
        </>}
      />
      {info.reason && <p className="eo-note">{info.reason}</p>}
      {!info.tiene_detalle_vivo && <p className="eo-note">La evidencia se conserva en el archivo; no hay un detalle vivo disponible.</p>}
      {info.tiene_detalle_vivo && info.plane === 'media-plane' && <p className="eo-note"><Link to={`/runs/${encodeURIComponent(info.run_id)}`}>Abrir detalle vivo</Link> · requiere el servicio de medios.</p>}
      {info.tiene_detalle_vivo && info.plane === 'control-plane' && <p className="eo-note">El directorio original de control está disponible. Esta consola no tiene una vista viva de control.</p>}
      <Card title="Procedencia">
        <dl className="eo-deflist">
          <div>
            <dt>Fuente</dt>
            <dd className="eo-mono">{info.source_ref}</dd>
          </div>
          <div>
            <dt>Rol</dt>
            <dd><Rol role={info.role} /></dd>
          </div>
        </dl>
        {data.relations && data.relations.length > 0 && (
          <>
            <h3 className="eo-editor__section">Resultados que la citan</h3>
            <ul className="eo-mini__list">
              {data.relations.map((relation) => <li key={`${relation.result_id}/${relation.role}/${relation.source_ref}`}>
                <span><Link to={resultUrl(relation.result_id, paso)}>{relation.result_id}</Link></span>
                <span><Rol role={relation.role} /></span>
              </li>)}
            </ul>
          </>
        )}
      </Card>
      {data.notice && <p className="eo-note">{data.notice}</p>}
      {data.summary && <Card title="Summary congelado" flush>
        {data.summary_source && <p className="eo-note eo-cardnote">Conservado en <span className="eo-mono">{data.summary_source}</span></p>}
        <TableScroll label="Summary congelado">
          <Table aria-label="Summary congelado"><thead><tr><th>Campo</th><th>Valor</th></tr></thead>
            <tbody>{values.map(([key, value]) => <tr key={key}><td className="eo-mono">{key}</td><td>{valor(value)}</td></tr>)}</tbody>
          </Table>
        </TableScroll>
        <Disclosure className="eo-adv--inset" summary="Datos originales (JSON completo)">
          <pre className="eo-pre eo-cap--inset">{JSON.stringify(data.summary, null, 2)}</pre>
        </Disclosure>
      </Card>}
      {data.substitutes.map((artifact) => <Card key={artifact.name} title={artifact.name}>
        <p className="eo-note">Artefacto sustituto preservado: reemplaza al summary individual que no se conservó.</p>
        <Disclosure summary="Datos originales (JSON completo)" open={!data.summary}>
          <pre className="eo-pre">{JSON.stringify(artifact.data, null, 2)}</pre>
        </Disclosure>
      </Card>)}
    </Evidencia>
  }
  return <Evidencia>
    <PageHeader title={runId || 'Corrida de evidencia'} />
    <EmptyState>No se encontró evidencia para esta referencia.</EmptyState>
  </Evidencia>
}
