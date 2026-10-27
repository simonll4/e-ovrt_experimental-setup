import { MemoryRouter } from 'react-router-dom'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import type { DemoCifra, DemoSessionDetail, DemoState } from '../types'

let rutas: Record<string, () => Response> = {}
let inesperadas: string[] = []

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

function instalar(motor: DemoState['motor'], cifras: DemoCifra[] = CIFRAS_PENDIENTES) {
  rutas = {
    [`/api/demo/sessions/${SID}`]: () => json(DETALLE),
    '/api/demo/cifras': () => json(cifras),
    '/api/demo/state': () => json({ fase: 'done', session_id: SID, stack: 'compose', motor }),
    '/api/demo/preflight': () => json({ listo: true, items: [], congelado: { tag: null, ok: true, items: [] }, motor, stack: 'compose', comprobado_en: '' }),
    '/api/documentacion': () => json({ terminos: {} }),
  }
}

beforeEach(() => {
  inesperadas = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const path = new URL(String(input), 'http://localhost').pathname
    const ruta = rutas[path]
    if (ruta) return ruta()
    inesperadas.push(path)
    return json({ detail: 'sin fixture' }, 500)
  }))
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(inesperadas).toEqual([])
})

const montar = (ruta = `/demo/resultado/${SID}`) =>
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
    montar(`/demo/resultado/${SID}?respaldo=1`)
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
