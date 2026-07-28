import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSidebarCounts } from '../useSidebarCounts'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  getExperimentManifests: vi.fn(),
  listPromptSets: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

describe('useSidebarCounts', () => {
  it('cuenta las corridas en curso, los manifiestos y los conjuntos de prompts', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r1', status: 'running' } as any,
      { run_id: 'r2', status: 'succeeded' } as any,
    ])
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any, { slug: 'b' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([{ id: 'p1' } as any])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.runs).toBe(1))
    expect(result.current.experiments).toBe(2)
    expect(result.current.promptSets).toBe(1)
  })

  it('si un fetch falla, ese contador queda en null sin romper los demas', async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error('x'))
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.experiments).toBe(1))
    expect(result.current.runs).toBeNull()
  })
})
