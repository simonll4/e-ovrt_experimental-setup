import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api'
import {
  useControlCurrent,
  useExperiment,
  useExperimentAlerts,
  useExperimentReport,
} from '../api/queries/experiments'
import ExperimentSummary, { readMetricRow, type MetricRow } from '../components/ExperimentSummary'
import {
  alertSeverityTone,
  experimentStatusLabel,
  experimentStatusTone,
  isNonTemporal,
  patternActiveSeconds,
} from '../experimentview'
import {
  APPLICABILITY_CAUSE,
  APPLICABILITY_STATUS,
  applicabilityLabel,
  conditionLabel,
} from '../labels'
import type {
  ActiveRiskPattern,
  ExperimentAlert,
  ExperimentReport,
  ExperimentRunState,
} from '../types'
import {
  Badge,
  Banner,
  Card,
  EmptyState,
  ErrorBanner,
  NumCell,
  PageHeader,
  Table,
} from '../components/ui'

const CONTROL_CURRENT_POLL_MS = 2000

const SEVERITY_LABEL: Record<string, string> = { high: 'Alta', medium: 'Media', low: 'Baja' }

function RiskActiveBanner({ patterns }: { patterns: ActiveRiskPattern[] }) {
  if (patterns.length === 0) return null
  return (
    <div className="eo-risk-banner" role="alert">
      {patterns.map((p) => {
        const seconds = patternActiveSeconds(p.active_ms)
        return (
          <div
            key={p.subject_key ?? p.pattern_id}
            className={`eo-risk-banner__item eo-risk-banner__item--${p.severity}`}
          >
            <Badge tone={alertSeverityTone(p.severity)}>{p.condition_id}</Badge>
            <span>riesgo activo{seconds !== null ? ` — hace ${seconds}s` : ''}</span>
          </div>
        )
      })}
    </div>
  )
}

/**
 * Mensaje de error para la interfaz.
 *
 * Antes devolvía `error 404`, que es un código filtrado a la pantalla. El número
 * se conserva —sirve para reportar el problema— pero acompañado de qué significa.
 */
function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 404) return 'no encontrado (404)'
    if (e.status >= 500) return `el servicio falló (${e.status})`
    return `no se pudo leer (${e.status})`
  }
  return String(e)
}

/** Un 404 no es una falla: el artefacto todavía no existe. */
function isNotFound(e: unknown): boolean {
  return e instanceof ApiError && e.status === 404
}

const fmtValue = (m: MetricRow): string => {
  if (m.value == null) return '—'
  const digits = Math.abs(m.value) >= 100 ? 0 : 3
  const n = m.value.toFixed(digits).replace('.', ',')
  return m.unit ? `${n} ${m.unit}` : n
}

const fmtMoment = (ms: number | null | undefined): string =>
  ms == null ? '—' : `${(ms / 1000).toFixed(1).replace('.', ',')} s`

