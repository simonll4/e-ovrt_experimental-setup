import { MemoryRouter } from 'react-router-dom'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import type { DemoCamara, DemoCamaraChequeo, DemoCondicion, DemoPreflight, DemoState } from '../types'

// Estilo del contrato: se mockea `fetch` (no el módulo de API) y se verifican las
// peticiones y los nombres accesibles. Una petición sin respuesta preparada hace
// fallar el test: así se prueba que /demo no dispara ninguna consulta global.

interface Peticion { path: string; method: string; body: unknown }
let peticiones: Peticion[] = []
let inesperadas: string[] = []
let rutas: Record<string, (p: Peticion) => Response> = {}
// En el modo consola el armazón hace sus consultas globales (barra lateral, salud):
// esos tests las permiten con una respuesta neutra; los de proyección, no.
let globales = false

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

const CAMARAS: DemoCamara[] = [
  { id: 'oak_d_lab', nombre: 'OAK-D laboratorio', plugin: 'oak_d', destino: '169.254.31.137', por_defecto: true,
    estado: 'sin_comprobar', detalle: 'La OAK-D admite una sola conexión: no se sondea sola. Tocá «Comprobar».',
    medido_en: '2026-11-01T00:00:00+00:00' },
  { id: 'rtsp_dvr_1', nombre: 'RTSP DVR canal 1', plugin: 'rtsp', destino: '169.254.31.140:554', por_defecto: false,
    estado: 'activa', detalle: '169.254.31.140:554 responde (12 ms).', medido_en: '2026-11-01T00:00:00+00:00' },
]
const chequeo = (extra: Partial<DemoCamaraChequeo>): DemoCamaraChequeo => ({
  camara: 'oak_d_lab', nombre: 'OAK-D laboratorio', plugin: 'oak_d', destino: '169.254.31.137', estado: 'ok',
  causa: null, pasos: [], ayuda: [], acciones: [{ id: 'reintentar', etiqueta: 'Volver a comprobar' }],
  comprobado_en: '2026-11-01T00:00:00+00:00', ...extra,
})

/** El visor de la vista previa abre un WebSocket: en jsdom se reemplaza por uno inerte. */
class WebSocketInerte {
  binaryType = 'blob'
  onopen: (() => void) | null = null
  onmessage: (() => void) | null = null
  onclose: (() => void) | null = null
  close() {}
}

function instalar(estado: () => DemoState, preflight: DemoPreflight = PREFLIGHT_VERDE) {
  rutas = {
    'GET /api/demo/state': () => json(estado()),
    'GET /api/demo/preflight': () => json(preflight),
    'POST /api/demo/start': () => json({ session_id: 'demo_x', experiment_id: 'exp_x' }, 202),
    'POST /api/demo/finish': () => json({ session_id: 'demo_x', fase: 'finishing' }, 202),
    'GET /api/demo/respaldo': () => json({ detail: 'No hay' }, 404),
    'GET /api/demo/stack': () => json({ modo: 'compose', contenedores: [], error: null, host: { presente: false }, repos: [], servicios: {} }),
    'GET /api/demo/cifras': () => json([]),
    'GET /api/demo/camaras': () => json(CAMARAS),
    'GET /api/documentacion': () => json({ terminos: {} }),
  }
}

beforeEach(() => {
  peticiones = []
  inesperadas = []
  globales = false
  localStorage.clear()
  vi.stubGlobal('WebSocket', WebSocketInerte)
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    const p = { path: url.pathname, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : null }
    peticiones.push(p)
    const ruta = rutas[`${p.method} ${p.path}`]
    if (ruta) return ruta(p)
    if (globales && !p.path.startsWith('/api/demo/')) return json({ detail: 'fuera de la demo' }, 503)
    inesperadas.push(`${p.method} ${p.path}`)
    return json({ detail: 'sin fixture' }, 500)
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(inesperadas).toEqual([])
})

function montar(ruta = '/demo?proyectar=1') {
  return render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>)
}

const tecla = (key: string) => act(() => { fireEvent.keyDown(window, { key }) })

