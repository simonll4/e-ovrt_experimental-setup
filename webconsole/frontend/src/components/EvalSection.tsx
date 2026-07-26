import { useEffect, useState } from 'react'
import { ApiError, evaluateRun, getEvaluation } from '../api'
import { Card, ErrorBanner } from './ui'
import { conditionLabel } from '../labels'
import type { EvalResult } from '../types'

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422)
      return 'El run no es evaluable (no fue sobre un split del BENCH o falta el GT en disco).'
    if (e.status === 409) return 'El run sigue en curso: esperá a que termine.'
    if (e.status === 502) return 'Servicio media-plane inaccesible.'
  }
  return String(e)
}

const fmt = (v: number | null | undefined) => (v == null ? '—' : v)

export default function EvalSection({ runId, benchSplit, evaluated }: {
  runId: string
  benchSplit: string | null | undefined
  evaluated: boolean | undefined
}) {
  const [result, setResult] = useState<EvalResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(Boolean(benchSplit && evaluated))

  useEffect(() => {
    if (benchSplit && evaluated)
      getEvaluation(runId)
        .then(setResult)
        .catch((e) => setError(errorMessage(e)))
        .finally(() => setLoading(false))
  }, [runId, benchSplit, evaluated])

  if (!benchSplit) return null

  const evaluate = () => {
    setBusy(true)
    setError(null)
    evaluateRun(runId)
      .then(setResult)
      .catch((e) => setError(errorMessage(e)))
      .finally(() => setBusy(false))
  }

  return (
    <Card title={`Evaluación BENCH (${benchSplit})`}>
      {!result && loading && <p>Cargando…</p>}
      {!result && !loading && (
        <button onClick={evaluate} disabled={busy}>
          {busy ? 'Evaluando…' : 'Evaluar contra BENCH'}
        </button>
      )}
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {result && (
        <>
          <p>
            <b>mAP@0.5: {fmt(result.mAP50)}</b> · {conditionLabel('CR-01')} (exhaustividad: {fmt(result.cr01_detection_recall)})
            {' '}· IoU ≥ {result.iou_threshold}
          </p>
          <table className="eo-table">
            <thead>
              <tr>
                {['clase', 'AP@0.5', 'n_gt', 'n_det'].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.per_class.map((c) => (
                <tr key={c.class_name}>
                  <td>{c.class_name}</td>
                  <td className="eo-num">{fmt(c.AP50)}</td>
                  <td className="eo-num">{c.n_gt}</td>
                  <td className="eo-num">{c.n_det}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Card>
  )
}
