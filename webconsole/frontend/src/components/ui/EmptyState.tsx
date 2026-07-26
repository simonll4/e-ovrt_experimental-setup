import type { ReactNode } from 'react'

export default function EmptyState({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <p className="eo-empty">
      {children}
      {hint && <><br /><span className="eo-empty__hint">{hint}</span></>}
    </p>
  )
}
