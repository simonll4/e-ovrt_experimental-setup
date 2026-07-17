import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, getExperiment, getExperimentAlerts, getExperimentReport } from '../api'
import { alertSeverityTone, experimentStatusLabel, experimentStatusTone, isNonTemporal } from '../experimentview'
import type { ExperimentAlert, ExperimentReport, ExperimentRunState } from '../types'
import { Badge, Card, EmptyState, ErrorBanner } from '../components/ui'

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

  if (error) return <ErrorBanner>Error cargando el experimento {id}: {error}</ErrorBanner>
  if (!experiment) return <p className="eo-empty">Cargando experimento {id}…</p>

  const nonTemporal = isNonTemporal(report)

  return (
    <div style={{ display: 'grid', gap: 'var(--space-5)' }}>
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
