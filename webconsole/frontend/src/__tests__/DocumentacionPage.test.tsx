import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import DocumentacionPage from '../pages/DocumentacionPage'
import { NAV_GROUPS, crumbsFor } from '../nav'
import type { Documentacion } from '../types'

/** Se mockea `fetch`, nunca el módulo de API: así el test también afirma QUÉ
 *  pide la pantalla, que es la mitad del contrato. */
const termino = (id: string, extra: Partial<Documentacion['terminos'][string]> = {}) => ({
  id, termino: id, definicion: `Definición de ${id}.`, mono: false, nivel: null,
  result_ids: [], familia: 'f1', familia_titulo: 'Familia uno', ...extra,
})

const doc: Documentacion = {
  available: true, message: null,
  titulo: 'Cómo leer esta consola',
  bajada: 'Qué se hizo, por qué, y qué significa cada nombre.',
  metodo: [
    {
      n: 1, titulo: 'De dónde salen los datos',
      hizo: 'Se juntaron datasets públicos de obra.',
      porque: 'Cada dataset le pone su propio nombre a la misma cosa.',
      quedo: 'El banco de imágenes congelado.',
      evidencia_href: '/evidencia/paso?n=1', evidencia_label: 'Paso 1 — Qué ve el detector',
      terminos: ['bench_v3'],
    },
    {
      n: 2, titulo: 'Cómo se eligió el modelo',
      hizo: 'Se corrieron seis modelos crudos.',
      porque: 'El modelo no se elige por reputación.',
      quedo: 'Un campeón robusto a la fuente.',
      // Sin evidencia declarada: la pantalla no debe inventar un enlace.
      evidencia_href: null, evidencia_label: null, terminos: [],
    },
  ],
  aportes: [
    {
      id: 'corrida', termino: 'Corrida', identificador: 'run_id',
      que_es: 'Una ejecución de un plano.', que_suma: 'La prueba material.',
      donde: 'Corridas', href: '/', conteo: 1436, conteo_de: 'corridas',
    },
    {
      id: 'campana', termino: 'Campaña', identificador: null,
      que_es: 'Un experimento con intención de contraste.', que_suma: 'El significado.',
      donde: 'Evidencia', href: '/evidencia', conteo: null, conteo_de: null,
    },
  ],
  vocabulario: [{
    id: 'f1', titulo: 'Familia uno', nota: 'La nota de la familia.',
    terminos: [
      termino('bench_v3', { mono: true }),
      termino('T1', { nivel: 'B', result_ids: ['clip_bench/t1_gdinotiny560_v2short_scene'] }),
    ],
  }],
  colisiones: [{
    simbolo: 'R1', en_la_consola: 'Acá R1 a R6 son siempre campañas de densidad.',
    sentidos: [
      { de: 'R1 a R4', es: 'Los resultados defendibles del plan.' },
      { de: 'R1 a R6', es: 'Las campañas de densidad.' },
      { de: 'R-01 a R-26', es: 'Los redlines del informe.' },
    ],
  }],
  terminos: {
    bench_v3: termino('bench_v3', { mono: true }),
    T1: termino('T1', { nivel: 'B', result_ids: ['clip_bench/t1_gdinotiny560_v2short_scene'] }),
  },
}

let urls: URL[]
let cuerpo: Documentacion

