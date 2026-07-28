import { describe, expect, it } from 'vitest'
import { isLive, isRunning, runStatusLabel, runStatusTone, sourceLabel, topologyBadge } from '../runview'

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
  it('two_node → dos equipos (glosario)', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'two_node' } })).toBe('dos equipos')
  })
  it('single_host → un solo equipo (glosario)', () => {
    expect(topologyBadge({ run_descriptor: { topology: 'single_host' } })).toBe('un solo equipo')
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
    expect(runStatusLabel({ status: 'running' })).toBe('En curso')
  })
  it('succeeded es ok', () => {
    expect(runStatusTone({ status: 'succeeded' })).toBe('ok')
    expect(runStatusLabel({ status: 'succeeded' })).toBe('Completada')
  })
  it('failed es error', () => {
    expect(runStatusTone({ status: 'failed' })).toBe('error')
    expect(runStatusLabel({ status: 'failed' })).toBe('Fallida')
  })
  // TERMINAL_STATUSES del backend (runner.py) incluye error y stopped: sin
  // estas dos entradas el 21% del corpus real mostraba "stopped" en inglés.
  it('stopped es una parada deliberada: neutral, no error', () => {
    expect(runStatusTone({ status: 'stopped' })).toBe('neutral')
    expect(runStatusLabel({ status: 'stopped' })).toBe('Detenida')
  })
  it('error es error', () => {
    expect(runStatusTone({ status: 'error' })).toBe('error')
    expect(runStatusLabel({ status: 'error' })).toBe('Con error')
  })
  it('desconocido cae a neutral y muestra el status crudo', () => {
    expect(runStatusTone({ status: 'weird' })).toBe('neutral')
    expect(runStatusLabel({ status: 'weird' })).toBe('weird')
  })
})

describe('sourceLabel', () => {
  it('traduce los tipos de fuente conocidos', () => {
    expect(sourceLabel('oak_d')).toBe('Cámara OAK-D Pro')
    expect(sourceLabel('rtsp')).toBe('Cámara RTSP')
  })
  it('sin dato muestra guion, tipo desconocido cae al codigo crudo', () => {
    expect(sourceLabel(null)).toBe('—')
    expect(sourceLabel('algo_nuevo')).toBe('algo_nuevo')
  })
})
