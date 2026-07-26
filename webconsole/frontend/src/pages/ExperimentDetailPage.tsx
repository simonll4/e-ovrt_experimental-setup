import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, getControlCurrent, getExperiment, getExperimentAlerts, getExperimentReport } from '../api'
import {
  alertSeverityTone,
  experimentStatusLabel,
  experimentStatusTone,
  isNonTemporal,
  patternActiveSeconds,
} from '../experimentview'
import type { ActiveRiskPattern, ExperimentAlert, ExperimentReport, ExperimentRunState } from '../types'
import { Badge, Card, EmptyState, ErrorBanner } from '../components/ui'

const CONTROL_CURRENT_POLL_MS = 2000

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
            <span>
              riesgo activo{seconds !== null ? ` — hace ${seconds}s` : ''}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return `error ${e.status}`
  return String(e)
}

export default function ExperimentDetailPage() {
  const { id = '' } = useParams()
  const [experiment, setExperiment] = useState<ExperimentRunState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<ExperimentAlert[] | null>(null)
  const [alertsError, setAlertsError] = useState<string | null>(null)
  const [report, setReport] = useState<ExperimentReport | null>(null)
  const [reportError, setReportError] = useState<string | null>(null)
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
    refresh()
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
      })
      .catch((e) => {
        if (!alive) return
        setAlertsError(errorMessage(e))
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
        if (e instanceof ApiError && e.status === 404) {
          setReportError('Reporte no disponible todavia.')
        } else {
          setReportError(errorMessage(e))
        }
      })
    return () => {
      alive = false
    }
  }, [id])

  // Poll independiente (2s) del estado vivo del control-plane, solo mientras
  // el experimento esta running: es lo que mantiene el banner de riesgo
  // activo al dia entre confirmacion y resolucion del patron (motor
  // buffereado + card "Alertas" que solo carga una vez, spec del banner).
  // 404 (sin corrida activa) resuelve a null via getControlCurrent — no
  // banner, sin ensuciar la pagina; un error transitorio de red se traga acá
  // (no debe romper la pagina ni el badge de estado) y deja el ultimo estado
  // conocido tal cual, a la espera del proximo poll.
  useEffect(() => {
    if (!running) {
      setActivePatterns([])
      return
    }
    let alive = true
    const poll = () =>
      getControlCurrent()
        .then((snapshot) => {
          if (!alive) return
          setActivePatterns(snapshot?.patterns ?? [])
        })
        .catch(() => {
          /* error transitorio: no tocar la pagina, se reintenta en el proximo poll */
        })
    poll()
    const timer = setInterval(poll, CONTROL_CURRENT_POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, id])

  if (error) return <ErrorBanner>Error cargando el experimento {id}: {error}</ErrorBanner>
  if (!experiment) return <p className="eo-empty">Cargando experimento {id}…</p>

  const nonTemporal = isNonTemporal(report)

  return (
    <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
      <RiskActiveBanner patterns={activePatterns} />
      <h2>
        {experiment.experiment_id} — <Badge tone={experimentStatusTone(experiment)}>{experimentStatusLabel(experiment)}</Badge>
      </h2>
      <p>
        media run: {experiment.media_run_id ?? '—'} · control run: {experiment.control_run_id ?? '—'}
      </p>
      <Card title="Alertas">
        {alertsError && <ErrorBanner>{alertsError}</ErrorBanner>}
        {!alertsError && alerts && alerts.length === 0 && <EmptyState>Sin alertas.</EmptyState>}
        {!alertsError && alerts && alerts.length > 0 && (
          <table className="eo-table">
            <thead>
              <tr>
                {['alerta', 'condicion', 'severidad', 'ts (ms)'].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.alert_id}>
                  <td>{a.alert_id}</td>
                  <td>{a.condition_id}</td>
                  <td>
                    <Badge tone={alertSeverityTone(a.severity)}>{a.severity}</Badge>
                  </td>
                  <td className="eo-num">{a.timestamp_ms ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <Card title="Reporte">
        {reportError && <ErrorBanner>{reportError}</ErrorBanner>}
        {!reportError && report && (
          <>
            {nonTemporal && (
              <p>
                <Badge tone="neutral">no-temporal</Badge>
                {' '}— metricas temporales no disponibles (N/A).
              </p>
            )}
            {Array.isArray(report.resultados) && report.resultados.length > 0 && (
              <table className="eo-table">
                <thead>
                  <tr>
                    {['metrica', 'status', 'causa'].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.resultados.map((r, i) => {
                    const row = (r ?? {}) as Record<string, unknown>
                    return (
                      <tr key={i}>
                        <td>{String(row.name ?? row.metrica ?? row.metric ?? '—')}</td>
                        <td>{String(row.status ?? '—')}</td>
                        <td>{String(row.cause ?? row.causa ?? '—')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
            {(!Array.isArray(report.resultados) || report.resultados.length === 0) && (
              <EmptyState>Sin resultados todavia.</EmptyState>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
