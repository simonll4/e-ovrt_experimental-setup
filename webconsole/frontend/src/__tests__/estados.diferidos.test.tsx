import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import ExperimentsPage from '../pages/ExperimentsPage'
import CatalogPage from '../pages/CatalogPage'
import PromptSetsPage from '../pages/PromptSetsPage'
import CamerasPage from '../pages/CamerasPage'
import TargetBadge from '../components/TargetBadge'
import TraceSection from '../components/TraceSection'
import RunDetailPage from '../pages/RunDetailPage'
import { Route, Routes } from 'react-router-dom'

/** Una respuesta que se resuelve cuando el test lo decide: es lo que permite
 *  mirar la pantalla MIENTRAS espera, que es donde aparecían los falsos vacíos. */
function diferido() {
  let resolver!: (r: Response) => void
  const promesa = new Promise<Response>((r) => { resolver = r })
  return { promesa, resolver }
}

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

/** Todas las peticiones quedan pendientes salvo las que el test responde. */
function pendiente(responder: (url: URL) => Response | Promise<Response> | undefined = () => undefined) {
  const colgadas: Array<ReturnType<typeof diferido>> = []
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    const r = responder(url)
    if (r) return Promise.resolve(r)
    const d = diferido()
    colgadas.push(d)
    return d.promesa
  }))
  return colgadas
}

const montar = (ui: ReactElement, ruta = '/') => render(<MemoryRouter initialEntries={[ruta]}>{ui}</MemoryRouter>)

describe('Consulta pendiente: estructura estable, sin falsos vacíos ni ceros', () => {
  it('Experimentos mantiene la cabecera y anuncia la espera, sin decir que no hay manifiestos', async () => {
    pendiente()
    montar(<ExperimentsPage />, '/experiments')
    expect(screen.getByRole('heading', { level: 1, name: 'Experimentos' })).toBeTruthy()
    expect(screen.getByRole('status').textContent).toMatch(/Cargando el catálogo de manifiestos/)
    expect(screen.queryByText(/Sin manifiestos/)).toBeNull()
  })

  it('Nuevo experimento titula en contexto aunque el catálogo no haya respondido', () => {
    pendiente()
    montar(<ExperimentsPage />, '/experiments/new')
    expect(screen.getByRole('heading', { level: 1, name: 'Nuevo experimento' })).toBeTruthy()
  })

  it('Catálogos no presenta listas vacías mientras cada catálogo carga', () => {
    pendiente()
    montar(<CatalogPage />, '/catalog')
    expect(screen.queryByText('Sin orígenes de imágenes')).toBeNull()
    expect(screen.queryByText('Sin conjuntos de imágenes')).toBeNull()
    expect(screen.queryByText('Sin conjuntos de prompts')).toBeNull()
    expect(screen.queryByText('Servicio no listo')).toBeNull()
    expect(screen.getAllByRole('status').length).toBeGreaterThanOrEqual(3)
  })

  it('Conjuntos de prompts no dice "sin conjuntos" mientras la lista carga', () => {
    pendiente()
    montar(<PromptSetsPage />, '/prompts')
    expect(screen.queryByText(/Sin conjuntos de prompts todavía/)).toBeNull()
    expect(screen.getByText(/Cargando los conjuntos de prompts/)).toBeTruthy()
  })

  it('Cámaras no muestra el vacío grande mientras la lista carga', () => {
    pendiente()
    montar(<CamerasPage />, '/cameras')
    expect(screen.queryByText('Todavía no guardaste ninguna cámara')).toBeNull()
    expect(screen.getByText(/Cargando las cámaras guardadas/)).toBeTruthy()
  })

  it('la insignia de instancia arranca verificando, no con una alarma', () => {
    pendiente()
    montar(<TargetBadge />)
    expect(screen.getByText('Verificando instancia')).toBeTruthy()
    expect(screen.queryByText(/Sin conexión/)).toBeNull()
  })

  it('el detalle de corrida conserva su cabecera mientras espera', () => {
    pendiente()
    montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>, '/runs/run_x')
    expect(screen.getByRole('heading', { level: 1, name: 'run_x' })).toBeTruthy()
    expect(screen.getByRole('status').textContent).toMatch(/Cargando la corrida run_x/)
  })
})

describe('Consulta fallida: error recuperable, distinto de un vacío', () => {
  it('la insignia distingue la falta de conexión con la consola', async () => {
    pendiente((url) => (url.pathname === '/api/target' ? json({ detail: 'x' }, 503) : undefined))
    montar(<TargetBadge />)
    // Los 5xx se reintentan dos veces antes de declarar el fallo.
    await waitFor(() => expect(screen.getByText('Sin conexión con la consola')).toBeTruthy(), { timeout: 8000 })
  }, 10000)

  it('la traza que no se pudo leer no se declara inexistente, y se puede reintentar', async () => {
    let intentos = 0
    pendiente((url) => {
      if (url.pathname.endsWith('/trace')) {
        intentos++
        return json({ detail: 'caído' }, 404)
      }
      return undefined
    })
    montar(<TraceSection runId="r" totals={null} />)
    expect(await screen.findByText(/No se pudo leer la traza de esta corrida/)).toBeTruthy()
    expect(screen.queryByText('Esta corrida no tiene traza')).toBeNull()
    const antes = intentos
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() => expect(intentos).toBeGreaterThan(antes))
  })

  it('un refresco fallido conserva los últimos cuadros y avisa que pueden estar viejos', async () => {
    vi.useFakeTimers()
    try {
      const frame = (i: number) => ({
        frame_index: i, unit_id: `u${i}`, timestamp_ms: i * 100, detections: [], control: 'received',
        progress: [], alert: [], active_patterns: [],
      })
      let llamadas = 0
      pendiente((url) => {
        if (!url.pathname.endsWith('/trace')) return undefined
        llamadas++
        // La primera lectura responde; los refrescos de la corrida viva fallan.
        if (llamadas > 1) return json({ detail: 'caído' }, 404)
        return json({
          media_run_id: 'r', control_run_id: null, topology: null, control_error: null,
          totals: { frames: 2, detections: 0, dropped_by_reason: {}, alerts: 0, received: 2, not_received: 0 },
          page: 1, page_size: 200, total: 2, frames: [frame(0), frame(1)],
        })
      })
      montar(<TraceSection runId="r" totals={null} running />)
      await act(async () => { await vi.advanceTimersByTimeAsync(10) })
      expect(within(screen.getByRole('listbox')).getAllByRole('option')).toHaveLength(2)
      await act(async () => { await vi.advanceTimersByTimeAsync(4_100) })
      expect(screen.getByText(/No se pudo actualizar la traza/)).toBeTruthy()
      // Los cuadros conocidos siguen a la vista: el fallo no se volvió un vacío.
      expect(within(screen.getByRole('listbox')).getAllByRole('option')).toHaveLength(2)
      expect(screen.queryByText('Esta corrida no tiene traza')).toBeNull()
    } finally {
      vi.useRealTimers()
    }
  })
})
