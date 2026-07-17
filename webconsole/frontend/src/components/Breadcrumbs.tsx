import { Link, useLocation } from 'react-router-dom'
import { crumbsFor } from '../nav'

export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const crumbs = crumbsFor(pathname)
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
