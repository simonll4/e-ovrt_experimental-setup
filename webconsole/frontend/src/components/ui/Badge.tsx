import type { ReactNode } from 'react'
import type { BadgeTone } from '../../types'

export default function Badge({
  tone,
  pulse,
  children,
}: {
  tone: BadgeTone
  pulse?: boolean
  children: ReactNode
}) {
  return (
    <span className={`eo-badge eo-badge--${tone}`}>
      {pulse ? <span className="eo-badge__pulse" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}
