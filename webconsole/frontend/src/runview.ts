import type { BadgeTone } from './types'

export function isLive(run: { status: string; live?: boolean }): boolean {
  // live=true solo lo emite el servicio para SU run activo en memoria — el único
  // suscribible por WS. Un running externo (two-node) con WS abierto entra en
  // reconnect-loop infinito (spec 2026-07-06 §3.4).
  return run.status === 'running' && run.live === true
}

export function topologyBadge(summary: Record<string, unknown> | undefined): string | null {
  const desc = summary?.run_descriptor as Record<string, unknown> | undefined
  const topo = desc?.topology
  if (topo === 'two_node') return 'dos equipos'
  if (topo === 'single_host') return 'un solo equipo'
  return null
}

// Distinto de isLive a propósito: acá alcanza con que esté corriendo, incluso un
// running externo (two-node) que NO es suscribible por WS. Lo usan el listado y la
// píldora, que solo linkean; quien decide abrir el WS es el detalle, y ahí manda isLive.
export function isRunning(run: { status: string }): boolean {
  return run.status === 'running'
}

// Vocabulario terminal del backend (runner.py: TERMINAL_STATUSES):
// succeeded / failed / error / stopped. `stopped` es una parada deliberada del
// operador, NO un fallo — por eso tono neutral y no error.
export function runStatusTone(run: { status: string; live?: boolean }): BadgeTone {
  if (isRunning(run)) return 'live'
  if (run.status === 'succeeded') return 'ok'
  if (run.status === 'failed') return 'error'
  if (run.status === 'error') return 'error'
  if (run.status === 'stopped') return 'neutral'
  return 'neutral'
}

export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'en curso'
  if (run.status === 'succeeded') return 'completada'
  if (run.status === 'failed') return 'fallida'
  if (run.status === 'error') return 'con error'
  if (run.status === 'stopped') return 'detenida'
  return run.status
}

// Traduce `row.source_type` a la etiqueta legible del prototipo. Vocabulario real
// medido en proto-ref-02 §0.1: image_folder, video_file, rtsp, oak_d. Un tipo
// desconocido cae al código crudo en vez de ocultar el dato (ver §1.2, columna Fuente).
const SOURCE_LABELS: Record<string, string> = {
  image_folder: 'Carpeta de imágenes',
  video_file: 'Archivo de video',
  rtsp: 'Cámara RTSP',
  oak_d: 'Cámara OAK-D Pro',
}

export function sourceLabel(sourceType: string | null | undefined): string {
  if (!sourceType) return '—'
  return SOURCE_LABELS[sourceType] ?? sourceType
}
