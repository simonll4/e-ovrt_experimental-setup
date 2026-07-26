import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, cleanup } from '@testing-library/react'
import { useServiceHealth } from '../useServiceHealth'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn(),
  getPreflight: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('useServiceHealth', () => {
  it('ambos motores operativos', async () => {
    vi.mocked(api.getTarget).mockResolvedValue({
      service_url: 'x',
      healthy: true,
      ready: true,
      model: null,
    } as any)
    vi.mocked(api.getPreflight).mockResolvedValue({
      ready: true,
      blockers: [],
      media: { service_url: 'x', healthy: true, ready: true },
      control: { service_url: 'y', healthy: true, ready: true },
    } as any)
    const { result } = renderHook(() => useServiceHealth())
    await waitFor(() => expect(result.current.media).toBe('ok'))
    expect(result.current.control).toBe('ok')
  })

  it('el motor de reglas cae cuando control.healthy es false', async () => {
    vi.mocked(api.getTarget).mockResolvedValue({
      service_url: 'x',
      healthy: true,
      ready: true,
      model: null,
    } as any)
    vi.mocked(api.getPreflight).mockResolvedValue({
      ready: false,
      blockers: ['control down'],
      media: { service_url: 'x', healthy: true, ready: true },
      control: { service_url: 'y', healthy: false, ready: false },
    } as any)
    const { result } = renderHook(() => useServiceHealth())
    await waitFor(() => expect(result.current.control).toBe('down'))
    expect(result.current.media).toBe('ok')
  })

  it('el motor de reglas cae cuando el fetch de preflight rechaza', async () => {
    vi.mocked(api.getTarget).mockResolvedValue({
      service_url: 'x',
      healthy: true,
      ready: true,
      model: null,
    } as any)
    vi.mocked(api.getPreflight).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useServiceHealth())
    await waitFor(() => expect(result.current.control).toBe('down'))
    expect(result.current.media).toBe('ok')
  })

  it('el motor de deteccion cae cuando el fetch de target rechaza', async () => {
    vi.mocked(api.getTarget).mockRejectedValue(new Error('boom'))
    vi.mocked(api.getPreflight).mockResolvedValue({
      ready: true,
      blockers: [],
      media: { service_url: 'x', healthy: true, ready: true },
      control: { service_url: 'y', healthy: true, ready: true },
    } as any)
    const { result } = renderHook(() => useServiceHealth())
    await waitFor(() => expect(result.current.media).toBe('down'))
  })
})
