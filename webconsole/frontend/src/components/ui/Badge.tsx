import type { ReactNode } from 'react'
import type { BadgeTone } from '../../types'

/** Estado operativo: en curso, completada, fallida, operativo, caído.
 *
 *  Es lo único que lleva forma de píldora y color de estado. Identificadores,
 *  modelo, topología o clasificación son metadatos y van en `Tag`: con la misma
 *  silueta para todo, la pantalla no dejaba distinguir qué era un estado.
 *
 *  El texto es obligatorio: el color y el punto que late son apoyos. */
export default function Badge({
  tone,
  pulse,
  title,
  children,
}: {
  tone: BadgeTone
  pulse?: boolean
  title?: string
  children: ReactNode
}) {
  return (
    <span className={`eo-badge eo-badge--${tone}`} title={title}>
      {pulse ? <span className="eo-badge__pulse" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}
