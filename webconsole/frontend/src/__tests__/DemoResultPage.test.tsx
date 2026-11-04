import { MemoryRouter } from 'react-router-dom'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import type { DemoCifra, DemoSessionDetail, DemoState } from '../types'
import { MODOS, MODO_EDIR_SESION } from './fixtures/demoModos'

let rutas: Record<string, () => Response> = {}
let inesperadas: string[] = []
// Modo consola: el armazón hace sus consultas globales; se responden neutras.
let globales = false

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const SID = 'demo_20261026T150000Z'
const DETALLE: DemoSessionDetail = {
  session: {
    session_id: SID, variante: 'oakd', fase: 'done', stack: 'compose', experiment_id: 'exp_x',
    ids: { media_run_id: 'run_m', control_run_id: 'ctl_c' },
    iniciada_en: '2026-10-26T15:00:00+00:00', terminada_en: '2026-10-26T15:03:00+00:00',
    ended_by: 'operator', error: null, congelado: { tag: 'informe-2026', ok: true, items: [] },
  },
  resumen: {
    video: 'video.mp4', fps_efectivos: 4.6, faltantes: [], errores: [],
    cuadros_clave: [
      { alerta: 1, tipo: 'evidencia', archivo: 'cuadros/alerta01_CR-01_1-evidencia.jpg', frame_index: 10 },
      { alerta: 1, tipo: 'confirmacion', archivo: 'cuadros/alerta01_CR-01_2-confirmacion.jpg', frame_index: 30 },
    ],
  },
  linea_de_tiempo: [{
    n: 1, alert_id: 'al-1', condition_id: 'CR-01', severity: 'high',
    frame_primera_evidencia: 10, frame_confirmacion: 30, frame_resolucion: null,
    t_primera_evidencia_ms: 1000, t_confirmacion_ms: 5100, t_resolucion_ms: null,
    confirmed_wall_ms: 1, t_broker_ms: 13, broker_topic: 'eovrt/alerts/high', entrega: 'delivered',
    tramos: { evidencia_a_confirmacion_ms: 4100, confirmacion_a_broker_ms: 12 },
  }],
  testigo: [], state_log: [], respaldo: false,
}
const CIFRAS_PENDIENTES: DemoCifra[] = [
  { prueba: 'ALR-01', clave: 'f1', que_es: 'F1', valor: null, unidad: null, pendiente: true, texto: 'cifra pendiente (generación 2)' },
]

function instalar(motor: DemoState['motor'], cifras: DemoCifra[] = CIFRAS_PENDIENTES, detalle: DemoSessionDetail = DETALLE) {
  rutas = {
    [`/api/demo/sessions/${SID}`]: () => json(detalle),
    '/api/demo/cifras': () => json(cifras),
    '/api/demo/camaras': () => json([]),
    '/api/demo/modos': () => json(MODOS),
    '/api/demo/state': () => json({ fase: 'done', session_id: SID, stack: 'compose', motor }),
    '/api/demo/preflight': () => json({ listo: true, items: [], congelado: { tag: null, ok: true, items: [] }, motor, stack: 'compose', comprobado_en: '' }),
    '/api/documentacion': () => json({ terminos: {} }),
  }
}

beforeEach(() => {
  inesperadas = []
  globales = false
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname
    const ruta = rutas[path]
    if (ruta) return ruta()
    if (globales && !path.startsWith('/api/demo/')) return json({ detail: 'fuera de la demo' }, 503)
    inesperadas.push(path)
    return json({ detail: 'sin fixture' }, 500)
  }))
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(inesperadas).toEqual([])
})

const montar = (ruta = `/demo/resultado/${SID}?proyectar=1`) =>
  render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>)
const tecla = (key: string) => act(() => { fireEvent.keyDown(window, { key }) })

