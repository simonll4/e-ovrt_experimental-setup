import { Link } from 'react-router-dom'
import { useGen2Observaciones } from '../api/queries/gen2'
import { Card, EmptyState, PageHeader, Tag } from '../components/ui'
import { GEN1 } from '../nav'
import { EstadoDeLectura } from './evidencia/comun'
import { EstadoPrueba, Veredicto } from './gen2/comun'
import './gen2/Gen2.css'

/** Destinos que no son pruebas pero responden a una observación. */
const EXTRAS: Record<number, Array<{ to: string; texto: string }>> = {
  1: [{ to: '/demo', texto: 'La demo en vivo' }],
  2: [{ to: '/platform', texto: 'Plataforma: cómo se desplegó' }],
}

/** La entrada de la consola (doc 135 §3.2): las observaciones del tribunal, en
 *  su orden, cada una con qué pidió, qué hicimos y dónde verlo. Lee
 *  el archivo de observaciones del repo privado `docs` (no viaja en este repo, que es
 *  público): no depende de ningún servicio. */
export default function TribunalPage() {
  const q = useGen2Observaciones()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Para el tribunal" q={q} />
  const datos = q.data
  return (
    <div className="eo-gen2">
      <PageHeader
        title="Para el tribunal"
        meta="Las observaciones al informe y dónde ver la respuesta a cada una"
      />
      <p className="eo-note">
        Los resultados finales del informe son los de la <b>generación 2</b>: corridos en la PC de la
        demo, con toda la plataforma en contenedores, a partir de pruebas registradas antes de correr.
        Lo medido antes en otra máquina es la <Link to={GEN1.to}>validación inicial (generación 1)</Link>.
        Todas las pruebas están en <Link to="/resultados">Resultados</Link>.
      </p>
      {!datos.available ? (
        <EmptyState hint={datos.message ?? undefined}>Todavía no hay observaciones registradas</EmptyState>
      ) : (
        <ol className="eo-gen2__obs" aria-label="Observaciones del tribunal">
          {datos.observaciones.map((o) => (
            <li key={o.numero}>
              <Card title={`${o.numero}. ${o.titulo}`}>
                <dl className="eo-gen2__qa">
                  <div>
                    <dt>Qué pidió el tribunal</dt>
                    <dd>{o.pedido}</dd>
                  </div>
                  <div>
                    <dt>Qué hicimos</dt>
                    <dd>{o.respuesta}</dd>
                  </div>
                  <div>
                    <dt>Dónde verlo</dt>
                    <dd>
                      {o.pruebas.length === 0 && !EXTRAS[o.numero] && (
                        <span className="eo-note--meta">Se responde en el texto del informe.</span>
                      )}
                      {(o.pruebas.length > 0 || EXTRAS[o.numero]) && (
                        <ul className="eo-gen2__links">
                          {o.pruebas.map((p) => (
                            <li key={p.id}>
                              <Link to={`/resultados/${encodeURIComponent(p.id)}`}>
                                {p.id} — {p.titulo ?? 'prueba sin pre-registro'}
                              </Link>
                              <EstadoPrueba estado={p.estado} registro={p.registro} />
                              <Veredicto v={p.veredicto} />
                            </li>
                          ))}
                          {(EXTRAS[o.numero] ?? []).map((e) => (
                            <li key={e.to}><Link to={e.to}>{e.texto}</Link></li>
                          ))}
                        </ul>
                      )}
                      {o.secciones.length > 0 && (
                        <p className="eo-gen2__secciones">
                          En el informe: {o.secciones.map((s) => <Tag key={s}>{s}</Tag>)}
                        </p>
                      )}
                    </dd>
                  </div>
                </dl>
              </Card>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
