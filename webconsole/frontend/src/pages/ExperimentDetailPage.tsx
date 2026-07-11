import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, getExperiment, getExperimentAlerts, getExperimentReport } from '../api'
import { alertSeverityColor, experimentStatusLabel, isNonTemporal } from '../experimentview'
import type { ExperimentAlert, ExperimentReport, ExperimentRunState } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

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

  if (error) return <p style={{ color: '#b00' }}>Error cargando el experimento {id}: {error}</p>
  if (!experiment) return <p>Cargando experimento {id}…</p>

  const nonTemporal = isNonTemporal(report)

  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <h2>
        {experiment.experiment_id} — {experimentStatusLabel(experiment)}
      </h2>
      <p>
        media run: {experiment.media_run_id ?? '—'} · control run: {experiment.control_run_id ?? '—'}
      </p>
      <section>
        <h3>Alertas</h3>
        {alertsError && <p style={{ color: '#b00' }}>{alertsError}</p>}
        {!alertsError && alerts && alerts.length === 0 && <p>Sin alertas.</p>}
        {!alertsError && alerts && alerts.length > 0 && (
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                {['alerta', 'condicion', 'severidad', 'ts (ms)'].map((h) => (
                  <th key={h} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.alert_id}>
                  <td style={CELL}>{a.alert_id}</td>
                  <td style={CELL}>{a.condition_id}</td>
                  <td style={CELL}>
                    <span style={{ color: alertSeverityColor(a.severity) }}>● {a.severity}</span>
                  </td>
                  <td style={CELL}>{a.timestamp_ms ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      <section>
        <h3>Reporte</h3>
        {reportError && <p>{reportError}</p>}
        {!reportError && report && (
          <>
            {nonTemporal && (
              <p>
                <span style={{ background: '#eef', borderRadius: 4, padding: '2px 8px' }}>
                  diagnostico espacial / no-temporal
                </span>
                {' '}— metricas temporales no disponibles (N/A).
              </p>
            )}
            {Array.isArray(report.resultados) && report.resultados.length > 0 && (
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                <thead>
                  <tr>
                    {['metrica', 'status', 'causa'].map((h) => (
                      <th key={h} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.resultados.map((r, i) => {
                    const row = (r ?? {}) as Record<string, unknown>
                    return (
                      <tr key={i}>
                        <td style={CELL}>{String(row.name ?? row.metrica ?? row.metric ?? '—')}</td>
                        <td style={CELL}>{String(row.status ?? '—')}</td>
                        <td style={CELL}>{String(row.cause ?? row.causa ?? '—')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
            {(!Array.isArray(report.resultados) || report.resultados.length === 0) && (
              <p>Sin resultados todavia.</p>
            )}
          </>
        )}
      </section>
    </div>
  )
}
