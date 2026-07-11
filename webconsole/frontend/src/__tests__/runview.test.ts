import { describe, expect, it } from 'vitest'
import { isLive, topologyBadge } from '../runview'

describe('isLive', () => {
  it('true solo cuando running y live', () => {
    expect(isLive({ status: 'running', live: true })).toBe(true)
  })
  it('false para running externo (two-node): evita el reconnect-loop del WS', () => {
    expect(isLive({ status: 'running', live: false })).toBe(false)
    expect(isLive({ status: 'running' })).toBe(false) // live ausente = servicio viejo
  })
  it('false cuando no está running', () => {
    expect(isLive({ status: 'succeeded', live: true })).toBe(false)
  })
})

describe('topologyBadge', () => {
  it('two_node → two-node', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'two_node' } })).toBe('two-node')
  })
  it('single_host → single-host', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'single_host' } })).toBe('single-host')
  })
  it('sin descriptor → null', () => {
    expect(topologyBadge({})).toBeNull()
    expect(topologyBadge(undefined)).toBeNull()
  })
})
