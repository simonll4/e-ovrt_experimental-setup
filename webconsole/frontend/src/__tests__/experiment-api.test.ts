import { afterEach, describe, expect, it, vi } from 'vitest'
import { getExperiment, runExperiment, getCurrentExperiment, getExperimentAlerts } from '../api'

afterEach(() => vi.unstubAllGlobals())

function stub(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })))
}

describe('experiment api', () => {
  it('runExperiment postea a /api/experiments/run y devuelve el id', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ experiment_id: 'exp_1' }), { status: 202 }))
    vi.stubGlobal('fetch', fetchMock)
    const r = await runExperiment({ slug: 'd1' })
    expect(r.experiment_id).toBe('exp_1')
    const [url, init] = (fetchMock.mock.calls as Array<unknown[]>)[0]
    expect(url).toBe('/api/experiments/run')
    expect((init as RequestInit).method).toBe('POST')
  })
  it('getExperiment encodea el id en la URL', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ experiment_id: 'a b', status: 'succeeded' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await getExperiment('a b')
    expect((fetchMock.mock.calls as Array<unknown[]>)[0][0]).toBe('/api/experiments/a%20b')
  })
  it('getCurrentExperiment devuelve null en 404', async () => {
    stub(404, { detail: 'no hay run activo' })
    expect(await getCurrentExperiment()).toBeNull()
  })
  it('getExperimentAlerts devuelve la lista', async () => {
    stub(200, [{ alert_id: 'al1', condition_id: 'CR-01', severity: 'high' }])
    const a = await getExperimentAlerts('exp_1')
    expect(a[0].alert_id).toBe('al1')
  })
})
