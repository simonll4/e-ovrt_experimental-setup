import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, within } from '../test-utils'
import App from '../App'
import { crumbsFor } from '../nav'
import type { ArchivedRun, EvidenceResult, EvidenceStep } from '../types'

// `rid` es el resultado que aparece en el paso 3 con título propio
// ("Línea de base del Nivel B"): se reusa tal cual para las pruebas directas
// de `/evidencia/resultado` y `/evidencia/run`, así el `id` que viaja en la
// query es siempre el mismo, sea cual sea la puerta de entrada.
const rid = 'clip_bench/t1_gdinotiny560_v2short_scene'
const info: EvidenceResult = {
  result_id: rid, index: 'clip_bench', etiqueta: 't1 gdinotiny560 v2short scene',
  titulo: 'Línea de base del Nivel B',
  reclamo: 'Primera campaña sobre GT temporal humano. Es la referencia de escena: contra ella se lee cada campaña que cambia una sola cosa.',
  n_runs: 26, n_rows: 26, roles: { campaign_media: 26 },
  documents: ['docs/medicion.md'], source_refs: ['results/eval.json'], metricas: null,
}
// Segundo resultado del paso 3, sin título propio por default: sirve para
// probar la etiqueta derivada y, cuando `title` se completa, el título del
// usuario — el mismo par de casos que cubría la vista vieja de índice.
const secondRid = 'clip_bench/g1_gdinotiny560_v2short_subject'
const second: EvidenceResult = {
  result_id: secondRid, index: 'clip_bench', etiqueta: 'g1 gdinotiny560 v2short subject', titulo: null,
  reclamo: 'La identidad por sujeto: mismas detecciones, granularidad distinta.',
  n_runs: 34, n_rows: 34, roles: { campaign_media: 34 }, documents: [], source_refs: [],
  metricas: { esquema: 'talert_notification_metrics.v1',
    cabecera: [{ label: 'p95 control→MQTT', valor: 64.534, nota: 'ms' }], desgloses: [] },
}
const row: ArchivedRun = {
  result_id: rid, run_id: 'm1', plane: 'media-plane', status: 'copied',
  role: 'campaign_media', source_ref: 'results/eval.json', artifact_path: 'artifacts/media-plane/m1',
  tiene_detalle_vivo: true, reason: null,
}
const respaldoItem: EvidenceResult = {
  result_id: 'realtime/claqueta_reloj_externo', index: 'realtime', etiqueta: 'claqueta reloj externo',
  titulo: 'Claqueta con reloj externo', reclamo: 'Valida el aparato de medición, no el fenómeno.',
  n_runs: 3, n_rows: 3, roles: { campaign_media: 3 }, documents: [], source_refs: [], metricas: null,
}
const paso1: EvidenceStep = {
  n: 1, titulo: 'Qué ve el detector sin entrenar',
  claim: 'El campeón zero-shot sobre 6.477 imágenes de tres fuentes independientes.',
  cifra: '0,551', cifra_label: 'mAP50, bench_v3 completo', cifra_nota: 'gdino-tiny-560 · 560 / 0,30',
  cifra_origen: 'citada', fuente: 'results/bench_imagenes/index.md', n_resultados: 5, indices: ['bench_imagenes'],
}
const paso3: EvidenceStep = {
  n: 3, titulo: 'Qué agrega la plataforma sobre la detección cruda',
  claim: 'La histéresis rescata percepción intermitente, pero es palanca de doble filo.',
  cifra: '0,789 → 0,930', cifra_label: 'F1, escena → sujeto', cifra_nota: 'mismas detecciones',
  cifra_origen: 'leida', fuente: null, n_resultados: 2, indices: ['clip_bench'],
}
// Pasos 2 y 4: de relleno, sólo para que la entrada muestre las cuatro tarjetas
// reales (ningún test afirma su contenido).
const pasoRelleno = (n: number): EvidenceStep => ({
  n, titulo: `Paso de relleno ${n}`, claim: 'Claim de relleno.', cifra: null,
  cifra_label: null, cifra_nota: null, cifra_origen: 'leida', fuente: null, n_resultados: 0, indices: [],
})
const pasos = [paso1, pasoRelleno(2), paso3, pasoRelleno(4)]

