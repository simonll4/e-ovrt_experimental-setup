import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen } from '../test-utils'
import ExperimentsPage from '../pages/ExperimentsPage'
import type { ExperimentManifestSummary } from '../types'

const measured: ExperimentManifestSummary = {
  slug: 'talert_integrated_video', n_runs: 0, evidence: {
    is_evidence: true, result_ids: ['realtime/t_alert_notification'], collections: ['ebe_realtime'],
    clase: 'resultado', n_executions: 4, executions: ['exp_rep3', 'exp_rep2', 'exp_rep1'],
  },
}
const recipe: ExperimentManifestSummary = { slug: 'recipe', n_runs: 0, evidence: {
  is_evidence: false, result_ids: [], collections: [], clase: 'sin_clasificar',
  n_executions: 0, executions: [],
} }
let urls: URL[]
// Task 8 (+ ronda de arreglo 1): la fixture del contrato congelado NUNCA
// manda las cabeceras nuevas — 'sin_cabeceras' reproduce exactamente eso.
// Las otras variantes degradan UNA cabecera a la vez (denominador ausente,
// denominador en cero, desglose de slugs ausente) para probar cada rama de
// degradación por separado, sin inventar ceros donde el dato falta.
type Variante = 'completo' | 'sin_cabeceras' | 'sin_total' | 'total_cero' | 'sin_slugs'
  | 'registro_ausente' | 'sin_taxonomia' | 'taxonomia_parcial'
/** `X-Clasificacion-Roles` = "roles sin clase / roles del registro". */
const ROLES: Partial<Record<Variante, string>> = {
  registro_ausente: '0/0', sin_taxonomia: '21/21', taxonomia_parcial: '20/21',
}
let variante: Variante
beforeEach(() => {
  localStorage.clear()
  urls = []
  variante = 'completo'
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    if (url.pathname === '/api/experiments/current') return new Response('{}', { status: 404 })
    if (url.pathname === '/api/preflight') return new Response(JSON.stringify({
      ready: true, blockers: [], media: { healthy: true, ready: true }, control: { healthy: true, ready: true },
    }))
    if (url.pathname !== '/api/experiments/manifests') throw new Error(`Petición inesperada: ${url}`)
    const headers: Record<string, string> = {}
    if (variante !== 'sin_cabeceras') {
      headers['X-Evidence-Available'] = variante === 'registro_ausente' ? 'false' : 'true'
      headers['X-Clasificacion-Available'] = variante === 'sin_taxonomia' ? 'false' : 'true'
      headers['X-Clasificacion-Roles'] = ROLES[variante] ?? '0/21'
      headers['X-Archived-Count'] = '1'
      headers['X-Archived-Executions-Count'] = '456'
      headers['X-Platform-Test-Count'] = '445'
      if (variante !== 'sin_slugs') {
        headers['X-Platform-Test-Slugs'] = 'orq_1=90,orq_2a=90,orq_alerts_502=89,orq_alerts=89,gate_orq=87'
      }
      if (variante === 'total_cero') headers['X-Total-Executions-Count'] = '0'
      else if (variante !== 'sin_total') headers['X-Total-Executions-Count'] = '459'
    }
    return new Response(JSON.stringify([measured, recipe]), { headers })
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })
const page = () => render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)

// Desde Task 8 la pantalla ya no separa evidencia/archivadas (`vista`): pide
// SIEMPRE la lista completa y filtra por clase del lado del cliente con los
// mismos chips que Corridas (Task 7). Este test reemplaza al viejo "pide
// evidencia, conserva el conteo histórico..." que dependía del control de
// vista retirado.
it('pide siempre la lista completa y ofrece los enlaces a las ejecuciones de evidencia', async () => {
  page()
  await screen.findByText('talert_integrated_video')
  expect(screen.getByText('recipe')).toBeTruthy()
  expect(screen.getByText('3 ejecuciones de evidencia')).toBeTruthy()
  for (const id of ['exp_rep1', 'exp_rep2', 'exp_rep3']) {
    expect(screen.getByRole('link', { name: id }).getAttribute('href')).toBe(`/experiments/${id}`)
  }
  const peticionesDeManifiestos = urls.filter((u) => u.pathname === '/api/experiments/manifests')
  expect(peticionesDeManifiestos.length).toBeGreaterThan(0)
  expect(peticionesDeManifiestos.every((u) => u.searchParams.get('vista') === 'todas')).toBe(true)
  expect(screen.getAllByText('realtime/t_alert_notification')).toHaveLength(1)
})

it('filtra por clase con los chips (Task 7/8), sin pedir nada nuevo al servidor', async () => {
  page()
  await screen.findByText('talert_integrated_video')
  expect(screen.getByText('recipe')).toBeTruthy()
  const peticionesAntes = urls.length
  fireEvent.click(screen.getByRole('button', { name: /Resultado/ }))
  expect(screen.queryByText('recipe')).toBeNull()
  expect(screen.getByText('talert_integrated_video')).toBeTruthy()
  // El filtro es del lado del cliente: no dispara ninguna petición nueva.
  expect(urls.length).toBe(peticionesAntes)
  // Deseleccionar el mismo chip vuelve a mostrar todo.
  fireEvent.click(screen.getByRole('button', { name: /Resultado/ }))
  expect(screen.getByText('recipe')).toBeTruthy()
})

