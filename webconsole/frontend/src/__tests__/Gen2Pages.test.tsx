import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import App from '../App'
import ResultadosPage from '../pages/ResultadosPage'
import PruebaPage from '../pages/PruebaPage'
import type { Gen2Detalle, Gen2Prueba } from '../types'

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

const fila = (over: Partial<Gen2Prueba>): Gen2Prueba => ({
  id: 'ALR-01', titulo: 'Alerta por episodio, escena', fase: 'F3', familia: 'clips', informe: ['Tabla 53'],
  pregunta: '¿Qué F1 logra?', esperado: 'Igual a la gen 1.', registro: 'activa', depende_de: [],
  gen1: { result_id: 't1_x', doc: 'operacion/81', relacion: null, motivo: null, referencia: 'gt02.json', nota: null },
  estado: 'sin_correr', generado: null, resumen: [], veredicto: null, ...over,
})

const PRUEBAS: Gen2Prueba[] = [
  fila({ estado: 'completo', pregunta_consola: 'que-agrega', que_midio: 'Cuántos episodios alerta, mirando la escena.',
         resumen: [{ clave: 'f1', nombre: 'F1 del programa', nombre_consola: 'F1 por episodio', valor: 0.84058, unidad: null, gen1: 0.84058 }],
         veredicto: { propuesto: 'identico', confirmado: null } }),
  fila({ id: 'IMG-01', titulo: 'Percepción: campeón', familia: 'imagenes', informe: ['Tabla 51'], pregunta_consola: 'que-detecta' }),
  fila({ id: 'RT-03', titulo: 'Latencia en vivo', familia: 'vivo', estado: 'parcial', pregunta_consola: 'en-vivo' }),
]

/** Lo que usa el catálogo de las siete preguntas: su id y su título, en orden. */
const PREGUNTAS = {
  available: true,
  preguntas: [
    { id: 'que-detecta', titulo: '¿Qué detecta un modelo sin entrenar?' },
    { id: 'como-expresar', titulo: '¿Cómo conviene expresar la infracción?' },
    { id: 'que-agrega', titulo: '¿Qué agrega la plataforma sobre la detección?' },
    { id: 'en-vivo', titulo: '¿Funciona en vivo?' },
  ].map((p) => ({ ...p, informe: [], titular: '', respuesta: '', cifras: {}, tablas: [], limites: [] })),
}

