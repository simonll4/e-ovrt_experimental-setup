import { Link } from 'react-router-dom'
import { usePreguntas } from '../api/queries/gen2'
import { Banner, Card, EmptyState } from '../components/ui'
import { GEN1, PREGUNTA_PATH } from '../nav'
import { EstadoDeLectura } from './evidencia/comun'
import { Plantilla, fechaLlana } from './preguntas/comun'
import './preguntas/Preguntas.css'

/** La portada (plan de la consola de evidencia, §2.1): qué se hizo y qué se encontró. Tres líneas de
 *  encabezado, las siete preguntas con su cifra titular y un pie generado. Sin párrafos: todo sale de
 *  `results/evidence-vista/preguntas.yaml`, y cada cifra, de los resultados. */
export default function InicioPage() {
  const q = usePreguntas()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Inicio" q={q} />
  const v = q.data
  if (!v.available || !v.preguntas || !v.proyecto) {
    return <Card><EmptyState>{v.message ?? 'No están las preguntas de la consola.'}</EmptyState></Card>
  }
  const p = v.proyecto
  const pie = v.pie
  return (
    <div className="eo-inicio">
      <header className="eo-inicio__cab">
        <h1 tabIndex={-1}>
          <span className="eo-inicio__nombre">{p.nombre}</span>
          <span className="eo-inicio__titulo">{p.titulo}</span>
        </h1>
        {p.que_es && <p className="eo-inicio__que">{p.que_es}</p>}
        <p className="eo-inicio__autoria">
          {[p.institucion, p.carrera, ...(p.autores ?? [])].filter(Boolean).join(' · ')}
        </p>
      </header>

      {v.errores && v.errores.length > 0 && (
        <Banner tone="warn">
          {v.errores.length === 1 ? 'Una cifra no se pudo leer' : `${v.errores.length} cifras no se pudieron leer`}{' '}
          de los resultados: se muestran como «—».
        </Banner>
      )}

      <ol className="eo-inicio__preguntas" aria-label="Las siete preguntas">
        {v.preguntas.map((pr) => (
          <li key={pr.id}>
            <Link className="eo-inicio__pregunta" to={`${PREGUNTA_PATH}/${encodeURIComponent(pr.id)}`}>
              <span className="eo-inicio__q">{pr.titulo}</span>
              <span className="eo-inicio__titular"><Plantilla texto={pr.titular} cifras={pr.cifras} /></span>
            </Link>
          </li>
        ))}
      </ol>

      {pie && (
        <footer className="eo-inicio__pie">
          <ul className="eo-inicio__enlaces">
            {p.enlaces?.informe && (
              <li><a href={p.enlaces.informe} target="_blank" rel="noreferrer">El informe</a></li>
            )}
            <li><Link to="/documentacion">Cómo leer</Link></li>
            {/* Fuera de la barra (revisión del 2026-11-19): el Archivo tiene las cifras de la etapa de desarrollo, con la
                referencia anterior, y no son las del informe. Se dice en el enlace, no recién al entrar. */}
            <li>
              <Link to={GEN1.to} aria-describedby="eo-inicio-archivo">Archivo de la etapa de desarrollo</Link>
              <span className="eo-inicio__aclara" id="eo-inicio-archivo">
                Las cifras de la etapa de desarrollo, con la referencia anterior: no son las del informe
              </span>
            </li>
          </ul>
          {p.enlaces?.repositorios && p.enlaces.repositorios.length > 0 && (
            <div className="eo-inicio__repos">
              <span className="eo-inicio__rotulo">Repositorios</span>
              <ul>
                {p.enlaces.repositorios.map((r) => (
                  <li key={r.url}><a href={r.url} target="_blank" rel="noreferrer" className="eo-mono">{r.nombre}</a></li>
                ))}
              </ul>
            </div>
          )}
          <p className="eo-inicio__version">
            {pie.pruebas} pruebas · campaña del {fechaLlana(pie.desde)} al {fechaLlana(pie.hasta)}
            {pie.version && (
              <>
                {' · '}
                {pie.version.de === 'resultados' ? 'resultados en el commit ' : 'repositorio en el commit '}
                <code className="eo-mono">{pie.version.commit}</code>
              </>
            )}
          </p>
        </footer>
      )}
    </div>
  )
}
