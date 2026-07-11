import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ExperimentDetailPage from '../pages/ExperimentDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperiment: vi.fn(),
  getExperimentAlerts: vi.fn(),
  getExperimentReport: vi.fn(),
}))

function renderPage(id = 'exp_1') {
  return render(
    <MemoryRouter initialEntries={[`/experiments/${id}`]}>
      <Routes>
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('ExperimentDetailPage', () => {
  it('muestra alertas y marca no-temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([{ alert_id: 'al1', condition_id: 'CR-01', severity: 'high' } as any])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: true, resultados: [] } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('al1')).toBeTruthy())
    expect(screen.getByText(/no.?temporal/i)).toBeTruthy() // badge ADR-013
  })

  it('no muestra el badge no-temporal cuando el reporte es temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_2', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_2')
    await waitFor(() => expect(screen.getByText('Sin alertas.')).toBeTruthy())
    expect(screen.queryByText(/no.?temporal/i)).toBeNull()
  })

  it('reporte no consolidado (404) muestra un mensaje sin crashear', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_3', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockRejectedValue(new api.ApiError(404, { detail: 'no encontrado' }))
    renderPage('exp_3')
    await waitFor(() => expect(screen.getByText('Reporte no disponible todavia.')).toBeTruthy())
  })

  it('muestra el nombre de la metrica (campo "name" del backend) en la tabla de resultados', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_4', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [{ name: 't_capture->alert', status: 'not_applicable', cause: 'no_ground_truth' }],
    } as any)
    renderPage('exp_4')
    await waitFor(() => expect(screen.getByText(/t_capture->alert/)).toBeTruthy())
    expect(screen.getByText('not_applicable')).toBeTruthy()
    expect(screen.getByText('no_ground_truth')).toBeTruthy()
  })
})
