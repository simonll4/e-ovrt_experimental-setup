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
  if (topo === 'two_node') return 'two-node'
  if (topo === 'single_host') return 'single-host'
  return null
}

// Distinto de isLive a propósito: acá alcanza con que esté corriendo, incluso un
// running externo (two-node) que NO es suscribible por WS. Lo usan el listado y la
// píldora, que solo linkean; quien decide abrir el WS es el detalle, y ahí manda isLive.
export function isRunning(run: { status: string }): boolean {
  return run.status === 'running'
}

export function runStatusTone(run: { status: string; live?: boolean }): BadgeTone {
  if (isRunning(run)) return 'live'
  if (run.status === 'succeeded') return 'ok'
  if (run.status === 'failed') return 'error'
  return 'neutral'
}

export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'en curso'
  if (run.status === 'succeeded') return 'completada'
  if (run.status === 'failed') return 'fallida'
  return run.status
}
