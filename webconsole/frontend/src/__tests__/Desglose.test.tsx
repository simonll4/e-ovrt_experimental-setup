import { afterEach, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '../test-utils'
import Desglose from '../pages/evidencia/Desglose'
import type { EvidenceMetrics } from '../types'

afterEach(() => cleanup())

/**
 * Reproduce la colisión real de `id` entre esquemas del backend
 * (`webconsole/backend/src/eovrt_webconsole/evidence_metrics.py`):
 * `_clip_campaign` ("Por clip", 6 columnas: Clip/Escenario/Esperados/
 * Detectados/recall/t_alert) y `_clip_person_state` ("Por clip y condición",
 * 3 columnas: Clip/Condición/F1) usan el MISMO `id: "clip"`.
 *
 * Antes de la Ronda de arreglo 1, el resolvedor de columnas indexaba sólo por
 * `id` y dependía de que la cantidad de columnas no coincidiera para no
 * confundir los dos esquemas — un guardia incidental de conteo, no una
 * verificación real. Este desglose fuerza el peor caso: EXACTAMENTE las mismas
 * 6 columnas que "Por clip" de `clip_campaign`, pero declarado bajo
 * `clip_person_state.v1`. Si el resolvedor volviera a indexar sólo por `id`,
 * el spec de `clip_campaign` se aplicaría igual y un valor de `recall`
 * aparecería con barra bajo el encabezado "recall" mientras que `t_alert_ms`
 * se formatearía como "100 ms" — datos de un esquema ajeno, mostrados como si
 * fueran los propios.
 */
const colisionPorId: EvidenceMetrics['desgloses'][number] = {
  id: 'clip', titulo: 'Desglose de colisión (id compartido a propósito)', nota: null,
  columnas: ['Clip', 'Escenario', 'Esperados', 'Detectados', 'recall', 't_alert'],
  filas: [{
    nombre: 'cb_p1_01', escenario: 'P1', esperados: 1, detectados: 1, recall: 0.9, t_alert_ms: 100,
    no_aplica: null,
  }],
}

it('un desglose "clip" de clip_person_state no resuelve con el spec de clip_campaign aunque coincida la cantidad de columnas', () => {
  render(<Desglose esquema="clip_person_state.v1" desglose={colisionPorId} />)
  const fila = screen.getByRole('row', { name: /cb_p1_01/ })
  // Nada del formato propio de clip_campaign.clip: ni barra de recall...
  expect(fila.querySelector('.eo-bar')).toBeNull()
  // ...ni t_alert formateado en milisegundos...
  expect(within(fila).queryByText('100 ms')).toBeNull()
  expect(within(fila).queryByText('0,900')).toBeNull()
  // ...cae al genérico: el registro completo, sin inventar a qué columna
  // corresponde cada valor. La presencia del JSON crudo prueba que se tomó
  // este camino y no el spec de clip_campaign.
  expect(within(fila).getByText(/"recall":0\.9/)).toBeTruthy()
  expect(within(fila).getByText(/"t_alert_ms":100/)).toBeTruthy()
})

it('el mismo id bajo clip_campaign_metrics.v1 sí resuelve con su spec propio (control positivo)', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={colisionPorId} />)
  const fila = screen.getByRole('row', { name: /cb_p1_01/ })
  expect(fila.querySelector('.eo-bar')).toBeTruthy()
  expect(within(fila).getByText('100 ms')).toBeTruthy()
})

/** I-1: tres de los cuatro esquemas caían al genérico y salían como JSON crudo
 *  bajo un encabezado que prometía columnas. El desglose no es un opcional
 *  (limitación L5), así que cada esquema declara sus columnas. */
const filaPersonState: EvidenceMetrics['desgloses'][number] = {
  id: 'clip', titulo: 'Por clip y condición', nota: null,
  columnas: ['Clip', 'Condición', 'F1'],
  filas: [
    { nombre: 'v01_c02', condicion: 'CR-01', f1: 0.31666, no_aplica: null },
    { nombre: 'v01_c02', condicion: 'CR-02', f1: null,
      no_aplica: 'sin person-frames GT positivas' },
  ],
}