export default function ExperimentDetailPage() {
  const { id = '' } = useParams()

  // El estado del experimento se repregunta solo mientras está en curso.
  const consultaExperimento = useExperiment(id)
  const experiment = consultaExperimento.data ?? null
  const error = consultaExperimento.error ? errorMessage(consultaExperimento.error) : null
  const running = experiment?.status === 'running'

  // Alertas y reporte: un 404 acá es "todavía no se consolidó", no una falla —
  // por eso se separa del error rojo y se muestra como pendiente.
  const consultaAlertas = useExperimentAlerts(id, Boolean(id))
  const alerts: ExperimentAlert[] | null = consultaAlertas.data ?? null
  const alertsPending = Boolean(consultaAlertas.error && isNotFound(consultaAlertas.error))
  const alertsError =
    consultaAlertas.error && !alertsPending ? errorMessage(consultaAlertas.error) : null

  const consultaReporte = useExperimentReport(id, Boolean(id))
  const report: ExperimentReport | null = consultaReporte.data ?? null
  const reportPending = Boolean(consultaReporte.error && isNotFound(consultaReporte.error))
  const reportError =
    consultaReporte.error && !reportPending ? errorMessage(consultaReporte.error) : null

  // Estado vivo del motor de reglas, solo mientras el experimento está en curso:
  // es lo que mantiene al día el banner de riesgo activo entre la confirmación y
  // la resolución del patrón. Un 404 (sin corrida activa) resuelve a null y no
  // muestra banner; un error transitorio deja el último estado conocido.
  const activePatterns: ActiveRiskPattern[] =
    useControlCurrent(Boolean(running)).data?.patterns ?? []

  const metrics: MetricRow[] = useMemo(
    () => (Array.isArray(report?.resultados) ? report.resultados.map(readMetricRow) : []),
    [report],
  )

  if (error) {
    return <ErrorBanner>Error cargando el experimento {id}: {error}</ErrorBanner>
  }
  if (!experiment) return <p className="eo-empty">Cargando experimento {id}…</p>

  const nonTemporal = isNonTemporal(report)

  return (
    <>
      <RiskActiveBanner patterns={activePatterns} />

      <PageHeader
        title={experiment.slug || experiment.experiment_id}
        meta={
          <>
            <Badge tone={experimentStatusTone(experiment)} pulse={running}>
              {experimentStatusLabel(experiment)}
            </Badge>
            {/* El id solo se repite si el título es el slug: si no, ya está arriba. */}
            {experiment.slug && <span className="eo-mono">{experiment.experiment_id}</span>}
          </>
        }
        actions={
          experiment.media_run_id ? (
            <Link className="eo-btn eo-btn--secondary" to={`/runs/${experiment.media_run_id}`}>
              Ver la corrida
            </Link>
          ) : undefined
        }
      />

      {nonTemporal && (
        <Banner tone="warn">
          El conjunto evaluado <b>no es temporal</b>: no hay secuencia sobre la que medir
          continuidad, así que las métricas temporales quedan sin dato en vez de en cero.
        </Banner>
      )}

      <ExperimentSummary metrics={metrics} alerts={alertsError ? null : alerts} />

      <Card title="Resultados del experimento" meta={`${metrics.length} métricas`} flush>
        {reportError && <ErrorBanner>No se pudo leer el reporte: {reportError}</ErrorBanner>}
        {!reportError && metrics.length === 0 && (
          <EmptyState
            hint={
              !reportPending
                ? 'El reporte se generó pero no trajo métricas.'
                : running
                  ? 'El reporte se consolida cuando el experimento termina.'
                  : // Ya terminó y sigue sin reporte: no se consolidó. Decir
                    // "cuando termine" acá sería falso.
                    'El experimento terminó sin consolidar el reporte. Suele pasar cuando una de las dos corridas falla.'
            }
          >
            {reportPending ? 'No hay reporte' : 'Sin resultados'}
          </EmptyState>
        )}
        {!reportError && metrics.length > 0 && (
          <>
            <Table>
              <thead>
                <tr>
                  <th>Métrica</th>
                  <th className="eo-num">Medido</th>
                  <th>Estado</th>
                  <th>Por qué</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m, i) => (
                  <tr key={`${m.name}-${i}`}>
                    <td className="eo-mono">{m.name}</td>
                    <NumCell>{fmtValue(m)}</NumCell>
                    <td>
                      {m.status === 'computed' ? (
                        <Badge tone="ok">Medida</Badge>
                      ) : (
                        <Badge tone="neutral">Sin dato</Badge>
                      )}
                    </td>
                    <td className="eo-cell--why">
                      {m.status === 'computed'
                        ? '—'
                        : [
                            applicabilityLabel(m.status, APPLICABILITY_STATUS),
                            m.cause ? applicabilityLabel(m.cause, APPLICABILITY_CAUSE) : null,
                          ]
                            .filter(Boolean)
                            .join(': ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            {/* El backend no expone umbrales: MetricResult es {name, value, unit,
                status, cause}. Decirlo evita que se lea como un veredicto. */}
            <p className="eo-cap eo-cap--inset">
              El reporte informa el valor medido y por qué una métrica no se pudo medir. No
              incluye umbrales de aceptación: el criterio de éxito vive en el manifiesto del
              experimento, no en estos números.
            </p>
          </>
        )}
      </Card>

      <Card title="Alertas emitidas" meta={alerts ? String(alerts.length) : undefined} flush>
        {alertsError && <ErrorBanner>No se pudieron leer las alertas: {alertsError}</ErrorBanner>}
        {alertsPending && (
          <EmptyState
            hint={
              running
                ? 'Las alertas se consolidan cuando el experimento termina.'
                : 'El motor de reglas no dejó archivo de alertas para este experimento.'
            }
          >
            No hay alertas registradas
          </EmptyState>
        )}
        {!alertsError && !alertsPending && alerts && alerts.length === 0 && (
          <EmptyState hint="Ninguna condición de riesgo llegó a confirmarse.">
            Sin alertas
          </EmptyState>
        )}
        {!alertsError && alerts && alerts.length > 0 && (
          <Table>
            <thead>
              <tr>
                <th>Alerta</th>
                <th>Condición</th>
                <th>Severidad</th>
                <th className="eo-num">Momento</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.alert_id}>
                  <td className="eo-mono">{a.alert_id}</td>
                  <td>{conditionLabel(a.condition_id)}</td>
                  <td>
                    <Badge tone={alertSeverityTone(a.severity)}>
                      {SEVERITY_LABEL[a.severity] ?? a.severity}
                    </Badge>
                  </td>
                  <NumCell>{fmtMoment(a.timestamp_ms)}</NumCell>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Trazabilidad">
        <dl className="eo-deflist">
          <div>
            <dt>Corrida de video</dt>
            <dd className="eo-mono">
              {experiment.media_run_id ? (
                <Link to={`/runs/${experiment.media_run_id}`}>{experiment.media_run_id}</Link>
              ) : (
                '—'
              )}
            </dd>
          </div>
          <div>
            <dt>Corrida de reglas</dt>
            <dd className="eo-mono">{experiment.control_run_id ?? '—'}</dd>
          </div>
          <div>
            <dt>Manifiesto</dt>
            <dd className="eo-mono">{experiment.slug ?? '—'}</dd>
          </div>
        </dl>
      </Card>
    </>
  )
}
