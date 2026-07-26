import { useEffect, useState } from 'react'
import { ApiError, evaluateRun, getEvaluation } from '../api'
import { Button, Card, ErrorBanner, Table } from './ui'
import { conditionLabel } from '../labels'
import type { EvalResult } from '../types'

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422)
      return 'La corrida no es evaluable (no fue sobre un conjunto de evaluación, o falta la referencia en disco).'
    if (e.status === 409) return 'La corrida sigue en curso: esperá a que termine.'
    if (e.status === 502) return 'Motor de detección inaccesible.'
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
    <Card title={<>Evaluación contra el conjunto <span className="eo-mono">{benchSplit}</span></>}>
      {!result && loading && <p>Cargando…</p>}
      {!result && !loading && (
        <Button variant="primary" onClick={evaluate} disabled={busy}>
          {busy ? 'Evaluando…' : 'Evaluar contra el conjunto de evaluación'}
        </Button>
      )}
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {result && (
        <>
          <p>
            <b>Precisión media (mAP@0.5): {fmt(result.mAP50)}</b> · {conditionLabel('CR-01')}
            {' '}(exhaustividad (recall): {fmt(result.cr01_detection_recall)})
            {' '}· IoU ≥ {result.iou_threshold}
          </p>
          <Table>
            <thead>
              <tr>
                {['clase', 'Precisión (AP@0.5)', 'referencia', 'detectadas'].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.per_class.map((c) => (
                <tr key={c.class_name}>
                  {/* nombre de clase: dato del vocabulario canónico, nunca se traduce */}
                  <td className="eo-mono">{c.class_name}</td>
                  <td className="eo-num">{fmt(c.AP50)}</td>
                  <td className="eo-num">{c.n_gt}</td>
                  <td className="eo-num">{c.n_det}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}
    </Card>
  )
}
