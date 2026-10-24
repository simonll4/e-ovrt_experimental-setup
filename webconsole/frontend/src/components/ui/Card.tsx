import type { ReactNode } from 'react'

/**
 * Tarjeta: un marco por agrupación real, con su título como encabezado.
 *
 * Título y metadatos son elementos hermanos, no uno dentro del otro: así cada
 * uno envuelve por su cuenta y un conteo largo no empuja ni corta el título.
 *
 * `level` es el nivel del encabezado. El default (2) es el de una tarjeta que
 * cuelga directo del `h1` de la página; una tarjeta dentro de una sección con
 * su propio `h2` pide 3. Antes era siempre `h3`, y cada pantalla saltaba de
 * `h1` a `h3`.
 *
 * Por default los hijos se envuelven en `.eo-card__body`, que es quien aporta el
 * padding. `flush` saca ese envoltorio para el contenido que va a sangre: una
 * tabla densa o una lista de filas con borde inferior.
 */
export default function Card({
  title,
  meta,
  className,
  flush,
  level = 2,
  id,
  children,
}: {
  title?: ReactNode
  meta?: ReactNode
  className?: string
  flush?: boolean
  level?: 2 | 3 | 4
  id?: string
  children: ReactNode
}) {
  const cls = ['eo-card', flush ? 'eo-card--flush' : '', className].filter(Boolean).join(' ')
  const Heading = `h${level}` as 'h2' | 'h3' | 'h4'
  return (
    <section className={cls} id={id}>
      {title ? (
        <header className="eo-card__head">
          <Heading className="eo-card__title">{title}</Heading>
          {meta ? <div className="eo-card__meta">{meta}</div> : null}
        </header>
      ) : null}
      {flush ? children : <div className="eo-card__body">{children}</div>}
    </section>
  )
}
