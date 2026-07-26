import { useEffect, useState } from 'react'
import { getCompare, listRuns } from '../api'
import GroupedBars from '../components/GroupedBars'
import { Badge, EmptyState, ErrorBanner, MonoCell, Table } from '../components/ui'
import { conditionLabel } from '../labels'
import type { CompareResult, RunRow } from '../types'

// Índice del mejor valor no-nulo de la fila (−1 si no hay ninguno).
export function bestPerRow(values: Array<number | null>): number {
  let best = -1
  let bestValue = -Infinity
  values.forEach((v, i) => {
    if (v != null && v > bestValue) {
      bestValue = v
      best = i
    }
  })
  return best
}

function MetricRow({ name, values }: { name: string; values: Array<number | null> }) {
  const best = bestPerRow(values)
  return (
    <tr>
      <td>{name}</td>
      {values.map((v, i) => (
        <td key={i} className={i === best ? 'eo-num eo-best' : 'eo-num'}>
          {v ?? '—'}
        </td>
      ))}
    </tr>
  )
}

export default function ComparePage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [result, setResult] = useState<CompareResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listRuns().then(setRows).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (selected.length < 2) {
      setResult(null)
      return
    }
    getCompare(selected)
      .then((r) => {
        setResult(r)
        setError(null)
      })
      .catch((e) => setError(String(e)))
  }, [selected])

  const toggle = (id: string) =>
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  if (error && !rows) return <ErrorBanner>Error: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  const evaluables = rows.filter((r) => r.evaluated)
  const series = result
    ? result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c]?.[i] ?? null))
    : []
  return (
    <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
      <h2>Comparar runs (BENCH)</h2>
      {evaluables.length === 0 && (
        <EmptyState>No hay runs evaluados todavía. Evaluá un run BENCH desde su detalle.</EmptyState>
      )}
      <div style={{ display: 'grid', gap: 'var(--space-1)' }}>
        {evaluables.map((r) => (
          <label key={r.run_id}>
            <input
              type="checkbox"
              checked={selected.includes(r.run_id)}
              onChange={() => toggle(r.run_id)}
            />{' '}
            <span className="eo-mono">{r.run_id}</span> — {r.model ?? '—'} · {r.bench_split ?? '—'}
          </label>
        ))}
      </div>
      {evaluables.length > 0 && selected.length < 2 && <p>Seleccioná al menos 2 runs.</p>}
      {error && rows && <ErrorBanner>{error}</ErrorBanner>}
      {result && (
        <>
          {result.skipped.length > 0 && (
            <p>
              Sin evaluación (omitidos):{' '}
              {result.skipped.map((id) => (
                <Badge key={id} tone="warn">
                  <span className="eo-mono">{id}</span>
                </Badge>
              ))}
            </p>
          )}
          {(() => {
            const splits = new Set(
              result.runs.map((r) => r.bench_split).filter((b): b is string => b !== null),
            )
            return splits.size > 1 ? (
              <p className="eo-note eo-note--warn">
                ⚠ Estás comparando corridas sobre conjuntos de evaluación distintos (
                {result.runs.map((r) => r.bench_split ?? 'sin dato').join(' vs. ')}).
              </p>
            ) : null
          })()}
          <Table>
            <thead>
              <tr>
                <th>métrica</th>
                {result.runs.map((r) => (
                  <th key={r.run_id}>{r.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.classes.map((cls) => (
                <MetricRow key={cls} name={`AP@0.5 ${cls}`} values={result.ap_by_class[cls] ?? []} />
              ))}
              <MetricRow
                name={`${conditionLabel('CR-01')} (exhaustividad)`}
                values={result.runs.map((r) => r.cr01_detection_recall)}
              />
              <MetricRow name="mAP@0.5" values={result.runs.map((r) => r.mAP50)} />
            </tbody>
          </Table>
          <GroupedBars
            groups={result.classes}
            series={series}
            labels={result.runs.map((r) => r.label)}
          />
        </>
      )}
    </div>
  )
}
