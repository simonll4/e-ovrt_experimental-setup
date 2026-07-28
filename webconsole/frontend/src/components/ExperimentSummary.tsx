import Meter, { type MeterSegment } from './charts/Meter'
import { APPLICABILITY_CAUSE, applicabilityLabel } from '../labels'
import type { ExperimentAlert } from '../types'

export interface MetricRow {
  name: string
  value: number | null
  unit: string | null
  status: string
  cause: string | null
}

/**
 * Lectura tolerante de una fila de `report.resultados`.
 *
 * El backend no fija el esquema (ver spec §4): las filas llegan como `name` pero
 * versiones viejas del reporte usaban `metrica`/`metric`. Se acepta cualquiera en
 * vez de romper la pantalla con un reporte de hace dos semanas.
 */
export function readMetricRow(raw: unknown): MetricRow {
  const row = (raw ?? {}) as Record<string, unknown>
  const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)
  const str = (v: unknown) => (typeof v === 'string' && v ? v : null)
  return {
    name: str(row.name) ?? str(row.metrica) ?? str(row.metric) ?? '—',
    value: num(row.value) ?? num(row.valor),
    unit: str(row.unit) ?? str(row.unidad),
    status: str(row.status) ?? 'computed',
    cause: str(row.cause) ?? str(row.causa),
  }
}

const SEVERITY_ORDER = ['high', 'medium', 'low'] as const
const SEVERITY_LABEL: Record<string, string> = { high: 'alta', medium: 'media', low: 'baja' }
const SEVERITY_TONE: Record<string, MeterSegment['tone']> = {
  high: 'error',
  medium: 'warn',
  low: 'ok',
}

/**
 * Tres indicadores del experimento.
 *
 * No hay tile de "criterios cumplidos": `MetricResult` del backend es
 * `{name, value, unit, status, cause}` — **no tiene umbral**. El prototipo dibujaba
 * una columna "Límite" que ningún dato respalda, y compararla contra nada sería
 * inventar el veredicto. Lo que sí se puede afirmar es cuántas métricas se
 * pudieron medir y cuántas no, con su causa.
 */
export default function ExperimentSummary({
  metrics,
  alerts,
}: {
  metrics: MetricRow[]
  alerts: ExperimentAlert[] | null
}) {
  const computed = metrics.filter((m) => m.status === 'computed').length
  const notComputed = metrics.length - computed

  const bySeverity = SEVERITY_ORDER.map((s) => ({
    key: s,
    count: (alerts ?? []).filter((a) => a.severity === s).length,
  })).filter((s) => s.count > 0)

  const otherSeverities = (alerts ?? []).filter(
    (a) => !SEVERITY_ORDER.includes(a.severity as (typeof SEVERITY_ORDER)[number]),
  ).length

  // Causa más frecuente entre las no medidas: es la explicación que sirve.
  const causes = metrics.filter((m) => m.status !== 'computed' && m.cause).map((m) => m.cause as string)
  const topCause = causes.length
    ? causes.sort(
        (a, b) => causes.filter((c) => c === b).length - causes.filter((c) => c === a).length,
      )[0]
    : null

  return (
    <div className="eo-kpis">
      <div className="eo-kpi">
        <span className="eo-kpi__label">
          <i className="eo-kpi__dot" style={{ background: 'var(--ok)' }} />
          Métricas medidas
        </span>
        {/* Sin reporte no hay nada que contar: "0 de 0" leería como un resultado. */}
        <span className="eo-kpi__value">
          {metrics.length === 0 ? '—' : computed}
          {metrics.length > 0 && <small> de {metrics.length}</small>}
        </span>
        <span className="eo-kpi__foot">
          {metrics.length > 0 && (
            <Meter
              total={metrics.length}
              segments={[
                { value: computed, tone: 'ok', label: 'medidas' },
                { value: notComputed, tone: 'neutral', label: 'sin medir' },
              ]}
            />
          )}
        </span>
      </div>

      <div className="eo-kpi">
        <span className="eo-kpi__label">
          <i className="eo-kpi__dot" style={{ background: 'var(--sr)' }} />
          Alertas emitidas
        </span>
        <span className="eo-kpi__value">
          {alerts == null ? '—' : alerts.length}
          {alerts != null && alerts.length > 0 && <small> en total</small>}
        </span>
        <span className="eo-kpi__foot">
          {bySeverity.length > 0 && (
            <>
              <Meter
                segments={bySeverity.map((s) => ({
                  value: s.count,
                  tone: SEVERITY_TONE[s.key],
                  label: SEVERITY_LABEL[s.key],
                }))}
              />
              <span className="eo-kpi__sub">
                {bySeverity.map((s) => `${s.count} ${SEVERITY_LABEL[s.key]}`).join(' · ')}
                {otherSeverities > 0 && ` · ${otherSeverities} sin severidad conocida`}
              </span>
            </>
          )}
          {alerts != null && alerts.length === 0 && (
            <span className="eo-kpi__sub">ninguna condición se confirmó</span>
          )}
        </span>
      </div>

      <div className="eo-kpi">
        <span className="eo-kpi__label">
          <i className="eo-kpi__dot" style={{ background: 'var(--nt)' }} />
          Sin poder medir
        </span>
        <span className="eo-kpi__value">
          {metrics.length === 0 ? '—' : notComputed}
          {metrics.length > 0 && <small> de {metrics.length}</small>}
        </span>
        <span className="eo-kpi__foot">
          {topCause && (
            <span className="eo-kpi__sub">
              Causa más frecuente: {applicabilityLabel(topCause, APPLICABILITY_CAUSE)}
            </span>
          )}
        </span>
      </div>
    </div>
  )
}
