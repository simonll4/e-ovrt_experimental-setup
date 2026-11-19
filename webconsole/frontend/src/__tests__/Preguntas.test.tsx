import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import App from '../App'
import InicioPage from '../pages/InicioPage'
import PreguntaPage from '../pages/PreguntaPage'
import { textoCifra } from '../pages/preguntas/comun'
import type { CifraPregunta, Pregunta, VistaPreguntas } from '../types'

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

const cifra = (valor: CifraPregunta['valor'], extra: Partial<CifraPregunta> = {}): CifraPregunta =>
  ({ ok: true, valor, prueba: 'ALR-01', ...extra })

const pregunta = (over: Partial<Pregunta>): Pregunta => ({
  id: 'que-agrega', titulo: '¿Qué agrega la plataforma sobre la detección?', informe: ['§17.5.4', 'Tabla 53'],
  titular: 'F1 {escena} por escena y {sujeto} por sujeto',
  respuesta: 'Con las mismas detecciones, F1 {escena} por escena y {sujeto} siguiendo a cada persona.',
  cifras: { escena: cifra(0.84058, { decimales: 3 }), sujeto: cifra(0.898551, { decimales: 3, prueba: 'ALR-02' }) },
  tablas: [{
    titulo: 'Alerta por episodio en el rodaje guionado', informe: 'Tabla 53', columnas: ['F1', 'Tiempo hasta la alerta'], nota: null,
    filas: [
      { nombre: 'Núcleo E-IND, escena', pruebas: ['ALR-01'],
        celdas: [[cifra(0.84058, { decimales: 3 })], [cifra(5.39, { decimales: 2, unidad: 's' })]] },
      { nombre: 'Núcleo E-IND, sujeto', pruebas: ['ALR-02', 'DEN-02'],
        celdas: [[cifra(0.898551, { decimales: 3, etiqueta: 'banco' }), cifra(0.83, { decimales: 3, etiqueta: 'vivo' })], null] },
    ],
  }],
  limites: ['Se mide contra una referencia anotada por una sola persona.'],
  ...over,
})

const VISTA: VistaPreguntas = {
  available: true,
  proyecto: {
    nombre: 'E-OVRT-VDP', titulo: 'Plataforma experimental de prueba', que_es: 'Una oración que dice qué es.',
    institucion: 'Institución', carrera: 'Carrera', autores: ['Autor Uno', 'Autora Dos'],
    enlaces: { informe: 'https://example.org/informe', repositorios: [{ nombre: 'repo-a', url: 'https://example.org/a' }] },
  },
  preguntas: [
    pregunta({ id: 'que-se-construyo', titulo: '¿Qué se construyó?', titular: 'La cadena completa; {perdidos} eventos perdidos',
               respuesta: 'Se perdieron {perdidos} eventos.', cifras: { perdidos: cifra(0, { decimales: 0 }) }, tablas: [] }),
    pregunta({}),
    pregunta({ id: 'confianza', titulo: '¿Cuánto se puede confiar en estas cifras?',
               titular: '{pruebas} pruebas escritas antes de correr', respuesta: '{pruebas} pruebas.',
               cifras: { pruebas: cifra(49, { prueba: null }) }, tablas: [], limites: [] }),
  ],
  pie: { pruebas: 49, desde: '2026-10-29', hasta: '2026-11-12', version: { commit: '656c088', fecha: '2026-11-13', de: 'resultados' } },
  errores: [],
}

const montarPregunta = (id: string) => render(
  <MemoryRouter initialEntries={[`/preguntas/${id}`]}>
    <Routes><Route path="/preguntas/:id" element={<PreguntaPage />} /></Routes>
  </MemoryRouter>,
)

describe('las cifras se resuelven, no se escriben (plan §9)', () => {
  it('formatea lo que resolvió el backend y nunca inventa un número', () => {
    expect(textoCifra(cifra(0.84058, { decimales: 3 }))).toBe('0,841')
    expect(textoCifra(cifra(5, { decimales: 2, unidad: '' }))).toBe('5,00')
    expect(textoCifra(cifra(6.2, { decimales: 1, unidad: 's' }))).toBe('6,2 s')
    expect(textoCifra(cifra(0.058, { decimales: 3, formato: 'signo' }))).toBe('+0,058')
    expect(textoCifra(cifra(-0.094, { decimales: 3, formato: 'signo' }))).toBe('-0,094')
    expect(textoCifra(cifra(0.9174, { decimales: 0, formato: 'porcentaje' }))).toBe('92 %')
    expect(textoCifra(cifra('ok', { formato: 'verificado' }))).toBe('sí')
    expect(textoCifra(cifra(true))).toBe('sí')
    expect(textoCifra(cifra(2, { total: 4 }))).toBe('2 de 4')
    expect(textoCifra(cifra('32/33'))).toBe('32/33')
    expect(textoCifra({ ok: false, valor: null, prueba: 'ALR-01', error: 'no está' })).toBe('—')
  })
})

