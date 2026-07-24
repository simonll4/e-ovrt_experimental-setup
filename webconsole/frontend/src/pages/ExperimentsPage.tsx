import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, getCurrentExperiment, getExperimentManifests, runExperiment } from '../api'
import type { ExperimentManifestSummary, ExperimentRunState } from '../types'
import { experimentStatusLabel, experimentStatusTone } from '../experimentview'
import { usePreflight } from '../usePreflight'
import PlatformStatus from '../components/PlatformStatus'
import { Badge, Card, ErrorBanner, EmptyState } from '../components/ui'

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: string; active_experiment_id?: string }
    if (e.status === 409) {
      return `Ya hay un experimento activo: ${payload.active_experiment_id ?? '?'}`
    }
    if (e.status === 422) return 'Manifiesto invalido'
    if (e.status === 502) return 'Servicio no disponible'
    if (e.status === 503) return payload.detail ?? 'Plataforma no lista'
  }
  return String(e)
}

export default function ExperimentsPage() {
  const navigate = useNavigate()
  const preflight = usePreflight()
  const [rows, setRows] = useState<ExperimentManifestSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [current, setCurrent] = useState<ExperimentRunState | null>(null)
  const [slug, setSlug] = useState('')
  const [busy, setBusy] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    getExperimentManifests()
      .then((r) => {
        if (!alive) return
        setRows(r)
        setError(null)
        if (r.length > 0 && !slug) setSlug(r[0].slug)
      })
      .catch((e) => alive && setError(String(e)))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      getCurrentExperiment()
        .then((c) => {
          if (!alive) return
          setCurrent(c)
          if (c?.status === 'running') timer = setTimeout(tick, 4000)
        })
        .catch(() => {
          /* banner de estado activo: silencioso si falla el poll */
        })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const trigger = async () => {
    if (!slug) return
    setBusy(true)
    setRunError(null)
    try {
      const { experiment_id } = await runExperiment({ slug })
      navigate(`/experiments/${experiment_id}`)
    } catch (e) {
      setRunError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  // Gate de lanzamiento: sin preflight verde no se lanza (el BFF igualmente lo
  // rechaza con 503; acá se corta antes y con el motivo a la vista).
  const experimentRunning = current?.status === 'running'
  const blocked = !preflight?.ready || experimentRunning
  const blockedReason = experimentRunning
    ? 'hay un experimento en curso'
    : preflight === null
      ? 'verificando servicios…'
      : preflight.blockers[0]

  if (error) return <ErrorBanner>Error listando experimentos: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
      <h2>Experimentos</h2>
      {current && (
        <p>
          Experimento activo: <Link to={`/experiments/${current.experiment_id}`}>{current.experiment_id}</Link>
          {' — '}<Badge tone={experimentStatusTone(current)}>{experimentStatusLabel(current)}</Badge>
        </p>
      )}
      <Card title="Lanzar">
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
          <PlatformStatus status={preflight} />
          <select value={slug} onChange={(e) => setSlug(e.target.value)}>
            {rows.map((r) => (
              <option key={r.slug} value={r.slug}>{r.slug}</option>
            ))}
          </select>
          <button onClick={trigger} disabled={busy || !slug || blocked}>
            {busy ? 'Lanzando…' : 'Lanzar experimento'}
          </button>
        </div>
        {blocked && !busy && (
          <p className="eo-note eo-note--warn">No se puede lanzar: {blockedReason}.</p>
        )}
        {runError && <ErrorBanner>{runError}</ErrorBanner>}
      </Card>
      {rows.length === 0 ? (
        <EmptyState>Sin manifiestos todavía.</EmptyState>
      ) : (
        <table className="eo-table">
          <thead>
            <tr>
              {['slug', 'experimento'].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.slug}>
                <td>{r.slug}</td>
                <td>
                  {r.experiment_id ? (
                    <Link to={`/experiments/${r.experiment_id}`}>{r.experiment_id}</Link>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
