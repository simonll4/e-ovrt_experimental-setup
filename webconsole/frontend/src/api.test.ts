import { describe, test, expect, vi } from 'vitest'
import { deleteRun } from './api'

describe('deleteRun', () => {
  test('deleteRun hace DELETE al endpoint del run', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 204 }),
    )
    const result = await deleteRun('run-1')
    expect(spy).toHaveBeenCalledWith(
      '/api/runs/run-1',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(result).toBeUndefined()
    spy.mockRestore()
  })
})
