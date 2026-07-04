import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { getCompare, listRuns } from '../api'
import GroupedBars from '../components/GroupedBars'
import type { CompareResult, RunRow } from '../types'

const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }

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
      <td style={CELL}>{name}</td>
      {values.map((v, i) => (
        <td key={i} style={{ ...CELL, fontWeight: i === best ? 700 : 400 }}>
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

  if (error && !rows) return <p style={{ color: '#b00' }}>Error: {error}</p>
  if (!rows) return <p>Cargando…</p>
  const evaluables = rows.filter((r) => r.evaluated)
  const series = result
    ? result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c]?.[i] ?? null))
    : []
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h2>Comparar runs (BENCH)</h2>
      {evaluables.length === 0 && (
        <p>No hay runs evaluados todavía. Evaluá un run BENCH desde su detalle.</p>
      )}
      <div style={{ display: 'grid', gap: 4 }}>
        {evaluables.map((r) => (
          <label key={r.run_id}>
            <input
              type="checkbox"
              checked={selected.includes(r.run_id)}
              onChange={() => toggle(r.run_id)}
            />{' '}
            {r.run_id} — {r.model ?? '—'} · {r.bench_split ?? '—'}
          </label>
        ))}
      </div>
      {evaluables.length > 0 && selected.length < 2 && <p>Seleccioná al menos 2 runs.</p>}
      {error && rows && <p style={{ color: '#b00' }}>{error}</p>}
      {result && (
        <>
          {result.skipped.length > 0 && (
            <p style={{ color: '#a60' }}>Sin evaluación (omitidos): {result.skipped.join(', ')}</p>
          )}
          <table style={{ borderCollapse: 'collapse', maxWidth: 760 }}>
            <thead>
              <tr>
                <th style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>métrica</th>
                {result.runs.map((r) => (
                  <th key={r.run_id} style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}>
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.classes.map((cls) => (
                <MetricRow key={cls} name={`AP@0.5 ${cls}`} values={result.ap_by_class[cls] ?? []} />
              ))}
              <MetricRow
                name="CR-01 recall"
                values={result.runs.map((r) => r.cr01_detection_recall)}
              />
              <MetricRow name="mAP@0.5" values={result.runs.map((r) => r.mAP50)} />
            </tbody>
          </table>
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
