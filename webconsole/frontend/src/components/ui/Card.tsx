import type { ReactNode } from 'react'

export default function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <section className="eo-card">
      {title ? <h3 className="eo-card__title">{title}</h3> : null}
      {children}
    </section>
  )
}
