import { Fragment, type ReactElement } from 'react'
import { Card, Table } from '../../components/ui'
import { SERIES_COLORS } from '../../palette'
import type { EvidenceMetricRow, EvidenceMetrics } from '../../types'

type DesgloseData = EvidenceMetrics['desgloses'][number]

const fmtDec = (v: unknown, dec = 3) =>
  typeof v === 'number' ? v.toFixed(dec).replace('.', ',') : '—'
const fmtInt = (v: unknown) => (typeof v === 'number' ? String(Math.round(v)) : '—')
const miles = (n: number) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
const fmtMs = (v: unknown) => (typeof v === 'number' ? `${miles(v)} ms` : '—')
const fmtTexto = (v: unknown) => (v == null ? '—' : String(v))

// Columnas cuyo encabezado se alinea a la derecha, como en el mockup — sólo
// cosmética: no condiciona qué campo se lee (eso lo decide `ESQUEMAS`).
const NUMERICAS = new Set([
  'Clips', 'Episodios', 'recall', 'FP', 'SDR', 't_alert', 'Esperados', 'Detectados',
  'Tiempo observado', 'n', 'p50', 'p95', 'p99', 'F1',
  'Faltantes E-IND', 'Faltantes E-DIR', 'Rescatadas por E-DIR', 'Fracción rescatada',
])

/** Identificador de causa → la frase que se lee. Son 70 filas de «Por clip»
 *  con un único valor crudo (`negative_clip_no_episodes`) y la pantalla la
 *  mostraba tal cual.
 *
 *  Lo NO reconocido pasa tal cual, nunca se vacía: la misma celda la usa la
 *  columna «recall» de «Por escenario» con una cadena que el backend ya escribe
 *  legible («sin episodios evaluables»), y un mapeo que devolviera '' borraría
 *  la única declaración que esa fila tiene. */
const CAUSA: Record<string, string> = {
  negative_clip_no_episodes: 'clip negativo: sin episodios esperados',
}
const causaLegible = (valor: string): string => CAUSA[valor] ?? valor

/** Barra de UNA sola tinta: esto es magnitud, no identidad — el violeta es
 *  acción, nunca condición (ver `palette.ts`). El valor va en tinta de TEXTO
 *  (`.eo-barval`); el color vive en la marca, `SERIES_COLORS[0]` (el azul del
 *  sistema, validado para superficie oscura). Se aplica inline porque es un
 *  color de serie, no un token del sistema — el mismo criterio que ya siguen
 *  `GroupedBars` y `ComparePage`. Lo que no tiene dato no se dibuja. */
function Barra({ valor }: { valor: number | null }) {
  if (valor == null) return null
  return (
    <span className="eo-track">
      <i
        className="eo-bar"
        style={{ width: `${Math.max(0, Math.min(1, valor)) * 100}%`, background: SERIES_COLORS[0] }}
      />
    </span>
  )
}

const celdaNombre = (f: EvidenceMetricRow) => <td className="eo-mono">{fmtTexto(f.nombre)}</td>
const celdaEntero = (get: (f: EvidenceMetricRow) => unknown) => (f: EvidenceMetricRow) =>
  <td className="eo-num">{fmtInt(get(f))}</td>
const celdaDec = (get: (f: EvidenceMetricRow) => unknown) => (f: EvidenceMetricRow) =>
  <td className="eo-num">{fmtDec(get(f))}</td>
const celdaMs = (get: (f: EvidenceMetricRow) => unknown) => (f: EvidenceMetricRow) =>
  <td className="eo-num">{fmtMs(get(f))}</td>
const celdaMono = (get: (f: EvidenceMetricRow) => unknown) => (f: EvidenceMetricRow) =>
  <td className="eo-mono">{fmtTexto(get(f))}</td>

/** Ronda de arreglo 1 — defecto 2: una métrica DERIVADA (se calcula a partir
 *  de un denominador que puede no existir: SDR, t_alert, F1…) nunca muestra el
 *  valor crudo que mande el backend cuando la fila declara `no_aplica` — sólo
 *  la columna "principal" (`celdaRecall`, abajo) dice la causa completa; el
 *  resto de las derivadas se declara "—", no un número. El backend hoy decide
 *  `no_aplica` mirando sólo el numerador principal (`recall`) y reenvía SDR/
 *  t_alert tal cual vengan — hoy coinciden en null, pero esa correlación vive
 *  en LOS DATOS, no en el código: sin este guardia, un cambio en los datos que
 *  dejara de nulear SDR mostraría un número donde la fila dice "sin dato". Es
 *  el mismo patrón del bug histórico (F1: 0.0 en filas "sin dato"), acá
 *  cerrado en el código en vez de depender de que el backend lo siga
 *  cumpliendo. NO se usa en columnas de CONTEO (clips, episodios, FP,
 *  esperados, detectados): esas siguen siendo números reales aunque el ratio
 *  de la fila no tenga denominador — el mockup respalda esto (P3: Clips=2,
 *  Episodios=0, FP=0 se muestran; sólo el recall se declara). */
