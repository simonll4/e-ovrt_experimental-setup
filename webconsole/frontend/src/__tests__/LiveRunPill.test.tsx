import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '../test-utils'
import { MemoryRouter } from 'react-router-dom'
import LiveRunPill from '../components/LiveRunPill'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRunsPaged: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPill = () => render(<MemoryRouter><LiveRunPill /></MemoryRouter>)

describe('LiveRunPill', () => {
  it('no renderiza nada si no hay corrida viva', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({ items: [{ run_id: 'r_1', status: 'succeeded' } as any], total: 1 })
    const { container } = renderPill()
    await waitFor(() => expect(vi.mocked(api.listRunsPaged)).toHaveBeenCalled())
    expect(container.textContent).toBe('')
  })

  it('muestra el run vivo con fps y linkea a su detalle', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({ items: [
      { run_id: 'r_9', status: 'running', live: true, fps_effective: 42 } as any,
    ], total: 1 })
    renderPill()
    await waitFor(() => expect(screen.getByText('r_9')).toBeTruthy())
    expect(screen.getByText(/42/)).toBeTruthy()
    expect(screen.getByRole('link').getAttribute('href')).toContain('/runs/r_9')
  })

  it('toma running aunque live no venga', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({ items: [{ run_id: 'r_x', status: 'running' } as any], total: 1 })
    renderPill()
    await waitFor(() => expect(screen.getByText('r_x')).toBeTruthy())
  })
})
