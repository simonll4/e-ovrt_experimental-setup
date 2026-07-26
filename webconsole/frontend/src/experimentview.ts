import type { BadgeTone, ExperimentReport, ExperimentRunState } from './types'

export function isNonTemporal(report: ExperimentReport | null): boolean {
  return report?.non_temporal === true
}

export function alertSeverityTone(severity: string): BadgeTone {
  if (severity === 'high') return 'error'
  if (severity === 'medium') return 'warn'
  return 'ok'
}

export function experimentStatusLabel(state: ExperimentRunState | null): string {
  if (state === null) return '—'
  if (state.status === 'running') return 'corriendo'
  if (state.status === 'succeeded' || state.ok === true) return 'OK'
  if (state.status === 'failed') return 'fallo'
  return state.status
}

export function experimentStatusTone(state: ExperimentRunState | null): BadgeTone {
  if (state === null) return 'neutral'
  if (state.status === 'running') return 'live'
  if (state.status === 'succeeded' || state.ok === true) return 'ok'
  if (state.status === 'failed') return 'error'
  return 'neutral'
}

/** Segundos activos de un patron de riesgo, a partir de `activeMs` (bloque
 *  `patterns[].active_ms` de GET /api/control/current). `active_ms` lo
 *  calcula el control-plane con su reloj monotonico propio contra el hito de
 *  primera evidencia del episodio -- NO se calcula aca contra `since_timestamp_ms`:
 *  ese campo es tiempo de FUENTE/frame (relativo al archivo en corridas
 *  video_file, p.ej. 0.0 en la primera unidad) y usarlo con el reloj de
 *  pared del cliente mostraba "hace 1785005982s" en un humo real. `null` si
 *  `active_ms` no vino (sin `first_evidence_monotonic_ms` en el motor).
 *  Nunca negativo aunque llegue algo raro: el motor ya clampea, esto es
 *  defensa adicional del lado del cliente. */
export function patternActiveSeconds(activeMs: number | null | undefined): number | null {
  if (activeMs === null || activeMs === undefined) return null
  return Math.max(0, Math.floor(activeMs / 1000))
}
