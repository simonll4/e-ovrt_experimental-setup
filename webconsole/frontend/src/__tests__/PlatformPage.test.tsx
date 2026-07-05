import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PlatformPage from '../pages/PlatformPage'
import { activateInstance, getInstances } from '../api'
import type { PlatformInstance } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getInstances: vi.fn(),
  activateInstance: vi.fn(),
  stopPlatform: vi.fn(),
}))

const FLEET: PlatformInstance[] = [
  { name: 'mp-mock', model_ref: 'mock', state: 'exited', ready: false, is_target: false },
  { name: 'mp-gdino-tiny', model_ref: 'grounding-dino/gdino-tiny', state: 'absent', ready: false, is_target: false },
]

const FLEET_ACTIVE: PlatformInstance[] = [
  { ...FLEET[0], state: 'running', ready: true, is_target: true },
  FLEET[1],
]

beforeEach(() => vi.clearAllMocks())

describe('PlatformPage', () => {
  it('lista el fleet y activa una instancia', async () => {
    vi.mocked(getInstances)
      .mockResolvedValueOnce(FLEET)         // carga inicial
      .mockResolvedValue(FLEET_ACTIVE)      // refresh post-activate
    vi.mocked(activateInstance).mockResolvedValue({ target: 'mp-mock', model_ref: 'mock' })

    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText('mp-mock')).toBeTruthy())

    fireEvent.click(screen.getAllByText('Activar')[0])

    await waitFor(() => expect(activateInstance).toHaveBeenCalledWith('mp-mock'))
    await waitFor(() => expect(screen.getByText('TARGET')).toBeTruthy())
  })

  it('409 muestra el mensaje de run activo', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET)
    const { ApiError } = await import('../api')
    vi.mocked(activateInstance).mockRejectedValue(
      new ApiError(409, { detail: 'Hay un run activo en el target actual', run_id: 'run_x' }),
    )
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText('mp-mock')).toBeTruthy())
    fireEvent.click(screen.getAllByText('Activar')[0])
    await waitFor(() => expect(screen.getByText(/run activo/i)).toBeTruthy())
  })

  it('501 muestra el hint de orquestación no habilitada', async () => {
    const { ApiError } = await import('../api')
    vi.mocked(getInstances).mockRejectedValue(new ApiError(501, { detail: 'x' }))
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText(/no habilitada/i)).toBeTruthy())
  })
})
