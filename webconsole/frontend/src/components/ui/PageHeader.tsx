import type { ReactNode } from 'react'

/** Cabecera de pantalla. Comparte el eje del contenido: sin sangría propia, el
 *  título arranca donde arrancan las migas, los avisos y las tablas. */
export default function PageHeader({
  title,
  meta,
  actions,
}: {
  title: ReactNode
  meta?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="eo-pageheader">
      <div className="eo-pageheader__text">
        <h1 tabIndex={-1}>{title}</h1>
        {meta && <div className="eo-pageheader__meta">{meta}</div>}
      </div>
      {actions && <div className="eo-pageheader__actions">{actions}</div>}
    </header>
  )
}
