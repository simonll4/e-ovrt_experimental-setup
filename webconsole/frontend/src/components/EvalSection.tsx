import { useState } from 'react'
import { ApiError } from '../api'
import { useEvaluateRun, useEvaluation } from '../api/queries/runs'
import { Card, ErrorBanner } from './ui'

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
  const [errorAccion, setErrorAccion] = useState<string | null>(null)

  // Solo se relee si el run ya fue evaluado; si no, hay que apretar el botón.
  const consulta = useEvaluation(runId, Boolean(benchSplit && evaluated))
  const evaluacion = useEvaluateRun(runId)

  // La mutación siembra el resultado en la misma clave que lee la consulta, así
  // que evaluar deja los datos a la vista sin una segunda vuelta a la red.
  const result = consulta.data ?? null
  const loading = consulta.isPending && Boolean(benchSplit && evaluated)
  const busy = evaluacion.isPending
  const error = errorAccion ?? (consulta.error ? errorMessage(consulta.error) : null)

  if (!benchSplit) return null

  const evaluate = () => {
    setErrorAccion(null)
    evaluacion.mutateAsync().catch((e: unknown) => setErrorAccion(errorMessage(e)))
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
            <b>mAP@0.5: {fmt(result.mAP50)}</b> · CR-01 recall: {fmt(result.cr01_detection_recall)}
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
