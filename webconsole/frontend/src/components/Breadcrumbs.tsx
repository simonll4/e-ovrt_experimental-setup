import { Link, useLocation } from 'react-router-dom'
import { usePreguntas } from '../api/queries/gen2'
import { PREGUNTA_PATH, crumbsFor } from '../nav'

/** La miga de una pregunta lleva su título, que vive en el archivo de preguntas: se lee de la misma
 *  consulta que la página (comparten caché, no hay una petición de más). */
function useTituloDePregunta(pathname: string): string | undefined {
  const esPregunta = pathname.startsWith(`${PREGUNTA_PATH}/`)
  const q = usePreguntas(esPregunta)
  if (!esPregunta) return undefined
  const id = decodeURIComponent(pathname.slice(PREGUNTA_PATH.length + 1))
  return q.data?.preguntas?.find((p) => p.id === id)?.titulo
}

export default function Breadcrumbs() {
  const { pathname, search } = useLocation()
  const titulo = useTituloDePregunta(pathname)
  const crumbs = crumbsFor(pathname, search).map((c) => (c.to === pathname && titulo ? { ...c, label: titulo } : c))
  if (crumbs.length === 0) return null
  return (
    <nav className="eo-crumbs" aria-label="Ruta de navegación">
      {crumbs.map((c, i) => (
        <span key={c.to}>
          {i > 0 ? <span className="eo-crumbs__sep"> / </span> : null}
          {i === crumbs.length - 1 ? (
            <span className="eo-crumbs__current" aria-current="page">{c.label}</span>
          ) : (
            <Link to={c.to}>{c.label}</Link>
          )}
        </span>
      ))}
    </nav>
  )
}
