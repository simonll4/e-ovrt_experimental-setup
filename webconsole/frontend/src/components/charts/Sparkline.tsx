import { areaPaths } from './layout'

export type ChartTone = 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'accent'

/** Mismo vocabulario de tono que BadgeTone, más `accent`. `alert` es el naranja
 *  (--sr); no existe un tono llamado "serious". */
export const TONE_VAR: Record<ChartTone, string> = {
  live: '--live',
  ok: '--ok',
  warn: '--wn',
  alert: '--sr',
  error: '--er',
  accent: '--ac',
}

/**
 * Serie de una sola variable dentro de un tile KPI: sin ejes, sin leyenda y sin
 * hover. El número grande del tile es la etiqueta y el valor; el sparkline solo
 * aporta la forma del cambio.
 */
export default function Sparkline({
  values,
  tone = 'live',
  width = 132,
  height = 26,
}: {
  values: Array<number | null>
  tone?: ChartTone
  width?: number
  height?: number
}) {
  const { line, area } = areaPaths(values, width, height)
  const color = `var(${TONE_VAR[tone]})`
  if (!line) {
    return <span className="eo-spark eo-spark--empty" style={{ width, height }} aria-hidden="true" />
  }
  const gid = `eo-spark-grad-${tone}`
  return (
    <svg className="eo-spark" width={width} height={height} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
