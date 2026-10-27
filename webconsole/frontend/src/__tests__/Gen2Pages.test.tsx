import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import App from '../App'
import TribunalPage from '../pages/TribunalPage'
import ResultadosPage from '../pages/ResultadosPage'
import PruebaPage from '../pages/PruebaPage'
import type { Gen2Detalle, Gen2Observaciones, Gen2Prueba } from '../types'

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

const OBS: Gen2Observaciones = {
  available: true,
  observaciones: [
    // Contenido sintético: el archivo real de observaciones no vive en este repo.
    { numero: 1, titulo: 'Observación de ejemplo A', pedido: 'Pedido de ejemplo A.',
      respuesta: 'Respuesta de ejemplo A.', secciones: ['§17.5'],
      pruebas: [{ id: 'RT-04', titulo: 'Alertas en vivo', estado: 'sin_correr', veredicto: null }] },
    { numero: 8, titulo: 'Observación de ejemplo B', pedido: 'Pedido de ejemplo B.',
      respuesta: 'Respuesta de ejemplo B.', secciones: ['resumen'],
      pruebas: [{ id: 'ALR-01', titulo: 'Alerta por episodio, escena', estado: 'completo',
                  veredicto: { propuesto: 'identico', confirmado: { valor: 'identico', quien: 'Nombre' } } }] },
    { numero: 3, titulo: 'Observación de ejemplo C', pedido: 'Pedido de ejemplo C.', respuesta: 'Respuesta de ejemplo C.', secciones: [], pruebas: [] },
  ],
}

const fila = (over: Partial<Gen2Prueba>): Gen2Prueba => ({
  id: 'ALR-01', titulo: 'Alerta por episodio, escena', fase: 'F3', familia: 'clips', informe: ['Tabla 53'],
  pregunta: '¿Qué F1 logra?', esperado: 'Igual a la gen 1.', registro: 'activa', depende_de: [],
  gen1: { result_id: 't1_x', doc: 'operacion/81', relacion: null, motivo: null, referencia: 'gt02.json', nota: null },
  estado: 'sin_correr', generado: null, resumen: [], veredicto: null, ...over,
})

const PRUEBAS: Gen2Prueba[] = [
  fila({ estado: 'completo', resumen: [{ clave: 'f1', nombre: 'F1 por episodio', valor: 0.84058, unidad: null, gen1: 0.84058 }],
         veredicto: { propuesto: 'identico', confirmado: null } }),
  fila({ id: 'IMG-01', titulo: 'Percepción: campeón', familia: 'imagenes', informe: ['Tabla 51'] }),
  fila({ id: 'RT-03', titulo: 'Latencia en vivo', familia: 'vivo', estado: 'parcial' }),
]

describe('Para el tribunal (/)', () => {
  it('lista las observaciones con qué pidió, qué hicimos y dónde verlo, sin consultar servicios', async () => {
    const urls = http((u) => (u.pathname === '/api/gen2/observaciones' ? json(OBS) : undefined))
    render(<MemoryRouter><TribunalPage /></MemoryRouter>)
    const obs8 = await screen.findByRole('heading', { name: '8. Observación de ejemplo B' })
    const tarjeta = within(obs8.closest('section, .eo-card') as HTMLElement)
    expect(tarjeta.getByText('Pedido de ejemplo B.')).toBeTruthy()
    expect(tarjeta.getByRole('link', { name: 'ALR-01 — Alerta por episodio, escena' }).getAttribute('href'))
      .toBe('/resultados/ALR-01')
    expect(tarjeta.getByText(/confirmado por Nombre/)).toBeTruthy()
    // La primera tiene destinos extra (la demo en vivo) además de sus pruebas.
    const obs1 = within(screen.getByRole('heading', { name: '1. Observación de ejemplo A' }).closest('.eo-card') as HTMLElement)
    expect(obs1.getByRole('link', { name: 'La demo en vivo' }).getAttribute('href')).toBe('/demo')
    expect(obs1.getByText('Todavía no se corrió')).toBeTruthy()
    // Sin pruebas ni destinos: se dice que la respuesta está en el texto.
    expect(screen.getByText('Se responde en el texto del informe.')).toBeTruthy()
    expect(urls.map((u) => u.pathname)).toEqual(['/api/gen2/observaciones'])
  })

  it('sin el archivo de observaciones lo dice, sin romper', async () => {
    http((u) => (u.pathname === '/api/gen2/observaciones'
      ? json({ available: false, observaciones: [], message: 'No está el archivo de observaciones (docs/observaciones-tribunal/observaciones.yaml).' })
      : undefined))
    render(<MemoryRouter><TribunalPage /></MemoryRouter>)
    expect(await screen.findByText('Todavía no hay observaciones registradas')).toBeTruthy()
  })
})

