import type { ReactNode } from 'react'

export default function StatTile({ label, value, unit }: { label: string; value: ReactNode; unit?: string }) {
  return (
    <div className="eo-stat">
      <span className="eo-stat__label">{label}</span>
      <span className="eo-stat__value">
        {value}
        {unit ? <span className="eo-stat__unit">{unit}</span> : null}
      </span>
    </div>
  )
}
