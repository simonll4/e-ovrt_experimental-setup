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

export default function GroupedBars({ groups, series, labels, width = 560, height = 220 }: {
  groups: string[]
  series: Array<Array<number | null>>
  labels: string[]
  width?: number
  height?: number
}) {
  const plotHeight = height - 40
  const rects = groupedBarsLayout(groups, series, width, plotHeight)
  return (
    <div>
      <svg width={width} height={height}>
        <line x1={0} y1={plotHeight} x2={width} y2={plotHeight} style={{ stroke: 'var(--border-strong)' }} />
        {rects.map((r) => (
          <rect
            key={`${r.series}-${r.group}`}
            x={r.x} y={r.y} width={r.width} height={r.height} fill={r.color} rx={2}
          >
            <title>{`${labels[r.series]} — ${groups[r.group]}: ${r.value.toFixed(3)}`}</title>
          </rect>
        ))}
        {groups.map((group, gi) => (
          <text
            key={group}
            x={(gi + 0.5) * (width / groups.length)}
            y={plotHeight + 16}
            textAnchor="middle"
            style={{ fontSize: 'var(--text-xs)', fill: 'var(--text-muted)' }}
          >
            {group}
          </text>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', fontSize: 'var(--text-sm)' }}>
        {labels.map((label, i) => (
          <span key={label}>
            <span
              style={{
                background: SERIES_COLORS[i % SERIES_COLORS.length],
                display: 'inline-block', width: 10, height: 10, marginRight: 4,
              }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
