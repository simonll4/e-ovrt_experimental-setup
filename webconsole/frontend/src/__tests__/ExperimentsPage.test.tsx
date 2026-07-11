import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ExperimentsPage from '../pages/ExperimentsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperimentManifests: vi.fn(),
  getCurrentExperiment: vi.fn(),
  runExperiment: vi.fn(),
}))
beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('ExperimentsPage', () => {
  it('lista manifiestos y dispara un experimento', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1', experiment_id: null } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_9' })
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    fireEvent.click(screen.getByRole('button', { name: /ejecutar/i }))
    await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
    expect(vi.mocked(api.runExperiment)).toHaveBeenCalledWith({ slug: 'd1' })
  })

  it('muestra 409 con el experimento activo', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    const err = new api.ApiError(409, { active_experiment_id: 'exp_prev' })
    vi.mocked(api.runExperiment).mockRejectedValue(err)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    fireEvent.click(screen.getByRole('button', { name: /ejecutar/i }))
    await waitFor(() => expect(screen.getByText(/exp_prev/)).toBeTruthy())
  })
})
