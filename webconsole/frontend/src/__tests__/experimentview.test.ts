import { describe, expect, it } from 'vitest'
import { isNonTemporal, alertSeverityColor, experimentStatusLabel } from '../experimentview'

describe('isNonTemporal', () => {
  it('true cuando el reporte marca non_temporal', () => {
    expect(isNonTemporal({ non_temporal: true } as any)).toBe(true)
    expect(isNonTemporal({ non_temporal: false } as any)).toBe(false)
    expect(isNonTemporal(null)).toBe(false)
  })
})
describe('alertSeverityColor', () => {
  it('high rojo, medium ambar, otro verde', () => {
    expect(alertSeverityColor('high')).toBe('#b00')
    expect(alertSeverityColor('medium')).toBe('#c80')
    expect(alertSeverityColor('low')).toBe('#080')
  })
})
describe('experimentStatusLabel', () => {
  it('mapea estados', () => {
    expect(experimentStatusLabel({ status: 'running' } as any)).toBe('corriendo')
    expect(experimentStatusLabel({ status: 'failed' } as any)).toBe('fallo')
    expect(experimentStatusLabel(null)).toBe('—')
  })
})
