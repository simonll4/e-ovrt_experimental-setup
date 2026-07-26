import { describe, test, it, expect, vi } from 'vitest'
import { deleteRun, getMasters, generateClip, masterMediaUrl, clipMediaUrl } from './api'

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

describe('clips api', () => {
  it('getMasters pega al endpoint correcto', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ masters: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await getMasters()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/clips/masters')
  })

  it('generateClip postea las marcas', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ clip_id: 'a_p1_c01', warnings: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await generateClip({ master: 'P1-a-take1.mp4', marks: [6, 12] })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/clips')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body).marks).toEqual([6, 12])
  })

  it('media urls escapan el nombre', () => {
    expect(masterMediaUrl('P1-a-take1.mp4')).toBe('/api/clips/media/master/P1-a-take1.mp4')
    expect(clipMediaUrl('a_p1_c01')).toBe('/api/clips/media/clip/a_p1_c01')
  })
})