it('clip_person_state.v1 sale en columnas, no como {"condicion":…,"f1":0.0}', () => {
  render(<Desglose esquema="clip_person_state.v1" desglose={filaPersonState} />)
  const conDato = screen.getByRole('row', { name: /CR-01/ })
  expect(within(conDato).getByText('0,317')).toBeTruthy()
  expect(within(conDato).queryByText(/"f1"/)).toBeNull()
  // La fila sin denominador declara su causa; el 0.0 de la fuente no se dibuja.
  const sinDato = screen.getByRole('row', { name: /CR-02/ })
  expect(within(sinDato).getByText('sin person-frames GT positivas')).toBeTruthy()
  expect(within(sinDato).queryByText('0,000')).toBeNull()
})

it('nivel_a_gate sale en columnas, no como {"valores":{…}}', () => {
  render(<Desglose esquema="nivel_a_gate" desglose={{
    id: 'estrato', titulo: 'Por estrato', nota: null,
    columnas: ['Estrato / condición', 'Variante E-DIR', 'Faltantes E-IND',
               'Faltantes E-DIR', 'Rescatadas por E-DIR', 'Fracción rescatada'],
    filas: [{ nombre: 'bench_obra/CR-02', variante: 'cr02_obs', eind_misses: 48,
              edir_misses: 49, recuperadas: 9, fraccion: 0.1875, no_aplica: null }],
  }} />)
  const fila = screen.getByRole('row', { name: /bench_obra/ })
  expect(within(fila).getByText('cr02_obs')).toBeTruthy()
  expect(within(fila).getByText('48')).toBeTruthy()
  expect(within(fila).getByText('0,188')).toBeTruthy()
  expect(within(fila).queryByText(/"best_edir_variant"/)).toBeNull()
})

it('t_alert sale en milisegundos redondeados, no con doce decimales', () => {
  render(<Desglose esquema="talert_notification_metrics.v1" desglose={{
    id: 'origen', titulo: 'Por origen del evento', nota: null,
    columnas: ['Origen', 'n', 'p50', 'p95', 'p99'],
    filas: [{ nombre: 'ebe', n: 447, p50: 41.392578125, p95: 64.5341796875,
              p99: 90.1, no_aplica: null }],
  }} />)
  const fila = screen.getByRole('row', { name: /ebe/ })
  expect(within(fila).getByText('41 ms')).toBeTruthy()
  expect(within(fila).queryByText(/41\.392578125/)).toBeNull()
})

/** V-2: la causa salía como identificador crudo en 70 filas de "Por clip". */
const conCausaCruda = (n: number): EvidenceMetrics['desgloses'][number] => ({
  id: 'clip', titulo: 'Por clip', nota: null,
  columnas: ['Clip', 'Escenario', 'Esperados', 'Detectados', 'recall', 't_alert'],
  filas: Array.from({ length: n }, (_, i) => ({
    nombre: `cb_n${i}`, escenario: 'N1', esperados: 0, detectados: 0, recall: null,
    t_alert_ms: null, no_aplica: 'negative_clip_no_episodes',
  })),
})

it('traduce la causa cruda y deja pasar la que ya es legible', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={conCausaCruda(1)} />)
  expect(screen.getByText('clip negativo: sin episodios esperados')).toBeTruthy()
  expect(screen.queryByText('negative_clip_no_episodes')).toBeNull()

  cleanup()
  // La MISMA celda la usa "Por escenario" con una cadena que el backend ya
  // escribe legible: un mapeo que vaciara lo no reconocido borraría la única
  // declaración que esa fila tiene.
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={{
    id: 'escenario', titulo: 'Por escenario', nota: null,
    columnas: ['Escenario', 'Clips', 'Episodios', 'recall', 'FP', 'SDR'],
    filas: [{ nombre: 'P3', clips: 2, episodios: 0, recall: null, fp: 0, sdr: null,
              no_aplica: 'sin episodios evaluables' }],
  }} />)
  expect(screen.getByText('sin episodios evaluables')).toBeTruthy()
})