let urls: URL[]
let unavailable: boolean
let archived: boolean
let title: string | null
let fallaPaso: boolean
beforeEach(() => {
  urls = []; unavailable = false; archived = false; title = null; fallaPaso = false
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost'); urls.push(url)
    const state = { available: !unavailable, message: unavailable ? 'Falta results/evidence-runs/. Restaurar desde docs/operacion/126.' : null }
    const result = { ...info }
    const segundo = { ...second, titulo: title }
    if (url.pathname === '/api/evidencia') {
      return new Response(JSON.stringify({
        ...state,
        pasos: unavailable ? [] : pasos,
        respaldo: unavailable ? null : {
          titulo: 'Respaldo instrumental',
          claim: 'Lo que valida el aparato de medición, no el fenómeno.',
          n_resultados: 1, resultados: [respaldoItem],
        },
        indices: unavailable ? [] : [
          { id: 'bench_imagenes', n_results: 5 }, { id: 'bench_nivel_a', n_results: 4 },
          { id: 'clip_bench', n_results: 20 }, { id: 'realtime', n_results: 6 },
        ],
      }))
    }
    if (url.pathname === '/api/evidencia/paso') {
      // Una falla de lectura que NO es "ese paso no existe" (servicio caído,
      // 500, lo que sea): no lleva 404, así que Paso.tsx no debe leerla como
      // un 404.
      if (fallaPaso) return new Response(JSON.stringify({ detail: 'boom' }), { status: 500 })
      if (unavailable) return new Response(JSON.stringify({ ...state, paso: null, resultados: [] }))
      const n = Number(url.searchParams.get('n'))
      const paso = pasos.find((p) => p.n === n)
      if (!paso) return new Response(JSON.stringify({ detail: 'Ese paso del recorrido no existe' }), { status: 404 })
      return new Response(JSON.stringify({
        ...state, paso, n_pasos: pasos.length,
        resultados: n === 3 ? [result, segundo] : [],
      }))
    }
    if (url.pathname === '/api/evidencia/resultado') {
      const page = Number(url.searchParams.get('page'))
      return new Response(JSON.stringify({ ...state, result, items: [{ ...row, run_id: page === 1 ? 'm1' : 'm26' }], total: 26, page, page_size: 25 }))
    }
    if (url.pathname === '/api/evidencia/run') return new Response(JSON.stringify({ ...state,
      run: { ...row, status: archived ? 'archived_only' : 'copied', tiene_detalle_vivo: !archived, reason: archived ? 'Original retirado; evaluación preservada.' : null },
      summary: archived ? null : { run_id: 'm1', units_processed: 17 },
      substitutes: archived ? [{ name: 'eval.json', data: { precision: .75 } }] : [],
      notice: archived ? 'Sin summary individual; artefacto sustituto.' : null, relations: [row],
    }))
    throw new Error(`Esta vista no debe consultar ${url}`)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })
const open = (url = '/evidencia') => render(<MemoryRouter initialEntries={[url]}><App /></MemoryRouter>)

it('navega el recorrido paso → resultado → corrida, sin consultar servicios desde el Shell', async () => {
  open('/evidencia/paso?n=3')
  fireEvent.click(await screen.findByRole('link', { name: 'Línea de base del Nivel B' }))
  await screen.findByText('docs/medicion.md')
  fireEvent.click(await screen.findByRole('link', { name: 'm1' }))
  await screen.findByRole('heading', { name: 'Summary congelado' })
  expect(screen.getByText('17')).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Abrir detalle vivo' }).getAttribute('href')).toBe('/runs/m1')
  expect(urls.map(url => url.pathname)).toEqual(['/api/evidencia/paso', '/api/evidencia/resultado', '/api/evidencia/run'])
  expect(urls[0].searchParams.get('n')).toBe('3')
  expect(urls[1].searchParams.get('id')).toBe(rid)
  expect(urls[2].searchParams.get('plane')).toBe('media-plane')
  expect(screen.queryByRole('group', { name: 'Estado de los servicios' })).toBeNull()
  expect(screen.getByText('Archivo local · servicios no consultados')).toBeTruthy()
})

