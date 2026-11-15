import { Link } from 'react-router-dom'
import { useGen2Pruebas, usePreguntas } from '../api/queries/gen2'
import { Card, PageHeader } from '../components/ui'
import NombreCodigo, { ConCodigos } from '../components/ui/NombreCodigo'
import { PREGUNTA_PATH } from '../nav'
import type { Gen2Prueba } from '../types'
import { NOMBRE_DE_PRUEBA } from '../vocabulario'
import { EstadoDeLectura } from './evidencia/comun'
import { EstadoPrueba, noSeRegenera, valorTexto } from './gen2/comun'
import './gen2/Gen2.css'

/** Cuántas cifras del resumen se muestran en la tarjeta; el resto, en el detalle. */
const CIFRAS_EN_TARJETA = 3

function TarjetaPrueba({ p }: { p: Gen2Prueba }) {
  const cifras = p.resumen.slice(0, CIFRAS_EN_TARJETA)
  return (
    <article className="eo-gen2__prueba" aria-labelledby={`prueba-${p.id}`}>
      <h3 id={`prueba-${p.id}`}>
        <Link to={`/resultados/${encodeURIComponent(p.id)}`}>
          <NombreCodigo codigo={p.id} nombre={NOMBRE_DE_PRUEBA[p.id] ?? p.titulo ?? undefined} />
        </Link>
      </h3>
      {p.que_midio && <p className="eo-note">{p.que_midio}</p>}
      {p.estado !== 'completo' && (
        <div className="eo-gen2__estado"><EstadoPrueba estado={p.estado} registro={p.registro} /></div>
      )}
      {cifras.length > 0 && !noSeRegenera(p) && (
        <dl className="eo-gen2__cifras">
          {cifras.map((c) => (
            <div key={c.clave}>
              <dt><ConCodigos texto={c.nombre_consola ?? c.nombre} /></dt>
              <dd><b>{valorTexto(c.valor, c.unidad)}</b></dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  )
}

/** «Pruebas» (plan de la consola, §3): el catálogo de la campaña agrupado por las siete preguntas, en
 *  su orden. Solo cifras finales: lo escrito antes de correr, los veredictos y la comparación con la
 *  etapa anterior están en el detalle de cada prueba, en «Cómo se validó». */
export default function ResultadosPage() {
  const q = useGen2Pruebas()
  const qp = usePreguntas()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Pruebas" q={q} />
  const pruebas = q.data
  const preguntas = qp.data?.preguntas ?? []
  const completas = pruebas.filter((p) => p.estado === 'completo').length
  const sinPregunta = pruebas.filter((p) => !preguntas.some((pr) => pr.id === p.pregunta_consola))
  return (
    <div className="eo-gen2">
      <PageHeader title="Pruebas" meta={`${completas} de ${pruebas.length} pruebas completas`} />
      {preguntas.map((pr, i) => {
        const delGrupo = pruebas.filter((p) => p.pregunta_consola === pr.id)
        if (delGrupo.length === 0) return null
        return (
          <Card
            key={pr.id}
            title={`${i + 1}. ${pr.titulo}`}
            meta={<Link to={`${PREGUNTA_PATH}/${encodeURIComponent(pr.id)}`}>Ver la pregunta</Link>}
          >
            <div className="eo-gen2__grid">
              {delGrupo.map((p) => <TarjetaPrueba key={p.id} p={p} />)}
            </div>
          </Card>
        )
      })}
      {sinPregunta.length > 0 && (
        <Card title={qp.isPending ? 'Las pruebas' : 'Sin pregunta asignada'}>
          <div className="eo-gen2__grid">
            {sinPregunta.map((p) => <TarjetaPrueba key={p.id} p={p} />)}
          </div>
        </Card>
      )}
    </div>
  )
}
