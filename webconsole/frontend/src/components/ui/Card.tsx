import type { ReactNode } from 'react'

/**
 * Tarjeta del prototipo: el título es una banda con borde inferior, y el cuerpo
 * lleva su propio padding.
 *
 * Por default los hijos se envuelven en `.eo-card__body`, que es quien aporta el
 * padding. Así las pantallas que ya existían —que lo heredaban de `.eo-card`—
 * siguen viéndose igual sin tocarlas.
 *
 * `flush` saca ese envoltorio para el contenido que va a sangre: una tabla densa
 * o una lista de filas con borde inferior tienen que llegar hasta el borde de la
 * tarjeta, no quedar flotando adentro con un margen.
 */
export default function Card({
  title,
  meta,
  className,
  flush,
  children,
}: {
  title?: ReactNode
  meta?: ReactNode
  className?: string
  flush?: boolean
  children: ReactNode
}) {
  const cls = ['eo-card', className].filter(Boolean).join(' ')
  return (
    <section className={cls}>
      {title ? (
        <h3 className="eo-card__title">
          {title}
          {meta ? <span className="eo-card__meta">{meta}</span> : null}
        </h3>
      ) : null}
      {flush ? children : <div className="eo-card__body">{children}</div>}
    </section>
  )
}