it('pagina corridas preservando el result_id con barra y el rol', async () => {
  open(`/evidencia/resultado?${new URLSearchParams({ id: rid })}`)
  await screen.findByRole('link', { name: 'm1' })
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
  await screen.findByRole('link', { name: 'm26' })
  expect(screen.queryByRole('link', { name: 'm1' })).toBeNull()
  expect(screen.getByText('Página 2 de 2')).toBeTruthy()
  expect((screen.getByRole('button', { name: 'Siguiente' }) as HTMLButtonElement).disabled).toBe(true)
  expect(urls.every(url => url.searchParams.get('id') === rid)).toBe(true)
  expect(within(screen.getByRole('table', { name: 'Corridas de evidencia' })).getByText('campaign_media')).toBeTruthy()
})

it('archived_only muestra motivo y sustituto, sin enlace vivo ni imágenes', async () => {
  archived = true
  open(`/evidencia/run?plane=media-plane&run_id=m1&id=${encodeURIComponent(rid)}`)
  await screen.findByText('Original retirado; evaluación preservada.')
  expect(screen.getByRole('heading', { name: 'eval.json' })).toBeTruthy()
  expect(screen.queryByRole('link', { name: 'Abrir detalle vivo' })).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Summary congelado' })).toBeNull()
  expect(screen.queryByRole('img')).toBeNull()
})

it('muestra el estado vacío con la ubicación y el backup, sin servicios', async () => {
  unavailable = true
  open()
  await screen.findByText('Archivo de evidencia no disponible')
  expect(screen.getByText(/Restaurar desde docs\/operacion\/126/)).toBeTruthy()
  expect(urls.map(url => url.pathname)).toEqual(['/api/evidencia'])
})

it('muestra la etiqueta derivada cuando el resultado no tiene título propio', async () => {
  open('/evidencia/paso?n=3')
  expect(await screen.findByRole('link', { name: 'g1 gdinotiny560 v2short subject' })).toBeTruthy()
})

it('usa el título del usuario cuando está, en vez de la etiqueta derivada', async () => {
  title = 'Título de prueba aportado por el usuario'
  open('/evidencia/paso?n=3')
  expect(await screen.findByRole('link', { name: title })).toBeTruthy()
  expect(screen.queryByRole('link', { name: 'g1 gdinotiny560 v2short subject' })).toBeNull()
})

it('las migas conservan id con barra en query y la raíz sigue siendo Corridas', () => {
  const search = `?${new URLSearchParams({ id: rid, plane: 'media-plane', run_id: 'm1' })}`
  const crumbs = crumbsFor('/evidencia/run', search)
  expect(crumbs.map(crumb => crumb.label)).toEqual(['Evidencia', rid, 'm1'])
  expect(new URL(crumbs[1].to, 'http://localhost').searchParams.get('id')).toBe(rid)
  expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Corridas' }])
})

it('la entrada muestra los cuatro números del argumento, no las colecciones', async () => {
  open('/evidencia')
  expect(await screen.findByText('Qué agrega la plataforma sobre la detección cruda')).toBeTruthy()
  expect(screen.getByText('0,789 → 0,930')).toBeTruthy()
  // El conteo de corridas NO es la cifra de cabecera de la entrada.
  expect(screen.queryByText(/relaciones registradas/)).toBeNull()
  // Los CUATRO números, no sólo el 3: una regresión que se comiera un paso
  // del argumento tiene que fallar acá, no pasar en silencio.
  expect(screen.getByText('Qué ve el detector sin entrenar')).toBeTruthy()
  expect(screen.getByText('Paso de relleno 2')).toBeTruthy()
  expect(screen.getByText('Paso de relleno 4')).toBeTruthy()
})

it('una cifra citada se marca y dice su fuente', async () => {
  open('/evidencia')
  const citada = await screen.findByTitle('results/bench_imagenes/index.md')
  expect(citada.textContent).toContain('0,551')
})

it('clickear un número abre sus resultados con título redactado', async () => {
  open('/evidencia/paso?n=3')
  expect(await screen.findByText('Línea de base del Nivel B')).toBeTruthy()
  expect(screen.getByText(/es la referencia de escena: contra ella se lee cada campaña/i)).toBeTruthy()
})

