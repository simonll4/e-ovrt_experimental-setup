import type { BadgeTone, TraceFrame } from './types'
import { SERIES_COLORS } from './components/GroupedBars'
import { CONTROL_DROP_REASONS } from './labels'

export function controlTone(control: string): BadgeTone {
  if (control === 'received') return 'ok'
  if (control.startsWith('dropped:')) return 'warn'
  if (control === 'not_received') return 'error'
  return 'neutral'
}

export function controlLabel(control: string): string {
  if (control.startsWith('dropped:')) {
    const reason = control.slice('dropped:'.length)
    return CONTROL_DROP_REASONS[reason] ?? reason
  }
  if (control === 'received') return 'recibido'
  if (control === 'not_received') return 'no recibido'
  return control
}

export function labelColor(label: string): string {
  let hash = 0
  for (let i = 0; i < label.length; i++) {
    hash += label.charCodeAt(i)
  }
  return SERIES_COLORS[hash % SERIES_COLORS.length]
}

export function frameHasActivity(f: TraceFrame): boolean {
  return (
    (f.detections?.length ?? 0) > 0 ||
    f.control.startsWith('dropped:') ||
    f.control === 'not_received' ||
    f.progress.length > 0 ||
    f.alert.length > 0 ||
    (f.active_patterns?.length ?? 0) > 0
  )
}
