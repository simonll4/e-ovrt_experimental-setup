import { describe, expect, it } from 'vitest'
import {
  isNonTemporal,
  alertSeverityTone,
  experimentStatusLabel,
  experimentStatusTone,
} from '../experimentview'

describe('isNonTemporal', () => {
  it('true cuando el reporte marca non_temporal', () => {
    expect(isNonTemporal({ non_temporal: true } as any)).toBe(true)
    expect(isNonTemporal({ non_temporal: false } as any)).toBe(false)
    expect(isNonTemporal(null)).toBe(false)
  })
})
describe('alertSeverityTone', () => {
  it('high error, medium warn, otro ok', () => {
    expect(alertSeverityTone('high')).toBe('error')
    expect(alertSeverityTone('medium')).toBe('warn')
    expect(alertSeverityTone('low')).toBe('ok')
  })
})
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('corriendo')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallo')
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
  it('estado desconocido cae en el default neutral', () => {
    expect(experimentStatusTone({ status: 'queued' } as any)).toBe('neutral')
  })
})
