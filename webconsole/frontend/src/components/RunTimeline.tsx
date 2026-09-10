import { useMemo } from 'react'
import ActivityTimeline from './charts/ActivityTimeline'
import { Card } from './ui'
import type { TraceFrame, TraceIndex } from '../types'

/**
 * Tarjeta que compone la línea de tiempo con su estado vacío y el enganche con
 * la selección de cuadro.
 *
 * Se alimenta del índice de actividad —una sola petición con la corrida
 * completa— y no de la traza paginada: para 200 cuadros son 8 KB contra 247, y
 * la diferencia crece con la corrida. La primitiva `ActivityTimeline` no sabe
 * qué es una corrida: recibe cuadros y dibuja. Lo que sabe de corridas vive acá.
 */
export default function RunTimeline({
  index,
  selected,
  onSelect,
  loading,
}: {
  index: TraceIndex | null
  selected: number | null
  onSelect: (frameIndex: number, position: number) => void
  loading: boolean
}) {
  // El índice viene en arrays paralelos (así pesa una fracción); acá se rearma
  // lo mínimo que `ActivityTimeline` necesita, sin las cajas de detección ni el
  // progreso de condiciones, que la línea de tiempo no dibuja.
  const frames = useMemo<TraceFrame[]>(() => {
    if (!index) return []
    return index.control_state.map((estado, i) => ({
      frame_index: index.frame_index[i],
      unit_id: index.unit_id[i],
      timestamp_ms: index.timestamp_ms[i],
      detections: new Array(index.detections[i]).fill(null) as TraceFrame['detections'],
      control: estado === 'unknown' ? 'n/d' : estado,
      control_state: estado,
      progress: [],
      alert: index.alert[i] ? [{ condition_id: '', severity: '' }] : [],
    }))
  }, [index])

  return (
    // flush: el padding lo pone .eo-timeline__body, no el cuerpo genérico de la
    // tarjeta — si no, se suman los dos.
    <Card title="Línea de tiempo" meta={loading ? 'leyendo…' : `${frames.length} cuadros`} flush>
      <div className="eo-timeline__body">
        {loading ? (
          <p className="eo-cap">Leyendo la traza de la corrida…</p>
        ) : (
          <ActivityTimeline frames={frames} selected={selected} onSelect={onSelect} />
        )}
      </div>
    </Card>
  )
}
