import { useEffect, useState } from 'react'
import { labelColor } from '../traceview'
import type { TraceDetection } from '../types'
import { Button, Dialog, IconClose, IconExpand } from './ui'

function Cajas({ detections }: { detections: TraceDetection[] }) {
  return (
    <>
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
    </>
  )
}

export default function PreviewWithBoxes({
  src,
  alt,
  detections,
  width = 240,
  emptyMessage = 'sin vista previa',
  zoomable = false,
}: {
  src: string
  alt: string
  detections: TraceDetection[]
  width?: number
  /** Qué decir cuando no hay imagen. El default sirve para las miniaturas; el
   *  visor grande explica el porqué, que es lo que un jurado necesita leer. */
  emptyMessage?: string
  /** Ofrece ampliar la MISMA imagen con sus cajas en un diálogo. Reemplaza al
   *  escalado automático al pasar el mouse, que tapaba lo vecino y no existía
   *  en pantallas táctiles ni para el teclado. */
  zoomable?: boolean
}) {
  const [hidden, setHidden] = useState(false)
  const [ampliada, setAmpliada] = useState(false)

  // Otra imagen, otra oportunidad: un cuadro sin preview no deja a los
  // siguientes marcados como «sin imagen».
  useEffect(() => {
    setHidden(false)
  }, [src])

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
    <>
      <span className="eo-preview">
        {/* loading="lazy": una traza puede tener miles de cuadros; sin esto el
            navegador encola miles de pedidos de imagen al montar. */}
        <img src={src} alt={alt} width={width} loading="lazy" onError={() => setHidden(true)} />
        <Cajas detections={detections} />
      </span>
      {zoomable && (
        <>
          <Button onClick={() => setAmpliada(true)} aria-haspopup="dialog">
            <IconExpand />
            Ampliar
          </Button>
          <Dialog open={ampliada} onClose={() => setAmpliada(false)} label={`Ampliación: ${alt}`} className="eo-zoom">
            {ampliada && (
              <>
                <div className="eo-zoom__head">
                  <h2>{alt}</h2>
                  <Button variant="ghost" className="eo-btn--icon" aria-label="Cerrar ampliación" onClick={() => setAmpliada(false)}>
                    <IconClose />
                  </Button>
                </div>
                <div className="eo-zoom__body">
                  {/* La misma imagen, con su proporción y sus cajas: no se
                      edita ni se reproduce, sólo se agranda. */}
                  <span className="eo-preview">
                    <img src={src} alt="" />
                    <Cajas detections={detections} />
                  </span>
                </div>
              </>
            )}
          </Dialog>
        </>
      )}
    </>
  )
}
