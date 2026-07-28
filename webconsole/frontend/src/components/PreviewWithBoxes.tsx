import { useState } from 'react'
import { labelColor } from '../traceview'
import type { TraceDetection } from '../types'

export default function PreviewWithBoxes({
  src,
  alt,
  detections,
  width = 240,
  emptyMessage = 'sin vista previa',
}: {
  src: string
  alt: string
  detections: TraceDetection[]
  width?: number
  /** Qué decir cuando no hay imagen. El default sirve para las miniaturas; el
   *  visor grande explica el porqué, que es lo que un jurado necesita leer. */
  emptyMessage?: string
}) {
  const [hidden, setHidden] = useState(false)

  // Sin imagen (cuadro descartado, nunca procesado, o preview no escrita):
  // explicación explícita en vez de un rectángulo negro que parece un error.
  if (hidden) {
    return (
      <span className="eo-preview eo-preview--empty" style={{ width }}>
        {emptyMessage}
      </span>
    )
  }

  return (
    <span className="eo-preview">
      {/* loading="lazy": una traza puede tener miles de cuadros; sin esto el
          navegador encola miles de pedidos de imagen al montar. */}
      <img src={src} alt={alt} width={width} loading="lazy" onError={() => setHidden(true)} />
      {detections.map((d, i) => {
        const box = d.bbox_norm_xyxy
        if (!box || box.length !== 4) return null
        const [x1, y1, x2, y2] = box
        return (
          <span
            key={i}
            className="eo-preview__box"
            title={`${d.label} ${d.confidence.toFixed(2)}`}
            style={{
              left: `${x1 * 100}%`,
              top: `${y1 * 100}%`,
              width: `${(x2 - x1) * 100}%`,
              height: `${(y2 - y1) * 100}%`,
              borderColor: labelColor(d.label),
            }}
          />
        )
      })}
    </span>
  )
}
