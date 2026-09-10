import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook } from '../test-utils'
import { useTraceIndex, useTracePage } from '../api/queries/runs'
import * as api from '../api'
import type { TraceIndex, TracePage } from '../types'

vi.mock('../api', async (original) => ({
  ...(await original<typeof import('../api')>()), getTraceIndex: vi.fn(), getTrace: vi.fn(),
}))
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks() })

describe('Traza al finalizar la corrida', () => {
  it('relee índice y página al terminar aunque el arranque haya quedado vacío en caché', async () => {
    vi.useFakeTimers()
    const totals = { frames: 0, detections: 0, dropped_by_reason: {}, alerts: 0,
      received: null, not_received: null }
    const index: TraceIndex = { media_run_id: 'r', control_run_id: null, topology: null,
      control_error: null, totals, total: 0, frame_index: [], unit_id: [], timestamp_ms: [],
      detections: [], control_state: [], alert: [] }
    const page: TracePage = { media_run_id: 'r', control_run_id: null, topology: null,
      control_error: null, totals, total: 0, page: 1, page_size: 200, frames: [] }
    vi.mocked(api.getTraceIndex).mockResolvedValue(index)
    vi.mocked(api.getTrace).mockResolvedValue(page)
    const { result, rerender } = renderHook(({ live }) => ({
      index: useTraceIndex('r', true, live), page: useTracePage('r', 1, 200, null, true, live),
    }), { initialProps: { live: true } })
    await act(async () => { await vi.advanceTimersByTimeAsync(20) })
    expect(result.current.index.data?.total).toBe(0)
    expect(result.current.page.data?.total).toBe(0)
    vi.mocked(api.getTraceIndex).mockResolvedValue({ ...index, total: 1,
      totals: { ...totals, frames: 1 }, frame_index: [0], unit_id: ['f0'],
      timestamp_ms: [0], detections: [0], control_state: ['unknown'], alert: [0] })
    vi.mocked(api.getTrace).mockResolvedValue({ ...page, total: 1,
      totals: { ...totals, frames: 1 }, frames: [{ frame_index: 0, unit_id: 'f0',
        timestamp_ms: 0, detections: [], control: 'n/d', progress: [], alert: [] }] })
    rerender({ live: false })
    await act(async () => { await vi.advanceTimersByTimeAsync(20) })
    expect(result.current.index.data?.total).toBe(1)
    expect(result.current.page.data?.total).toBe(1)
    expect(api.getTraceIndex).toHaveBeenCalledTimes(2)
    expect(api.getTrace).toHaveBeenCalledTimes(2)
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
    expect(api.getTraceIndex).toHaveBeenCalledTimes(2)
    expect(api.getTrace).toHaveBeenCalledTimes(2)
  })
})