/** V-3: plegar no puede esconder lo que L5 obliga a mostrar, así que el
 *  `<summary>` dice cuántas filas hay y cuántas declaran causa. */
it('un desglose largo arranca plegado y su resumen dice qué esconde', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={conCausaCruda(34)} />)
  const detalle = document.querySelector('details')
  expect(detalle).toBeTruthy()
  expect(detalle?.hasAttribute('open')).toBe(false)
  expect(screen.getByText('34 filas, 34 declaran causa en vez de cifra')).toBeTruthy()
})

it('un desglose corto no se pliega: ahí se lee el argumento', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={conCausaCruda(3)} />)
  expect(document.querySelector('details')).toBeNull()
})

/** 34 filas sin ninguna causa declarada, pero con celdas nulas: `t_alert` no
 *  existe para las que no dispararon alerta. Es la forma REAL de los desgloses
 *  «Por clip» del banco de video — medido sobre
 *  `clip_bench/d1_gdinotiny560_edirpair_scene`, 24 de 34 filas traen alguna
 *  celda nula sin declarar causa. */
const sinCausaConHuecos = (n: number, huecos: number): EvidenceMetrics['desgloses'][number] => ({
  id: 'clip', titulo: 'Por clip', nota: null,
  columnas: ['Clip', 'Escenario', 'Esperados', 'Detectados', 'recall', 't_alert'],
  filas: Array.from({ length: n }, (_, i) => ({
    nombre: `cb_p${i}`, escenario: 'P1', esperados: 1, detectados: 1, recall: 0.9,
    t_alert_ms: i < huecos ? null : 1200, no_aplica: null,
  })),
})

/** R-29, 6ª aparición del defecto reincidente: el `<summary>` medía
 *  completitud con `no_aplica`, que cubre UNA columna (recall/F1). Sin ninguna
 *  causa declarada afirmaba «34 filas, todas con cifra» encima de una tabla
 *  plegada donde 24 filas tenían celdas vacías — una afirmación de completitud
 *  derivada de una señal parcial, justo en el control que se agregó para
 *  ESCONDER filas. */
it('sin causas declaradas no afirma completitud: declara las celdas sin dato', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={sinCausaConHuecos(34, 24)} />)
  expect(screen.queryByText(/todas con cifra/)).toBeNull()
  expect(screen.getByText('34 filas, ninguna declara causa; 24 con alguna celda sin dato')).toBeTruthy()
})

it('con causas declaradas cuenta aparte las filas que tienen huecos sin causa', () => {
  // Las dos señales viajan: las que DECLARAN por qué no hay cifra, y las que
  // simplemente no la traen. Ninguna de las dos queda escondida por el plegado.
  const mezcla = sinCausaConHuecos(34, 24)
  mezcla.filas = mezcla.filas.map((f, i) => (
    i >= 30 ? { ...f, recall: null, no_aplica: 'sin episodios evaluables' } : f))
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={mezcla} />)
  expect(screen.getByText(
    '34 filas, 4 declaran causa en vez de cifra; otras 24 con alguna celda sin dato')).toBeTruthy()
})

it('sin causas y sin huecos dice lo que midió, no que la tabla esté completa', () => {
  render(<Desglose esquema="clip_campaign_metrics.v1" desglose={sinCausaConHuecos(34, 0)} />)
  // La afirmación de completitud ya no se hace en ninguna rama: lo que se dice
  // es lo que se midió, ni una palabra más.
  expect(screen.queryByText(/todas con cifra/)).toBeNull()
  expect(screen.getByText('34 filas, ninguna declara causa')).toBeTruthy()
})
