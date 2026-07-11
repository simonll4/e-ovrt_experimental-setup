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
