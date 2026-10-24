import { useEffect, useState, type MouseEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useLocation } from 'react-router-dom'
import { getDocumentacion, qk } from '../api'
import {
  Card, Disclosure, EmptyState, ErrorBanner, LoadingState, PageHeader, Table, TableScroll,
} from '../components/ui'
import { IconChevron } from '../components/ui/icons'
import Termino from '../components/Glosario'
import './DocumentacionPage.css'

/** Desplaza hasta un elemento por id y le da el foco, sin dejarlo en el orden
 *  de tabulación. */
function irA(id: string) {
  const el = document.getElementById(id)
  if (!el) return false
  if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1')
  el.scrollIntoView?.({ block: 'start' })
  el.focus({ preventScroll: true })
  return true
}

/** La primera pantalla que conviene leer: qué se hizo, por qué, y qué significa
 *  cada nombre que aparece en el resto de la consola.
 *
 *  Se lee del disco (`results/evidence-vista/documentacion.yaml`, servido por
 *  `/api/documentacion`) y **no consulta ningún servicio**: funciona con los
 *  tres planos apagados, igual que `/evidencia`.
 *
 *  Tres bloques, con el método como espina: cómo se trabajó, qué aporta cada
 *  cosa, y el vocabulario agrupado por familia — cada familia plegable con su
 *  cantidad, y un índice para llegar sin recorrer la página entera. Un enlace
 *  directo a un término (`/documentacion#T1`) abre su familia y lo enfoca. */
