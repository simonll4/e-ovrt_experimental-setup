import { afterEach, expect, it, vi } from 'vitest'
import { act, cleanup, renderHook } from '../test-utils'
import { useExperimentAlerts, useExperimentReport } from '../api/queries/experiments'
import * as api from '../api'

vi.mock('../api', async (original) => ({
  ...(await original<typeof import('../api')>()),
  getExperimentAlerts: vi.fn(), getExperimentReport: vi.fn(),
}))
afterEach(() => { cleanup(); vi.useRealTimers(); vi.clearAllMocks() })

it('relee alertas y reporte al finalizar, incluso después de un 404 de consolidación pendiente', async () => {
  vi.useFakeTimers()
  vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
  vi.mocked(api.getExperimentReport).mockRejectedValue(new api.ApiError(404, { detail: 'Pendiente' }))
  const { result, rerender } = renderHook(({ live }) => {
    const alerts = useExperimentAlerts('e', true, live)
    const report = useExperimentReport('e', true, live)
    // Leer durante render, igual que la pantalla: Query registra qué propiedades observa.
    return { alerts: { data: alerts.data }, report: { data: report.data, isError: report.isError } }
  }, { initialProps: { live: true } })
  await act(async () => { await vi.advanceTimersByTimeAsync(20) })
  expect(result.current.report.isError).toBe(true)
  expect(result.current.alerts.data).toEqual([])
  vi.mocked(api.getExperimentAlerts).mockResolvedValue([{ alert_id: 'a', condition_id: 'CR-01', severity: 'high' }])
  vi.mocked(api.getExperimentReport).mockResolvedValue({
    non_temporal: false, resultados: [], distribucion: { counts: { delivered: 1 } },
    distribucion_por_alerta: { a: { alert_id: 'a', outcome: 'delivered' } },
  })
  rerender({ live: false })
  await act(async () => { await vi.advanceTimersByTimeAsync(20) })
  expect(result.current.report.isError).toBe(false)
  expect(result.current.alerts.data).toHaveLength(1)
  expect(result.current.report.data?.distribucion_por_alerta).toMatchObject({ a: { outcome: 'delivered' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
  expect(api.getExperimentAlerts).toHaveBeenCalledTimes(2)
  expect(api.getExperimentReport).toHaveBeenCalledTimes(2)
})
