import type { ReactNode } from 'react'
import { IconChevron, IconClose, IconWarn } from './icons'

/** Aviso de bloque a lo ancho del contenido. `children` dice la condición y su
 *  consecuencia; `detail` es la recuperación técnica completa (rutas, comandos)
 *  y va plegada: está, pero no compite con lo que hay que decidir. */
export default function Banner({
  tone,
  children,
  onClose,
  action,
  detail,
  detailLabel = 'Cómo recuperarlo',
}: {
  tone: 'warn' | 'error' | 'live'
  children: ReactNode
  onClose?: () => void
  action?: ReactNode
  detail?: ReactNode
  detailLabel?: string
}) {
  return (
    <div className={`eo-banner eo-banner--${tone}`}>
      <span className="eo-banner__icon" aria-hidden="true">
        {tone === 'live' ? <span className="eo-badge__pulse" /> : <IconWarn />}
      </span>
      <div className="eo-banner__body">
        {children}
        {detail ? (
          <details className="eo-banner__detail">
            <summary><IconChevron />{detailLabel}</summary>
            <div className="eo-banner__detail-body">{detail}</div>
          </details>
        ) : null}
      </div>
      {action ? <div className="eo-banner__action">{action}</div> : null}
      {onClose && (
        <button type="button" className="eo-btn eo-btn--ghost eo-btn--icon" aria-label="Cerrar aviso" onClick={onClose}>
          <IconClose />
        </button>
      )}
    </div>
  )
}
