import ActivityTimeline from './charts/ActivityTimeline'
import { Card } from './ui'
import type { TraceFrame } from '../types'

/**
 * Tarjeta que compone la línea de tiempo con su estado vacío, su aviso de traza
 * truncada y el enganche con la selección de cuadro.
 *
 * La primitiva `ActivityTimeline` no sabe qué es una corrida: recibe cuadros y
 * dibuja. Lo que sabe de corridas vive acá.
 */
export default function RunTimeline({
  frames,
  selected,
  onSelect,
  truncated,
  loading,
}: {
  frames: TraceFrame[]
  selected: number | null
  onSelect: (frameIndex: number, position: number) => void
  truncated: boolean
  loading: boolean
}) {
  return (
    // flush: el padding lo pone .eo-timeline__body, no el cuerpo genérico de la
    // tarjeta — si no, se suman los dos.
    <Card title="Línea de tiempo" meta={loading ? 'leyendo…' : `${frames.length} cuadros`} flush>
      <div className="eo-timeline__body">
        {loading ? (
          <p className="eo-cap">Leyendo la traza de la corrida…</p>
        ) : (
          <>
            <ActivityTimeline frames={frames} selected={selected} onSelect={onSelect} />
            {truncated && (
              <p className="eo-cap">
                La traza se cortó en {frames.length} cuadros: la corrida tiene más de los que
                la consola trae de una vez. Lo que se ve acá es el comienzo, no la corrida entera.
              </p>
            )}
          </>
        )}
      </div>
    </Card>
  )
}
