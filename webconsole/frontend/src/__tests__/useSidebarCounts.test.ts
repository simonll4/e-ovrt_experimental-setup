import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '../test-utils'
import { useSidebarCounts } from '../api/queries/sidebar'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRunsPaged: vi.fn(),
  getExperimentManifests: vi.fn(),
  listPromptSets: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

describe('useSidebarCounts', () => {
  // El contador sale de `X-Total-Count`, no de contar filas: con el listado
  // paginado, contar en el cliente daría las corridas en curso de la página.
  it('cuenta las corridas en curso, los manifiestos y los conjuntos de prompts', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({
      items: [{ run_id: 'r1', status: 'running' }],
      total: 1,
    } as never)
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any, { slug: 'b' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([{ id: 'p1' } as any])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.runs).toBe(1))
    expect(result.current.experiments).toBe(2)
    expect(result.current.promptSets).toBe(1)
  })

  it('informa el total del servidor aunque la página traiga menos filas', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({
      items: [{ run_id: 'r1', status: 'running' }],
      total: 7,
    } as never)
    vi.mocked(api.getExperimentManifests).mockResolvedValue([])
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.runs).toBe(7))
  })

  it('si un fetch falla, ese contador queda en null sin romper los demas', async () => {
    vi.mocked(api.listRunsPaged).mockRejectedValue(new Error('x'))
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.experiments).toBe(1))
    expect(result.current.runs).toBeNull()
  })
})
