import { describe, expect, it } from 'vitest'
import { applyEvent, initialLiveState } from '../stream'

describe('applyEvent', () => {
  it('acumula métricas con historia acotada', () => {
    let state = initialLiveState()
    for (let i = 0; i < 400; i++) {
      state = applyEvent(state, {
        type: 'metric', unit_id: `u${i}`, fps: i, latency_total_ms: 100,
        detections_count: 1, gpu_memory_mb: 0,
      })
    }
    expect(state.lastMetric?.fps).toBe(399)
    expect(state.fpsHistory.length).toBeLessThanOrEqual(300) // acotada
  })

  it('suma detecciones y acota el tail de errores', () => {
    let state = initialLiveState()
    state = applyEvent(state, { type: 'detection', unit_id: 'u0', count: 3 })
    state = applyEvent(state, { type: 'detection', unit_id: 'u1', count: 2 })
    expect(state.detectionsTotal).toBe(5)
    for (let i = 0; i < 150; i++) {
      state = applyEvent(state, { type: 'error', unit_id: `u${i}`, stage: 'x', message: 'boom' })
    }
    expect(state.errors.length).toBeLessThanOrEqual(100)
  })

  it('registra el estado final', () => {
    const state = applyEvent(initialLiveState(), { type: 'state', status: 'succeeded', error: null })
    expect(state.finalState?.status).toBe('succeeded')
  })
})
