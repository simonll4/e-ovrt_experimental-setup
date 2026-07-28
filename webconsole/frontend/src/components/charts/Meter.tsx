import { TONE_VAR, type ChartTone } from './Sparkline'

export type MeterTone = ChartTone | 'neutral'

export interface MeterSegment {
  value: number
  tone: MeterTone
  label: string
}

const VAR: Record<MeterTone, string> = { ...TONE_VAR, neutral: '--nt' }

/**
 * Barra segmentada horizontal.
 *
 * `total` fija el denominador cuando la barra representa una proporción contra un
 * límite ("2 de 3 criterios"): sin él, los segmentos se reparten el ancho completo
 * y una barra llena dejaría de significar "todo cumplido".
 *
 * Cada segmento lleva su etiqueta en `title` y el conjunto se describe en
 * `aria-label`: el color nunca es el único portador del significado.
 */
export default function Meter({
  segments,
  total,
  height = 4,
}: {
  segments: MeterSegment[]
  total?: number
  height?: number
}) {
  const sum = segments.reduce((acc, s) => acc + Math.max(0, s.value), 0)
  const denom = total ?? sum
  const pct = (v: number) => (denom > 0 ? (Math.max(0, v) / denom) * 100 : 0)
  return (
    <div
      className="eo-meter"
      style={{ height }}
      role="img"
      aria-label={segments.map((s) => `${s.label}: ${s.value}`).join(', ')}
    >
      {segments.map((s) => (
        <i
          key={s.label}
          className="eo-meter__seg"
          title={`${s.label}: ${s.value}`}
          style={{ width: `${pct(s.value)}%`, background: `var(${VAR[s.tone]})` }}
        />
      ))}
    </div>
  )
}
