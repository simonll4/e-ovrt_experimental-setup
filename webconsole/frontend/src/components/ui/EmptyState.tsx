import type { ReactNode } from 'react'

/** Un vacío REAL: la consulta respondió y no hay nada. No se usa para una
 *  espera ni para un fallo — para eso están `LoadingState` y `ErrorBanner`.
 *
 *  `action` es el siguiente paso pertinente (crear, ir a otra pantalla, quitar
 *  un filtro): un vacío que no conduce a nada obliga a adivinar qué hacer. */
export default function EmptyState({
  children,
  hint,
  action,
}: {
  children: ReactNode
  hint?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="eo-empty">
      <p className="eo-empty__msg">{children}</p>
      {hint && <p className="eo-empty__hint">{hint}</p>}
      {action && <div className="eo-empty__action">{action}</div>}
    </div>
  )
}
