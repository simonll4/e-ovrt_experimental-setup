import type { ReactNode } from 'react'

/** Cabecera de pantalla. Comparte el eje del contenido: sin sangría propia, el
 *  título arranca donde arrancan las migas, los avisos y las tablas. */
export default function PageHeader({
  title,
  meta,
  bajada,
  actions,
}: {
  title: ReactNode
  meta?: ReactNode
  /** Una o dos frases que dicen qué es esta pantalla. Visible, no un tooltip: lo que
   *  hay que entender para leer la pantalla no puede depender de pasar el cursor. */
  bajada?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="eo-pageheader">
      <div className="eo-pageheader__text">
        <h1 tabIndex={-1}>{title}</h1>
        {meta && <div className="eo-pageheader__meta">{meta}</div>}
        {bajada && <p className="eo-pageheader__bajada">{bajada}</p>}
      </div>
      {actions && <div className="eo-pageheader__actions">{actions}</div>}
    </header>
  )
}
