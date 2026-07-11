import type { ExperimentReport, ExperimentRunState } from './types'

export function isNonTemporal(report: ExperimentReport | null): boolean {
  return report?.non_temporal === true
}

export function alertSeverityColor(severity: string): string {
  if (severity === 'high') return '#b00'
  if (severity === 'medium') return '#c80'
  return '#080'
}

export function experimentStatusLabel(state: ExperimentRunState | null): string {
  if (state === null) return '—'
  if (state.status === 'running') return 'corriendo'
  if (state.status === 'succeeded' || state.ok === true) return 'OK'
  if (state.status === 'failed') return 'fallo'
  return state.status
}
