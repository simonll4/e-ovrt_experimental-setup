import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import DemoSesionesPage from '../pages/DemoSesionesPage'
import { crumbsFor } from '../nav'
import type { VistaTomas } from '../types'

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** Stub de `fetch` (como el contrato: se mockea el transporte, no el módulo de API). */
function http(responder: (url: URL) => Response | undefined) {
  const urls: URL[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    return responder(url) ?? json({ detail: 'sin fixture' }, 404)
  }))
  return urls
}

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const VISTA: VistaTomas = {
  pruebas: [
    { id: 'RT-04', tomas: [
      { session_id: 'demo_20261107T160250Z_P1', escena: 'P1', remera: 'blanca lisa', como_se_esperaba: false,
        sujeto_como_se_esperaba: true, disponible: true },
      { session_id: 'demo_20261107T161545Z_P1', escena: 'P1', remera: 'blanca lisa', como_se_esperaba: true,
        sujeto_como_se_esperaba: true, disponible: false },
    ] },
    { id: 'RT-06', tomas: [
      { session_id: 'demo_20261107T200449Z_P1', escena: 'P1', stream: 'secundario', como_se_esperaba: true, disponible: true },
    ] },
  ],
  otras: [
    { session_id: 'demo_20261107T151131Z_CAL', escena: 'CAL', disponible: true, tipo: 'calibracion',
      motivo: 'Calibración del encuadre antes de las tomas.' },
    { session_id: 'demo_20261107T160004Z_P1', escena: 'P1', disponible: true, tipo: 'descartada',
      motivo: 'Causa física: el actor esperó en el borde del cuadro.', quien: 'equipo E-OVRT-VDP', prueba: 'RT-04' },
  ],
}

const montar = () => render(<MemoryRouter><DemoSesionesPage /></MemoryRouter>)

describe('Tomas en vivo (/demo/sesiones, plan §6)', () => {
  it('agrupa las tomas por la prueba en la que cuentan, con su escena y si salió como el guion', async () => {
    const urls = http((u) => (u.pathname === '/api/tomas' ? json(VISTA) : undefined))
    montar()
    const rt04 = await screen.findByRole('table', { name: 'Tomas de RT-04' })
    expect(screen.getByRole('link', { name: 'Rodaje guionado en vivo RT-04' }).getAttribute('href')).toBe('/resultados/RT-04')
    expect(screen.getByText('1 de 2 como el guion')).toBeTruthy()
    expect(within(rt04).getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['Escena', 'Remera', 'Como el guion', 'Toma'])
    const [, primera, segunda] = within(rt04).getAllByRole('row')
    expect(within(primera).getByText(/por sujeto: sí/)).toBeTruthy()
    expect(within(primera).getByRole('link', { name: 'demo_20261107T160250Z_P1' }).getAttribute('href'))
      .toBe('/demo/resultado/demo_20261107T160250Z_P1')
    // Sin la carpeta de la toma en este equipo se dice, sin enlace roto (§6).
    expect(within(segunda).queryByRole('link')).toBeNull()
    expect(within(segunda).getByText(/el video no se publica/)).toBeTruthy()
    expect(within(screen.getByRole('table', { name: 'Tomas de RT-06' })).getAllByRole('columnheader').map((th) => th.textContent))
      .toEqual(['Escena', 'Stream', 'Como el guion', 'Toma'])
    expect(urls.map((u) => u.pathname)).toEqual(['/api/tomas'])
  })

  it('lo que no cuenta va plegado, con qué es y su motivo', async () => {
    http((u) => (u.pathname === '/api/tomas' ? json(VISTA) : undefined))
    montar()
    const titulo = await screen.findByRole('heading', { name: /Ensayos, calibraciones y tomas que no cuentan \(2\)/ })
    expect((titulo.closest('details') as HTMLDetailsElement).open).toBe(false)
    const tabla = screen.getByRole('table', { name: 'Tomas que no cuentan' })
    const descartada = within(tabla).getByRole('row', { name: /Descartada/ })
    expect(descartada.textContent).toMatch(/Causa física: el actor esperó en el borde del cuadro\. · firmó equipo E-OVRT-VDP en RT-04/)
    expect(within(tabla).getByRole('row', { name: /Calibración/ })).toBeTruthy()
  })

  it('las migas llevan de un resultado a «Tomas en vivo» (plan §3)', () => {
    expect(crumbsFor('/demo/sesiones')).toEqual([{ to: '/demo/sesiones', label: 'Tomas en vivo' }])
    expect(crumbsFor('/demo/resultado/demo_x').map((c) => c.to)).toEqual(['/demo/sesiones', '/demo/resultado/demo_x'])
  })
})
