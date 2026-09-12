import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError, getEvidenceStep } from '../../api'
import { Card, EmptyState, ErrorBanner, PageHeader, StatTile, Table } from '../../components/ui'
import type { EvidenceResult } from '../../types'

/** Una cifra de cabecera de resultado: siempre LEÍDA de metrics.json (a
 *  diferencia de la cifra de un paso, que puede ser citada) — `entero` marca
 *  un conteo que se muestra sin coma decimal (episodios, falsos positivos). */
export const fmt = (v: number | null | undefined, entero?: boolean) =>
  typeof v !== 'number' ? '—' : entero ? String(v) : v.toFixed(3).replace('.', ',')

// `pasoN`, si viene, enhebra el paso de origen en la miga del resultado
// (`Evidencia > Paso N > resultado`, no sólo `Evidencia > resultado`): es
// información real de la navegación (de qué paso se vino), no estado
// inventado — `crumbsFor` en `nav.ts` la lee del mismo query param.
const resultUrl = (id: string, pasoN?: number) =>
  `/evidencia/resultado?${new URLSearchParams(pasoN ? { id, paso: String(pasoN) } : { id })}`

/** La cifra de cabecera de un resultado CON su unidad.
 *
 *  La `nota` del adaptador es lo que distingue «64,534» de «64,534 ms», y esta
 *  columna mezcla resultados de esquemas distintos: sin unidad, el p95 de
 *  `t_alert_notification` quedaba junto a F1 entre 0 y 1 como si fuera
 *  comparable. `Resultado.tsx` ya la mostraba (`unit` del StatTile); acá se
 *  descartaba, así que la misma cifra perdía su unidad según el nivel. */
function CifraDeCabecera({ fila }: { fila: EvidenceResult }) {
  const c = fila.metricas?.cabecera[0]
  if (!c) return <span className="eo-na">sin artefacto en este repositorio</span>
  return <><i>{c.label}</i>{fmt(c.valor, c.entero)}{c.nota && <u>{c.nota}</u>}</>
}

/** La tabla de resultados que comparte un paso del recorrido con el respaldo
 *  instrumental (`/evidencia/respaldo`, servido inline desde `EvidencePage`
 *  porque no tiene ruta propia en la API — su desglose viaja en `recorrido()`). */
export function TablaResultados({ resultados, caption, pasoN }: { resultados: EvidenceResult[]; caption: string; pasoN?: number }) {
  return <Table aria-label={caption}>
    <thead><tr>
      <th>Resultado</th><th>Cifra de cabecera</th><th>Combinación declarada</th>
      <th className="eo-num">Respaldo</th>
    </tr></thead>
    <tbody>
      {resultados.map((r) => (
        <tr key={r.result_id}>
          <td>
            <div className="eo-rowname">
              <Link to={resultUrl(r.result_id, pasoN)}>
                <b>{r.titulo || r.etiqueta}</b>
              </Link>
              <span className="eo-mono">{r.result_id}</span>
            </div>
          </td>
          <td className="eo-cifra"><CifraDeCabecera fila={r} /></td>
          <td className="eo-comb">{r.reclamo}</td>
          <td className="eo-num eo-mono">{r.n_runs} corridas</td>
        </tr>
      ))}
      {resultados.length === 0 && <tr><td colSpan={4}><span className="eo-na">Sin resultados registrados.</span></td></tr>}
    </tbody>
  </Table>
}

export default function Paso() {
  const [params] = useSearchParams()
  const n = Number(params.get('n') ?? '1')
  const q = useQuery({ queryKey: ['evidencia', 'paso', n], queryFn: () => getEvidenceStep(n) })
  if (q.isPending) return <EmptyState>Leyendo archivo de evidencia…</EmptyState>
  if (q.error) {
    // Un 404 real (ese `n` no tiene paso) es la ÚNICA falla que puede decir
    // "no existe": cualquier otra (servicio caído, 500, JSON roto) tiene que
    // hablar como el resto del feature (`Entrada.tsx`, `EvidencePage.tsx`) — si
    // no, una falla de red durante una demo se leería como que el argumento
    // del informe tiene un hueco, que es falso.
    if (q.error instanceof ApiError && q.error.status === 404) {
      return <ErrorBanner>Ese paso del recorrido no existe.</ErrorBanner>
    }
    return <ErrorBanner>No se pudo leer el archivo de evidencia.</ErrorBanner>
  }
  const paso = q.data.paso
  if (!paso) return <EmptyState hint={q.data.message}>Archivo de evidencia no disponible</EmptyState>
  return <div className="eo-evidence">
    {/* Cuántos pasos hay lo decide `recorrido.yaml`, no esta plantilla: el
        «de 4» estaba hardcodeado y un paso nuevo en el YAML lo dejaba mintiendo.
        Sin `n_pasos` (respuesta vieja) se dice «paso N» a secas, nunca un total
        inventado. */}
    <PageHeader title={paso.titulo} meta={
      `paso ${paso.n}${q.data.n_pasos ? ` de ${q.data.n_pasos}` : ''} · ${q.data.resultados.length} resultados`
    } />
    <p className="eo-note">{paso.claim}</p>
    <Card title="El hallazgo del paso" meta={paso.cifra_nota ?? undefined}>
      <div className="eo-stats-row">
        <StatTile
          label={paso.cifra_label ?? ''}
          value={
            <span className={paso.cifra_origen === 'citada' ? 'eo-cifra--cit' : undefined} title={paso.fuente ?? undefined}>
              {paso.cifra ?? '—'}
            </span>
          }
        />
      </div>
    </Card>
    <Card title="Los resultados de este paso" flush>
      <TablaResultados resultados={q.data.resultados} caption={`Resultados del paso ${paso.n}`} pasoN={paso.n} />
    </Card>
  </div>
}