it('un resultado sin metrics.json declara la ausencia, no dibuja un cero', async () => {
  open('/evidencia/paso?n=3')
  const fila = (await screen.findByText('Línea de base del Nivel B')).closest('tr')
  expect(fila).toBeTruthy()
  expect(within(fila as HTMLElement).getByText('sin artefacto en este repositorio')).toBeTruthy()
})

it('el respaldo instrumental reusa la tabla de resultados de un paso, sin ruta propia en la API', async () => {
  open('/evidencia/respaldo')
  await screen.findByRole('heading', { name: 'Respaldo instrumental' })
  expect(await screen.findByRole('link', { name: 'Claqueta con reloj externo' })).toBeTruthy()
  // No hay endpoint `/api/evidencia/respaldo`: sale de `respaldo.resultados`.
  expect(urls.map(url => url.pathname)).toEqual(['/api/evidencia'])
})

it('un paso que no existe (404) dice eso, y sólo eso', async () => {
  open('/evidencia/paso?n=99')
  expect(await screen.findByText('Ese paso del recorrido no existe.')).toBeTruthy()
})

it('una falla de lectura del paso (no 404) no se disfraza de "no existe"', async () => {
  fallaPaso = true
  open('/evidencia/paso?n=3')
  expect(await screen.findByText('No se pudo leer el archivo de evidencia.')).toBeTruthy()
  expect(screen.queryByText('Ese paso del recorrido no existe.')).toBeNull()
})

it('las migas encadenan Evidencia > Paso N y Evidencia > Respaldo instrumental', () => {
  expect(crumbsFor('/evidencia/paso', '?n=3').map(c => c.label)).toEqual(['Evidencia', 'Paso 3'])
  expect(crumbsFor('/evidencia/respaldo').map(c => c.label)).toEqual(['Evidencia', 'Respaldo instrumental'])
})

it('un resultado abierto desde un paso encadena Evidencia > Paso N > resultado', () => {
  const search = `?${new URLSearchParams({ id: rid, paso: '3' })}`
  expect(crumbsFor('/evidencia/resultado', search).map(c => c.label)).toEqual(['Evidencia', 'Paso 3', rid])
  // Sin `paso` en el query (se entró directo, o desde el respaldo) la miga
  // vuelve a los dos niveles de siempre: no se inventa un paso de origen.
  expect(crumbsFor('/evidencia/resultado', `?${new URLSearchParams({ id: rid })}`).map(c => c.label))
    .toEqual(['Evidencia', rid])
})

