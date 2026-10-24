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
import Termino from '../components/Glosario'
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
  Disclosure,
  EmptyState,
  ErrorBanner,
  LoadingState,
  NumCell,
  PageHeader,
  Table,
  TableScroll,
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

/** Tabla de métricas: nombre literal, valor con unidad, estado y por qué. */
function TablaMetricas({ filas, label }: { filas: MetricRow[]; label: string }) {
  return (
    <TableScroll label={label}>
      <Table aria-label={label}>
        <thead>
          <tr>
            <th>Métrica</th>
            <th className="eo-num">Medido</th>
            <th>Estado</th>
            <th>Por qué</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((m, i) => (
            <tr key={`${m.name}-${i}`}>
              {/* El nombre es un identificador del reporte: se muestra tal
                  cual, también el de una métrica que esta consola no conoce. */}
              <td className="eo-mono">{m.name}</td>
              <NumCell>{fmtValue(m)}</NumCell>
              <td>
                {m.status === 'computed' ? (
                  <Badge tone="ok">Medida</Badge>
                ) : (
                  <Badge tone="neutral">Sin dato</Badge>
                )}
              </td>
              <td className="eo-cell--wrap">
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
    </TableScroll>
  )
}

/** Resumen de las no medidas, por estado y por causa, con las mismas cuentas
 *  que las filas plegadas: «no aplica» y «no calculada» no se funden. */
function resumenNoMedidas(filas: MetricRow[]): string {
  const porEstado = new Map<string, Map<string, number>>()
  for (const m of filas) {
    const causas = porEstado.get(m.status) ?? new Map<string, number>()
    const causa = m.cause ? applicabilityLabel(m.cause, APPLICABILITY_CAUSE) : 'sin causa declarada'
    causas.set(causa, (causas.get(causa) ?? 0) + 1)
    porEstado.set(m.status, causas)
  }
  return [...porEstado.entries()]
    .map(([estado, causas]) => {
      const n = [...causas.values()].reduce((a, b) => a + b, 0)
      const detalle = [...causas.entries()].map(([c, k]) => `${c} ${k}`).join(', ')
      return `${applicabilityLabel(estado, APPLICABILITY_STATUS)} ${n} (${detalle})`
    })
    .join(' · ')
}

export default function ExperimentDetailPage() {
  const { id = '' } = useParams()

  // El estado del experimento se repregunta solo mientras está en curso.
  const consultaExperimento = useExperiment(id)
  const experiment = consultaExperimento.data ?? null
  const error = consultaExperimento.error ? errorMessage(consultaExperimento.error) : null
  const running = experiment?.status === 'running'

  // Alertas y reporte: un 404 acá es "todavía no se consolidó", no una falla —
  // por eso se separa del error rojo y se muestra como pendiente.
  const consultaAlertas = useExperimentAlerts(id, Boolean(id), running)
  const alerts: ExperimentAlert[] | null = consultaAlertas.data ?? null
  const alertsPending = Boolean(consultaAlertas.error && isNotFound(consultaAlertas.error))
  const alertsError =
    consultaAlertas.error && !alertsPending ? errorMessage(consultaAlertas.error) : null
  const alertsLoading = consultaAlertas.isPending && !consultaAlertas.data && !consultaAlertas.error

  const consultaReporte = useExperimentReport(id, Boolean(id), running)
  const report: ExperimentReport | null = consultaReporte.data ?? null
  const reportPending = Boolean(consultaReporte.error && isNotFound(consultaReporte.error))
  const reportError =
    consultaReporte.error && !reportPending ? errorMessage(consultaReporte.error) : null
  const reportLoading = consultaReporte.isPending && !consultaReporte.data && !consultaReporte.error

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
  const medidas = useMemo(() => metrics.filter((m) => m.status === 'computed'), [metrics])
  const noMedidas = useMemo(() => metrics.filter((m) => m.status !== 'computed'), [metrics])
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

  if (!experiment) {
    return (
      <>
        <PageHeader title={id} meta={error ? 'No se pudo leer el experimento' : 'Cargando el experimento…'} />
        {error ? (
          <ErrorBanner
            detail={String(consultaExperimento.error)}
            onRetry={() => void consultaExperimento.refetch()}
            retrying={consultaExperimento.isFetching}
          >
            Error cargando el experimento {id}: {error}
          </ErrorBanner>
        ) : (
          <LoadingState lines={4}>Cargando experimento {id}…</LoadingState>
        )}
      </>
    )
  }

  const nonTemporal = isNonTemporal(report)
  // «No incluida» sólo cuando el reporte lo declara: la métrica de entrega
  // trae la causa `no_distribution`. Sin esa declaración, una ausencia es sólo
  // eso — el reporte no trajo el resumen.
  const distribucionNoIncluida = distributionMetric?.cause === 'no_distribution'

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

      <Card title="Resultados del experimento" meta={report ? `${metrics.length} métricas` : undefined} flush>
        {reportError && (
          <ErrorBanner
            detail={String(consultaReporte.error)}
            onRetry={() => void consultaReporte.refetch()}
            retrying={consultaReporte.isFetching}
          >
            No se pudo leer el reporte: {reportError}
          </ErrorBanner>
        )}
        {reportLoading && <LoadingState lines={4}>Leyendo el reporte del experimento…</LoadingState>}
        {!reportError && !reportLoading && metrics.length === 0 && (
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
            {/* Lo medido a la vista; lo que no se pudo medir plegado, con su
                cantidad y el resumen de causas en el rótulo. Ninguna fila se
                pierde: están todas, sólo cambia lo que se ve primero. */}
            <h3 className="eo-section__h eo-cardhead">
              Medidas <small>{medidas.length} de {metrics.length}</small>
            </h3>
            {medidas.length > 0 ? (
              <TablaMetricas filas={medidas} label="Métricas medidas del experimento" />
            ) : (
              <p className="eo-note eo-cardnote">Ninguna métrica se pudo medir en este experimento.</p>
            )}
            {noMedidas.length > 0 && (
              <Disclosure className="eo-adv--inset" summary={`Sin medir (${noMedidas.length}) — ${resumenNoMedidas(noMedidas)}`}>
                <TablaMetricas filas={noMedidas} label="Métricas sin medir del experimento" />
              </Disclosure>
            )}
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
        {alertsError && (
          <ErrorBanner
            detail={String(consultaAlertas.error)}
            onRetry={() => void consultaAlertas.refetch()}
            retrying={consultaAlertas.isFetching}
          >
            No se pudieron leer las alertas: {alertsError}
          </ErrorBanner>
        )}
        {alertsLoading && <LoadingState lines={2}>Leyendo las alertas…</LoadingState>}
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
        {/* Cero alertas es un dato, no un vacío a explicar: una línea. */}
        {!alertsError && !alertsPending && alerts && alerts.length === 0 && (
          <p className="eo-note eo-cardnote">
            <b>Sin alertas</b> — ninguna condición de riesgo llegó a confirmarse.
          </p>
        )}
        {!alertsError && alerts && alerts.length > 0 && (
          <TableScroll label="Alertas emitidas">
            <Table aria-label="Alertas emitidas">
              <thead>
                <tr>
                  <th>Alerta</th>
                  <th>Condición</th>
                  <th>Severidad</th>
                  <th>Notificada</th>
                  <th className="eo-num">Momento</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.alert_id}>
                    <td className="eo-mono">{a.alert_id}</td>
                    <td><Termino id={a.condition_id}>{conditionLabel(a.condition_id)}</Termino></td>
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
          </TableScroll>
        )}
        {!alertsError && alerts && alerts.length > 0 && !distributionHasRun && (
          <p className="eo-cap eo-cap--inset">«—» en Notificada: el módulo de distribución no corrió para este experimento.</p>
        )}
      </Card>

      <Card title="Distribución de alertas" flush>
        {reportLoading ? (
          <LoadingState lines={2}>Leyendo el reporte de distribución…</LoadingState>
        ) : reportError ? (
          <p className="eo-note eo-cardnote">
            No se sabe: el reporte no se pudo leer (ver arriba).
          </p>
        ) : reportPending ? (
          <EmptyState
            hint={running ? 'Se consolida con el reporte, cuando el experimento termina.' : 'El reporte no se consolidó.'}
          >
            Distribución pendiente
          </EmptyState>
        ) : distribution === null ? (
          <EmptyState
            hint={
              distribucionNoIncluida
                ? `El reporte lo declara: ${distributionMetricLabel || 'sin distribución'}.`
                : 'El reporte no trae el resumen de distribución.'
            }
          >
            {distribucionNoIncluida ? 'El experimento no incluyó distribución' : 'Sin datos de distribución'}
          </EmptyState>
        ) : (
          <div className="eo-stack">
            {distributionSegments.length > 0 ? (
              <div className="eo-cardnote">
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
                <p className="eo-cap">
                  {distributionSegments
                    .map((segment) => `${segment.label}: ${segment.value}`)
                    .join(' · ')}
                </p>
              </div>
            ) : (
              <p className="eo-cap eo-cardnote">No hay resultados de entregas para graficar aún.</p>
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

      <Card title="Identificación y procedencia">
        <dl className="eo-deflist">
          <div>
            <dt>Experimento</dt>
            <dd className="eo-mono">{experiment.experiment_id}</dd>
          </div>
          <div>
            <dt>Manifiesto</dt>
            <dd className="eo-mono">{experiment.slug ?? '—'}</dd>
          </div>
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
        </dl>
      </Card>
    </>
  )
}
