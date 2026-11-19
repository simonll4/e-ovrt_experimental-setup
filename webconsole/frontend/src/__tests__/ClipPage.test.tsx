import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, within } from '../test-utils'
import ClipPage from '../pages/ClipPage'
import FalsasAlarmasUnaPorUna from '../pages/gen2/FalsasAlarmasUnaPorUna'
import type { ClipDePrueba, FalsasAlarmasErr01 } from '../types'

/** «Mostrame un run donde pasó esto» (revisión del 2026-11-19). Se mockea `fetch`, no el módulo de API. */
const CLIP: ClipDePrueba = {
  prueba: 'ALR-08', clip: 'v01_c01', tipo_clip: 'obra_real', lectura: null, lecturas: [null], fps: 30, duracion_ms: 37000,
  conteos: { episodios: 0, aciertos: 0, perdidos: 0, falsas_alarmas: 2, re_alertas: 0, censurados: 0 },
  episodios: [],
  alertas: [
    { alert_id: 'fa-1', condicion: 'CR-01', tipo: 'falsa_alarma', cuadro: 120, ms: 4000, motivo: 'outside_all_episode_windows',
      causa: 'P-no-detectado', caja: [1, 2, 3, 4], sujeto: 'subject_001', primera_evidencia_ms: 0 },
    { alert_id: 'fa-2', condicion: 'CR-02', tipo: 'falsa_alarma', cuadro: 219, ms: 7300, motivo: 'outside_all_episode_windows',
      causa: 'P-intermitente', caja: [1, 2, 3, 4], sujeto: 'subject_002', primera_evidencia_ms: 6000 },
  ],
  alertas_completas: true, cuadros: true, cajas: true, video: true, faltan: [],
  origen: { evaluacion: 'results/gen2/ALR-08/evals/eval_v01_c01.json', experiment_id: 'exp_x', media_run_id: 'run_x', control_run_id: 'ctl_x' },
}
const ERR01: FalsasAlarmasErr01 = {
  prueba_de_las_alertas: 'ALR-08',
  falsas_alarmas: [
    { alert_id: 'fa-1', clip: 'v01_c01', condicion: 'CR-01', causa: 'P-no-detectado', cuadro: 120, banda: '120-220', iluminacion: 'diurna' },
    { alert_id: 'fa-2', clip: 'v01_c01', condicion: 'CR-02', causa: 'P-intermitente', cuadro: 219, banda: null, iluminacion: 'diurna' },
  ],
}

let urls: string[]
beforeEach(() => {
  urls = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url.pathname + url.search)
    if (url.pathname === '/api/gen2/pruebas/ALR-08/clips/v01_c01') return new Response(JSON.stringify(CLIP))
    if (url.pathname === '/api/gen2/pruebas/ERR-01/falsas-alarmas') return new Response(JSON.stringify(ERR01))
    return new Response('{}', { status: 404 })
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const abrir = (ruta: string) => render(
  <MemoryRouter initialEntries={[ruta]}>
    <Routes>
      <Route path="/resultados/:id/clips/:clip" element={<ClipPage />} />
      <Route path="/resultados/ERR-01" element={<FalsasAlarmasUnaPorUna />} />
    </Routes>
  </MemoryRouter>,
)

describe('El run de un clip', () => {
  it('abre en la alerta que pide la dirección, con su causa, su cuadro con cajas y la persona acercada', async () => {
    abrir('/resultados/ALR-08/clips/v01_c01?alerta=fa-2')
    expect(await screen.findByText(/falsas alarmas/)).toBeTruthy()
    expect(screen.getByText('EPP visto de a ratos.', { exact: false })).toBeTruthy()
    const imagenes = screen.getAllByRole('img', { hidden: true }).map((i) => i.getAttribute('src'))
    expect(imagenes).toContain('/api/gen2/pruebas/ALR-08/clips/v01_c01/cuadro/219?alerta=fa-2')
    expect(imagenes).toContain('/api/gen2/pruebas/ALR-08/clips/v01_c01/cuadro/219?alerta=fa-2&acercar=true')
    expect(urls).toContain('/api/gen2/pruebas/ALR-08/clips/v01_c01')
  })

  it('sin alerta pedida abre en la primera falsa alarma; «Ver» en la tabla cambia lo que se muestra', async () => {
    abrir('/resultados/ALR-08/clips/v01_c01')
    await screen.findByText('EPP no detectado.', { exact: false })
    const tabla = screen.getByRole('table', { name: 'Las alertas' })
    fireEvent.click(within(tabla).getAllByRole('button', { name: 'Ver' })[1])
    expect(screen.getByText('EPP visto de a ratos.', { exact: false })).toBeTruthy()
  })

  it('cada marca de la línea de tiempo se elige con el teclado', async () => {
    abrir('/resultados/ALR-08/clips/v01_c01')
    const marca = await screen.findByRole('button', { name: /Falsa alarma de CR-02 a los 7,3 s/ })
    fireEvent.keyDown(marca, { key: 'Enter' })
    expect(screen.getByText('EPP visto de a ratos.', { exact: false })).toBeTruthy()
  })
})

describe('Las falsas alarmas de ERR-01, una por una', () => {
  it('filtra por la causa de la dirección y cada una abre su clip en el run de ALR-08', async () => {
    abrir('/resultados/ERR-01?causa=P-intermitente')
    const tabla = await screen.findByRole('table', { name: 'Las falsas alarmas, una por una' })
    const enlaces = within(tabla).getAllByRole('link')
    expect(enlaces).toHaveLength(1)
    expect(enlaces[0].getAttribute('href')).toBe('/resultados/ALR-08/clips/v01_c01?alerta=fa-2')
  })
})