beforeEach(() => {
  urls = []
  cuerpo = doc
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    if (url.pathname === '/api/documentacion') return new Response(JSON.stringify(cuerpo))
    throw new Error(`Esta vista no debe consultar ${url}`)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const abrir = () => render(
  <MemoryRouter initialEntries={['/documentacion']}><DocumentacionPage /></MemoryRouter>,
)

describe('Documentación', () => {
  it('es el primer destino del grupo Trabajo y tiene su propia miga e icono', () => {
    const trabajo = NAV_GROUPS.find((g) => g.title === 'Trabajo')!
    expect(trabajo.items[0].to).toBe('/documentacion')
    expect(trabajo.items[0].label).toBe('Documentación')
    expect(trabajo.items[0].icon).toBeTruthy()
    // Icono propio, no el de otro destino: con la barra colapsada es lo único
    // que queda para distinguirlos.
    const otros = NAV_GROUPS.flatMap((g) => g.items)
      .filter((i) => i.to !== '/documentacion').map((i) => i.icon)
    expect(otros).not.toContain(trabajo.items[0].icon)
    expect(crumbsFor('/documentacion')).toEqual([
      { to: '/documentacion', label: 'Documentación' },
    ])
  })

  it('lee del disco y NO consulta ningún servicio', async () => {
    abrir()
    await screen.findByRole('heading', { name: 'Cómo leer esta consola' })
    expect(urls.map((u) => u.pathname)).toEqual(['/api/documentacion'])
  })

  it('cada paso del método dice qué se hizo, POR QUÉ y qué quedó', async () => {
    abrir()
    await screen.findByRole('heading', { name: 'De dónde salen los datos' })
    expect(screen.getAllByText('Por qué')).toHaveLength(2)
    expect(screen.getByText('Cada dataset le pone su propio nombre a la misma cosa.')).toBeTruthy()
    expect(screen.getByText('El banco de imágenes congelado.')).toBeTruthy()
  })

  it('enlaza a la evidencia sólo cuando el paso la declara', async () => {
    abrir()
    const enlace = await screen.findByRole('link', { name: 'Paso 1 — Qué ve el detector' })
    expect(enlace.getAttribute('href')).toBe('/evidencia/paso?n=1')
    // El paso 2 no declara evidencia: no hay un segundo enlace a /evidencia/paso.
    expect(screen.getAllByRole('link').filter(
      (a) => a.getAttribute('href')?.startsWith('/evidencia/paso'),
    )).toHaveLength(1)
  })

  it('la tabla de aportes distingue los cinco términos y no inventa identificadores', async () => {
    const { container } = abrir()
    await screen.findByRole('table', { name: 'Qué aporta cada cosa' })
    const fila = container.querySelector('#aporte-corrida')!
    expect(within(fila as HTMLElement).getByText('run_id')).toBeTruthy()
    expect(within(fila as HTMLElement).getByText('1436 hoy')).toBeTruthy()
    // «Campaña» no es un campo de ningún contrato: se DECLARA que no tiene
    // identificador propio en vez de dibujarle uno.
    const campana = container.querySelector('#aporte-campana')!
    expect(within(campana as HTMLElement).getByText('sin identificador propio')).toBeTruthy()
    expect(within(campana as HTMLElement).queryByText(/hoy$/)).toBeNull()
  })

  it('muestra las colisiones de símbolo con sus tres sentidos y qué significa acá', async () => {
    abrir()
    await screen.findByText('Los redlines del informe.')
    expect(screen.getByText('Las campañas de densidad.')).toBeTruthy()
    expect(screen.getByText('Acá R1 a R6 son siempre campañas de densidad.')).toBeTruthy()
  })

  it('cada término del vocabulario tiene ancla propia y enlaza su evidencia', async () => {
    const { container } = abrir()
    await screen.findByText('Definición de T1.')
    expect(container.querySelector('#bench_v3')).toBeTruthy()
    const rid = screen.getByRole('link', { name: 'clip_bench/t1_gdinotiny560_v2short_scene' })
    expect(rid.getAttribute('href')).toBe(
      '/evidencia/resultado?id=clip_bench%2Ft1_gdinotiny560_v2short_scene')
    // `bench_v3` no cita ningún result_id: no dibuja una lista vacía.
    expect(screen.getAllByRole('link').filter(
      (a) => a.getAttribute('href')?.startsWith('/evidencia/resultado'),
    )).toHaveLength(1)
  })

  it('sin documentación en disco lo DECLARA con su remedio, en vez de dibujar una vacía', async () => {
    cuerpo = {
      ...doc, available: false,
      message: 'Documentación no disponible. Falta el archivo: restauralo del repositorio.',
      titulo: null, bajada: null, metodo: [], aportes: [], vocabulario: [],
      colisiones: [], terminos: {},
    }
    abrir()
    await screen.findByText('Documentación no disponible')
    expect(screen.getByText(/restauralo del repositorio/)).toBeTruthy()
    expect(screen.queryByRole('table', { name: 'Qué aporta cada cosa' })).toBeNull()
  })
})
