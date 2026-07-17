import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPage = () => render(<MemoryRouter><RunsPage /></MemoryRouter>)

describe('RunsPage', () => {
  it('lista corridas y marca la viva con badge', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_1', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.getByText('vivo').className).toContain('eo-badge--live')
    expect(screen.getByText('OK').className).toContain('eo-badge--ok')
  })

  it('estado vacío cuando no hay corridas', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText('Sin corridas todavía.')).toBeTruthy())
  })

  it('muestra el error con role alert', async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error('boom'))
    renderPage()
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })
})
