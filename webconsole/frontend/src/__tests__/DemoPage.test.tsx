import { MemoryRouter } from 'react-router-dom'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import type { DemoCondicion, DemoPreflight, DemoState } from '../types'

// Estilo del contrato: se mockea `fetch` (no el módulo de API) y se verifican las
// peticiones y los nombres accesibles. Una petición sin respuesta preparada hace
// fallar el test: así se prueba que /demo no dispara ninguna consulta global.

interface Peticion { path: string; method: string; body: unknown }
let peticiones: Peticion[] = []
let inesperadas: string[] = []
let rutas: Record<string, (p: Peticion) => Response> = {}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const PREFLIGHT_VERDE: DemoPreflight = {
  listo: true,
  items: ['sesion', 'deteccion', 'motor', 'reglas', 'distribucion', 'broker', 'congelado', 'host'].map((id) => ({
    id, nombre: id, estado: 'ok' as const, detalle: id === 'host' ? 'hace 2 min' : 'listo', accion: null,
  })),
  congelado: { tag: 'informe-2026', ok: true, items: [] },
  motor: { estado: 'fresco' },
  stack: 'compose',
  comprobado_en: '2026-10-26T15:00:00+00:00',
}

const cond = (condicion: string, nombre: string, extra: Partial<DemoCondicion> = {}): DemoCondicion => ({
  condicion, nombre, estado: 'ok', transcurrido_ms: null, umbral_ms: null, severidad: null,
  alertas: 0, alerta_desde: null, broker: null, ...extra,
})

const EN_VIVO: DemoState = {
  fase: 'live', session_id: 'demo_20261026T150000Z', variante: 'oakd', stack: 'compose',
  experiment_id: 'exp_20261026T150000Z_demo_defensa',
  ids: { control_run_id: 'ctl', media_run_id: 'run' },
  iniciada_en: new Date().toISOString(), transcurrido_s: 65,
  pasos: [], condiciones: [
    cond('CR-01', 'Casco', { estado: 'confirmando', transcurrido_ms: 2100, umbral_ms: 4000, severidad: 'high' }),
    cond('CR-02', 'Chaleco'),
  ],
  broker: { mensajes: 0, ultimo: null },
  camara: { cuadros: 120, ultimo_cuadro_hace_s: 0.2, sin_senal: false, bus_perdidos: 0 },
  metricas: {}, eventos: [], motor: { estado: 'usado' },
}

const IDLE: DemoState = { fase: 'idle', session_id: null, motor: { estado: 'fresco' } }

function instalar(estado: () => DemoState, preflight: DemoPreflight = PREFLIGHT_VERDE) {
  rutas = {
    'GET /api/demo/state': () => json(estado()),
    'GET /api/demo/preflight': () => json(preflight),
    'POST /api/demo/start': () => json({ session_id: 'demo_x', experiment_id: 'exp_x' }, 202),
    'POST /api/demo/finish': () => json({ session_id: 'demo_x', fase: 'finishing' }, 202),
    'GET /api/demo/respaldo': () => json({ detail: 'No hay' }, 404),
    'GET /api/demo/stack': () => json({ modo: 'compose', contenedores: [], error: null, host: { presente: false }, repos: [], servicios: {} }),
    'GET /api/demo/cifras': () => json([]),
    'GET /api/documentacion': () => json({ terminos: {} }),
  }
}

beforeEach(() => {
  peticiones = []
  inesperadas = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const p = { path: url.pathname, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : null }
    peticiones.push(p)
    const ruta = rutas[`${p.method} ${p.path}`]
    if (ruta) return ruta(p)
    inesperadas.push(`${p.method} ${p.path}`)
    return json({ detail: 'sin fixture' }, 500)
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(inesperadas).toEqual([])
})

function montar(ruta = '/demo') {
  return render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>)
}

const tecla = (key: string) => act(() => { fireEvent.keyDown(window, { key }) })

