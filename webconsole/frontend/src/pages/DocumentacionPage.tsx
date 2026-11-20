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

/** Los dos niveles de evaluación, con el nombre que usa el informe (decisión del 2026-11-19: ya no
 *  «Nivel A/B»). El YAML sigue guardando A y B como clave. */
const NIVEL: Record<string, string> = {
  A: 'Estado por persona',
  B: 'Alerta por episodio',
  'A y B': 'Estado por persona y alerta por episodio',
}

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
      <PageHeader title="Cómo leer" meta="Lectura del disco" />
      <LoadingState lines={6}>Leyendo la documentación…</LoadingState>
    </>
  }
  if (q.error) {
    return <>
      <PageHeader title="Cómo leer" />
      <ErrorBanner detail={String(q.error)} onRetry={() => void q.refetch()} retrying={q.isFetching}>
        No se pudo leer la documentación.
      </ErrorBanner>
    </>
  }
  if (!q.data.available) return <>
    <PageHeader title="Cómo leer" />
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
        <li><a href="#/documentacion#guia" onClick={saltar('guia')}>Cómo se lee esta consola</a></li>
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

  // «Cómo leer» corto (revisión del 2026-11-19): la consola muestra la evidencia y el sistema funcionando; cómo se
  // trabajó, las equivalencias con el código, qué aporta cada cosa y los símbolos con más de un sentido son
  // documentación y viven en el repositorio público (generados desde el mismo documentacion.yaml). Acá queda cómo se
  // lee la consola y el vocabulario, que es a donde apuntan los términos marcados de las otras pantallas.
  return <div className="eo-doc">
    <PageHeader title="Cómo leer" meta={`${Object.keys(doc.terminos).length} términos definidos · lectura del disco`} />

    <div className="eo-doc__layout">
      {indice}
      <div className="eo-doc__main">
        <h2 className="eo-doc__h2" id="guia">Cómo se lee esta consola</h2>
        <ul className="eo-doc__guia">
          <li><b>Las siete preguntas</b> del <Link to="/">Inicio</Link> son las del informe. Cada una tiene su respuesta
            en una oración, la tabla del informe que la sostiene y las pruebas que la respaldan.</li>
          <li><b>Cada prueba</b> se escribió antes de correr y dice qué midió, su resultado y, en el banco temporal, clip
            por clip. <b>Cada clip abre su run</b>: la referencia, las alertas, el cuadro de cada una con las cajas que
            vio el sistema y el video.</li>
          <li><b>Las tomas en vivo</b> son las sesiones con cámara de las jornadas, agrupadas por la prueba en la que
            cuentan. Cada una abre su resultado: video, alertas y el mensaje que llegó al broker.</li>
          <li><b>La concordancia</b> compara cada prueba con la referencia de su pre-registro: <i>idéntico</i> (valor por
            valor), <i>equivalente con diferencia</i> (con la diferencia declarada) u <i>otra combinación</i> (se
            muestra al lado, nunca en reemplazo). <i>Parcial</i> quiere decir que no tiene todo lo que pedía su
            pre-registro, y dice por qué.</li>
          <li><b>Por escena</b> juzga la condición sobre el cuadro entero; <b>por sujeto</b>, persona por persona.</li>
          <li>Los términos subrayados muestran su definición al pasar el mouse y abren su entrada abajo.</li>
          <li>Cómo se trabajó, las equivalencias con el código y los símbolos con más de un sentido están en la
            documentación pública, en el repositorio <span className="eo-mono">e-ovrt-vdp</span>{' '}
            (<span className="eo-mono">evidencia/consola/como-leer.md</span>).</li>
        </ul>

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
                      {t.nivel && <span className="eo-doc__nivel">{NIVEL[t.nivel] ?? t.nivel}</span>}
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
