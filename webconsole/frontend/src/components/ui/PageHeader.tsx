import type { ReactNode } from 'react'

export default function PageHeader({
  title,
  meta,
  actions,
}: {
  title: string
  meta?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="eo-pageheader">
      <div>
        <h1>{title}</h1>
        {meta && <div className="eo-pageheader__meta">{meta}</div>}
      </div>
      {actions && <div className="eo-pageheader__actions">{actions}</div>}
    </header>
  )
}