describe('Pruebas (/resultados)', () => {
  const servir = (pruebas: Gen2Prueba[]) => http((u) => (u.pathname === '/api/gen2/pruebas' ? json(pruebas)
    : u.pathname === '/api/preguntas' ? json(PREGUNTAS) : undefined))

  it('agrupa el catálogo por las siete preguntas, en su orden, con solo cifras finales (plan §3)', async () => {
    const urls = servir(PRUEBAS)
    render(<MemoryRouter><ResultadosPage /></MemoryRouter>)
    const grupos = await screen.findAllByRole('heading', { level: 2 })
    expect(grupos.map((h) => h.textContent)).toEqual([
      '1. ¿Qué detecta un modelo sin entrenar?', '3. ¿Qué agrega la plataforma sobre la detección?', '4. ¿Funciona en vivo?',
    ])
    // El nombre llano primero y el código al lado (plan §4.2); el nombre sale del vocabulario.
    const enlace = screen.getByRole('link', { name: 'Alerta por episodio, por escena ALR-01' })
    expect(enlace.getAttribute('href')).toBe('/resultados/ALR-01')
    const tarjeta = within(enlace.closest('article') as HTMLElement)
    expect(tarjeta.getByText('Cuántos episodios alerta, mirando la escena.')).toBeTruthy()
    // La cifra lleva el nombre de la consola, no el del programa.
    expect(tarjeta.getByText('F1 por episodio')).toBeTruthy()
    // Con los decimales del informe (revisión del 2026-11-19): 0,8406 se escribe 0,841.
    expect(tarjeta.getByText('0,841')).toBeTruthy()
    expect(screen.getByText('Todavía no se corrió')).toBeTruthy()
    expect(screen.getByText('Parcial')).toBeTruthy()
    // Ni la etapa anterior, ni el veredicto, ni la jerga de la campaña (§2.3, §4.3).
    expect(document.body.textContent).not.toMatch(/etapa de desarrollo|veredicto|propuesto|id[eé]ntic|generaci[oó]n|campe[oó]n/i)
    expect(screen.getByText(/1 de 3 pruebas completas/)).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Ver la pregunta' })[0].getAttribute('href')).toBe('/preguntas/que-detecta')
    expect(urls.map((u) => u.pathname).sort()).toEqual(['/api/gen2/pruebas', '/api/preguntas'])
  })

  it('un contraste que no se regenera no figura «sin correr» ni muestra cifras de otra etapa', async () => {
    servir([...PRUEBAS, { ...CONTRASTE, pregunta_consola: 'que-agrega' }])
    render(<MemoryRouter><ResultadosPage /></MemoryRouter>)
    const titulo = await screen.findByRole('link', { name: 'Alerta por episodio con el contraste base-560 ALR-03' })
    const tarjeta = within(titulo.closest('article') as HTMLElement)
    expect(tarjeta.getByText('No se regenera')).toBeTruthy()
    expect(tarjeta.queryByText('Todavía no se corrió')).toBeNull()
    expect(tarjeta.queryByText('0,714')).toBeNull()
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
    // Mientras carga, el encabezado ya lleva el nombre llano: se espera el aviso, no el título.
    expect(await screen.findByText(/Todavía no se corrió\. En «Cómo se validó» está lo que se escribió antes de correr/)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Latencia en vivo con la OAK-D RT-03' })).toBeTruthy()
    // Antes de correr, «Cómo se validó» viene abierto: es lo único que hay para leer.
    expect((screen.getByRole('heading', { name: 'Cómo se validó' }).closest('details') as HTMLDetailsElement).open).toBe(true)
    expect(screen.getByText(/id: RT-03/)).toBeTruthy()
    expect(screen.queryByRole('table', { name: 'Cifras de la prueba' })).toBeNull()
    expect(screen.getByText('La concordancia aparece cuando la prueba corre.')).toBeTruthy()
  })

  it('completa: cifras contra la etapa de desarrollo, diferencias, cómo corrió, corridas y archivos', async () => {
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
    expect(within(cifras).getAllByText('0,841')).toHaveLength(2)
    const difs = screen.getByRole('table', { name: 'Diferencias con la etapa de desarrollo' })
    expect(within(difs).getByText('matched')).toBeTruthy()
    expect(screen.getByText(/Difiere de la etapa de desarrollo: lo revisa una persona/)).toBeTruthy()
    expect(screen.getByText('NVIDIA GeForce RTX 4060')).toBeTruthy()
    expect(screen.getByText('Contenedores (Docker)')).toBeTruthy()
    const corridas = screen.getByRole('table', { name: 'Corridas de la prueba' })
    expect(within(corridas).getByRole('link', { name: 'exp_1' }).getAttribute('href')).toBe('/experiments/exp_1')
    expect(screen.getByText(/se cambió después de correr/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'evals/eval_a_p1_c02.json' }).getAttribute('href'))
      .toBe('/api/gen2/pruebas/ALR-01/archivo?ruta=evals%2Feval_a_p1_c02.json')
    expect(screen.getByRole('img', { name: 'Captura consola.png' })).toBeTruthy()
  })

  const completa = (over: Partial<Gen2Detalle>): Gen2Detalle => ({
    ...fila({ estado: 'completo', resumen: [{ clave: 'f1', nombre: 'F1 por episodio', valor: 0.72973, unidad: null, gen1: null }] }),
    pre_registro: { texto: 'id: X\n', origen: 'copia_al_correr', coincide_con_catalogo: true },
    resultado: {}, comandos: null, corridas: null, entorno: null, plataforma: null,
    archivos: { logs: [], evals: [], capturas: [] }, ...over,
  })

  it('el resultado muestra todas las lecturas lado a lado, con nombres llanos (plan §2.4)', async () => {
    const detalle = completa({
      id: 'ALR-13', titulo: 'Sensibilidad de la regla',
      lecturas: [
        { nombre: 'combinada_sujeto', resumen: [{ clave: 'f1', nombre: 'F1 por episodio', valor: 0.763158, unidad: null, gen1: null }] },
        { nombre: 'casco', resumen: [
          { clave: 'f1', nombre: 'F1 por episodio', valor: 0.771429, unidad: null, gen1: null },
          { clave: 'falsas', nombre: 'Falsas alarmas', valor: 10, unidad: null, gen1: null }] },
      ],
    })
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-13' ? json(detalle) : undefined))
    montarPrueba('ALR-13')
    const tabla = await screen.findByRole('table', { name: 'El resultado' })
    const cabeceras = within(tabla).getAllByRole('columnheader').map((th) => th.textContent)
    expect(cabeceras).toEqual(['Qué se mide', 'Lectura principal', 'combinada, por sujeto', 'solo casco'])
    const f1 = within(tabla).getByRole('row', { name: /F1 por episodio/ })
    expect(within(f1).getAllByRole('cell').map((td) => td.textContent)).toEqual(['F1 por episodio', '0,730', '0,763', '0,771'])
    // Una cifra que solo tiene una lectura aparece igual, con «—» en las que no la traen.
    const falsas = within(tabla).getByRole('row', { name: /Falsas alarmas/ })
    expect(within(falsas).getAllByRole('cell').map((td) => td.textContent)).toEqual(['Falsas alarmas', '—', '—', '10'])
  })

  it('una prueba sin otras lecturas muestra una sola columna, sin la etapa anterior a la vista', async () => {
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-01' ? json(completa({ lecturas: [] })) : undefined))
    montarPrueba('ALR-01')
    const tabla = await screen.findByRole('table', { name: 'El resultado' })
    expect(within(tabla).getAllByRole('columnheader').map((th) => th.textContent)).toEqual(['Qué se mide', 'Resultado'])
    expect(screen.queryByRole('table', { name: 'Tomas de la prueba' })).toBeNull()
    // La comparación con la etapa de desarrollo vive plegada, en «Cómo se validó».
    const plegado = screen.getByRole('heading', { name: 'Cómo se validó' }).closest('details') as HTMLDetailsElement
    expect(plegado.open).toBe(false)
    expect(within(plegado).getByRole('table', { name: 'Cifras de la prueba' })).toBeTruthy()
  })

  it('el desglose: clip por clip sobre un banco de clips, y por fuente y clase sobre imágenes', async () => {
    const clips = completa({ desglose: { tipo: 'clips', clips: [
      { clip: 'a_p1_c02', episodios: 1, aciertos: 1, perdidos: 0, falsas_alarmas: 2, re_alertas: 1, t_alert_ms: 4600.33, sdr: 0.485771 },
    ] } })
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-01' ? json(clips) : undefined))
    montarPrueba('ALR-01')
    const tabla = await screen.findByRole('table', { name: 'Clip por clip' })
    const [, fila] = within(tabla).getAllByRole('row')
    expect(within(fila).getAllByRole('cell').map((c) => c.textContent)).toEqual(['a_p1_c02', '1', '1', '0', '2', '1', '4,60 s', '0,486'])
    cleanup()
    const imagenes = completa({ id: 'IMG-01', desglose: { tipo: 'imagenes', fuentes: [
      { fuente: 'obra_test', map50: 0.4771, recall_cr01: 0.28, clases: [{ clase: 'person', ap50: 0.6951, n_gt: 135 }] },
    ] } })
    http((u) => (u.pathname === '/api/gen2/pruebas/IMG-01' ? json(imagenes) : undefined))
    montarPrueba('IMG-01')
    const porFuente = await screen.findByRole('table', { name: 'Por fuente y por clase' })
    expect(within(porFuente).getAllByRole('columnheader').map((th) => th.textContent))
      .toEqual(['Fuente', 'mAP50', 'AP50 persona', 'Recall de sin casco CR-01 por evidencia directa'])
    const [, obra] = within(porFuente).getAllByRole('row')
    expect(within(obra).getAllByRole('cell').map((c) => c.textContent)).toEqual(['Obra curada, prueba', '0,477', '0,695 · n = 135', '0,280'])
  })

  it('una prueba en vivo muestra sus tomas: qué se esperaba, qué pasó y cuánto tardó la alerta', async () => {
    const detalle = completa({
      id: 'RT-06', titulo: 'Obra simulada con la cámara IP', familia: 'rodaje',
      tomas: [
        { escena: 'P1', session_id: 'demo_20261107T200449Z_P1', stream: 'secundario', remera: 'blanca lisa',
          por_condicion: { 'CR-01': { esperado: 'alerta', alertas: 1, ok: true }, 'CR-02': { esperado: 'sin_alerta', alertas: 0, ok: true } },
          como_se_esperaba: true, sujeto_como_se_esperaba: true, alertas_antes_de_la_accion: 0,
          alertas: [{ condicion: 'CR-01', accion: 'sacar_casco', accion_a_confirmacion_ms: 7319.2, confirmacion_a_broker_ms: 15.5 }] },
        { escena: 'P5', session_id: 'demo_20261107T200801Z_P5', stream: 'secundario', remera: 'blanca lisa',
          por_condicion: { 'CR-01': { esperado: 'sin_alerta', alertas: 1, ok: false }, 'CR-02': { esperado: 'sin_alerta', alertas: 1, ok: false } },
          como_se_esperaba: false, sujeto_como_se_esperaba: false, alertas_antes_de_la_accion: 2, alertas: [] },
      ],
    })
    http((u) => (u.pathname === '/api/gen2/pruebas/RT-06' ? json(detalle) : undefined))
    montarPrueba('RT-06')
    const tabla = await screen.findByRole('table', { name: 'Tomas de la prueba' })
    expect(screen.getByText('1 de 2 como el guion')).toBeTruthy()
    const cabeceras = within(tabla).getAllByRole('columnheader').map((th) => th.textContent)
    expect(cabeceras).toEqual(['Escena', 'Stream', 'Remera', 'CR-01', 'CR-02', 'Como el guion', 'De la acción a la alerta', 'Sesión'])
    const [, p1, p5] = within(tabla).getAllByRole('row')
    expect(within(p1).getByText('1 alerta')).toBeTruthy()
    expect(within(p1).getByText('CR-01 7,3 s')).toBeTruthy()
    expect(within(p1).getByRole('link', { name: 'demo_20261107T200449Z_P1' }).getAttribute('href'))
      .toBe('/demo/resultado/demo_20261107T200449Z_P1')
    expect(within(p5).getByText('no')).toBeTruthy()
    expect(within(p5).getByText(/2 antes de la acción/)).toBeTruthy()
  })

  it('si la prueba no registró la GPU, muestra la de la prueba de plataforma y dice de dónde sale', async () => {
    const detalle = completa({ id: 'RT-04', entorno: { modo: 'docker', gpu: null, host: { nombre: 'x' } },
                               gpu_de_la_plataforma: 'NVIDIA GeForce RTX 4060 Laptop GPU' })
    http((u) => (u.pathname === '/api/gen2/pruebas/RT-04' ? json(detalle) : undefined))
    montarPrueba('RT-04')
    expect(await screen.findByText('NVIDIA GeForce RTX 4060 Laptop GPU')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'PLAT-01' }).getAttribute('href')).toBe('/resultados/PLAT-01')
  })

  it('un contraste muestra por qué no se regenera y su cifra de la etapa de desarrollo, sin veredicto', async () => {
    const detalle: Gen2Detalle = {
      ...CONTRASTE,
      pre_registro: { texto: 'id: ALR-03\n', origen: 'catalogo', coincide_con_catalogo: null },
      resultado: null, corridas: null, entorno: null, plataforma: null, comandos: null,
      archivos: { logs: [], evals: [], capturas: [] },
    }
    http((u) => (u.pathname === '/api/gen2/pruebas/ALR-03' ? json(detalle) : undefined))
    montarPrueba('ALR-03')
    expect(await screen.findByRole('heading', { name: 'Cómo se validó' })).toBeTruthy()
    expect(screen.getByText(/cambia el modelo, no la plataforma/)).toBeTruthy()
    const cifras = screen.getByRole('table', { name: 'Cifras de la etapa de desarrollo' })
    expect(within(cifras).getByText('0,714')).toBeTruthy()
    expect(screen.queryByText(/Todavía no se corrió/)).toBeNull()
    expect(screen.getByText(/No se regenera, así que no tiene concordancia/)).toBeTruthy()
  })

  it('una prueba que no está en el catálogo da un 404 dicho en llano', async () => {
    http(() => undefined)
    montarPrueba('ZZZ-99')
    expect(await screen.findByText('Esa prueba no está en el catálogo.')).toBeTruthy()
  })
})

describe('Rutas (plan de la consola, §5)', () => {
  it('el Archivo está en /archivo y sigue en sus dos URLs anteriores, con su aviso fijo', async () => {
    http(() => undefined)
    for (const ruta of ['/archivo', '/evidencia', '/evidencia/generacion-1']) {
      render(<MemoryRouter initialEntries={[ruta]}><App /></MemoryRouter>)
      const aviso = screen.getByText(/Estas cifras son de la etapa de desarrollo/).closest('.eo-banner') as HTMLElement
      expect(aviso.textContent).toMatch(/no son las del informe/)
      expect(within(aviso).getByRole('link', { name: 'Pruebas' }).getAttribute('href')).toBe('/resultados')
      cleanup()
    }
  })
})
