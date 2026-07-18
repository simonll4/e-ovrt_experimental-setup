import { useEffect, useRef } from 'react'
import { labelColor } from '../traceview'
import type { PreviewFrameHeader } from '../types'
import Badge from './ui/Badge'

interface Props {
  frameUrl: string | null
  header: PreviewFrameHeader | null
  connected: boolean
  fps: number
  mode: 'raw' | 'detect'
}

const DEFAULT_ASPECT = 16 / 9

function drawFrame(
  canvas: HTMLCanvasElement,
  img: HTMLImageElement,
  header: PreviewFrameHeader | null,
) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const width = header?.width ?? img.naturalWidth
  const height = header?.height ?? img.naturalHeight
  canvas.width = width
  canvas.height = height
  ctx.clearRect(0, 0, width, height)
  ctx.drawImage(img, 0, 0, width, height)

  for (const det of header?.detections ?? []) {
    const [x1, y1, x2, y2] = det.bbox_norm_xyxy
    const bx = x1 * width
    const by = y1 * height
    const bw = (x2 - x1) * width
    const bh = (y2 - y1) * height
    const color = labelColor(det.label)

    ctx.strokeStyle = color
    ctx.lineWidth = Math.max(2, width / 320)
    ctx.strokeRect(bx, by, bw, bh)

    const text = `${det.label} ${det.score.toFixed(2)}`
    ctx.font = `${Math.max(12, Math.round(width / 60))}px sans-serif`
    const textWidth = ctx.measureText(text).width
    const labelHeight = Math.max(16, Math.round(width / 45))
    const labelY = Math.max(0, by - labelHeight)
    ctx.fillStyle = color
    ctx.fillRect(bx, labelY, textWidth + 8, labelHeight)
    ctx.fillStyle = '#0a0a0a'
    ctx.fillText(text, bx + 4, labelY + labelHeight - 4)
  }
}

/**
 * Viewer en vivo de la ventana Cámaras: pinta cada frame en un <canvas> de una
 * sola vez (decodificado completo + cajas), sin el destello del <img src=...>
 * swap frame a frame. Un frame que termina de decodificar fuera de orden (llega
 * tarde respecto de uno más nuevo) se descarta.
 */
export default function LiveViewer({ frameUrl, header, connected, fps, mode }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const generationRef = useRef(0)

  useEffect(() => {
    if (!frameUrl) return
    const canvas = canvasRef.current
    if (!canvas) return
    const generation = ++generationRef.current
    const img = new Image()
    img.onload = () => {
      if (generation !== generationRef.current) return
      drawFrame(canvas, img, header)
    }
    img.src = frameUrl
  }, [frameUrl, header])

  const aspect = header ? header.width / header.height : DEFAULT_ASPECT

  return (
    <div className="eo-live-viewer" style={{ aspectRatio: `${aspect}` }}>
      <canvas ref={canvasRef} className="eo-live-viewer__canvas" />
      {!frameUrl && <span className="eo-live-viewer__empty">sin señal</span>}
      <div className="eo-live-viewer__overlay">
        <Badge tone={connected ? 'live' : 'neutral'}>{connected ? 'conectado' : 'desconectado'}</Badge>
        <span>{fps} fps</span>
        {header && (
          <span>
            {header.width}×{header.height}
          </span>
        )}
        <span>modo: {header?.mode ?? mode}</span>
      </div>
    </div>
  )
}
