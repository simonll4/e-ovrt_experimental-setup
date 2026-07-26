import { describe, expect, it } from 'vitest'
import {
  isNonTemporal,
  alertSeverityTone,
  experimentStatusLabel,
  experimentStatusTone,
  patternActiveSeconds,
} from '../experimentview'

describe('isNonTemporal', () => {
  it('true cuando el reporte marca non_temporal', () => {
    expect(isNonTemporal({ non_temporal: true } as any)).toBe(true)
    expect(isNonTemporal({ non_temporal: false } as any)).toBe(false)
    expect(isNonTemporal(null)).toBe(false)
  })
})
describe('alertSeverityTone', () => {
  it('high alert, medium warn, otro ok', () => {
    expect(alertSeverityTone('high')).toBe('alert')
    expect(alertSeverityTone('medium')).toBe('warn')
    expect(alertSeverityTone('low')).toBe('ok')
  })
})
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('en curso')
    expect(experimentStatusLabel({ status: 'succeeded' } as any)).toBe('completada')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallida')
    expect(experimentStatusLabel({ status: 'error' } as any)).toBe('con error')
    expect(experimentStatusLabel({ status: 'stopped' } as any)).toBe('detenida')
    expect(experimentStatusLabel(null)).toBe('—')
  })
})
describe('experimentStatusTone', () => {
  it('null es neutral', () => {
    expect(experimentStatusTone(null)).toBe('neutral')
  })
  it('running es live', () => {
    expect(experimentStatusTone({ status: 'running' } as any)).toBe('live')
  })
  it('succeeded es ok', () => {
    expect(experimentStatusTone({ status: 'succeeded' } as any)).toBe('ok')
  })
  it('ok===true es ok aunque el status no sea succeeded (y no sea running)', () => {
    expect(experimentStatusTone({ status: 'queued', ok: true } as any)).toBe('ok')
  })
  it('failed es error', () => {
    expect(experimentStatusTone({ status: 'failed' } as any)).toBe('error')
  })
  it('error es error', () => {
    expect(experimentStatusTone({ status: 'error' } as any)).toBe('error')
  })
  it('stopped (parada deliberada) es neutral, no error', () => {
    expect(experimentStatusTone({ status: 'stopped' } as any)).toBe('neutral')
  })
  it('estado desconocido cae en el default neutral', () => {
    expect(experimentStatusTone({ status: 'queued' } as any)).toBe('neutral')
  })
})
describe('patternActiveSeconds', () => {
  // active_ms lo calcula el control-plane con su propio reloj monotonico
  // (mismo que alert_registered_ms), NO con since_timestamp_ms contra el
  // reloj del cliente: since_timestamp_ms es tiempo de FUENTE/frame y en
  // corridas video_file puede ser relativo al archivo (0.0 en la primera
  // unidad) -- usarlo con Date.now() del cliente producia "hace
  // 1785005982s" en un humo real (control-plane doc
  // .superpowers-report-patterns-live.md). active_ms ya viene en ms
  // transcurridos reales; esta funcion solo lo redondea a segundos.
  it('convierte active_ms a segundos enteros', () => {
    expect(patternActiveSeconds(12_345)).toBe(12)
  })
  it('null cuando active_ms viene null (sin first_evidence_monotonic_ms)', () => {
    expect(patternActiveSeconds(null)).toBeNull()
  })
  it('null cuando active_ms viene undefined', () => {
    expect(patternActiveSeconds(undefined)).toBeNull()
  })
  it('nunca negativo: el motor ya clampea, pero el cliente no confia ciegamente', () => {
    expect(patternActiveSeconds(-5)).toBe(0)
  })
})
