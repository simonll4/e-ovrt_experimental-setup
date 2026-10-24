import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getEvidenceRecorrido } from '../../api'
import { EmptyState, PageHeader } from '../../components/ui'
import { ArchivoAusente, Cifra, EstadoDeLectura, Evidencia } from './comun'

/** La entrada de `/evidencia`: los cuatro números del argumento del informe,
 *  no un índice de carpetas. Cada paso abre en `/evidencia/paso?n=`; el
 *  respaldo instrumental abre en `/evidencia/respaldo` (misma tabla que un
 *  paso, servida inline desde `EvidencePage`: no tiene ruta propia en la API).
 *  «Por material» es deliberadamente informativa, no un link: la API sólo
 *  expone el conteo por índice, no los resultados de cada uno, así que no hay
 *  a dónde navegar — mejor una tarjeta honesta que un link muerto. */
export default function Entrada() {
  const q = useQuery({ queryKey: ['evidencia', 'recorrido'], queryFn: getEvidenceRecorrido })
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Evidencia" q={q} />
  if (q.data.available === false) return <ArchivoAusente message={q.data.message} />
  // Los DOS sumandos del mismo conjunto, nombrados: el recorrido son 30 y el
  // respaldo instrumental 5. El 35 es el número canónico del proyecto, así que
  // se dice entero y se muestra de qué se compone.
  const enRecorrido = q.data.pasos.reduce((n, p) => n + p.n_resultados, 0)
  const enRespaldo = q.data.respaldo?.n_resultados ?? null
  const meta = enRespaldo == null
    ? `${enRecorrido} resultados en el recorrido · lectura del archivo curado`
    : `${enRecorrido + enRespaldo} resultados reportados — ${enRecorrido} en el recorrido `
      + `y ${enRespaldo} de respaldo instrumental · lectura del archivo curado`
  return <Evidencia>
    <PageHeader title="Evidencia" meta={meta} />
    <p className="eo-note">El recorrido del argumento del informe. Cada número abre los
      resultados que lo sostienen; cada resultado, su desglose y las corridas que lo respaldan.</p>
    <div className="eo-evsteps">
      {q.data.pasos.map((paso) => (
        // La tarjeta entera abre el paso (el enlace del título se estira con
        // CSS), pero la fuente de una cifra citada sigue siendo su propio
        // control: no hay un botón adentro de un enlace.
        <article key={paso.n} className="eo-evstep">
          <div className="eo-evstep__n" aria-hidden="true">{paso.n}</div>
          <div className="eo-evstep__body">
            <h2 className="eo-evstep__t">
              <Link className="eo-evstep__link" to={`/evidencia/paso?n=${paso.n}`}>{paso.titulo}</Link>
            </h2>
            <p className="eo-evstep__c">{paso.claim}</p>
            {/* Cada índice con su barra: `join(' + ') + '/'` dejaba
                «clip_bench + realtime/», como si sólo el último fuera una carpeta. */}
            <div className="eo-evstep__m">{paso.n_resultados} resultados · {paso.indices.map((i) => `${i}/`).join(' + ')}</div>
          </div>
          <div className="eo-fig">
            <div className="eo-fig__l">{paso.cifra_label}</div>
            <div className="eo-fig__v">
              <Cifra valor={paso.cifra ?? '—'} origen={paso.cifra_origen} fuente={paso.fuente} />
            </div>
            <div className="eo-fig__u">{paso.cifra_nota}</div>
          </div>
        </article>
      ))}
      {q.data.pasos.length === 0 && <EmptyState>No hay pasos registrados en el recorrido.</EmptyState>}
    </div>

    <div className="eo-side3">
      <Link className="eo-mini" to="/evidencia/respaldo">
        <div className="eo-mini__h">{q.data.respaldo?.titulo}</div>
        <p className="eo-mini__d">{q.data.respaldo?.claim}</p>
        <div className="eo-mini__n">{q.data.respaldo?.n_resultados} mediciones</div>
      </Link>
      {/* Informativa, no navegable: ver nota de arriba. */}
      <div className="eo-mini eo-mini--static">
        <div className="eo-mini__h">Por material</div>
        <p className="eo-mini__d">La organización canónica de <b>results/</b>, que es la
          fuente de las cifras: imágenes, Nivel A por sujeto, banco de clips y tiempo real.</p>
        <ul className="eo-mini__list">
          {q.data.indices.map((idx) => (
            <li key={idx.id}>
              <span className="eo-mono">{idx.id}</span>
              <span className="eo-num eo-mono">{idx.n_results}</span>
            </li>
          ))}
        </ul>
      </div>
      {/* Los tres ejes se nombran, no se enlazan: son archivos del repositorio
          y esta pantalla funciona sin red ni servicios. */}
      <div className="eo-mini eo-mini--static">
        <div className="eo-mini__h">Ejes de lectura</div>
        <p className="eo-mini__d">La misma evidencia cortada por otros ejes, sin agregar
          mediciones: offline contra vivo, el día de rodaje, y zero-shot contra la jornada de ajuste.</p>
        <div className="eo-mini__n">3 vistas · <span className="eo-mono">results/ejes/</span> del repositorio</div>
      </div>
    </div>

    <p className="eo-cap">Las cifras se leen del <b>metrics.json</b> de cada campaña al
      abrirla; las que no tienen artefacto en este repositorio se muestran citadas, con la
      fuente a un toque. Nada de esto consulta a los servicios.</p>
  </Evidencia>
}
