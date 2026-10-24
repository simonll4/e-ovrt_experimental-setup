import { useRef, useState } from 'react'
import type { TraceFrame } from '../../types'
import { frameAtX, timelineLayout, type LaneKind } from './timeline'

const COLOR: Record<LaneKind, string> = {
  dropped: 'var(--wn)',
  not_received: 'var(--er)',
  alert: 'var(--sr)',
}

/** Alto del área de detecciones y de los carriles de eventos, en el viewBox.
 *  Coinciden con el alto en pantalla (56 y 16 px): así el trazo no se deforma. */
const DET_H = 56
const STRIP_H = 16

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
 * Geometría: una grilla de dos columnas —rótulos y gráfico— donde cada carril
 * es una fila. Los tres gráficos y el eje viven en la MISMA columna, así que
 * comparten inicio y ancho por construcción; el cursor va dentro de cada
 * gráfico, posicionado en absoluto, y no participa de las filas. Antes el
 * cursor era un ítem más de la grilla y empujaba los carriles a columnas
 * equivocadas: el gráfico de detecciones quedaba de 82 px.
 *
 * Es el control de navegación de la traza, no un adorno: tocar la línea de
 * tiempo selecciona el cuadro, el control deslizante hace lo mismo con el
 * teclado, y el cursor marca dónde está parada la lista.
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
    parts.push(`${dets} ${dets === 1 ? 'detección' : 'detecciones'}`)
    if (alerts) parts.push(`${alerts} ${alerts === 1 ? 'alerta' : 'alertas'}`)
    if (fr.control !== 'received') parts.push(fr.control)
    return parts.join(' · ')
  }

  if (!frames.length) {
    return <p className="eo-cap">Todavía no hay cuadros para dibujar la línea de tiempo.</p>
  }

  const entrega = marks.filter((m) => m.kind !== 'alert')
  const alertas = marks.filter((m) => m.kind === 'alert')

  const elegir = (pos: number) => {
    const fr = frames[pos]
    if (fr && onSelect) onSelect(fr.frame_index ?? pos, pos)
  }

  const haySeleccion = selected != null && selected >= 0 && selected < frames.length
  const cursor = haySeleccion ? (
    <span className="eo-timeline__cursor" style={{ left: `${posOf(selected!)}%` }} aria-hidden="true" />
  ) : null

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
        onClick={(e) => elegir(pick(e.clientX))}
      >
        <span className="eo-timeline__label">Detecciones por cuadro</span>
        <div className="eo-timeline__plot">
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
          {cursor}
        </div>

        <span className="eo-timeline__label">Entrega al motor de reglas</span>
        <div className="eo-timeline__plot">
          {strip(entrega, 'Estado de entrega por cuadro')}
          {cursor}
        </div>

        <span className="eo-timeline__label">Alertas</span>
        <div className="eo-timeline__plot">
          {strip(alertas, 'Alertas confirmadas por cuadro')}
          {cursor}
        </div>
      </div>

      {/* La escala vive en una grilla con las mismas columnas que los carriles:
          el control deslizante y el eje arrancan y terminan donde los gráficos.
          El deslizante es la misma selección que el click, con teclado. */}
      <div className="eo-timeline__scale">
        <span className="eo-timeline__label eo-timeline__label--scale">Ir a un cuadro</span>
        <div className="eo-timeline__scalebody">
          <input
            type="range"
            className="eo-timeline__range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            step={1}
            value={haySeleccion ? selected! : 0}
            aria-label="Cuadro elegido en la línea de tiempo"
            aria-valuetext={haySeleccion ? describe(selected!) : 'ningún cuadro elegido'}
            onChange={(e) => elegir(Number(e.target.value))}
          />
          {/* En segundos y no en cuadros: es lo que permite ir al mismo instante
              del video. Sin marca de tiempo utilizable se cae a cuadros antes
              que inventar un eje temporal. */}
          <div className="eo-timeline__axis">
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
        </div>
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

      <p className="eo-timeline__hint">
        {hover != null && hover >= 0
          ? describe(hover)
          : haySeleccion
            ? describe(selected!)
            : 'Tocá la línea de tiempo o usá el control para ir a un cuadro'}
      </p>
    </div>
  )
}