const sinNumeroSiNoAplica = (celda: (f: EvidenceMetricRow) => ReactElement) => (f: EvidenceMetricRow) =>
  f.no_aplica ? <td className="eo-num" style={{ color: 'var(--tx4)' }}>—</td> : celda(f)

/** La única celda que dice la causa completa cuando `no_aplica` está
 *  presente: el resto de la fila sigue teniendo datos reales (clips,
 *  episodios, FP no dejan de existir porque el recall no tenga denominador),
 *  así que declarar TODA la fila borraría datos reales — no se hace. Ni el
 *  valor ni la barra aparecen cuando `no_aplica` está presente. */
const celdaRecall = (get: (f: EvidenceMetricRow) => unknown) => (f: EvidenceMetricRow) => {
  if (f.no_aplica) return <td className="eo-na">{causaLegible(f.no_aplica)}</td>
  const valor = get(f)
  const num = typeof valor === 'number' ? valor : null
  return <td><div className="eo-barcell"><span className="eo-barval">{fmtDec(num)}</span><Barra valor={num} /></div></td>
}

/** Qué campo del registro corresponde a cada columna, indexado por **esquema
 *  Y `id`** de desglose, y por POSICIÓN dentro de esa combinación.
 *
 *  Ronda de arreglo 1 — defecto 1: antes se indexaba sólo por `id`, y
 *  `_clip_person_state` (backend) produce un desglose con `id: "clip"` —EL
 *  MISMO id que usa `clip_campaign`'s "Por clip"— pero con columnas distintas
 *  (3 contra 6). Sólo un guardia incidental de conteo (`spec.length ===
 *  columnas.length`) evitaba la colisión; si algún día las formas coincidieran
 *  en cantidad de columnas, el spec equivocado se habría aplicado igual. La
 *  clave real de qué significa cada columna es "esquema + id", no sólo "id":
 *  ver los cuatro adaptadores reales en `webconsole/backend/.../evidence_metrics.py`.
 *  Una combinación sin entrada — o cuya cantidad de columnas no coincide con
 *  lo declarado — cae al genérico de abajo, que nunca inventa a qué columna
 *  corresponde un valor. */
const ESQUEMAS: Record<string, Record<string, Array<(f: EvidenceMetricRow) => ReactElement>>> = {
  'clip_campaign_metrics.v1': {
    condicion: [
      celdaNombre, celdaEntero((f) => f.episodios),
      sinNumeroSiNoAplica(celdaDec((f) => f.sdr)), sinNumeroSiNoAplica(celdaMs((f) => f.t_alert_ms)),
    ],
    escenario: [
      celdaNombre, celdaEntero((f) => f.clips), celdaEntero((f) => f.episodios),
      celdaRecall((f) => f.recall), celdaEntero((f) => f.fp), sinNumeroSiNoAplica(celdaDec((f) => f.sdr)),
    ],
    clip: [
      celdaNombre, celdaMono((f) => f.escenario), celdaEntero((f) => f.esperados),
      celdaEntero((f) => f.detectados), celdaRecall((f) => f.recall),
      sinNumeroSiNoAplica(celdaMs((f) => f.t_alert_ms)),
    ],
    negativos: [
      celdaEntero((f) => f.clips), celdaEntero((f) => f.fp), celdaMs((f) => f.observado_ms),
    ],
  },
  // `bench_nivel_a/na1_…`: 34 filas que salían como `{"condicion":"CR-01","f1":0.0}`.
  'clip_person_state.v1': {
    clip: [celdaNombre, celdaMono((f) => f.condicion), celdaRecall((f) => f.f1)],
  },
  // `bench_nivel_a/d1_…`: salía como `{"valores":{"best_edir_variant":…}}`. Las
  // columnas las aplana ahora `_nivel_a_gate` en `evidence_metrics.py`.
  nivel_a_gate: {
    estrato: [
      celdaNombre, celdaMono((f) => f.variante), celdaEntero((f) => f.eind_misses),
      celdaEntero((f) => f.edir_misses), celdaEntero((f) => f.recuperadas),
      celdaDec((f) => f.fraccion),
    ],
  },
  // `realtime/t_alert_notification`: salía como `{"n":447,"p50":41.392578125,…}`,
  // con doce decimales. Las latencias son milisegundos, no adimensionales.
  'talert_notification_metrics.v1': {
    origen: [
      celdaNombre, celdaEntero((f) => f.n), celdaMs((f) => f.p50),
      celdaMs((f) => f.p95), celdaMs((f) => f.p99),
    ],
    entrega: [
      celdaNombre, celdaEntero((f) => f.n), celdaMs((f) => f.p50),
      celdaMs((f) => f.p95), celdaMs((f) => f.p99),
    ],
  },
}