describe('Inicio (/)', () => {
  it('la entrada de la consola es la portada, con las preguntas y el pie generado', async () => {
    const urls = http((u) => (u.pathname === '/api/preguntas' ? json(VISTA) : undefined))
    render(<MemoryRouter><InicioPage /></MemoryRouter>)
    // Mientras lee, el encabezado dice «Inicio»: se espera la lista, no el título.
    const lista = await screen.findByRole('list', { name: 'Las siete preguntas' })
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('E-OVRT-VDPPlataforma experimental de prueba')
    expect(screen.getByText('Una oración que dice qué es.')).toBeTruthy()
    expect(screen.getByText('Institución · Carrera · Autor Uno · Autora Dos')).toBeTruthy()
    const enlaces = within(lista).getAllByRole('link')
    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual(
      ['/preguntas/que-se-construyo', '/preguntas/que-agrega', '/preguntas/confianza'])
    // La cifra titular sale de lo resuelto, formateada.
    expect(enlaces[1].textContent).toContain('F1 0,841 por escena y 0,899 por sujeto')
    expect(enlaces[0].textContent).toContain('La cadena completa; 0 eventos perdidos')
    const pie = screen.getByRole('contentinfo')
    expect(pie.textContent).toMatch(/49 pruebas · campaña del 29 de octubre de 2026 al 12 de noviembre de 2026/)
    expect(pie.textContent).toMatch(/resultados en el commit 656c088/)
    // Fuera de la barra desde el 2026-11-19: el pie dice que es la etapa de desarrollo, no las cifras del informe.
    expect(within(pie).getByRole('link', { name: 'Archivo de la etapa de desarrollo' }).getAttribute('href')).toBe('/archivo')
    expect(within(pie).getByRole('link', { name: 'Cómo leer' }).getAttribute('href')).toBe('/documentacion')
    expect(within(pie).getByRole('link', { name: 'El informe' }).getAttribute('href')).toBe('https://example.org/informe')
    expect(within(pie).getByRole('link', { name: 'repo-a' })).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/tribunal|generaci[oó]n/i)
    expect(urls.map((u) => u.pathname)).toEqual(['/api/preguntas'])
  })

  it('si una cifra no se pudo leer lo dice, y la muestra como «—»', async () => {
    const conFalla: VistaPreguntas = {
      ...VISTA,
      preguntas: [pregunta({ cifras: { escena: { ok: false, valor: null, prueba: 'ALR-01', error: 'x' }, sujeto: cifra(0.9, { decimales: 3 }) } })],
      errores: ['que-agrega.cifras.escena: x'],
    }
    http((u) => (u.pathname === '/api/preguntas' ? json(conFalla) : undefined))
    render(<MemoryRouter><InicioPage /></MemoryRouter>)
    expect(await screen.findByText(/Una cifra no se pudo leer/)).toBeTruthy()
    expect(screen.getByRole('link', { name: /F1 — por escena/ })).toBeTruthy()
  })

  it('la ruta / monta la portada', async () => {
    http((u) => (u.pathname === '/api/preguntas' ? json(VISTA) : undefined))
    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>)
    expect(await screen.findByRole('list', { name: 'Las siete preguntas' })).toBeTruthy()
  })
})

describe('Una pregunta (/preguntas/:id)', () => {
  it('la respuesta, la tabla del informe con su respaldo y lo que la cifra no dice', async () => {
    http((u) => (u.pathname === '/api/preguntas' ? json(VISTA) : undefined))
    montarPregunta('que-agrega')
    expect(await screen.findByRole('heading', { level: 1, name: '¿Qué agrega la plataforma sobre la detección?' })).toBeTruthy()
    expect(screen.getByText(/Con las mismas detecciones/).textContent)
      .toBe('Con las mismas detecciones, F1 0,841 por escena y 0,899 siguiendo a cada persona.')
    const tabla = screen.getByRole('table', { name: 'Alerta por episodio en el rodaje guionado' })
    const escena = within(tabla).getByRole('row', { name: /Núcleo E-IND, escena/ })
    expect(within(escena).getAllByRole('cell').map((c) => c.textContent)).toEqual(['0,841', '5,39 s', 'ALR-01'])
    expect(within(escena).getByRole('link', { name: /Ver respaldo: Alerta por episodio, por escena ALR-01/ })
      .getAttribute('href')).toBe('/resultados/ALR-01')
    const sujeto = within(tabla).getByRole('row', { name: /Núcleo E-IND, sujeto/ })
    expect(within(sujeto).getAllByRole('cell').map((c) => c.textContent)).toEqual(
      ['banco 0,899 · vivo 0,830', '—', 'ALR-02 · DEN-02'])
    expect(screen.getByRole('heading', { name: 'Qué no dice esta cifra' })).toBeTruthy()
    expect(screen.getByText('Se mide contra una referencia anotada por una sola persona.')).toBeTruthy()
    // Solo cifras finales: sin la etapa anterior ni veredictos (§2.3).
    expect(document.body.textContent).not.toMatch(/etapa de desarrollo|veredicto|idéntic/i)
    const pasos = screen.getByRole('navigation', { name: 'Otras preguntas' })
    expect(within(pasos).getByRole('link', { name: /¿Qué se construyó\?/ }).getAttribute('href')).toBe('/preguntas/que-se-construyo')
    expect(within(pasos).getByRole('link', { name: /¿Cuánto se puede confiar/ }).getAttribute('href')).toBe('/preguntas/confianza')
  })

  it('una pregunta que no existe lo dice en llano', async () => {
    http((u) => (u.pathname === '/api/preguntas' ? json(VISTA) : undefined))
    montarPregunta('no-existe')
    expect(await screen.findByRole('heading', { name: 'Esa pregunta no existe' })).toBeTruthy()
  })
})
