import { describe, expect, it } from 'vitest'
import { controlTone, controlLabel, controlLabelIsRaw, frameHasActivity, labelColor } from '../traceview'
import { SERIES_COLORS } from '../palette'

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
  it('traduce los cuatro motivos de descarte reales (DropReason del media-plane)', () => {
    expect(controlLabel('dropped:rate_gate')).toBe('límite de tasa')
    expect(controlLabel('dropped:queue_full')).toBe('cola llena')
    expect(controlLabel('dropped:staleness_timeout')).toBe('cuadro vencido')
    expect(controlLabel('dropped:channel_closed')).toBe('canal cerrado')
  })

  it('cae al código crudo para un motivo de descarte fuera del vocabulario conocido', () => {
    expect(controlLabel('dropped:algo_raro')).toBe('algo_raro')
  })

  it('recibido / no recibido / sin dato', () => {
    expect(controlLabel('received')).toBe('recibido')
    expect(controlLabel('not_received')).toBe('no recibido')
    expect(controlLabel('n/d')).toBe('n/d')
  })
})

describe('controlLabelIsRaw', () => {
  it('es true para un motivo de descarte no reconocido', () => {
    expect(controlLabelIsRaw('dropped:algo_raro')).toBe(true)
  })
  it('es false para los motivos de descarte del vocabulario real', () => {
    expect(controlLabelIsRaw('dropped:rate_gate')).toBe(false)
    expect(controlLabelIsRaw('dropped:queue_full')).toBe(false)
    expect(controlLabelIsRaw('dropped:staleness_timeout')).toBe(false)
    expect(controlLabelIsRaw('dropped:channel_closed')).toBe(false)
  })
  it('es false para recibido/no recibido/n-d (no son "dropped")', () => {
    expect(controlLabelIsRaw('received')).toBe(false)
    expect(controlLabelIsRaw('not_received')).toBe(false)
    expect(controlLabelIsRaw('n/d')).toBe(false)
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