describe('el resultado con su desglose (Task 6)', () => {
  const campaignId = 'clip_bench/campaign'
  const razonControl = 'Las corridas de control se conservan sólo como archivo: '
    + 'vivían en un scratchpad ausente y cada eval versionado preserva su resultado derivado y el ID original.'
  const campaignResult: EvidenceResult = {
    result_id: campaignId, index: 'clip_bench', etiqueta: 'campaign',
    titulo: 'Línea de base del Nivel B',
    reclamo: 'Primera campaña sobre GT temporal humano: los 34 clips del rodaje de punta a '
      + 'punta con el modelo campeón y el prompt set congelado.',
    n_runs: 5, n_rows: 5, roles: { campaign_media: 2, campaign_control: 3 },
    documents: ['docs/medicion.md'], source_refs: ['results/clip_bench/campaign/metrics.json'],
    metricas: {
      esquema: 'clip_campaign_metrics.v1',
      cabecera: [
        { label: 'F1 micro', valor: 0.789 },
        { label: 'recall micro', valor: 0.824 },
        { label: 'precision micro', valor: 0.757 },
        { label: 'episodios evaluables', valor: 34, entero: true, nota: 'de 35' },
        { label: 'falsos positivos', valor: 9, entero: true },
      ],
      desgloses: [
        {
          id: 'condicion', titulo: 'Por condición de riesgo',
          nota: 'El t_alert está dominado por la persistencia del patrón, no por el transporte.',
          columnas: ['Condición', 'Episodios', 'SDR', 't_alert'],
          filas: [
            { nombre: 'CR-01', episodios: 28, sdr: 0.805, t_alert_ms: 4314, no_aplica: null },
            { nombre: 'CR-02', episodios: 7, sdr: 0.281, t_alert_ms: 8572, no_aplica: null },
          ],
        },
        {
          id: 'escenario', titulo: 'Por escenario', nota: 'Nunca sólo el agregado — limitación L5.',
          columnas: ['Escenario', 'Clips', 'Episodios', 'recall', 'FP', 'SDR'],
          filas: [
            { nombre: 'P1', clips: 11, episodios: 11, recall: 1, fp: 0, sdr: 0.816, no_aplica: null },
            // `sdr` viene en 0.5 a propósito (no `null`): el backend decide
            // `no_aplica` mirando sólo `recall` y podría reenviar cualquier otro
            // campo derivado tal cual venga — la correlación con `null` es un
            // hecho de LOS DATOS, no algo que el código pueda asumir. Si el
            // guardia de "sin dato" dependiera de que `sdr` también fuera
            // `null`, este valor decoy lo destaparía mostrando "0,500".
            { nombre: 'P3', clips: 2, episodios: 0, recall: null, fp: 0, sdr: 0.5, no_aplica: 'sin episodios evaluables' },
            { nombre: 'P5', clips: 2, episodios: 0, recall: null, fp: 0, sdr: 0.5, no_aplica: 'sin episodios evaluables' },
            { nombre: 'P7', clips: 4, episodios: 5, recall: 0.4, fp: 5, sdr: 0.884, no_aplica: null },
          ],
        },
        {
          id: 'clip', titulo: 'Por clip', nota: null,
          columnas: ['Clip', 'Escenario', 'Esperados', 'Detectados', 'recall', 't_alert'],
          filas: [
            { nombre: 'cb_p1_01', escenario: 'P1', esperados: 1, detectados: 1, recall: 1, t_alert_ms: 4200, no_aplica: null },
          ],
        },
        {
          id: 'negativos', titulo: 'Control de negativos',
          nota: 'Los negativos no entran a precision, recall ni F1: su métrica son los FP.',
          columnas: ['Clips', 'FP', 'Tiempo observado'],
          filas: [{ nombre: 'negativos', clips: 4, fp: 0, observado_ms: 129000, no_aplica: null }],
        },
      ],
    },
  }
  const campaignItems: ArchivedRun[] = [
    { result_id: campaignId, run_id: 'm1', plane: 'media-plane', role: 'campaign_media', status: 'copied',
      source_ref: 'results/eval.json', artifact_path: 'artifacts/media-plane/m1', tiene_detalle_vivo: true, reason: null },
    { result_id: campaignId, run_id: 'm2', plane: 'media-plane', role: 'campaign_media', status: 'copied',
      source_ref: 'results/eval.json', artifact_path: 'artifacts/media-plane/m2', tiene_detalle_vivo: true, reason: null },
    { result_id: campaignId, run_id: 'c1', plane: 'control-plane', role: 'campaign_control', status: 'archived_only',
      source_ref: 'results/eval.json', artifact_path: 'artifacts/control-plane/c1', tiene_detalle_vivo: false, reason: razonControl },
    { result_id: campaignId, run_id: 'c2', plane: 'control-plane', role: 'campaign_control', status: 'archived_only',
      source_ref: 'results/eval.json', artifact_path: 'artifacts/control-plane/c2', tiene_detalle_vivo: false, reason: razonControl },
    { result_id: campaignId, run_id: 'c3', plane: 'control-plane', role: 'campaign_control', status: 'archived_only',
      source_ref: 'results/eval.json', artifact_path: 'artifacts/control-plane/c3', tiene_detalle_vivo: false, reason: razonControl },
  ]
  beforeEach(() => {
    // Mock propio de este describe: pisa el `fetch` del beforeEach de arriba
    // (corre después) con uno que sólo entiende `/api/evidencia/resultado`
    // para `campaignId` — es todo lo que estos tests necesitan.
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input), 'http://localhost')
      if (url.pathname === '/api/evidencia/resultado' && url.searchParams.get('id') === campaignId) {
        return new Response(JSON.stringify({
          available: true, message: null, result: campaignResult,
          items: campaignItems, total: campaignItems.length, page: 1, page_size: 25,
        }))
      }
      throw new Error(`Petición inesperada: ${url}`)
    }))
  })
  const openCampaign = () => render(
    <MemoryRouter initialEntries={[`/evidencia/resultado?${new URLSearchParams({ id: campaignId })}`]}><App /></MemoryRouter>,
  )

  it('muestra el agregado Y el desglose, nunca sólo el agregado', async () => {
    openCampaign()
    expect(await screen.findByText('0,789')).toBeTruthy()
    expect(screen.getByText('Por escenario')).toBeTruthy()
    expect(screen.getByText('Por condición de riesgo')).toBeTruthy()
  })

  it('un escenario sin episodios evaluables se declara, no se dibuja como cero', async () => {
    openCampaign()
    const fila = await screen.findByRole('row', { name: /P3/ })
    expect(within(fila).getByText('sin episodios evaluables')).toBeTruthy()
    expect(within(fila).queryByText('0,000')).toBeNull()
    // Y no hay barra: lo que no tiene dato no se dibuja. `within()` devuelve
    // consultas, no un contenedor — se consulta el elemento de la fila directo.
    expect(fila.querySelector('.eo-bar')).toBeNull()
  })

  it('las dos mitades valen también para SDR: la fila declara la causa una vez y SDR no muestra el número crudo', async () => {
    openCampaign()
    const fila = await screen.findByRole('row', { name: /P3/ })
    // La causa aparece (una sola vez, en la columna de recall)...
    expect(within(fila).getByText('sin episodios evaluables')).toBeTruthy()
    // ...y SDR —una métrica derivada distinta, en la misma fila— no muestra el
    // 0,5 crudo que trae el fixture ni ningún otro número: se declara "—",
    // no se dibuja como si tuviera dato.
    expect(within(fila).queryByText('0,500')).toBeNull()
  })

  it('agrupa el motivo repetido de las corridas en vez de repetirlo por fila', async () => {
    openCampaign()
    const motivo = await screen.findAllByText(/vivían en un scratchpad ausente/)
    expect(motivo).toHaveLength(1)
  })
})

