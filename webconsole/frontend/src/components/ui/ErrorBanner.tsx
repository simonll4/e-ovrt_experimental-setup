import type { ReactNode } from 'react'
import Button from './Button'
import { IconChevron } from './icons'

/** Un fallo, con su condición y su consecuencia a la vista.
 *
 *  `detail` es el detalle técnico íntegro (código, cuerpo, ruta): no se recorta
 *  ni se esconde, pero va plegado para que no tape lo que la persona tiene que
 *  decidir. `onRetry` sólo se ofrece para LECTURAS: una mutación no se reintenta
 *  sola ni con un botón genérico — la decide la persona desde su acción. */
export default function ErrorBanner({
  children,
  detail,
  onRetry,
  retrying,
}: {
  children: ReactNode
  detail?: ReactNode
  onRetry?: () => void
  retrying?: boolean
}) {
  return (
    <div className="eo-error" role="alert">
      <div className="eo-error__body">{children}</div>
      {detail != null && detail !== '' && (
        <details className="eo-error__detail">
          <summary><IconChevron />Detalle técnico</summary>
          <pre>{detail}</pre>
        </details>
      )}
      {onRetry && (
        <div className="eo-error__actions">
          <Button onClick={onRetry} disabled={retrying}>
            {retrying ? 'Reintentando…' : 'Reintentar'}
          </Button>
        </div>
      )}
    </div>
  )
}