function Fila({ esquema, desglose, fila }: { esquema: string; desglose: DesgloseData; fila: EvidenceMetricRow }) {
  const spec = ESQUEMAS[esquema]?.[desglose.id]
  if (spec && spec.length === desglose.columnas.length) {
    return <tr>{spec.map((celda, j) => <Fragment key={j}>{celda(fila)}</Fragment>)}</tr>
  }
  // Esquema/id no reconocidos (o cantidad de columnas inesperada): el nombre,
  // y aparte, el resto del registro tal cual llegó — nunca adivina en qué
  // columna va cada valor.
  const resto = Object.fromEntries(
    Object.entries(fila).filter(([k]) => k !== 'nombre' && k !== 'no_aplica'),
  )
  return <tr>
    <td className="eo-mono">{fmtTexto(fila.nombre)}</td>
    <td colSpan={Math.max(1, desglose.columnas.length - 1)} className={fila.no_aplica ? 'eo-na' : 'eo-mono'}>
      {fila.no_aplica ? causaLegible(fila.no_aplica) : JSON.stringify(resto)}
    </td>
  </tr>
}

/** A partir de cuántas filas el desglose arranca plegado. «Por clip» son 34 (y
 *  70 en la campaña más larga): dibujarlas siempre empujaba todo lo demás fuera
 *  de pantalla. Los desgloses cortos —condición, escenario, negativos— siguen
 *  abiertos, que es donde se lee el argumento. */
const PLEGAR_DESDE = 12

/** Una fila con al menos una celda sin dato, dejando fuera `nombre` (el
 *  identificador, nunca una cifra) y `no_aplica` (la causa, que se cuenta
 *  aparte). Es la señal que `no_aplica` NO cubre: esa sólo habla de la columna
 *  principal (recall/F1) y el resto de las columnas lleva `null` legítimos que
 *  la tabla dibuja como «—». */
const tieneCeldaSinDato = (f: EvidenceMetricRow): boolean =>
  Object.entries(f).some(([k, v]) => k !== 'nombre' && k !== 'no_aplica' && v == null)

/** Qué hay adentro del plegado, dicho en el `<summary>`: cuántas filas y
 *  cuántas DECLARAN una causa en vez de traer una cifra. Sin eso, plegar
 *  escondería justo lo que la limitación L5 obliga a mostrar — el desglose no
 *  es un opcional, y una fila declarada no puede desaparecer sin dejar rastro.
 *
 *  R-29 (6ª aparición del defecto reincidente): la versión anterior decía
 *  «N filas, todas con cifra» cuando ninguna declaraba causa — una afirmación
 *  de COMPLETITUD derivada de `no_aplica`, que mide UNA columna. Medido sobre
 *  datos reales: en el desglose «Por clip» de `clip_bench/d1_…_edirpair_scene`,
 *  24 de 34 filas traen alguna celda nula sin declarar causa. Acá no se afirma
 *  completitud en ninguna rama: se cuenta lo que se mide —las que declaran
 *  causa— y se declara aparte lo que no se medía —las que tienen huecos sin
 *  causa—. Una ausencia de dato nunca se convierte en una afirmación. */
function resumenDe(filas: EvidenceMetricRow[]): string {
  const conCausa = filas.filter((f) => f.no_aplica).length
  const conHueco = filas.filter((f) => !f.no_aplica && tieneCeldaSinDato(f)).length
  const cuantas = `${filas.length} ${filas.length === 1 ? 'fila' : 'filas'}`
  const declaran = conCausa === 0
    ? 'ninguna declara causa'
    : `${conCausa} ${conCausa === 1 ? 'declara' : 'declaran'} causa en vez de cifra`
  const sujeto = conHueco === 1
    ? (conCausa === 0 ? 'una' : 'otra')
    : `${conCausa === 0 ? '' : 'otras '}${conHueco}`
  const huecos = conHueco === 0 ? '' : `; ${sujeto} con alguna celda sin dato`
  return `${cuantas}, ${declaran}${huecos}`
}

export default function Desglose({ esquema, desglose }: { esquema: string; desglose: DesgloseData }) {
  const tabla = (
    <Table aria-label={desglose.titulo}>
      <thead><tr>
        {desglose.columnas.map((c) => <th key={c} className={NUMERICAS.has(c) ? 'eo-num' : undefined}>{c}</th>)}
      </tr></thead>
      <tbody>
        {desglose.filas.map((fila, i) => (
          <Fila key={`${i}:${fila.nombre}`} esquema={esquema} desglose={desglose} fila={fila} />
        ))}
        {desglose.filas.length === 0 && (
          <tr><td colSpan={desglose.columnas.length}><span className="eo-na">Sin filas registradas.</span></td></tr>
        )}
      </tbody>
    </Table>
  )
  return <Card title={desglose.titulo} flush>
    {desglose.filas.length > PLEGAR_DESDE ? (
      <details className="eo-adv eo-adv--inset">
        <summary>{resumenDe(desglose.filas)}</summary>
        {tabla}
      </details>
    ) : tabla}
    {/* La tabla va a sangre (`flush`): el pie necesita su propio padding
        horizontal, igual que en ComparePage/ExperimentDetailPage/FrameInspector. */}
    {desglose.nota && <p className="eo-cap eo-cap--inset">{desglose.nota}</p>}
  </Card>
}