describe('/demo — Listo', () => {
  it('en proyección va a pantalla completa, sin el armazón y sin consultas globales', async () => {
    instalar(() => IDLE)
    montar()
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
    expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull()
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/preflight')).toBe(true))
    const paths = new Set(peticiones.map((p) => p.path))
    expect([...paths].every((p) => p.startsWith('/api/demo/'))).toBe(true)
    // La proyección no pide la lista de cámaras (usa la recordada).
    expect(paths.has('/api/demo/camaras')).toBe(false)
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
    montar('/demo?variante=ensayo&proyectar=1')
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

describe('/demo — dentro de la consola (por defecto)', () => {
  it('se ve con la navegación de la consola y los botones de la demo', async () => {
    instalar(() => IDLE)
    globales = true
    montar('/demo')
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
    expect(screen.getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
    const acciones = screen.getByRole('toolbar', { name: 'Acciones de la demo' })
    expect(within(acciones).getByRole('button', { name: /Iniciar/ })).toBeTruthy()
    expect(within(acciones).getByRole('button', { name: /Proyectar/ })).toBeTruthy()
  })

  it('el botón Iniciar inicia la corrida como la tecla I', async () => {
    instalar(() => IDLE)
    globales = true
    montar('/demo?variante=ensayo')
    const chequeos = await screen.findByRole('list', { name: 'Chequeo previo' })
    await waitFor(() => expect(within(chequeos).getAllByRole('listitem')).toHaveLength(8))
    await screen.findByRole('radiogroup', { name: 'Cámara de la demo' })
    fireEvent.click(screen.getByRole('button', { name: /^Iniciar/ }))
    await waitFor(() => expect(peticiones.find((p) => p.path === '/api/demo/start')?.body).toEqual({ variante: 'ensayo', camara: 'oak_d_lab' }))
  })

  it('Proyectar (o P) saca el armazón y P vuelve a la consola', async () => {
    instalar(() => IDLE)
    globales = true
    montar('/demo')
    await screen.findByRole('heading', { name: /Demo en vivo/ })
    fireEvent.click(screen.getByRole('button', { name: /Proyectar/ }))
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull())
    expect(screen.queryByRole('toolbar', { name: 'Acciones de la demo' })).toBeNull()
    expect(screen.getByLabelText('Teclas').textContent).toMatch(/volver a la consola/)
    await tecla('p')
    expect(await screen.findByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
  })

  it('el botón Finalizar pide confirmación con un segundo toque', async () => {
    instalar(() => EN_VIVO)
    globales = true
    montar('/demo')
    await screen.findByRole('region', { name: /Casco/ })
    fireEvent.click(screen.getByRole('button', { name: /Finalizar/ }))
    expect(await screen.findByText('Tocá Finalizar otra vez para cortar')).toBeTruthy()
    expect(peticiones.some((p) => p.path === '/api/demo/finish')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: /Finalizar/ }))
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/finish' && p.method === 'POST')).toBe(true))
  })
})

describe('/demo — la cámara de la demo', () => {
  const radio = (nombre: RegExp) => screen.findByRole('radio', { name: nombre }) as Promise<HTMLInputElement>
  const elegir = async (nombre: RegExp) => fireEvent.click(await radio(nombre))
  const grupo = () => screen.findByRole('radiogroup', { name: 'Cámara de la demo' })

  it('lista las cámaras con su estado a la vista y deja elegida la de la demo', async () => {
    instalar(() => IDLE)
    globales = true
    montar('/demo')
    const g = await grupo()
    const filas = within(g).getAllByRole('radio') as HTMLInputElement[]
    expect(filas.map((r) => r.checked)).toEqual([true, false])  // la OAK-D de la demo
    const oak = within(g).getByRole('radio', { name: /OAK-D laboratorio/ })
    const dvr = within(g).getByRole('radio', { name: /RTSP DVR canal 1/ })
    // El estado está en cada fila, sin tocar nada.
    expect(oak.closest('label')?.textContent).toMatch(/Sin comprobar/)
    expect(oak.closest('label')?.textContent).toMatch(/una sola conexión/)
    expect(dvr.closest('label')?.textContent).toMatch(/Activa/)
    expect(dvr.closest('label')?.textContent).toMatch(/169\.254\.31\.140:554 responde/)
  })

  it('una cámara que no contesta se ve «Sin respuesta»; con problemas, «Con problemas»', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['GET /api/demo/camaras'] = () => json([
      { ...CAMARAS[0], estado: 'inactiva', detalle: 'Comprobada hace 2 min: La OAK-D no responde en 169.254.31.137.' },
      { ...CAMARAS[1], estado: 'problema', detalle: 'El puerto contesta, pero la última comprobación falló: usuario o clave.' },
    ])
    montar('/demo')
    const g = await grupo()
    await waitFor(() => expect(g.textContent).toMatch(/Sin respuesta/))
    expect(g.textContent).toMatch(/Con problemas/)
    expect(g.textContent).toMatch(/La OAK-D no responde/)
    expect(g.textContent).toMatch(/usuario o clave/)
  })

  it('el estado se mantiene al día solo: la lista se vuelve a pedir', async () => {
    instalar(() => IDLE)
    globales = true
    let estado: DemoCamara['estado'] = 'inactiva'
    rutas['GET /api/demo/camaras'] = () => json([CAMARAS[0], { ...CAMARAS[1], estado, detalle: estado }])
    montar('/demo')
    const g = await grupo()
    await waitFor(() => expect(g.textContent).toMatch(/Sin respuesta/))
    estado = 'activa'  // alguien enchufó la cámara
    await act(async () => { await new Promise((r) => setTimeout(r, 5_300)) })
    await waitFor(() => expect(g.textContent).toMatch(/Activa/))
  }, 12_000)

  it('Comprobar muestra la causa, los pasos y cómo arreglarlo; la acción de arreglo funciona', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['POST /api/demo/camaras/oak_d_lab/comprobar'] = () => json(chequeo({
      estado: 'falla', causa: 'Otro proceso tiene la cámara: la OAK-D admite una sola conexión a la vez.',
      pasos: [{ id: 'prueba', nombre: 'Prueba de la cámara', ok: false, detalle: 'X_LINK_DEVICE_ALREADY_IN_USE' }],
      ayuda: ['Si fue una sesión anterior, reiniciar el motor libera la cámara.'],
      acciones: [{ id: 'reiniciar_motor', etiqueta: 'Reiniciar el motor' },
                 { id: 'reintentar', etiqueta: 'Volver a comprobar' }],
    }))
    rutas['POST /api/demo/motor/reiniciar'] = () => json({ motor: 'reiniciando' }, 202)
    montar('/demo')
    await grupo()
    fireEvent.click(screen.getByRole('button', { name: 'Comprobar' }))
    const resultado = await screen.findByRole('status', { name: 'Resultado de la comprobación' })
    expect(resultado.textContent).toMatch(/Otro proceso tiene la cámara/)
    expect(resultado.textContent).toMatch(/X_LINK_DEVICE_ALREADY_IN_USE/)
    expect(resultado.textContent).toMatch(/Cómo arreglarlo/)
    expect(screen.getByText('No se ve')).toBeTruthy()
    fireEvent.click(within(resultado).getByRole('button', { name: 'Reiniciar el motor' }))
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/motor/reiniciar' && p.method === 'POST')).toBe(true))
    expect(await screen.findByText(/Reiniciando el motor/)).toBeTruthy()
  })

  it('una cámara que se ve lo dice, y volver a comprobar repite la prueba', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['POST /api/demo/camaras/oak_d_lab/comprobar'] = () => json(chequeo({
      pasos: [{ id: 'prueba', nombre: 'Prueba de la cámara', ok: true, detalle: 'cuadro recibido, conectó en 9.4 s' }],
    }))
    montar('/demo')
    await grupo()
    fireEvent.click(screen.getByRole('button', { name: 'Comprobar' }))
    await screen.findByText('Se ve')
    fireEvent.click(screen.getByRole('button', { name: 'Volver a comprobar' }))
    await waitFor(() => expect(peticiones.filter((p) => p.path === '/api/demo/camaras/oak_d_lab/comprobar')).toHaveLength(2))
  })

  it('elegir otra cámara se recuerda y es la que se manda al iniciar', async () => {
    instalar(() => IDLE)
    globales = true
    montar('/demo')
    await elegir(/RTSP DVR canal 1/)
    expect(localStorage.getItem('eovrt-demo-camara')).toBe('rtsp_dvr_1')
    fireEvent.click(screen.getByRole('button', { name: /^Iniciar/ }))
    await waitFor(() => expect(peticiones.find((p) => p.path === '/api/demo/start')?.body)
      .toEqual({ variante: 'oakd', camara: 'rtsp_dvr_1' }))
  })

  it('la proyección usa la cámara recordada sin pedir la lista', async () => {
    instalar(() => IDLE)
    localStorage.setItem('eovrt-demo-camara', 'rtsp_dvr_1')
    montar('/demo?proyectar=1')
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/preflight')).toBe(true))
    await waitFor(() => expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0))
    await tecla('i')
    await waitFor(() => expect(peticiones.find((p) => p.path === '/api/demo/start')?.body)
      .toEqual({ variante: 'oakd', camara: 'rtsp_dvr_1' }))
    expect(peticiones.some((p) => p.path === '/api/demo/camaras')).toBe(false)
  })

  it('Ver la cámara abre la vista previa, y al iniciar se corta', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['POST /api/demo/camaras/rtsp_dvr_1/vista'] = () => json(CAMARAS[1], 201)
    montar('/demo')
    await elegir(/RTSP DVR canal 1/)
    fireEvent.click(screen.getByRole('button', { name: 'Ver la cámara' }))
    expect(await screen.findByRole('button', { name: 'Cortar la vista' })).toBeTruthy()
    expect(peticiones.some((p) => p.path === '/api/demo/camaras/rtsp_dvr_1/vista' && p.method === 'POST')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: /^Iniciar/ }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Cortar la vista' })).toBeNull())
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/start')).toBe(true))
  })

  it('cortar la vista de la OAK-D reinicia el motor para dejarlo apto para iniciar', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['POST /api/demo/camaras/oak_d_lab/vista'] = () => json(CAMARAS[0], 201)
    rutas['DELETE /api/demo/vista'] = () => new Response(null, { status: 204 })
    rutas['POST /api/demo/motor/reiniciar'] = () => json({ motor: 'reiniciando' }, 202)
    montar('/demo')
    await grupo()
    fireEvent.click(screen.getByRole('button', { name: 'Ver la cámara' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Cortar la vista' }))
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/vista' && p.method === 'DELETE')).toBe(true))
    await waitFor(() => expect(peticiones.some((p) => p.path === '/api/demo/motor/reiniciar')).toBe(true))
    expect(await screen.findByText(/Reiniciando el motor/)).toBeTruthy()
  })

  it('si la vista no se puede abrir, lo dice con el motivo', async () => {
    instalar(() => IDLE)
    globales = true
    rutas['POST /api/demo/camaras/oak_d_lab/vista'] = () => json({ detail: 'hay una sesión o un experimento en curso' }, 409)
    montar('/demo')
    await grupo()
    fireEvent.click(screen.getByRole('button', { name: 'Ver la cámara' }))
    expect(await screen.findByText(/No se pudo ver la cámara: hay una sesión o un experimento en curso/)).toBeTruthy()
  })

  it('durante la corrida no hay panel de cámara y avisa que solo viaja el estado', async () => {
    instalar(() => EN_VIVO)
    globales = true
    montar('/demo')
    await screen.findByRole('region', { name: /Casco/ })
    expect(screen.queryByRole('radiogroup', { name: 'Cámara de la demo' })).toBeNull()
    expect(screen.getByText(/La consola no recibe video durante la corrida: solo el estado/)).toBeTruthy()
  })
})
