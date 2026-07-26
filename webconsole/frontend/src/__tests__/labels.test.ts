import { describe, expect, it } from 'vitest'
import { conditionLabel, CONDITION_NAMES, CONTROL_DROP_REASONS } from '../labels'

describe('conditionLabel', () => {
  it('agrega el nombre legible a un código de condición conocido', () => {
    expect(conditionLabel('CR-01')).toBe('CR-01 — Presencia de persona sin casco')
    expect(conditionLabel('CR-02')).toBe('CR-02 — Presencia de persona sin chaleco')
  })

  it('cae al código crudo si no hay nombre mapeado (no inventa uno)', () => {
    expect(conditionLabel('CR-99')).toBe('CR-99')
  })
})

describe('CONDITION_NAMES / CONTROL_DROP_REASONS', () => {
  it('trae los nombres de las dos condiciones vigentes', () => {
    expect(Object.keys(CONDITION_NAMES).sort()).toEqual(['CR-01', 'CR-02'])
  })

  it('trae traducciones para los motivos de descarte conocidos', () => {
    expect(CONTROL_DROP_REASONS.rate_gate).toBe('límite de tasa')
    expect(CONTROL_DROP_REASONS.overload).toBe('sobrecarga')
  })
})
