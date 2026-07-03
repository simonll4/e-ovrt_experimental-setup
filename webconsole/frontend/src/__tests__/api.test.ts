import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, artifactUrl, launchRun, listRuns, streamUrl } from '../api'

const COMP = {
  ingest: { plugin: 'image_folder', config: { dataset: 'demo_v2' } },
  prompts: { set_id: 'demo_set', active_ids: ['person'] },
  run: {},
}

function stubFetch(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })))
}

afterEach(() => vi.unstubAllGlobals())

describe('api client', () => {
  it('launchRun devuelve run_id en 201', async () => {
    stubFetch(201, { run_id: 'run_x' })
    expect(await launchRun(COMP)).toEqual({ run_id: 'run_x' })
  })

  it('launchRun lanza ApiError con payload en 409', async () => {
    stubFetch(409, { detail: 'busy', active_run_id: 'run_a' })
    const error = await launchRun(COMP).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.payload.active_run_id).toBe('run_a')
  })

  it('launchRun lanza ApiError con errores de campo en 422', async () => {
    stubFetch(422, { errors: [{ field: 'prompts.set_id', message: 'no existe' }] })
    const error = await launchRun(COMP).catch((e) => e)
    expect(error.status).toBe(422)
    expect(error.payload.errors[0].field).toBe('prompts.set_id')
  })

  it('listRuns parsea filas', async () => {
    stubFetch(200, [{ run_id: 'r1', status: 'succeeded' }])
    expect(await listRuns()).toHaveLength(1)
  })

  it('artifactUrl encodea segmentos', () => {
    const url = artifactUrl('run x', 'previews/u 0.jpg')
    expect(url).toBe('/api/runs/run%20x/artifacts/previews/u%200.jpg')
    // '/' de path se preserva como separador, no se encodea a %2F
    expect(url.split('/')).toEqual(['', 'api', 'runs', 'run%20x', 'artifacts', 'previews', 'u%200.jpg'])

    // Caracteres que romperían/truncarían la URL sin encode (#, ?, %) quedan encodeados.
    const trickyId = artifactUrl('run#1', 'a?b/c%d.jpg')
    expect(trickyId).toBe('/api/runs/run%231/artifacts/a%3Fb/c%25d.jpg')
  })

  it('streamUrl encodea el id', () => {
    const url = streamUrl('run x#1')
    expect(url).toContain('/api/runs/run%20x%231/stream')
  })
})