export default function DocumentacionPage() {
  const q = useQuery({ queryKey: qk.documentacion, queryFn: getDocumentacion, staleTime: Infinity })
  const { hash } = useLocation()
  const [abiertas, setAbiertas] = useState<Set<string>>(new Set())

  const destino = hash ? decodeURIComponent(hash.slice(1)) : ''

  // El término pedido por el enlace: se abre su familia y, ya dibujada, se lo
  // enfoca. Lo mismo para un ancla de sección o de paso.
  useEffect(() => {
    if (!destino || !q.data?.available) return
    const familia = q.data.vocabulario.find((f) => f.terminos.some((t) => t.id === destino))
    if (familia) setAbiertas((prev) => (prev.has(familia.id) ? prev : new Set([...prev, familia.id])))
    const id = window.setTimeout(() => irA(destino), 0)
    return () => window.clearTimeout(id)
  }, [destino, q.data])

  if (q.isPending) {
    return <>
      <PageHeader title="Documentación" meta="Lectura del disco" />
      <LoadingState lines={6}>Leyendo la documentación…</LoadingState>
    </>
  }
  if (q.error) {
    return <>
      <PageHeader title="Documentación" />
      <ErrorBanner detail={String(q.error)} onRetry={() => void q.refetch()} retrying={q.isFetching}>
        No se pudo leer la documentación.
      </ErrorBanner>
    </>
  }
  if (!q.data.available) return <>
    <PageHeader title="Documentación" />
    <EmptyState hint={q.data.message ?? undefined}>Documentación no disponible</EmptyState>
  </>
  const doc = q.data

  const alternar = (id: string, abierta: boolean) =>
    setAbiertas((prev) => {
      const next = new Set(prev)
      if (abierta) next.add(id)
      else next.delete(id)
      return next
    })

  const saltar = (id: string, familia?: string) => (e: MouseEvent) => {
    // HashRouter usa el fragmento para la ruta: se desplaza a mano.
    e.preventDefault()
    if (familia) alternar(familia, true)
    window.setTimeout(() => irA(id), 0)
  }

  const indice = (
    <nav className="eo-doc__index" aria-label="Índice de la documentación">
      <p className="eo-doc__index-t">En esta página</p>
      <ol>
        <li><a href="#/documentacion#metodo" onClick={saltar('metodo')}>Cómo se trabajó</a></li>
        <li><a href="#/documentacion#aportes" onClick={saltar('aportes')}>Qué aporta cada cosa</a></li>
        <li><a href="#/documentacion#colisiones" onClick={saltar('colisiones')}>Símbolos con más de un sentido</a></li>
        <li>
          <a href="#/documentacion#vocabulario" onClick={saltar('vocabulario')}>Vocabulario</a>
          <ol>
            {doc.vocabulario.map((f) => (
              <li key={f.id}>
                <a href={`#/documentacion#familia-${f.id}`} onClick={saltar(`familia-${f.id}`, f.id)}>
                  {f.titulo} <span className="eo-doc__count">{f.terminos.length}</span>
                </a>
              </li>
            ))}
          </ol>
        </li>
      </ol>
    </nav>
  )

  return <div className="eo-doc">
    <PageHeader
      title={doc.titulo ?? 'Documentación'}
      meta={`${doc.metodo.length} pasos · ${Object.keys(doc.terminos).length} términos definidos · lectura del disco`}
    />
    {doc.bajada && <p className="eo-note">{doc.bajada}</p>}

    <div className="eo-doc__layout">
      {indice}
      <div className="eo-doc__main">
        <h2 className="eo-doc__h2" id="metodo">Cómo se trabajó</h2>
        <p className="eo-doc__intro">Cinco pasos, en el orden en que se dieron. Cada uno dice
          qué se hizo, <b>por qué</b>, y qué quedó.</p>
        <ol className="eo-doc__pasos">
          {doc.metodo.map((paso) => (
            <li key={paso.n} className="eo-doc__paso" id={`paso-${paso.n}`}>
              <div className="eo-doc__n" aria-hidden="true">{paso.n}</div>
              <div className="eo-doc__cuerpo">
                <h3 className="eo-doc__t">{paso.titulo}</h3>
                <dl className="eo-doc__qpq">
                  <dt>Qué se hizo</dt><dd>{paso.hizo}</dd>
                  <dt>Por qué</dt><dd>{paso.porque}</dd>
                  <dt>Qué quedó</dt><dd>{paso.quedo}</dd>
                </dl>
                {paso.terminos.length > 0 && <p className="eo-doc__chips">
                  {paso.terminos.map((id) => <Termino key={id} id={id} />)}
                </p>}
                {/* El enlace a la evidencia sólo se dibuja si el YAML lo declara:
                    un paso sin evidencia asociada no inventa un link. */}
                {paso.evidencia_href && (
                  <p className="eo-doc__ev">
                    <Link to={paso.evidencia_href}>{paso.evidencia_label ?? 'Ver la evidencia'}</Link>
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>

        <h2 className="eo-doc__h2" id="aportes">Qué aporta cada cosa</h2>
        <p className="eo-doc__intro">Corrida, experimento, campaña, evidencia y resultado se usan
          casi como sinónimos y no lo son. Cada uno suma algo que los otros no.</p>
        <Card flush>
          <TableScroll label="Qué aporta cada cosa">
            <Table aria-label="Qué aporta cada cosa">
              <thead><tr>
                <th>Qué es</th><th>De qué habla</th><th>Qué suma</th><th>Dónde se ve</th>
              </tr></thead>
              <tbody>
                {doc.aportes.map((fila) => (
                  <tr key={fila.id} id={`aporte-${fila.id}`}>
                    <td>
                      <div className="eo-rowname">
                        <b>{fila.termino}</b>
                        {/* El identificador sólo si la fila lo tiene: «campaña» y
                            «evidencia» no son un campo de ningún contrato. */}
                        {fila.identificador
                          ? <span className="eo-mono">{fila.identificador}</span>
                          : <span className="eo-na">sin identificador propio</span>}
                      </div>
                    </td>
                    <td className="eo-cell--wrap">{fila.que_es}</td>
                    <td className="eo-cell--wrap">{fila.que_suma}</td>
                    <td>
                      {fila.href
                        ? <Link to={fila.href}>{fila.donde}</Link>
                        : <span className="eo-na">—</span>}
                      {/* El conteo lo calcula el servidor contra el registro. */}
                      {fila.conteo != null && <span className="eo-doc__n2">{fila.conteo} hoy</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>

        {/* El conteo sale de los datos, no se escribe a mano. */}
        <h2 className="eo-doc__h2" id="colisiones">Símbolos que significan más de una cosa</h2>
        <p className="eo-doc__intro">Son {doc.colisiones.length}. Es lo que más confusión ahorra:
          un lector que no estuvo los pisa sí o sí si no se los avisan.</p>
        <div className="eo-doc__cols">
          {doc.colisiones.map((c) => (
            <Card key={c.simbolo} level={3} title={<span className="eo-mono">{c.simbolo}</span>}>
              <ul className="eo-doc__sentidos">
                {c.sentidos.map((s) => (
                  <li key={s.de}><span className="eo-mono">{s.de}</span> {s.es}</li>
                ))}
              </ul>
              <p className="eo-doc__aqui">{c.en_la_consola}</p>
            </Card>
          ))}
        </div>

        <h2 className="eo-doc__h2" id="vocabulario">Vocabulario</h2>
        <p className="eo-doc__intro">Agrupado por familia; cada una se abre con su cantidad de
          términos. Los términos marcados en el resto de la consola apuntan acá y abren su
          familia.</p>
        {doc.vocabulario.map((familia) => (
          <details
            key={familia.id}
            id={`familia-${familia.id}`}
            className="eo-adv eo-doc__fam"
            open={abiertas.has(familia.id)}
            onToggle={(e) => alternar(familia.id, (e.currentTarget as HTMLDetailsElement).open)}
          >
            <summary>
              <span className="eo-adv__chev" aria-hidden="true"><IconChevron /></span>
              <h3 className="eo-doc__famt">{familia.titulo}</h3>
              <span className="eo-doc__count">{familia.terminos.length} términos</span>
            </summary>
            <div className="eo-doc__fambody">
              {familia.nota && <p className="eo-doc__nota">{familia.nota}</p>}
              <dl className="eo-doc__voc">
                {familia.terminos.map((t) => (
                  <div key={t.id} className="eo-doc__voci" id={t.id}>
                    <dt className={t.mono ? 'eo-mono' : undefined}>
                      {t.termino}
                      {t.nivel && <span className="eo-doc__nivel">Nivel {t.nivel}</span>}
                    </dt>
                    <dd>
                      {t.definicion}
                      {/* Los result_id que sostienen el término, enlazados a su
                          evidencia. Un término sin result_id no dibuja nada. */}
                      {t.result_ids.length > 0 && <span className="eo-doc__rids">
                        {t.result_ids.map((rid) => (
                          <Link key={rid} className="eo-mono"
                            to={`/evidencia/resultado?${new URLSearchParams({ id: rid })}`}>{rid}</Link>
                        ))}
                      </span>}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </details>
        ))}

        <Disclosure summary="Cómo se edita este texto" className="eo-doc__edit">
          <p className="eo-cap">Vive en <b>results/evidence-vista/documentacion.yaml</b> y se
            edita sin tocar código. Nada de esta pantalla consulta a los servicios.</p>
        </Disclosure>
      </div>
    </div>
  </div>
}
