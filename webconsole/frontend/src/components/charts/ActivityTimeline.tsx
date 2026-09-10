import { useRef, useState } from 'react'
import type { TraceFrame } from '../../types'
import { frameAtX, timelineLayout, type LaneKind } from './timeline'

const COLOR: Record<LaneKind, string> = {
  dropped: 'var(--wn)',
  not_received: 'var(--er)',
  alert: 'var(--sr)',
}

/** Alto del área de detecciones y de los carriles de eventos, en el viewBox. */
const DET_H = 42
const STRIP_H = 10

const dec1 = (v: number): string => v.toFixed(1).replace('.', ',')

/**
 * Actividad de una corrida a lo largo del tiempo, en tres carriles rotulados:
 * detecciones por cuadro, entrega al motor de reglas y alertas.
 *
 * Los tres van separados y con rótulo porque responden preguntas distintas, y
 * apilados sin nombre había que deducir cuál era cuál desde la leyenda. La
 * separación espacial es además la codificación secundaria que hace que el
 * significado no dependa del matiz: entre el naranja de "alerta" y el rojo de
 * "no recibido" hay ΔE 8,8 en visión normal, por debajo del piso de 15.
 *
 * Es el control de navegación de la traza, no un adorno: tocar la línea de
 * tiempo selecciona el cuadro, y el cursor marca dónde está parada la lista.
 */
export default function ActivityTimeline({
  frames,
  width = 1200,
  plotHeight = DET_H,
  selected,
  onSelect,
}: {
  frames: TraceFrame[]
  width?: number
  plotHeight?: number
  selected?: number | null
  onSelect?: (frameIndex: number, position: number) => void
}) {
  // Se mide contra el carril de detecciones y no contra el contenedor: éste
  // incluye la columna de rótulos, y usar su ancho corría el cuadro elegido.
  const detRef = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const { line, area, marks, maxDetections } = timelineLayout(frames, width, plotHeight)

  // Segundos transcurridos desde el primer cuadro. En corridas sobre archivo los
  // timestamps son relativos a la fuente y arrancan en 0, así que la resta vale
  // igual. Si no hay marca de tiempo utilizable, el eje cae a cuadros.
  const t0 = frames[0]?.timestamp_ms ?? null
  const tN = frames[frames.length - 1]?.timestamp_ms ?? null
  const segundos =
    t0 != null && tN != null && Number.isFinite(tN - t0) && tN - t0 > 0 ? (tN - t0) / 1000 : null

  const posOf = (i: number) => (frames.length ? (i / frames.length) * 100 : 0)

  const pick = (clientX: number): number => {
    const box = detRef.current?.getBoundingClientRect()
    if (!box || !box.width) return -1
    return frameAtX(clientX - box.left, box.width, frames.length)
  }

  const segundoDe = (pos: number): number | null => {
    const t = frames[pos]?.timestamp_ms
    if (t == null || t0 == null) return null
    return (t - t0) / 1000
  }

  const describe = (pos: number): string => {
    const fr = frames[pos]
    if (!fr) return ''
    const dets = fr.detections?.length ?? 0
    const alerts = fr.alert?.length ?? 0
    const s = segundoDe(pos)
    const parts = [`cuadro ${fr.frame_index ?? pos}`]
    if (s != null) parts.push(`${dec1(s)} s`)
    parts.push(`${dets} detecciones`)
    if (alerts) parts.push(`${alerts} alertas`)
    if (fr.control !== 'received') parts.push(fr.control)
    return parts.join(' · ')
  }

  if (!frames.length) {
    return <p className="eo-cap">Todavía no hay cuadros para dibujar la línea de tiempo.</p>
  }

  const entrega = marks.filter((m) => m.kind !== 'alert')
  const alertas = marks.filter((m) => m.kind === 'alert')

  const alSeleccionar = (clientX: number) => {
    const pos = pick(clientX)
    const fr = frames[pos]
    if (fr && onSelect) onSelect(fr.frame_index ?? pos, pos)
  }

  /** Carril de eventos discretos: una marca por cuadro afectado. */
  const strip = (items: typeof marks, label: string) => (
    <svg
      className="eo-timeline__strip"
      viewBox={`0 0 ${width} ${STRIP_H}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      {items.map((m, i) => (
        <rect
          key={`${m.kind}-${m.frameIndex}-${i}`}
          x={m.x}
          y={0}
          width={m.width}
          height={STRIP_H}
          rx={2}
          fill={COLOR[m.kind]}
        />
      ))}
    </svg>
  )

  return (
    <div className="eo-timeline">
      <div
        className="eo-timeline__lanes"
        onMouseMove={(e) => setHover(pick(e.clientX))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => alSeleccionar(e.clientX)}
      >
        <span className="eo-timeline__label">
          Detecciones
          <br />
          por cuadro
        </span>
        <svg
          ref={detRef}
          className="eo-timeline__det"
          viewBox={`0 0 ${width} ${plotHeight}`}
          preserveAspectRatio="none"
          role="img"
          aria-label={`Detecciones por cuadro a lo largo de ${frames.length} cuadros`}
        >
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
        </svg>

        <span className="eo-timeline__label">
          Entrega al
          <br />
          motor de reglas
        </span>
        {strip(entrega, 'Estado de entrega por cuadro')}

        <span className="eo-timeline__label">Alertas</span>
        {strip(alertas, 'Alertas confirmadas por cuadro')}

        <div className="eo-timeline__overlay">
          {selected != null && selected >= 0 && selected < frames.length && (
            <div className="eo-timeline__cursor" style={{ left: `${posOf(selected)}%` }} />
          )}
        </div>
      </div>

      {/* En segundos y no en cuadros: es lo que permite ir al mismo instante del
          video. Sin marca de tiempo utilizable se cae a cuadros antes que
          inventar un eje temporal. */}
      <div className="eo-timeline__axis eo-timeline__axis--secs">
        {segundos != null ? (
          <>
            <span className="eo-mono">0,0 s</span>
            <span className="eo-mono">{dec1(segundos / 2)} s</span>
            <span className="eo-mono">{dec1(segundos)} s</span>
          </>
        ) : (
          <>
            <span className="eo-mono">0</span>
            <span className="eo-mono">{frames.length} cuadros</span>
          </>
        )}
      </div>

      {/* Leyenda por FORMA además de color, por el mismo ΔE del docstring. */}
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
