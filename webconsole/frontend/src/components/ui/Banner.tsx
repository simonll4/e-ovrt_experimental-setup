import type { ReactNode } from 'react'
import { IconWarn } from './icons'

export default function Banner({
  tone,
  children,
  onClose,
  action,
}: {
  tone: 'warn' | 'error' | 'live'
  children: ReactNode
  onClose?: () => void
  action?: ReactNode
}) {
  return (
    <div className={`eo-banner eo-banner--${tone}`}>
      <span className="eo-banner__icon" aria-hidden="true">
        {tone === 'live' ? <span className="eo-badge__pulse" /> : <IconWarn />}
      </span>
      <div className="eo-banner__body">{children}</div>
      {action}
      {onClose && (
        <button type="button" className="eo-btn eo-btn--ghost" aria-label="Cerrar aviso" onClick={onClose}>
          ✕
        </button>
      )}
    </div>
  )
}
