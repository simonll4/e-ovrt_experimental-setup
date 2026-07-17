import { describe, expect, it } from 'vitest'
import { promptStatusTone } from '../promptview'

describe('promptStatusTone', () => {
  it('frozen es ok', () => {
    expect(promptStatusTone('frozen')).toBe('ok')
  })
  it('frozen_pending_review es warn', () => {
    expect(promptStatusTone('frozen_pending_review')).toBe('warn')
  })
  it('exploratory y cualquier otro estado caen a neutral', () => {
    expect(promptStatusTone('exploratory')).toBe('neutral')
    expect(promptStatusTone('weird')).toBe('neutral')
  })
})
