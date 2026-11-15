import { Link, useParams } from 'react-router-dom'
import { usePreguntas } from '../api/queries/gen2'
import { Card, EmptyState, PageHeader, Table, TableScroll, Tag } from '../components/ui'
import { PREGUNTA_PATH } from '../nav'
import type { TablaPregunta } from '../types'
import { nombreConCodigo } from '../vocabulario'
import { EstadoDeLectura } from './evidencia/comun'
import { CeldaCifras, Plantilla } from './preguntas/comun'
import './preguntas/Preguntas.css'

function TablaDelInforme({ t }: { t: TablaPregunta }) {
  return (
    <Card title={t.titulo} meta={t.informe ?? undefined} flush>
      <TableScroll label={t.titulo}>
        <Table aria-label={t.titulo}>
          <thead>
            <tr>
              <th><span className="eo-sr">Fila del informe</span></th>
              {t.columnas.map((c) => <th key={c} className="eo-num">{c}</th>)}
              <th>Respaldo</th>
            </tr>
          </thead>
          <tbody>
            {t.filas.map((f) => (
              <tr key={f.nombre}>
                <th scope="row" className="eo-pregunta__fila">{f.nombre}</th>
                {f.celdas.map((c, i) => <td key={i} className="eo-num"><CeldaCifras items={c} /></td>)}
                <td className="eo-pregunta__respaldo">
                  {f.pruebas.map((pid, i) => (
                    <span key={pid}>
                      {i > 0 && ' · '}
                      <Link to={`/resultados/${encodeURIComponent(pid)}`} aria-label={`Ver respaldo: ${nombreConCodigo(pid)}`}
                        title={nombreConCodigo(pid)}>
                        {pid}
                      </Link>
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
      {t.nota && <p className="eo-note eo-pregunta__nota">{t.nota}</p>}
    </Card>
  )
}

/** La página de una pregunta (plan de la consola de evidencia, §2.3): la respuesta en una oración, la
 *  tabla del informe con cada fila enlazada a su prueba y lo que la cifra no dice. Solo cifras
 *  finales, sin la etapa anterior ni veredictos. Las figuras («Cómo se ve») llegan en la etapa 4. */
export default function PreguntaPage() {
  const { id = '' } = useParams()
  const q = usePreguntas()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Pregunta" q={q} />
  const preguntas = q.data.preguntas ?? []
  const i = preguntas.findIndex((p) => p.id === id)
  if (i < 0) {
    return (
      <>
        <PageHeader title="Esa pregunta no existe" />
        <Card><EmptyState hint={<>Las siete están en el <Link to="/">inicio</Link>.</>}>No hay una pregunta «{id}».</EmptyState></Card>
      </>
    )
  }
  const pr = preguntas[i]
  const anterior = preguntas[i - 1]
  const siguiente = preguntas[i + 1]
  return (
    <div className="eo-pregunta">
      <PageHeader title={pr.titulo} meta={pr.informe.map((s) => <Tag key={s}>{s}</Tag>)} />
      <p className="eo-pregunta__respuesta"><Plantilla texto={pr.respuesta} cifras={pr.cifras} /></p>
      {pr.tablas.map((t) => <TablaDelInforme key={t.titulo} t={t} />)}
      {pr.limites.length > 0 && (
        <Card title="Qué no dice esta cifra">
          <ul className="eo-pregunta__limites">
            {pr.limites.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </Card>
      )}
      <nav className="eo-pregunta__pasos" aria-label="Otras preguntas">
        {anterior
          ? <Link to={`${PREGUNTA_PATH}/${encodeURIComponent(anterior.id)}`} rel="prev">← {anterior.titulo}</Link>
          : <Link to="/">← Inicio</Link>}
        {siguiente
          ? <Link to={`${PREGUNTA_PATH}/${encodeURIComponent(siguiente.id)}`} rel="next">{siguiente.titulo} →</Link>
          : <Link to="/">Inicio →</Link>}
      </nav>
    </div>
  )
}
