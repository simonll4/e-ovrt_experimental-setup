import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getEvidenceRecorrido } from '../../api'
import { EmptyState, ErrorBanner, PageHeader } from '../../components/ui'

/** La entrada de `/evidencia`: los cuatro números del argumento del informe,
 *  no un índice de carpetas. Cada paso abre en `/evidencia/paso?n=`; el
 *  respaldo instrumental abre en `/evidencia/respaldo` (misma tabla que un
 *  paso, servida inline desde `EvidencePage`: no tiene ruta propia en la API).
 *  «Por material» es deliberadamente informativa, no un link: la API sólo
 *  expone el conteo por índice, no los resultados de cada uno, así que no hay
 *  a dónde navegar — mejor una tarjeta honesta que un link muerto. */
export default function Entrada() {
  const q = useQuery({ queryKey: ['evidencia', 'recorrido'], queryFn: getEvidenceRecorrido })
  if (q.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (q.error) return <ErrorBanner>No se pudo leer el archivo de evidencia.</ErrorBanner>
  if (q.data.available === false) return <>
    <PageHeader title="Evidencia" />
    <EmptyState hint={q.data.message}>Archivo de evidencia no disponible</EmptyState>
  </>
  // Los DOS sumandos del mismo conjunto, nombrados: el recorrido son 30 y el
  // respaldo instrumental 5. Antes la cabecera decía «30 resultados
  // reportados» mientras la tarjeta de al lado listaba 35 por material — dos
  // totales del mismo conjunto, uno al lado del otro, sin explicación. El 35
  // es el número canónico del proyecto, así que se dice entero y se muestra de
  // qué se compone.
  const enRecorrido = q.data.pasos.reduce((n, p) => n + p.n_resultados, 0)
  const enRespaldo = q.data.respaldo?.n_resultados ?? null
  const meta = enRespaldo == null
    ? `${enRecorrido} resultados en el recorrido · lectura del archivo curado`
    : `${enRecorrido + enRespaldo} resultados reportados — ${enRecorrido} en el recorrido `
      + `y ${enRespaldo} de respaldo instrumental · lectura del archivo curado`
  return <div className="eo-evidence">
    <PageHeader title="Evidencia" meta={meta} />
    <p className="eo-note">El recorrido del argumento del informe. Cada número abre los
      resultados que lo sostienen; cada resultado, su desglose y las corridas que lo respaldan.</p>
    <div className="eo-steps">
      {q.data.pasos.map((paso) => (
        <Link key={paso.n} className="eo-step" to={`/evidencia/paso?n=${paso.n}`}>
          <div className="eo-step__n">{paso.n}</div>
          <div className="eo-step__body">
            <div className="eo-step__t">{paso.titulo}</div>
            <p className="eo-step__c">{paso.claim}</p>
            {/* Cada índice con su barra: `join(' + ') + '/'` dejaba
                «clip_bench + realtime/», como si sólo el último fuera una carpeta. */}
            <div className="eo-step__m">{paso.n_resultados} resultados · {paso.indices.map((i) => `${i}/`).join(' + ')}</div>
          </div>
          <div className="eo-fig">
            <div className="eo-fig__l">{paso.cifra_label}</div>
            <div
              className={paso.cifra_origen === 'citada' ? 'eo-fig__v eo-cifra--cit' : 'eo-fig__v'}
              title={paso.fuente ?? undefined}
            >{paso.cifra ?? '—'}</div>
            <div className="eo-fig__u">{paso.cifra_nota}</div>
          </div>
        </Link>
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
      {/* Los tres ejes se ENLAZAN, no se reimplementan: ya son documentos
          escritos y duplicarlos crearía una segunda fuente de verdad. Pero el
          enlace era a GitHub, a una rama sin mergear con archivos sin
          commitear, en un repo que todavía no es público: un link muerto, y lo
          único de esta pantalla que necesitaba internet cuando su propiedad
          declarada es funcionar con los tres planos apagados. Se dice dónde
          están —son archivos del repositorio— y no se promete abrirlos, igual
          que «Por material». */}
      <div className="eo-mini eo-mini--static">
        <div className="eo-mini__h">Ejes de lectura</div>
        <p className="eo-mini__d">La misma evidencia cortada por otros ejes, sin agregar
          mediciones: offline contra vivo, el día de rodaje, y zero-shot contra la jornada de ajuste.</p>
        <div className="eo-mini__n">3 vistas · <span className="eo-mono">results/ejes/</span> del repositorio</div>
      </div>
    </div>

    <p className="eo-cap">Las cifras se leen del <b>metrics.json</b> de cada campaña al
      abrirla; las que no tienen artefacto en este repositorio se muestran citadas, con la
      fuente al lado. Nada de esto consulta a los servicios.</p>
  </div>
}
