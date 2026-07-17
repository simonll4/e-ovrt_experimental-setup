import { labelColor } from '../../traceview'

/** Chip de detección: punto de color (labelColor) + label + confianza o conteo. */
export default function DetChip({
  label,
  confidence,
  count,
}: {
  label: string
  confidence?: number
  count?: number
}) {
  return (
    <span className="eo-chip">
      <span className="eo-chip__dot" style={{ background: labelColor(label) }} />
      {label}
      {confidence !== undefined && <span className="eo-chip__conf">{confidence.toFixed(2)}</span>}
      {count !== undefined && <span className="eo-chip__conf">{count}</span>}
    </span>
  )
}
