import { describe, expect, it } from 'vitest'
import { controlTone, controlLabel, frameHasActivity, labelColor } from '../traceview'
import { SERIES_COLORS } from '../components/GroupedBars'

describe('controlTone', () => {
  it('received ok, dropped warn, not_received error, n/d neutral', () => {
    expect(controlTone('received')).toBe('ok')
    expect(controlTone('dropped:rate_gate')).toBe('warn')
    expect(controlTone('dropped:queue_full')).toBe('warn')
    expect(controlTone('not_received')).toBe('error')
    expect(controlTone('n/d')).toBe('neutral')
  })
})

describe('controlLabel', () => {
  it('extrae el reason del dropped', () => {
    expect(controlLabel('dropped:rate_gate')).toBe('rate_gate')
    expect(controlLabel('received')).toBe('recibido')
    expect(controlLabel('not_received')).toBe('no recibido')
    expect(controlLabel('n/d')).toBe('n/d')
  })
})

describe('frameHasActivity', () => {
  const base = { frame_index: 0, unit_id: 'u0', timestamp_ms: null, detections: [], control: 'received', progress: [], alert: [], active_patterns: [] }
  it('sin nada es inactivo', () => expect(frameHasActivity(base as any)).toBe(false))
  it('deteccion, descarte, progreso o alerta activan', () => {
    expect(frameHasActivity({ ...base, detections: [{ label: 'p', confidence: 1 }] } as any)).toBe(true)
    expect(frameHasActivity({ ...base, control: 'dropped:rate_gate' } as any)).toBe(true)
    expect(frameHasActivity({ ...base, progress: [{ condition_id: 'CR-01', progress: 0.1 }] } as any)).toBe(true)
    expect(frameHasActivity({ ...base, alert: [{ condition_id: 'CR-01', severity: 'high' }] } as any)).toBe(true)
  })
  it('un frame intermedio (sin alert/progress propios) con active_patterns tambien activa', () => {
    // Es exactamente el caso del bug: frame_000456, sin evento propio, pero
    // con el riesgo confirmado y todavia abierto.
    expect(frameHasActivity({
      ...base,
      active_patterns: [{ pattern_id: 'CR-01', condition_id: 'CR-01', severity: 'high', subject_key: 'k1' }],
    } as any)).toBe(true)
  })
})

describe('labelColor', () => {
  it('es determinista: mismo label, mismo color siempre', () => {
    expect(labelColor('person')).toBe(labelColor('person'))
    expect(labelColor('helmet')).toBe(labelColor('helmet'))
  })

  it('pertenece a la paleta SERIES_COLORS', () => {
    expect(SERIES_COLORS).toContain(labelColor('person'))
    expect(SERIES_COLORS).toContain(labelColor('bare_head'))
    expect(SERIES_COLORS).toContain(labelColor('vest'))
  })
})
