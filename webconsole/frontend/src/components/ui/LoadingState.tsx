import type { ReactNode } from 'react'

/** Una consulta que todavía no respondió, dentro de la estructura que va a
 *  ocupar: la cabecera y el marco quedan quietos y sólo el contenido espera.
 *
 *  El esqueleto son barras sin datos: no hay porcentajes ni duraciones
 *  inventadas. El mensaje es texto real y se anuncia una vez (role=status); el
 *  polling posterior no vuelve a montar este componente, así que no repite el
 *  anuncio en cada tick. */
export default function LoadingState({
  children,
  lines = 3,
  inline,
}: {
  children: ReactNode
  lines?: number
  inline?: boolean
}) {
  return (
    <div className={inline ? 'eo-loading eo-loading--inline' : 'eo-loading'} role="status">
      <p className="eo-loading__msg">{children}</p>
      {lines > 0 && (
        <div className="eo-skel" aria-hidden="true">
          {Array.from({ length: lines }, (_, i) => (
            <span key={i} className="eo-skel__line" />
          ))}
        </div>
      )}
    </div>
  )
}