describe('/demo/resultado/:id', () => {
  it('muestra el video, los cuadros clave y los dos tramos de cada alerta', async () => {
    instalar({ estado: 'fresco' })
    const { container } = montar()
    expect(await screen.findByRole('heading', { name: 'Resultado de la demo' })).toBeTruthy()
    const video = container.querySelector('video')
    expect(video?.getAttribute('src')).toBe(`/api/demo/sessions/${SID}/archivo/resultado/video.mp4`)
    expect(screen.getByText(/Se ven exactamente los cuadros que procesó el sistema \(≈ 4,6 cuadros\/s efectivos\)/)).toBeTruthy()
    const alerta = screen.getByRole('region', { name: 'Alerta 1' })
    expect(within(alerta).getByAltText('Primera evidencia, cuadro 10')).toBeTruthy()
    expect(within(alerta).getByAltText('Confirmación, cuadro 30')).toBeTruthy()
    expect(within(alerta).getByText(/4,1/).textContent).toMatch(/no es un\s+requisito de latencia/)
    expect(within(alerta).getByText(/12 ms/)).toBeTruthy()
  })

  it('la tarjeta remite a las cifras de la generación 2 y las marca pendientes si no están', async () => {
    instalar({ estado: 'fresco' })
    montar()
    const tarjeta = await screen.findByRole('region', { name: 'Qué muestra y qué no muestra esta demo' })
    expect(within(tarjeta).getAllByText(/cifra pendiente \(generación 2\)/).length).toBeGreaterThan(0)
    expect(tarjeta.textContent).toMatch(/revisión\s+dirigida del 2026-10-26/)
  })

  it('con ?respaldo=1 se rotula como el ensayo en esta sala', async () => {
    instalar({ estado: 'fresco' })
    montar(`/demo/resultado/${SID}?respaldo=1&proyectar=1`)
    expect(await screen.findByText(/Ensayo del .* en esta sala/)).toBeTruthy()
  })

  it('L vuelve a Listo solo con el motor fresco', async () => {
    instalar({ estado: 'reiniciando' })
    montar()
    await screen.findByRole('heading', { name: 'Resultado de la demo' })
    await waitFor(() => expect(screen.getByLabelText('Teclas').textContent).toMatch(/reiniciando el motor/))
    await tecla('l')
    expect(await screen.findByText(/L funciona cuando quede fresco/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Resultado de la demo' })).toBeTruthy()
  })

  it('L con el motor fresco vuelve a /demo', async () => {
    instalar({ estado: 'fresco' })
    montar()
    await screen.findByRole('heading', { name: 'Resultado de la demo' })
    await waitFor(() => expect(screen.getByLabelText('Teclas').textContent).not.toMatch(/reiniciando/))
    await new Promise((r) => setTimeout(r, 50))
    await tecla('l')
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
  })
})

describe('/demo/resultado/:id — moverse y modos', () => {
  it('L conserva la variante de ensayo y la proyección al volver a Listo', async () => {
    instalar({ estado: 'fresco' })
    montar(`/demo/resultado/${SID}?variante=ensayo&proyectar=1`)
    await screen.findByRole('heading', { name: 'Resultado de la demo' })
    await waitFor(() => expect(screen.getByLabelText('Teclas').textContent).not.toMatch(/reiniciando/))
    await new Promise((r) => setTimeout(r, 50))
    await tecla('l')
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
    expect(screen.getByText(/la entrada es una grabación/)).toBeTruthy()
    expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull()
  })

  it('dentro de la consola se ve con la navegación y el botón Volver a Listo', async () => {
    instalar({ estado: 'fresco' })
    globales = true
    montar(`/demo/resultado/${SID}`)
    expect(await screen.findByRole('heading', { name: 'Resultado de la demo' })).toBeTruthy()
    expect(screen.getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
    // Deshabilitado hasta que el motor queda fresco (no hay carrera con el estado). Se
    // relee el botón: al llegar el detalle la cabecera se vuelve a montar.
    const volver = () => screen.getByRole('button', { name: /Volver a Listo/ }) as HTMLButtonElement
    await waitFor(() => expect(volver().disabled).toBe(false))
    fireEvent.click(volver())
    expect(await screen.findByRole('heading', { name: /Demo en vivo/ })).toBeTruthy()
    expect(screen.getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
  })
})

describe('/demo/resultado/:id — Volver a Listo con el motor reiniciando', () => {
  it('el botón queda deshabilitado y lo explica', async () => {
    instalar({ estado: 'reiniciando' })
    globales = true
    montar(`/demo/resultado/${SID}`)
    await screen.findByRole('toolbar', { name: 'Acciones del resultado' })
    const volver = () => screen.getByRole('button', { name: /Volver a Listo/ }) as HTMLButtonElement
    await waitFor(() => expect(volver().title).toMatch(/se está reiniciando/))
    expect(volver().disabled).toBe(true)
  })
})

describe('/demo/resultado/:id — sesión con otro modo de prompts', () => {
  const CON_MODO: DemoSessionDetail = {
    ...DETALLE,
    session: { ...DETALLE.session!, session_id: SID, modo_prompts: MODO_EDIR_SESION },
  }

  it('en la consola avisa que no es la configuración congelada ni cuenta como ensayo', async () => {
    instalar({ estado: 'fresco' }, CIFRAS_PENDIENTES, CON_MODO)
    globales = true
    montar(`/demo/resultado/${SID}`)
    expect(await screen.findByText('Modo E-DIR: no es la configuración congelada; no cuenta como ensayo.')).toBeTruthy()
  })

  it('en la proyección lo dice en la cabecera, con las frases', async () => {
    instalar({ estado: 'fresco' }, CIFRAS_PENDIENTES, CON_MODO)
    montar()
    const linea = await screen.findByRole('note', { name: 'Modo de prompts' })
    expect(linea.textContent).toMatch(/^Modo E-DIR: no es la configuración congelada; no cuenta como ensayo/)
    expect(linea.textContent).toMatch(/cr02_obs «person without bright colored safety clothing»/)
  })

  it('la capa de evidencia también lo dice', async () => {
    instalar({ estado: 'fresco' }, CIFRAS_PENDIENTES, CON_MODO)
    rutas['/api/demo/stack'] = () => json({ modo: 'compose', contenedores: [], error: null, host: { presente: false }, repos: [], servicios: {} })
    montar()
    await screen.findByRole('heading', { name: 'Resultado de la demo' })
    await tecla('e')
    const capa = await screen.findByRole('dialog', { name: 'Capa de evidencia' })
    expect(within(capa).getByRole('region', { name: 'Configuración congelada' }).textContent)
      .toMatch(/Modo E-DIR: no es la configuración congelada; no cuenta como ensayo/)
  })

  it('con el campeón no hay aviso de modo', async () => {
    instalar({ estado: 'fresco' })
    montar()
    await screen.findByRole('heading', { name: 'Resultado de la demo' })
    expect(screen.queryByRole('note', { name: 'Modo de prompts' })).toBeNull()
    expect(screen.queryByText(/no es la configuración congelada/)).toBeNull()
  })
})
