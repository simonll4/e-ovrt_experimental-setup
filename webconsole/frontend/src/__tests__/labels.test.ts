import { describe, expect, it } from 'vitest'
import {
  applicabilityLabel,
  APPLICABILITY_CAUSE,
  APPLICABILITY_STATUS,
  conditionLabel,
  CONDITION_NAMES,
  CONTROL_DROP_REASONS,
} from '../labels'

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

  it('trae exactamente el vocabulario real de DropReason del media-plane', () => {
    // contracts/dropped_unit.py: Literal["rate_gate","queue_full","staleness_timeout","channel_closed"]
    expect(Object.keys(CONTROL_DROP_REASONS).sort()).toEqual([
      'channel_closed',
      'queue_full',
      'rate_gate',
      'staleness_timeout',
    ])
  })

  it('trae traducciones al castellano para los cuatro motivos', () => {
    expect(CONTROL_DROP_REASONS.rate_gate).toBe('límite de tasa')
    expect(CONTROL_DROP_REASONS.queue_full).toBe('cola llena')
    expect(CONTROL_DROP_REASONS.staleness_timeout).toBe('cuadro vencido')
    expect(CONTROL_DROP_REASONS.channel_closed).toBe('canal cerrado')
  })

  it('no inventa motivos que no existen en el sistema', () => {
    expect(CONTROL_DROP_REASONS.overload).toBeUndefined()
  })
})

describe('applicabilityLabel', () => {
  it('traduce un código conocido usando el diccionario dado', () => {
    expect(applicabilityLabel('not_applicable', APPLICABILITY_STATUS)).toBe('no aplicable')
    expect(applicabilityLabel('non_temporal_source', APPLICABILITY_CAUSE)).toBe('fuente no temporal')
  })

  it('cae al código crudo si no hay traducción mapeada', () => {
    expect(applicabilityLabel('algo_desconocido', APPLICABILITY_STATUS)).toBe('algo_desconocido')
  })
})