describe('Resultados (/resultados)', () => {
  it('agrupa las pruebas como el informe y distingue propuesto de confirmado', async () => {
    const urls = http((u) => (u.pathname === '/api/gen2/pruebas' ? json(PRUEBAS) : undefined))
    render(<MemoryRouter><ResultadosPage /></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Alerta por episodio' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Percepción en imágenes' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Tiempo real' })).toBeTruthy()
    // Grupos sin pruebas no se dibujan vacíos.
    expect(screen.queryByRole('heading', { name: 'Estado por persona' })).toBeNull()
    expect(screen.getByRole('link', { name: 'ALR-01 — Alerta por episodio, escena' }).getAttribute('href'))
      .toBe('/resultados/ALR-01')
    expect(screen.getByText(/Propuesto: Idéntico a la generación 1 \(sin confirmar\)/)).toBeTruthy()
    expect(screen.getByText('Todavía no se corrió')).toBeTruthy()
    expect(screen.getByText('Parcial')).toBeTruthy()
    expect(screen.getByText(/generación 1: 0,8406/)).toBeTruthy()
    expect(screen.getByText(/1 de 3 pruebas completas/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Ajuste fino' })).toBeTruthy()
    expect(urls.map((u) => u.pathname)).toEqual(['/api/gen2/pruebas'])
  })

  it('un contraste que no se regenera no figura «sin correr»: muestra su cifra de la generación 1', async () => {
    const contraste = CONTRASTE
    http((u) => (u.pathname === '/api/gen2/pruebas' ? json([...PRUEBAS, contraste]) : undefined))
    render(<MemoryRouter><ResultadosPage /></MemoryRouter>)
    const titulo = await screen.findByRole('link', { name: 'ALR-03 — Alerta por episodio, gdino-base-560' })
    const tarjeta = within(titulo.closest('article') as HTMLElement)
    expect(tarjeta.getByText('Generación 1: no se regenera')).toBeTruthy()
    expect(tarjeta.queryByText('Todavía no se corrió')).toBeNull()
    expect(tarjeta.getByText('0,7143')).toBeTruthy()
    // Las completas se cuentan sobre las que se regeneran.
    expect(screen.getByText(/1 de 3 pruebas completas/)).toBeTruthy()
    expect(screen.getByText(/Una prueba de contraste no se regenera/)).toBeTruthy()
  })
})

const CONTRASTE: Gen2Prueba = fila({
  id: 'ALR-03', titulo: 'Alerta por episodio, gdino-base-560', registro: 'no_se_regenera',
  no_se_regenera: 'Contraste contra el campeón (ALR-01): cambia el modelo, no la plataforma.',
  gen1: { result_id: 't2_x', doc: 'operacion/84', relacion: null, motivo: null, referencia: 'gt02.json', nota: null,
          cifras: [{ clave: 'f1', nombre: 'F1 por episodio (micro)', valor: 0.714286 }] },
})

const montarPrueba = (id: string) => render(
  <MemoryRouter initialEntries={[`/resultados/${id}`]}>
    <Routes><Route path="/resultados/:id" element={<PruebaPage />} /></Routes>
  </MemoryRouter>,
)

const DETALLE_VACIO: Gen2Detalle = {
  ...fila({ id: 'RT-03', titulo: 'Latencia en vivo', familia: 'vivo' }),
  pre_registro: { texto: 'schema: prueba.gen2.v1\nid: RT-03\n', origen: 'catalogo', coincide_con_catalogo: null },
  resultado: null, corridas: null, entorno: null, plataforma: null, comandos: null,
  archivos: { logs: [], evals: [], capturas: [] },
}

describe('Detalle de una prueba (/resultados/:id)', () => {
  it('antes de correr muestra el pre-registro y dice que todavía no se corrió', async () => {
    http((u) => (u.pathname === '/api/gen2/pruebas/RT-03' ? json(DETALLE_VACIO) : undefined))
    montarPrueba('RT-03')
    expect(await screen.findByRole('heading', { name: 'RT-03 — Latencia en vivo' })).toBeTruthy()
    expect(screen.getByText(/Todavía no se corrió\. Abajo está su pre-registro/)).toBeTruthy()
    expect(screen.getByText(/id: RT-03/)).toBeTruthy()
    expect(screen.queryByRole('table', { name: 'Cifras de la prueba' })).toBeNull()
    expect(screen.getByText('El veredicto aparece cuando la prueba corre.')).toBeTruthy()
  })

  it('completa: cifras contra la gen 1, diferencias, cómo corrió, corridas y archivos', async () => {
    const detalle: Gen2Detalle = {
      ...fila({
        estado: 'completo', generado: '2026-11-01T03:00:00+00:00',
        resumen: [{ clave: 'f1', nombre: 'F1 por episodio', valor: 0.84058, unidad: null, gen1: 0.84058 }],
        veredicto: { propuesto: 'a_revisar', motivo: 'difiere', referencia: 'gt02.json',
                     diferencias: { matched: { gen2: 28, gen1: 29 } }, confirmado: null },
      }),
      pre_registro: { texto: 'id: ALR-01\n', origen: 'copia_al_correr', coincide_con_catalogo: false },
      resultado: {}, comandos: '[t] POST /api/experiments/run\n',
      corridas: { a_p1_c02: { estado: 'ok', experiment_id: 'exp_1', media_run_id: 'run_m', control_run_id: 'ctl_c', segundos: 180 } },
      entorno: { modo: 'docker', gpu: 'NVIDIA GeForce RTX 4060', host: { nombre: 'victus', cpu: 'Ryzen 5 8645HS', nucleos: 12 },
                 repos: { 'e-ovrt_datasets': { commit: 'abcdef1234567890', rama: 'main', archivos_sin_commitear: 0 } },
                 docker: { imagenes: { 'eovrt/console:latest': { id: 'sha256:0123456789abcdef', creada: '2026-10-30', digests: [] } } } },
      plataforma: null,
      archivos: { logs: ['logs/ejemplo/manifest.yaml'], evals: ['evals/eval_a_p1_c02.json'], capturas: ['capturas/consola.png'] },
    }
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-01' ? json(detalle) : undefined))
    montarPrueba('ALR-01')
    const cifras = await screen.findByRole('table', { name: 'Cifras de la prueba' })
    expect(within(cifras).getAllByText('0,8406')).toHaveLength(2)
    const difs = screen.getByRole('table', { name: 'Diferencias con la generación 1' })
    expect(within(difs).getByText('matched')).toBeTruthy()
    expect(screen.getByText(/Difiere de la generación 1: lo revisa una persona/)).toBeTruthy()
    expect(screen.getByText('NVIDIA GeForce RTX 4060')).toBeTruthy()
    expect(screen.getByText('Contenedores (Docker)')).toBeTruthy()
    const corridas = screen.getByRole('table', { name: 'Corridas de la prueba' })
    expect(within(corridas).getByRole('link', { name: 'exp_1' }).getAttribute('href')).toBe('/experiments/exp_1')
    expect(screen.getByText(/se cambió después de correr/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'evals/eval_a_p1_c02.json' }).getAttribute('href'))
      .toBe('/api/gen2/pruebas/ALR-01/archivo?ruta=evals%2Feval_a_p1_c02.json')
    expect(screen.getByRole('img', { name: 'Captura consola.png' })).toBeTruthy()
  })

  it('un contraste muestra por qué no se regenera y su cifra de la generación 1, sin veredicto', async () => {
    const detalle: Gen2Detalle = {
      ...CONTRASTE,
      pre_registro: { texto: 'id: ALR-03\n', origen: 'catalogo', coincide_con_catalogo: null },
      resultado: null, corridas: null, entorno: null, plataforma: null, comandos: null,
      archivos: { logs: [], evals: [], capturas: [] },
    }
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-03' ? json(detalle) : undefined))
    montarPrueba('ALR-03')
    expect(await screen.findByRole('heading', { name: 'Por qué no se regenera' })).toBeTruthy()
    expect(screen.getByText(/cambia el modelo, no la plataforma/)).toBeTruthy()
    const cifras = screen.getByRole('table', { name: 'Cifras de la generación 1' })
    expect(within(cifras).getByText('0,7143')).toBeTruthy()
    expect(screen.queryByText(/Todavía no se corrió\. Abajo está su pre-registro/)).toBeNull()
    expect(screen.getByText(/No se regenera, así que no tiene veredicto/)).toBeTruthy()
  })

  it('una prueba que no está en el catálogo da un 404 dicho en llano', async () => {
    http(() => undefined)
    montarPrueba('ZZZ-99')
    expect(await screen.findByText('Esa prueba no está en el catálogo de la generación 2.')).toBeTruthy()
  })
})

describe('Rutas (doc 135 §3.1)', () => {
  it('la entrada es «Para el tribunal»', async () => {
    http((u) => (u.pathname === '/api/gen2/observaciones' ? json(OBS) : undefined))
    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>)
    expect(await screen.findByRole('heading', { level: 1, name: 'Para el tribunal' })).toBeTruthy()
  })

  it('la generación 1 sigue en /evidencia y en /evidencia/generacion-1, con su aviso fijo', async () => {
    http(() => undefined)
    for (const ruta of ['/evidencia', '/evidencia/generacion-1']) {
      render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>)
      const aviso = screen.getByText(/Estas cifras son de la validación inicial/).closest('.eo-banner') as HTMLElement
      expect(within(aviso).getByRole('link', { name: 'Resultados' }).getAttribute('href')).toBe('/resultados')
      cleanup()
    }
  })
})