describe('/demo — Listo', () => {
  it('va a pantalla completa, sin el armazón y sin consultas globales', async () => {
    instalar(() => IDLE)
    montar()
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
    expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull()
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/preflight')).toBe(true))
    const paths = new Set(peticiones.map((p) => p.path))
    expect([...paths].every((p) => p.startsWith('/api/demo/'))).toBe(true)
  })

  it('con todo en verde, I inicia la corrida con la OAK-D', async () => {
    instalar(() => IDLE)
    montar()
    const chequeos = await screen.findByRole('list', { name: 'Chequeo previo' })
    await waitFor(() => expect(within(chequeos).getAllByRole('listitem')).toHaveLength(8))
    await tecla('i')
    await waitFor(() => expect(peticiones.find((p) => p.method === 'POST')).toEqual({
      path: '/api/demo/start', method: 'POST', body: { variante: 'oakd' },
    }))
  })

  it('con algo en rojo, I no hace nada y dice qué hacer', async () => {
    instalar(() => IDLE, {
      ...PREFLIGHT_VERDE, listo: false,
      items: PREFLIGHT_VERDE.items.map((i) => (i.id === 'broker'
        ? { ...i, estado: 'error' as const, detalle: 'el ping no volvió', accion: 'revisar mosquitto' } : i)),
    })
    montar()
    expect(await screen.findByText(/el ping no volvió/)).toBeTruthy()
    await tecla('i')
    expect(await screen.findByText('Todavía no: la tecla I funciona con todo en verde.')).toBeTruthy()
    expect(peticiones.some((p) => p.method === 'POST')).toBe(false)
  })

  it('la variante de ensayo lo anuncia y la manda al iniciar', async () => {
    instalar(() => IDLE)
    montar('/demo?variante=ensayo')
    expect(await screen.findByText(/la entrada es una grabación/)).toBeTruthy()
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/preflight')).toBe(true))
    await waitFor(() => expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0))
    await tecla('i')
    await waitFor(() => expect(peticiones.find((p) => p.method === 'POST')?.body).toEqual({ variante: 'ensayo' }))
  })
})

describe('/demo — corriendo', () => {
  it('muestra las dos tarjetas, el cronómetro, el broker y la cámara', async () => {
    instalar(() => EN_VIVO)
    montar()
    const casco = await screen.findByRole('region', { name: /Casco: confirmando/ })
    expect(within(casco).getByText(/Sin casco · confirmando 2,1 \/ 4 s/)).toBeTruthy()
    expect(within(casco).getByRole('progressbar', { name: 'Confirmando CR-01' })).toBeTruthy()
    expect(screen.getByRole('region', { name: /Chaleco: ok/ })).toBeTruthy()
    expect(screen.getByLabelText('Cronómetro').textContent).toBe('01:05')
    expect(screen.getByRole('region', { name: 'Broker' }).textContent).toMatch(/sin mensajes todavía/)
    expect(screen.getByLabelText('Cámara').textContent).toMatch(/120 cuadros/)
  })

  it('una sola F no corta: pide la segunda; F F finaliza', async () => {
    instalar(() => EN_VIVO)
    montar()
    await screen.findByRole('region', { name: /Casco/ })
    await tecla('f')
    expect(await screen.findByText('Apretá F otra vez para finalizar')).toBeTruthy()
    expect(peticiones.some((p) => p.path === '/api/demo/finish')).toBe(false)
    await tecla('f')
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/finish' && p.method === 'POST')).toBe(true))
  })

  it('E abre la capa de evidencia y Esc la cierra', async () => {
    instalar(() => EN_VIVO)
    montar()
    await screen.findByRole('region', { name: /Casco/ })
    await tecla('e')
    expect(await screen.findByRole('dialog', { name: 'Capa de evidencia' })).toBeTruthy()
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/stack')).toBe(true))
    await tecla('Escape')
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Capa de evidencia' })).toBeNull())
  })

  it('R sin sesión de respaldo lo dice y no hace nada más', async () => {
    instalar(() => EN_VIVO)
    montar()
    await screen.findByRole('region', { name: /Casco/ })
    await tecla('r')
    expect(await screen.findByText('No hay ninguna sesión marcada como respaldo.')).toBeTruthy()
    expect(screen.getByRole('region', { name: /Casco/ })).toBeTruthy()
  })

  it('al terminar la corrida pasa sola al Resultado', async () => {
    let fase: DemoState = EN_VIVO
    instalar(() => fase)
    rutas['GET /api/demo/sessions/demo_20261026T150000Z'] = () => json({
      session: null, resumen: null, linea_de_tiempo: [], testigo: [], state_log: [], respaldo: false,
    })
    montar()
    await screen.findByRole('region', { name: /Casco/ })
    fase = { ...EN_VIVO, fase: 'done' }
    expect(await screen.findByRole('heading', { name: 'Resultado de la demo' }, { timeout: 3000 })).toBeTruthy()
    expect(peticiones.some((p) => p.path === '/api/demo/sessions/demo_20261026T150000Z')).toBe(true)
  })
})