it('la entrada no muestra dos totales del mismo conjunto sin explicarlos', async () => {
  // I-2: la cabecera sumaba los pasos (30) mientras «Por material» listaba 35
  // —el número canónico del proyecto— lado a lado, sin decir que la
  // diferencia son las de respaldo. Acá: 5+0+2+0 = 7 en el recorrido, 1 de
  // respaldo, 8 en total; «Por material» suma 5+4+20+6 = 35 (la fixture no
  // los hace coincidir a propósito: lo que se afirma es la DESCOMPOSICIÓN).
  open('/evidencia')
  await screen.findByText('Qué agrega la plataforma sobre la detección cruda')
  const meta = screen.getByText(/resultados reportados/)
  expect(meta.textContent).toContain('8 resultados reportados')
  expect(meta.textContent).toContain('7 en el recorrido')
  expect(meta.textContent).toContain('1 de respaldo instrumental')
})

it('cada índice del paso lleva su barra, no sólo el último', async () => {
  // V-4: `join(' + ') + '/'` dejaba «clip_bench + realtime/».
  open('/evidencia')
  expect(await screen.findByText(/5 resultados · bench_imagenes\//)).toBeTruthy()
})

it('los ejes de lectura se nombran, no se enlazan a un repo que no es público', async () => {
  // I-3: era el único enlace externo de una pantalla cuya propiedad declarada
  // es funcionar con todo apagado, y apuntaba a una rama sin mergear.
  open('/evidencia')
  await screen.findByText('Ejes de lectura')
  expect(screen.queryByRole('link', { name: /Ejes de lectura/ })).toBeNull()
  expect(document.querySelector('a[href^="https://github.com"]')).toBeNull()
})

it('el total de pasos sale de recorrido.yaml, no de un 4 hardcodeado', async () => {
  open('/evidencia/paso?n=3')
  await screen.findByText('Línea de base del Nivel B')
  expect(screen.getByText(/paso 3 de 4/)).toBeTruthy()
})

it('la cifra de cabecera de un paso conserva su unidad', async () => {
  // I-4: «p95 control→MQTT 64,534» sin «ms», en una columna donde el resto
  // son F1 entre 0 y 1. `Resultado.tsx` sí la mostraba: la misma cifra perdía
  // su unidad según el nivel.
  open('/evidencia/paso?n=3')
  const fila = (await screen.findByText('g1 gdinotiny560 v2short subject')).closest('tr')
  expect(within(fila as HTMLElement).getByText('ms')).toBeTruthy()
})
