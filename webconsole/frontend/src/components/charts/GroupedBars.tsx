import { niceTicks } from './layout'

// Paleta categórica de 8 slots (skill dataviz), stepped para superficie oscura #1a1a19.
// Validada: banda L, croma, CVD adyacente (peor ΔE 8.4 protan), visión normal (19.3), contraste >=3:1.
// El ORDEN es el mecanismo de seguridad CVD, no cosmética: no reordenar sin re-validar.
export const SERIES_COLORS = [
  '#3987e5', // azul
  '#008300', // verde
  '#d55181', // magenta
  '#c98500', // amarillo
  '#199e70', // aqua
  '#d95926', // naranja
  '#9085e9', // violeta
  '#e66767', // rojo
]

export interface BarRect {
  x: number
  y: number
  width: number
  height: number
  color: string
  series: number
  group: number
  value: number
}

// Layout puro: dominio fijo [0,1] (AP@0.5). `series[i]` es paralela a `groups`.
export function groupedBarsLayout(
  groups: string[],
  series: Array<Array<number | null>>,
  width: number,
  plotHeight: number,
): BarRect[] {
  const rects: BarRect[] = []
  const nGroups = groups.length
  const nSeries = series.length
  if (!nGroups || !nSeries) return rects
  const slot = width / nGroups
  const inner = slot * 0.7
  const gap = 2
  const barWidth = Math.max(1, (inner - gap * (nSeries - 1)) / nSeries)
  groups.forEach((_group, gi) => {
    const start = gi * slot + (slot - inner) / 2
    series.forEach((values, si) => {
      const value = values[gi]
      if (value == null) return
      const clamped = Math.max(0, Math.min(1, value))
      rects.push({
        x: start + si * (barWidth + gap),
        y: plotHeight - clamped * plotHeight,
        width: barWidth,
        height: clamped * plotHeight,
        color: SERIES_COLORS[si % SERIES_COLORS.length],
        series: si,
        group: gi,
        value,
      })
    })
  })
  return rects
}

const fmtValue = (v: number) => v.toFixed(2).replace('.', ',')

export default function GroupedBars({ groups, series, labels, width = 720, height = 300 }: {
  groups: string[]
  series: Array<Array<number | null>>
  labels: string[]
  width?: number
  height?: number
}) {
  const axisW = 44
  const bottomH = 34
  const topPad = 18 // aire para la etiqueta de valor sobre la barra
  const plotWidth = width - axisW
  const plotHeight = height - bottomH - topPad
  const rects = groupedBarsLayout(groups, series, plotWidth, plotHeight)
  // AP@0.5 vive en [0,1]: dominio fijo, no automático. Un eje que se reescala
  // según los datos hace que dos gráficos no se puedan comparar entre sí.
  const ticks = niceTicks(1)

  return (
    <div className="eo-bars">
      <svg
        width="100%"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Precisión por clase, ${labels.join(' contra ')}`}
      >
        <g transform={`translate(${axisW}, ${topPad})`}>
          {ticks.map((t) => {
            const y = plotHeight - t * plotHeight
            return (
              <g key={t}>
                <line x1={0} y1={y} x2={plotWidth} y2={y} stroke="var(--bd)" />
                <text x={-8} y={y + 4} textAnchor="end" className="eo-bars__tick">
                  {fmtValue(t)}
                </text>
              </g>
            )
          })}
          {rects.map((r) => (
            <g key={`${r.series}-${r.group}`}>
              <rect x={r.x} y={r.y} width={r.width} height={r.height} fill={r.color} rx={4}>
                <title>{`${labels[r.series]} — ${groups[r.group]}: ${fmtValue(r.value)}`}</title>
              </rect>
              {/* Etiqueta directa: son 2–4 grupos, así que el valor va sobre la
                  barra y no hay que leerlo contra el eje. */}
              <text
                x={r.x + r.width / 2}
                y={r.y - 5}
                textAnchor="middle"
                className="eo-bars__value"
              >
                {fmtValue(r.value)}
              </text>
            </g>
          ))}
          {groups.map((group, gi) => (
            <text
              key={group}
              x={(gi + 0.5) * (plotWidth / groups.length)}
              y={plotHeight + 20}
              textAnchor="middle"
              className="eo-bars__group"
            >
              {group}
            </text>
          ))}
        </g>
      </svg>
      <ul className="eo-bars__legend">
        {labels.map((label, i) => (
          <li key={label}>
            <span
              className="eo-bars__key"
              style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }}
            />
            {label}
          </li>
        ))}
      </ul>
    </div>
  )
}
