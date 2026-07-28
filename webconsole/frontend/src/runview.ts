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

// Capitalizadas porque sus dos consumidores son chips de estado, y así las muestra
// el prototipo. Un código desconocido cae crudo en vez de inventarle traducción.
export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'En curso'
  if (run.status === 'succeeded') return 'Completada'
  if (run.status === 'failed') return 'Fallida'
  if (run.status === 'error') return 'Con error'
  if (run.status === 'stopped') return 'Detenida'
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

// El run_id es determinista (run_YYYYMMDD_HHMMSS_...): sirve de respaldo cuando la
// fila no vino hidratada. El BFF solo hidrata las primeras corridas, así que un
// listado largo mezcla filas con `started_at` y filas sin él.
export function parseRunIdDate(runId: string): Date | null {
  const m = runId.match(/^run_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/)
  if (!m) return null
  const [, y, mo, d, h, mi, s] = m
  return new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s))
}

/**
 * Instante de creación en milisegundos, o null si no se puede saber.
 *
 * Normalizar a número es obligatorio antes de ordenar: comparados como texto,
 * `"run_2026…"` queda por encima de `"2026-07-25T…"` —empieza con 'r'— y las
 * corridas más nuevas terminan enterradas en la última página.
 */
export function createdAtMs(run: { run_id: string; started_at?: string | null }): number | null {
  if (run.started_at) {
    const t = new Date(run.started_at).getTime()
    if (Number.isFinite(t)) return t
  }
  return parseRunIdDate(run.run_id)?.getTime() ?? null
}

/** Antigüedad legible. `now` es inyectable para que los tests no dependan del reloj. */
export function hace(
  run: { run_id: string; started_at?: string | null },
  now: number = Date.now(),
): string {
  const ms = createdAtMs(run)
  if (ms == null) return '—'
  const min = Math.floor((now - ms) / 60000)
  if (min < 1) return 'recién'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `hace ${h} h`
  return `hace ${Math.floor(h / 24)} d`
}
