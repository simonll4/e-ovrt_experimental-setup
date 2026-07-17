import { useState } from 'react'
import { labelColor } from '../traceview'
import type { TraceDetection } from '../types'

export default function PreviewWithBoxes({
  src,
  alt,
  detections,
  width = 80,
}: {
  src: string
  alt: string
  detections: TraceDetection[]
  width?: number
}) {
  const [hidden, setHidden] = useState(false)

  if (hidden) return null

  return (
    <span className="eo-preview">
      <img src={src} alt={alt} width={width} onError={() => setHidden(true)} />
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
