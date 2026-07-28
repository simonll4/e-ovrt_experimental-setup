import { useRef, useState } from 'react'
import type { TraceFrame } from '../../types'
import { frameAtX, timelineLayout, type LaneKind } from './timeline'

const LANE: Record<LaneKind, { row: number; color: string }> = {
  dropped: { row: 0, color: 'var(--wn)' },
  not_received: { row: 0, color: 'var(--er)' },
  alert: { row: 1, color: 'var(--sr)' },
}

const LANE_H = 8
const LANE_GAP = 4

/**
 * Actividad de una corrida a lo largo del tiempo: área de detecciones por cuadro
 * más dos carriles de eventos discretos (entrega al motor de reglas, alertas).
 *
 * Es el control de navegación de la traza, no un adorno: tocar la línea de tiempo
 * selecciona el cuadro, y el cursor marca dónde está parada la lista.
 */
export default function ActivityTimeline({
  frames,
  width = 1200,
  plotHeight = 56,
  selected,
  onSelect,
}: {
  frames: TraceFrame[]
  width?: number
  plotHeight?: number
  selected?: number | null
  onSelect?: (frameIndex: number, position: number) => void
}) {
  const ref = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const { line, area, marks, maxDetections } = timelineLayout(frames, width, plotHeight)
  const lanesTop = plotHeight + LANE_GAP
  const height = lanesTop + LANE_H * 2 + LANE_GAP * 2

  const posOf = (i: number) => (frames.length ? (i / frames.length) * width : 0)

  const pick = (clientX: number): number => {
    const box = ref.current?.getBoundingClientRect()
    if (!box || !box.width) return -1
    return frameAtX(clientX - box.left, box.width, frames.length)
  }

  const describe = (pos: number): string => {
    const fr = frames[pos]
    if (!fr) return ''
    const dets = fr.detections?.length ?? 0
    const alerts = fr.alert?.length ?? 0
    const parts = [`cuadro ${fr.frame_index ?? pos}`, `${dets} detecciones`]
    if (alerts) parts.push(`${alerts} alertas`)
    if (fr.control !== 'received') parts.push(fr.control)
    return parts.join(' · ')
  }

  if (!frames.length) {
    return <p className="eo-cap">Todavía no hay cuadros para dibujar la línea de tiempo.</p>
  }

  return (
    <div className="eo-timeline">
      <svg
        ref={ref}
        className="eo-timeline__svg"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Actividad de ${frames.length} cuadros: detecciones, entrega al motor de reglas y alertas`}
        onMouseMove={(e) => setHover(pick(e.clientX))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const pos = pick(e.clientX)
          const fr = frames[pos]
          if (fr && onSelect) onSelect(fr.frame_index ?? pos, pos)
        }}
      >
        <rect x={0} y={0} width={width} height={plotHeight} fill="var(--sunken)" />
        {area && <path d={area} fill="var(--live)" fillOpacity="0.22" />}
        {line && (
          <path
            d={line}
            fill="none"
            stroke="var(--live)"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        )}
        {marks.map((m, i) => (
          <rect
            key={`${m.kind}-${m.frameIndex}-${i}`}
            x={m.x}
            y={lanesTop + LANE[m.kind].row * (LANE_H + LANE_GAP)}
            width={m.width}
            height={LANE_H}
            rx={2}
            fill={LANE[m.kind].color}
          />
        ))}
        {selected != null && selected >= 0 && selected < frames.length && (
          <line
            x1={posOf(selected)}
            y1={0}
            x2={posOf(selected)}
            y2={height}
            stroke="var(--ac)"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>

      <div className="eo-timeline__axis">
        <span className="eo-mono">0</span>
        <span className="eo-mono">{frames.length} cuadros</span>
      </div>

      {/* Leyenda por FORMA además de color: entre `alerta` (--sr) y `fallida`
          (--er) hay ΔE 8,8 en visión normal, por debajo del piso de 15. Un
          cuadradito de color no alcanza para distinguirlos. */}
      <ul className="eo-timeline__legend">
        <li>
          <span className="eo-timeline__key eo-timeline__key--area" />
          Detecciones · pico {maxDetections}
        </li>
        <li>
          <span className="eo-timeline__key eo-timeline__key--dropped" />
          Descartado
        </li>
        <li>
          <span className="eo-timeline__key eo-timeline__key--notrecv" />
          No recibido
        </li>
        <li>
          <span className="eo-timeline__key eo-timeline__key--alert" />
          Alerta
        </li>
      </ul>

      <p className="eo-timeline__hint" aria-live="polite">
        {hover != null && hover >= 0
          ? describe(hover)
          : 'Tocá la línea de tiempo para ir a un cuadro'}
      </p>
    </div>
  )
}
