import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, waitFor } from '../test-utils'
import Termino, { GlosarioProvider } from '../components/Glosario'
import { TERMINOS_MARCADOS } from '../terminos'
import type { Documentacion } from '../types'

/** La regla que no se negocia: un término SIN definición se renderiza como
 *  texto plano, nunca como algo clickeable que no dice nada.
 *
 *  Este proyecto arrastra un defecto que apareció ocho veces —una ausencia de
 *  dato convertida en una afirmación— y un chip marcado que al abrirlo no
 *  explica nada es exactamente eso. El test de repositorio
 *  (`test_terminos_marcados_en_el_codigo_estan_definidos`, backend) evita que
 *  llegue a este punto; esto afirma qué pasa si igual llegara. */
const definicion = {
  id: 'CR-01', termino: 'CR-01', definicion: 'Presencia de persona sin casco.',
  mono: true, nivel: null, result_ids: [], familia: 'condiciones',
  familia_titulo: 'Condiciones de riesgo',
}
const cuerpo: Partial<Documentacion> = {
  available: true, message: null, metodo: [], aportes: [], vocabulario: [],
  colisiones: [], terminos: { 'CR-01': definicion },
}

let urls: URL[]
beforeEach(() => {
  urls = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    if (url.pathname === '/api/documentacion') return new Response(JSON.stringify(cuerpo))
    throw new Error(`no se debe consultar ${url}`)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const montar = (ui: React.ReactNode) => render(
  <MemoryRouter><GlosarioProvider>{ui}</GlosarioProvider></MemoryRouter>,
)

describe('Termino', () => {
  it('marca el término definido y lo enlaza a su entrada en la documentación', async () => {
    montar(<Termino id="CR-01" />)
    const enlace = await screen.findByRole('link', { name: 'CR-01' })
    expect(enlace.getAttribute('href')).toBe('/documentacion#CR-01')
    expect(enlace.getAttribute('title')).toContain('Presencia de persona sin casco.')
    expect(enlace.className).toContain('eo-termino')
  })

  it('un término SIN definición es texto plano, nunca un enlace mudo', async () => {
    montar(<Termino id="no_existe">Texto visible</Termino>)
    await waitFor(() => expect(urls.length).toBe(1))
    expect(screen.getByText('Texto visible')).toBeTruthy()
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('respeta el texto que le pasa la pantalla: el glosario no reescribe la celda', async () => {
    montar(<Termino id="CR-01">CR-01 — Presencia de persona sin casco</Termino>)
    const enlace = await screen.findByRole('link', {
      name: 'CR-01 — Presencia de persona sin casco',
    })
    expect(enlace).toBeTruthy()
  })

  it('sin provider no pide nada y cae a texto plano', async () => {
    render(<MemoryRouter><Termino id="CR-01">CR-01</Termino></MemoryRouter>)
    expect(screen.getByText('CR-01')).toBeTruthy()
    expect(screen.queryByRole('link')).toBeNull()
    expect(urls).toEqual([])
  })

  it('el provider no consulta nada hasta que se monta el primer término', async () => {
    montar(<p>Una pantalla sin términos marcados</p>)
    await screen.findByText('Una pantalla sin términos marcados')
    expect(urls).toEqual([])
  })

  it('varios términos comparten una sola petición', async () => {
    montar(<><Termino id="CR-01" /><Termino id="CR-01" /><Termino id="otro" /></>)
    await waitFor(() => expect(screen.getAllByRole('link')).toHaveLength(2))
    expect(urls.filter((u) => u.pathname === '/api/documentacion')).toHaveLength(1)
  })
})

describe('El alcance declarado de términos marcados', () => {
  it('no tiene ids repetidos y cubre las familias del alcance inicial', () => {
    expect(new Set(TERMINOS_MARCADOS).size).toBe(TERMINOS_MARCADOS.length)
    for (const id of ['T1', 'R6', 'CR-01', 'CR-02', 'L1', 'L8', 'DBE', 'EBE',
      'run_id', 'experiment_id', 'clip_id', 'track_id', 'clase_resultado']) {
      expect(TERMINOS_MARCADOS).toContain(id)
    }
  })
})
