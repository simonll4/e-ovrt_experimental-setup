import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import { separarEtiquetas } from '../components/charts/LineasPorPunto'
import ComoSeVe from '../pages/preguntas/ComoSeVe'
import type { CifraPregunta, FiguraInforme, VistaFiguras } from '../types'

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function http(vista: VistaFiguras | null) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    if (url.pathname === '/api/figuras' && vista) return json(vista)
    return json({ detail: 'sin fixture' }, 404)
  }))
}

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const cifra = (valor: number, extra: Partial<CifraPregunta> = {}): CifraPregunta => ({ ok: true, valor, prueba: 'ERR-01', ...extra })

const figura = (over: Partial<FiguraInforme>): FiguraInforme => ({
  id: 'x', numero: 1, titulo: 'Una figura', preguntas: ['obra-real'], seccion: '§17.5.4', prueba: 'ERR-01',
  pie: 'El pie de la figura.', privada: false, solo_informe: false, pendiente: null, fuente: {}, grafico: null,
  destino: null, disponible: false, url: null, ...over,
})

const VISTA: VistaFiguras = {
  errores: [],
  figuras: [
    figura({ id: 'obra-real-cuadro', numero: 6, titulo: 'Una falsa alarma en obra real', privada: true,
             fuente: { archivo: 'defensa/figuras/x.png' }, destino: 'defensa/capturas/figuras/figura-06-obra-real-cuadro.png' }),
    figura({ id: 'por-causa', numero: 7, titulo: 'Las falsas alarmas por causa', grafico: {
      tipo: 'barras', unidad: 'falsas alarmas', barras: [
        { etiqueta: 'EPP no detectado', aparte: false, cifra: cifra(109) },
        { etiqueta: 'EPP fuera de la región evaluada', aparte: false, cifra: cifra(0) },
        { etiqueta: 'De más por fragmentación de identidad', aparte: true, cifra: cifra(93) },
      ] } }),
    figura({ id: 'f1', numero: 8, titulo: 'El F1 según los cuadros por segundo', preguntas: ['en-vivo', 'obra-real'], grafico: {
      tipo: 'lineas', series: ['Por escena', 'Por sujeto'], puntos: [
        { etiqueta: 'Banco', valores: [cifra(0.84058, { decimales: 2 }), cifra(0.898551, { decimales: 2 })] },
        { etiqueta: 'Peor caso', valores: [cifra(0.615385, { decimales: 2 }), cifra(0.67742, { decimales: 2 })] },
      ] } }),
    figura({ id: 'mensaje', numero: 3, titulo: 'El mensaje que recibió el broker', fuente: { pantalla: '/demo/resultado/s1', selector: '#m' },
             disponible: true, url: '/api/figuras/mensaje/imagen' }),
    figura({ id: 'chaleco', numero: 5, titulo: 'El chaleco falso', pendiente: 'Hace falta elegir el cuadro de cada toma.' }),
    figura({ id: 'otra', numero: 10, titulo: 'De otra pregunta', preguntas: ['que-detecta'], disponible: true, url: '/api/figuras/otra/imagen' }),
  ],
}

const montar = () => render(
  <MemoryRouter initialEntries={['/']}>
    <Routes><Route path="/" element={<ComoSeVe preguntaId="obra-real" />} /></Routes>
  </MemoryRouter>,
)

describe('«Cómo se ve»: las figuras de una pregunta (plan §8)', () => {
  it('muestra solo las figuras de esa pregunta que tienen fuente, en orden', async () => {
    http({ ...VISTA, figuras: [...VISTA.figuras].map((f) => ({ ...f, preguntas: f.id === 'mensaje' ? ['obra-real'] : f.preguntas })) })
    montar()
    await screen.findByText('Cómo se ve')
    const titulos = screen.getAllByRole('figure').map((f) => f.getAttribute('aria-labelledby'))
    expect(titulos).toEqual(['figura-obra-real-cuadro', 'figura-por-causa', 'figura-f1', 'figura-mensaje'])
    expect(screen.queryByText('El chaleco falso')).toBeNull()
    expect(screen.queryByText('De otra pregunta')).toBeNull()
  })

  it('las barras llevan la cifra resuelta y lo que va aparte va separado', async () => {
    http(VISTA)
    const { container } = montar()
    const lienzo = await vi.waitFor(() => {
      const el = container.querySelector('[data-figura="por-causa"]')
      if (!el) throw new Error('todavía no')
      return el as HTMLElement
    })
    const principal = within(lienzo).getByRole('list', { name: 'Las falsas alarmas por causa' })
    expect(within(principal).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'EPP no detectado109', 'EPP fuera de la región evaluada0'])
    const aparte = within(lienzo).getByRole('list', { name: 'Las falsas alarmas por causa, aparte' })
    expect(aparte.textContent).toBe('De más por fragmentación de identidad93')
    expect(within(lienzo).getByText('falsas alarmas')).toBeTruthy()
  })

  it('las líneas tienen leyenda, la última cifra al final y la tabla con todas', async () => {
    http(VISTA)
    const { container } = montar()
    const lienzo = await vi.waitFor(() => {
      const el = container.querySelector('[data-figura="f1"]')
      if (!el) throw new Error('todavía no')
      return el as HTMLElement
    })
    expect(within(lienzo).getByRole('img', { name: 'El F1 según los cuadros por segundo' })).toBeTruthy()
    expect(lienzo.querySelectorAll('.eo-lineas__leyenda li')).toHaveLength(2)
    expect([...lienzo.querySelectorAll('.eo-lineas__final')].map((t) => t.textContent)).toEqual(['Por escena 0,62', 'Por sujeto 0,68'])
    const tabla = screen.getByRole('table', { name: 'Cifras: El F1 según los cuadros por segundo' })
    expect(within(tabla).getAllByRole('row').map((r) => r.textContent)).toEqual([
      'PuntoPor escenaPor sujeto', 'Banco0,840,90', 'Peor caso0,620,68'])
  })

  it('una imagen que ya se sacó se ve; una privada que no está lo dice', async () => {
    http({ ...VISTA, figuras: VISTA.figuras.map((f) => (f.id === 'mensaje' ? { ...f, preguntas: ['obra-real'] } : f)) })
    montar()
    const img = await screen.findByRole('img', { name: 'El mensaje que recibió el broker' })
    expect(img.getAttribute('src')).toBe('/api/figuras/mensaje/imagen')
    expect(screen.getByRole('link', { name: 'esta pantalla' }).getAttribute('href')).toBe('/demo/resultado/s1')
    expect(screen.getByText('No está en este equipo: tiene personas o cuadros de terceros y no se publica.')).toBeTruthy()
  })

  it('sin figuras para la pregunta no muestra el bloque; si no se pudieron leer, lo dice', async () => {
    http({ errores: [], figuras: [] })
    const { container } = montar()
    await vi.waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalled())
    expect(container.textContent).toBe('')
    cleanup()
    http(null)
    montar()
    expect(await screen.findByText(/No se pudieron leer las figuras/)).toBeTruthy()
  })
})

describe('las etiquetas del final de cada línea no se pisan', () => {
  it('separa las que quedan a menos del mínimo y respeta el orden', () => {
    expect(separarEtiquetas([100, 104], 16)).toEqual([100, 116])
    expect(separarEtiquetas([104, 100], 16)).toEqual([116, 100])
    expect(separarEtiquetas([10, 80], 16)).toEqual([10, 80])
  })
})
