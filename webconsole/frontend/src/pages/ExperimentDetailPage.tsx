import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ApiError,
  getControlCurrent,
  getExperiment,
  getExperimentAlerts,
  getExperimentReport,
} from '../api'
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
  DISTRIBUTION_OUTCOME,
  applicabilityLabel,
  conditionLabel,
} from '../labels'
import type {
  ActiveRiskPattern,
  ExperimentAlert,
  ExperimentReport,
  DistributionOutcomeRecord,
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
import Meter from '../components/charts/Meter'

const CONTROL_CURRENT_POLL_MS = 2000

const SEVERITY_LABEL: Record<string, string> = { high: 'Alta', medium: 'Media', low: 'Baja' }
const DISTRIBUTION_OUTCOME_TONE: Record<string, 'ok' | 'neutral' | 'error'> = {
  delivered: 'ok',
  suppressed_cooldown: 'neutral',
  skipped_duplicate: 'neutral',
  failed: 'error',
  dead_letter: 'error',
}

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

const isDistributionRun = (distribution: unknown): distribution is Record<string, unknown> => {
  return typeof distribution === 'object' && distribution !== null
}

const readDistributionSummary = (report: ExperimentReport | null): Record<string, unknown> | null => {
  if (!isDistributionRun(report?.distribucion)) return null
  if (Object.keys(report?.distribucion ?? {}).length === 0) return null
  return report?.distribucion ?? null
}

const readDistributionOutcome = (
  report: ExperimentReport | null,
  alert: ExperimentAlert,
): DistributionOutcomeRecord | null => {
  if (!isDistributionRun(report?.distribucion_por_alerta)) return null
  const payload = report.distribucion_por_alerta[alert.alert_id]
  return typeof payload === 'object' && payload !== null ? payload : null
}

const distributionOutcomeLabel = (outcome: string | null | undefined): string | null => {
  if (!outcome) return null
  return applicabilityLabel(outcome, DISTRIBUTION_OUTCOME)
}

const distributionOutcomeTone = (outcome: string | null | undefined): 'ok' | 'neutral' | 'error' => {
  if (!outcome) return 'neutral'
  return DISTRIBUTION_OUTCOME_TONE[outcome] ?? 'neutral'
}

const distributionOutcomeSegments = (distribution: Record<string, unknown>) => {
  const counts = distribution['counts']
  if (!isDistributionRun(counts)) return []

  const entries = Object.entries(counts)
    .filter(([, raw]) => typeof raw === 'number' && raw > 0)
    .map(([outcome, count]) => {
      const key = outcome
      return {
        key,
        label: applicabilityLabel(key, DISTRIBUTION_OUTCOME),
        value: count as number,
        tone: DISTRIBUTION_OUTCOME_TONE[key] ?? 'neutral',
      }
    })

  return entries
}

function DistributionOutcomeCell({
  report,
  alert,
}: {
  report: ExperimentReport | null
  alert: ExperimentAlert
}) {
  const outcome = readDistributionOutcome(report, alert)?.outcome
  if (!outcome || typeof outcome !== 'string') {
    return <span>—</span>
  }
  const label = distributionOutcomeLabel(outcome)
  return <Badge tone={distributionOutcomeTone(outcome)}>{label ?? outcome}</Badge>
}

const readSkippedInvalidAlerts = (
  distribution: Record<string, unknown> | null,
): number | null => {
  if (!distribution) return null
  const skippedInvalid = distribution['skipped_invalid_alerts']
  if (typeof skippedInvalid === 'number') return skippedInvalid
  return null
}

export default function ExperimentDetailPage() {
  const { id = '' } = useParams()
  const [experiment, setExperiment] = useState<ExperimentRunState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<ExperimentAlert[] | null>(null)
  const [alertsError, setAlertsError] = useState<string | null>(null)
  const [alertsPending, setAlertsPending] = useState(false)
  const [report, setReport] = useState<ExperimentReport | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
  /** El reporte todavía no se consolidó. No es un error: no va en rojo. */
  const [reportPending, setReportPending] = useState(false)
  const [activePatterns, setActivePatterns] = useState<ActiveRiskPattern[]>([])
  const running = experiment?.status === 'running'

  const refresh = () =>
    getExperiment(id)
      .then((e) => {
        setExperiment(e)
        setError(null)
      })
      .catch((e) => setError(errorMessage(e)))

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (!running) return
    const timer = setInterval(refresh, 4000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running])

  useEffect(() => {
    let alive = true
    getExperimentAlerts(id)
      .then((a) => {
        if (!alive) return
        setAlerts(a)
        setAlertsError(null)
        setAlertsPending(false)
      })
      .catch((e) => {
        if (!alive) return
        // Un 404 acá es "todavía no hay archivo de alertas", no una falla.
        if (isNotFound(e)) {
          setAlertsPending(true)
          setAlertsError(null)
        } else {
          setAlertsError(errorMessage(e))
        }
      })
    return () => {
      alive = false
    }
  }, [id])

  useEffect(() => {
    let alive = true
    getExperimentReport(id)
      .then((r) => {
        if (!alive) return
        setReport(r)
        setReportError(null)
      })
      .catch((e) => {
        if (!alive) return
        if (isNotFound(e)) {
          setReportPending(true)
          setReportError(null)
        } else {
          setReportError(errorMessage(e))
        }
      })
    return () => {
      alive = false
    }
  }, [id])

  // Poll independiente (2s) del estado vivo del motor de reglas, solo mientras el
  // experimento está en curso: es lo que mantiene al día el banner de riesgo activo
  // entre la confirmación y la resolución del patrón. Un 404 (sin corrida activa)
  // resuelve a null y no muestra banner; un error transitorio de red se traga acá y
  // deja el último estado conocido, a la espera del próximo poll.
  useEffect(() => {
    if (!running) {
      setActivePatterns([])
      return
    }
    let alive = true
    const poll = () =>
      getControlCurrent()
        .then((snapshot) => {
          if (alive) setActivePatterns(snapshot?.patterns ?? [])
        })
        .catch(() => {
          /* transitorio: no tocar la página, se reintenta */
        })
    poll()
    const timer = setInterval(poll, CONTROL_CURRENT_POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, id])

  const metrics: MetricRow[] = useMemo(
    () => (Array.isArray(report?.resultados) ? report.resultados.map(readMetricRow) : []),
    [report],
  )
  const distribution = useMemo(() => readDistributionSummary(report), [report])
  const distributionSegments = useMemo(
    () => (distribution ? distributionOutcomeSegments(distribution) : []),
    [distribution],
  )
  const distributionMetric = useMemo(
    () => metrics.find((row) => row.name === 't_alert-notification'),
    [metrics],
  )
  const distributionSkippedInvalid = useMemo(
    () => readSkippedInvalidAlerts(distribution),
    [distribution],
  )
  const distributionMetricLabel = useMemo(
    () =>
      distributionMetric && distributionMetric.cause
        ? applicabilityLabel(distributionMetric.cause, APPLICABILITY_CAUSE)
        : '',
    [distributionMetric],
  )
  const distributionHasRun = useMemo(() => {
    const byAlert = report?.distribucion_por_alerta
    return distribution !== null || (isDistributionRun(byAlert) && Object.keys(byAlert).length > 0)
  }, [distribution, report])
  const distributionMetricStatusLabel = useMemo(
    () =>
      distributionMetric
        ? applicabilityLabel(distributionMetric.status, APPLICABILITY_STATUS)
        : '',
    [distributionMetric],
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
                <th className="eo-mono">Notificada</th>
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
                  <td>
                    {!distributionHasRun ? (
                      <span
                        title="el módulo de distribución no corrió para este experimento"
                        className="eo-mono"
                      >
                        —
                      </span>
                    ) : (
                      <DistributionOutcomeCell
                        report={report}
                        alert={a}
                      />
                    )}
                  </td>
                  <NumCell>{fmtMoment(a.timestamp_ms)}</NumCell>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card title="Distribución de alertas" flush>
        {distribution === null ? (
          <EmptyState
            hint="Si el experimento no incluyó distribución, este resumen no se genera."
          >
            Sin datos de distribución
          </EmptyState>
        ) : (
          <div className="eo-stack">
            {distributionSegments.length > 0 ? (
              <div>
                <Meter
                  segments={distributionSegments.map((segment) => ({
                    value: segment.value,
                    tone: segment.tone,
                    label: segment.label,
                  }))}
                  total={Math.max(
                    1,
                    distributionSegments.reduce((acc, segment) => acc + segment.value, 0),
                  )}
                />
                <p className="eo-cap eo-cap--inset">
                  {distributionSegments
                    .map((segment) => `${segment.label}: ${segment.value}`)
                    .join(' · ')}
                </p>
              </div>
            ) : (
              <p className="eo-cap eo-cap--inset">No hay resultados de entregas para graficar aún.</p>
            )}

            <p className="eo-cap eo-cap--inset">
              Latencia de entrega:{' '}
              {distributionMetric ? <strong>{fmtValue(distributionMetric)}</strong> : '—'}
              {distributionMetric && distributionMetric.value == null && distributionMetricLabel
                ? ` (${distributionMetricLabel})`
                : ''}
              {distributionMetric ? ` · Estado: ${distributionMetricStatusLabel}` : ''}
            </p>

            {distributionSkippedInvalid !== null && distributionSkippedInvalid > 0 && (
              <p className="eo-cap eo-cap--inset">
                Alertas descartadas por datos inválidos: {distributionSkippedInvalid}
              </p>
            )}
          </div>
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
