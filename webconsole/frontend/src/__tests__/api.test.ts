import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError, activateInstance, artifactUrl, evaluateRun, getCompare, getInstances, launchRun,
  listRuns, listRunsPaged, streamUrl,
} from '../api'

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

  it('listRunsPaged manda los filtros y lee el total de la cabecera', async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(
      async () =>
        new Response(JSON.stringify([{ run_id: 'r1', status: 'running' }]), {
          status: 200,
          headers: { 'X-Total-Count': '87' },
        }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { items, total } = await listRunsPaged({
      estado: 'running',
      q: 'ronda',
      orden: 'fps_effective',
      direccion: 'asc',
      pagina: 3,
      pageSize: 25,
    })

    expect(items).toHaveLength(1)
    // El total es el del historial filtrado, no el de la página devuelta.
    expect(total).toBe(87)
    const url = new URL(fetchMock.mock.calls[0][0], 'http://x')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      estado: 'running',
      q: 'ronda',
      orden: 'fps_effective',
      direccion: 'asc',
      pagina: '3',
      page_size: '25',
    })
  })

  it('listRunsPaged cae a la cantidad de filas si falta la cabecera', async () => {
    // Un proxy que filtre `X-Total-Count` daría un total incorrecto pero acotado;
    // romper el listado entero por una cabecera sería peor.
    stubFetch(200, [{ run_id: 'r1' }, { run_id: 'r2' }])
    expect((await listRunsPaged()).total).toBe(2)
  })

  // Regresión: `GET /api/runs` pelado devuelve la primera página de 25 desde que
  // el listado pagina en el servidor. Quien pedía "todas" —Comparar— se quedaba
  // con las 25 más nuevas sin enterarse.
  it('listRuns agota la paginación en vez de quedarse con la primera página', async () => {
    const total = 250
    const fetchMock = vi.fn(async (url: string) => {
      const pagina = Number(new URL(url, 'http://x').searchParams.get('pagina') ?? '1')
      const desde = (pagina - 1) * 200
      const filas = Array.from({ length: Math.min(200, total - desde) }, (_, i) => ({
        run_id: `r_${desde + i}`,
        status: 'succeeded',
      }))
      return new Response(JSON.stringify(filas), {
        status: 200,
        headers: { 'X-Total-Count': String(total) },
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const filas = await listRuns()
    expect(filas).toHaveLength(total)
    expect(filas[total - 1].run_id).toBe('r_249')
    expect(fetchMock).toHaveBeenCalledTimes(2)
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

  it('evaluateRun postea y parsea el eval', async () => {
    stubFetch(200, { run_id: 'r1', mAP50: 0.47, per_class: [] })
    const result = await evaluateRun('r1')
    expect(result.mAP50).toBe(0.47)
  })

  it('evaluateRun lanza ApiError en 422', async () => {
    stubFetch(422, { errors: [{ field: '_service', message: 'no evaluable' }] })
    const error = await evaluateRun('r1').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
  })

  it('getCompare arma la URL con ids encodeados', async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify({ runs: [], classes: [], ap_by_class: {}, skipped: [] }), {
          status: 200,
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await getCompare(['run a', 'run_b'])
    const calls = (fetchMock.mock.calls as Array<unknown[]>)[0]
    expect(calls?.[0]).toBe('/api/compare?runs=run%20a,run_b')
  })

  it('getInstances parsea la lista', async () => {
    stubFetch(200, [{ name: 'mp-mock', model_ref: 'mock', state: 'exited', ready: false, is_target: false }])
    expect(await getInstances()).toHaveLength(1)
  })

  it('activateInstance postea al endpoint con el nombre encodeado', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ target: 'mp-mock', model_ref: 'mock' }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await activateInstance('mp-mock')
    const calls = fetchMock.mock.calls as Array<unknown[]>
    expect(calls?.[0]?.[0]).toBe('/api/platform/instances/mp-mock/activate')
    expect((calls?.[0]?.[1] as RequestInit)?.method).toBe('POST')
  })

  it('activateInstance lanza ApiError con payload en 409', async () => {
    stubFetch(409, { detail: 'Hay un run activo en el target actual', run_id: 'run_x' })
    const error = await activateInstance('mp-mock').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
  })
})
