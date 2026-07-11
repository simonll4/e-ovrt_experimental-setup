// Gate de integración para Task 5 (spec 44 §5.2): prueba el flujo completo de la UI
// de experimentos — disparo desde ExperimentsPage y lectura de estado/alertas/reporte
// (con detección de fuente no-temporal, ADR-013) en ExperimentDetailPage. La api se
// mockea; no hay backend real involucrado.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ExperimentsPage from '../pages/ExperimentsPage'
import ExperimentDetailPage from '../pages/ExperimentDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperimentManifests: vi.fn(),
  getCurrentExperiment: vi.fn(),
  runExperiment: vi.fn(),
  getExperiment: vi.fn(),
  getExperimentAlerts: vi.fn(),
  getExperimentReport: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

function renderDetail(id = 'exp_g') {
  return render(
    <MemoryRouter initialEntries={[`/experiments/${id}`]}>
      <Routes>
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('spec44c gate: flujo de experimentos por la UI', () => {
  it('ExperimentsPage: lista un manifiesto y dispara runExperiment al hacer click en "Ejecutar experimento"', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([
      { slug: 'gate-slug', experiment_id: null } as any,
    ])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_g' })

    render(
      <MemoryRouter>
        <ExperimentsPage />
      </MemoryRouter>,
    )

    // Esperar a que el manifiesto liste y el <select> quede pre-cargado con el slug.
    await waitFor(() => expect(screen.getAllByText('gate-slug').length).toBeGreaterThan(0))

    fireEvent.click(screen.getByRole('button', { name: /ejecutar experimento/i }))

    await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
    expect(vi.mocked(api.runExperiment)).toHaveBeenCalledWith({ slug: 'gate-slug' })
  })

  it('ExperimentDetailPage: reporte non_temporal:true muestra alertas y el badge no-temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({
      experiment_id: 'exp_g',
      status: 'succeeded',
      ok: true,
    } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([
      { alert_id: 'alert_g1', condition_id: 'CR-01', severity: 'high' } as any,
    ])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: true,
      resultados: [],
    } as any)

    renderDetail()

    await waitFor(() => expect(screen.getByText('alert_g1')).toBeTruthy())
    expect(screen.getByText(/no.?temporal/i)).toBeTruthy()
  })

  it('ExperimentDetailPage: reporte non_temporal:false NO muestra el badge no-temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({
      experiment_id: 'exp_g',
      status: 'succeeded',
      ok: true,
    } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [],
    } as any)

    renderDetail()

    await waitFor(() => expect(screen.getByText('Sin alertas.')).toBeTruthy())
    expect(screen.queryByText(/no.?temporal/i)).toBeNull()
  })
})
