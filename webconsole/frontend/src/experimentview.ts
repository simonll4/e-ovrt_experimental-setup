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
