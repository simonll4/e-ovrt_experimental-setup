import type { ReactNode } from 'react'

/** Metadato neutro: modelo, topología, clase, identificador corto.
 *
 *  No es un estado y por eso no usa ni color ni píldora: un rectángulo bajo de
 *  borde fino, con el texto envolviendo si no entra. `mono` para identificadores
 *  literales. */
export default function Tag({
  children,
  mono,
  title,
}: {
  children: ReactNode
  mono?: boolean
  title?: string
}) {
  return (
    <span className={mono ? 'eo-tag eo-tag--mono' : 'eo-tag'} title={title}>
      {children}
    </span>
  )
}
