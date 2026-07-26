import { describe, expect, it } from 'vitest'
import { isLive, isRunning, runStatusLabel, runStatusTone, topologyBadge } from '../runview'

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

describe('isRunning', () => {
  it('true para cualquier running, incluso sin live (two-node externo)', () => {
    expect(isRunning({ status: 'running' })).toBe(true)
  })
  it('false para terminados', () => {
    expect(isRunning({ status: 'succeeded' })).toBe(false)
    expect(isRunning({ status: 'failed' })).toBe(false)
  })
  it('no es isLive: isRunning no exige live=true', () => {
    const externo = { status: 'running' as const }
    expect(isRunning(externo)).toBe(true)
    expect(isLive(externo)).toBe(false)
  })
})

describe('runStatusTone / runStatusLabel', () => {
  it('running es live', () => {
    expect(runStatusTone({ status: 'running' })).toBe('live')
    expect(runStatusLabel({ status: 'running' })).toBe('en curso')
  })
  it('succeeded es ok', () => {
    expect(runStatusTone({ status: 'succeeded' })).toBe('ok')
    expect(runStatusLabel({ status: 'succeeded' })).toBe('completada')
  })
  it('failed es error', () => {
    expect(runStatusTone({ status: 'failed' })).toBe('error')
    expect(runStatusLabel({ status: 'failed' })).toBe('fallida')
  })
  it('desconocido cae a neutral y muestra el status crudo', () => {
    expect(runStatusTone({ status: 'weird' })).toBe('neutral')
    expect(runStatusLabel({ status: 'weird' })).toBe('weird')
  })
})
