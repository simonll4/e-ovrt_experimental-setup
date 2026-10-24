import { useRef, useState } from 'react'
import { ApiError } from '../api'
import { useEvaluateRun, useEvaluation } from '../api/queries/runs'
import { Button, Card, ErrorBanner, LoadingState, Table, TableScroll } from './ui'

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422)
      return 'La corrida no es evaluable: no fue sobre un split del BENCH, o falta en disco la anotación de referencia (GT).'
    if (e.status === 409) return 'La corrida sigue en curso: esperá a que termine para evaluarla.'
    if (e.status === 502) return 'El motor de detección no respondió (502).'
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
  const enviando = useRef(false)

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
    // Una evaluación por vez: el doble click no pide dos.
    if (enviando.current) return
    enviando.current = true
    setErrorAccion(null)
    evaluacion
      .mutateAsync()
      .catch((e: unknown) => setErrorAccion(errorMessage(e)))
      .finally(() => { enviando.current = false })
  }

  return (
    <Card title={`Evaluación BENCH (${benchSplit})`}>
      {!result && loading && <LoadingState lines={3}>Leyendo la evaluación guardada…</LoadingState>}
      {!result && !loading && (
        <>
          <p className="eo-note">
            Compara las detecciones de esta corrida con la anotación de referencia del conjunto
            {' '}<span className="eo-mono">{benchSplit}</span>.
          </p>
          <Button variant="primary" onClick={evaluate} disabled={busy} aria-busy={busy || undefined}>
            {busy ? 'Evaluando…' : 'Evaluar contra BENCH'}
          </Button>
        </>
      )}
      {error && (
        <ErrorBanner
          onRetry={consulta.error && !errorAccion ? () => void consulta.refetch() : undefined}
          retrying={consulta.isFetching}
        >
          {error}
        </ErrorBanner>
      )}
      {result && (
        <>
          <p>
            <b>mAP@0.5: {fmt(result.mAP50)}</b> · CR-01 recall: {fmt(result.cr01_detection_recall)}
            {' '}· IoU ≥ {result.iou_threshold}
          </p>
          <TableScroll label="Precisión por clase">
            <Table aria-label="Precisión por clase">
              <thead>
                <tr>
                  <th>Clase</th>
                  <th className="eo-num">Precisión <span className="eo-mono">AP@0.5</span></th>
                  <th className="eo-num">Anotadas <span className="eo-mono">n_gt</span></th>
                  <th className="eo-num">Detectadas <span className="eo-mono">n_det</span></th>
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
            </Table>
          </TableScroll>
        </>
      )}
    </Card>
  )
}
