import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, within } from '../test-utils'
import DemoSesionesPage from '../pages/DemoSesionesPage'
import { crumbsFor } from '../nav'
import type { DemoSesionFila } from '../types'

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Stub de `fetch` (como el contrato: se mockea el transporte, no el módulo de API). */
function http(responder: (url: URL) => Response | undefined) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    return responder(url) ?? json({ detail: 'sin fixture' }, 404)
  }))
}

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const sesion = (over: Partial<DemoSesionFila>): DemoSesionFila => ({
  session_id: 'demo_20261107T160250Z_P1', variante: 'oakd', fase: 'done', iniciada_en: '2026-11-07T16:02:50+00:00',
  ended_by: 'operator', respaldo: false, escena: 'P1', exploracion: null, modo_prompts: null,
  tiene_resultado: true, archivada: true, ...over,
})

const SESIONES: DemoSesionFila[] = [
  sesion({}),
  sesion({ session_id: 'demo_20261107T183422Z_DEMO_exp', escena: 'DEMO',
           exploracion: { motor: 'mp-yoloe-26s', modelo: 'yoloe/yoloe-26s', camara: '960x540@15' } }),
  sesion({ session_id: 'demo_20261031T120000Z', escena: null, archivada: false, tiene_resultado: false, fase: 'failed' }),
]

const montar = () => render(<MemoryRouter><DemoSesionesPage /></MemoryRouter>)

describe('Sesiones guardadas (/demo/sesiones)', () => {
  it('lista las sesiones con su escena, su configuración y de dónde vienen, y abre el resultado', async () => {
    http((u) => (u.pathname === '/api/demo/sessions' ? json(SESIONES) : undefined))
    montar()
    const tabla = await screen.findByRole('table', { name: 'Sesiones guardadas' })
    expect(screen.getByText('3 sesiones · 2 de las jornadas en vivo')).toBeTruthy()
    const [, p1, exp, propia] = within(tabla).getAllByRole('row')
    expect(within(p1).getByText('Configuración del informe')).toBeTruthy()
    expect(within(p1).getByText('jornada en vivo')).toBeTruthy()
    expect(within(p1).getByRole('link', { name: 'demo_20261107T160250Z_P1' }).getAttribute('href'))
      .toBe('/demo/resultado/demo_20261107T160250Z_P1')
    expect(within(exp).getByText('mp-yoloe-26s · 960x540@15')).toBeTruthy()
    // Una sesión sin el resultado armado no ofrece un enlace que daría una pantalla vacía.
    expect(within(propia).getByText('esta consola')).toBeTruthy()
    expect(within(propia).getByText('falló')).toBeTruthy()
    expect(within(propia).queryByRole('link')).toBeNull()
  })

  it('filtra por escena, fecha o motor', async () => {
    http((u) => (u.pathname === '/api/demo/sessions' ? json(SESIONES) : undefined))
    montar()
    const tabla = await screen.findByRole('table', { name: 'Sesiones guardadas' })
    fireEvent.change(screen.getByRole('searchbox', { name: 'Filtrar sesiones' }), { target: { value: 'yoloe' } })
    expect(within(tabla).getAllByRole('row')).toHaveLength(2)
    expect(screen.getByText('1 de 3')).toBeTruthy()
  })

  it('sin sesiones dice de dónde salen, sin romper', async () => {
    http((u) => (u.pathname === '/api/demo/sessions' ? json([]) : undefined))
    montar()
    expect(await screen.findByText('Todavía no hay sesiones')).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('las migas llevan de un resultado a la lista y a la demo', () => {
    expect(crumbsFor('/demo/sesiones').map((c) => c.to)).toEqual(['/demo', '/demo/sesiones'])
    expect(crumbsFor('/demo/resultado/demo_x').map((c) => c.to))
      .toEqual(['/demo', '/demo/sesiones', '/demo/resultado/demo_x'])
  })
})
