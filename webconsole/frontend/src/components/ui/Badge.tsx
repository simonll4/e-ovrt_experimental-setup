import type { ReactNode } from 'react'
import type { BadgeTone } from '../../types'

export default function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`eo-badge eo-badge--${tone}`}>{children}</span>
}