it('muestra las pruebas de plataforma como un bloque, con la proporción sobre el TOTAL en disco', async () => {
  page()
  await screen.findByText('talert_integrated_video')
  expect(await screen.findByText('445')).toBeTruthy()
  expect(screen.getByText(/la máquina probándose/i)).toBeTruthy()
  expect(screen.getByText('orq_1 · 90')).toBeTruthy()
  // 445 / 459 ≈ 96,95 % → redondea a 97. El denominador es `X-Total-
  // Executions-Count` (TODO lo que hay en disco), no `X-Archived-
  // Executions-Count` (eso sería casi tautológico: lo archivado es casi
  // todo smoke por definición).
  expect(screen.getByText('97 % de las 459 ejecuciones en disco')).toBeTruthy()
})

it('renderiza bien cuando las cabeceras no están (la fixture del contrato no las manda)', async () => {
  variante = 'sin_cabeceras'
  page()
  await screen.findByText('Manifiestos')
  expect(screen.getByText('talert_integrated_video')).toBeTruthy()
  expect(screen.queryByText(/pruebas de plataforma/i)).toBeNull()
  expect(screen.queryByText('445')).toBeNull()
})

// Ronda de arreglo 1 (IMPORTANT 2): la proporción es la pieza central del
// enunciado — el número que crece solo y por eso se cita como proporción —
// y no tenía ningún test de su rama de degradación.
it('sin el total en disco, muestra el bloque y el conteo pero no inventa un porcentaje', async () => {
  variante = 'sin_total'
  page()
  await screen.findByText('talert_integrated_video')
  expect(await screen.findByText('445')).toBeTruthy()
  expect(screen.queryByText(/% de las/)).toBeNull()
  expect(screen.getByText(/nunca se cita el número absoluto como si fuera estable\./)).toBeTruthy()
})

it('con el total en disco en cero, tampoco inventa un porcentaje (división por cero)', async () => {
  variante = 'total_cero'
  page()
  await screen.findByText('talert_integrated_video')
  expect(await screen.findByText('445')).toBeTruthy()
  expect(screen.queryByText(/% de las/)).toBeNull()
  expect(screen.getByText(/nunca se cita el número absoluto como si fuera estable\./)).toBeTruthy()
})

// Ronda de arreglo 1 (IMPORTANT 4): si el desglose de slugs falta pero el
// conteo total sí llegó, el texto no puede inventar "0 slugs" — eso es
// fabricar un cero para un dato que en realidad se desconoce.
it('sin el desglose de slugs, declara que no está disponible en vez de decir "0 slugs"', async () => {
  variante = 'sin_slugs'
  page()
  await screen.findByText('talert_integrated_video')
  expect(await screen.findByText('445')).toBeTruthy()
  expect(screen.queryByText(/0 slugs/)).toBeNull()
  expect(screen.getByText(/desglose por slug no está disponible/i)).toBeTruthy()
  expect(screen.queryByText('orq_1 · 90')).toBeNull()
})

// C-3 / ruling R-25: al reemplazar `EvidenceViewControl` por los chips de clase
// se perdió la advertencia junto con el filtro. El backend sigue mandando la
// cabecera; desde ese trabajo nadie la escuchaba, y la pantalla afirmaba una
// clasificación construida entera sobre un archivo ausente.
it('declara el registro de evidencia ausente en vez de clasificar igual', async () => {
  variante = 'registro_ausente'
  page()
  const banner = (await screen.findByText(/Registro de evidencia no disponible/)).closest('.eo-banner')
  // El CUERPO, no sólo el titular: desde R-31 el flag también dispara con los
  // cuatro CSV presentes y cero filas, así que ni afirma que el archivo no
  // está, ni manda a restaurar del backup a secas.
  expect(banner?.textContent).toMatch(/no se encontró, o está presente y no trae una sola fila/)
  expect(banner?.textContent).toMatch(/Si falta, restauralo.*si está, regeneralo/)
})

it('declara la taxonomía ausente aunque el registro sí esté', async () => {
  // Es la peor de las dos porque no se nota: el registro carga, `available`
  // queda en true y toda clase cae a «Fuera del registro» en silencio.
  variante = 'sin_taxonomia'
  page()
  const banner = (await screen.findByText(/Taxonomía de clases no disponible/)).closest('.eo-banner')
  expect(banner?.textContent).toMatch(/no está, o está y no declara ningún rol/)
  expect(banner?.textContent).not.toMatch(/pero falta results\/evidence-vista/)
})

it('declara la clasificación PARCIAL, que ningún booleano distingue', async () => {
  variante = 'taxonomia_parcial'
  page()
  const banner = (await screen.findByText(/Clasificación incompleta/)).closest('.eo-banner')
  expect(banner?.textContent).toMatch(/20 de 21 roles sin clasificar/)
})

it('no advierte nada cuando las dos cabeceras dicen que están', async () => {
  page()
  await screen.findByText('talert_integrated_video')
  expect(screen.queryByText(/no disponible/)).toBeNull()
})

it('sin las cabeceras no afirma ni que está ni que falta', async () => {
  // La fixture del contrato congelado no las manda: ausente no es `false`.
  variante = 'sin_cabeceras'
  page()
  await screen.findByText('talert_integrated_video')
  expect(screen.queryByText(/no disponible/)).toBeNull()
})
