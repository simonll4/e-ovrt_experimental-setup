import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { getCompare, listRuns } from '../api'
import GroupedBars, { SERIES_COLORS } from '../components/charts/GroupedBars'
import { Banner, Card, EmptyState, ErrorBanner, PageHeader, Table } from '../components/ui'
import { hace } from '../runview'
import type { CompareResult, RunRow } from '../types'

/**
 * Índice del mejor valor de la fila, o −1 si no hay un ganador legítimo.
 *
 * Resaltar exige que haya realmente algo que comparar y que uno gane:
 *
 * - Con menos de dos valores medidos no hay comparación. Antes, una fila con un
 *   solo valor lo pintaba de verde: en el banco real eso marcaba `bare_head`
 *   **0,000 como "mejor valor"**, que frente a un jurado dice lo contrario de lo
 *   que pasó.
 * - Con empate no hay ganador. Antes ganaba el primero por orden de aparición,
 *   inventando una diferencia entre dos corridas idénticas.
 */
export function bestPerRow(values: Array<number | null>): number {
  // Se compara con la precisión que se MUESTRA: si el lector ve dos números
  // iguales, no se puede pintar uno de verde. Los datos reales del banco tienen
  // pares como 0,7851 contra 0,7849 — ambos se leen "0,785", y coronar a uno
  // afirma una diferencia que nadie puede verificar en pantalla.
  const shown = values.map((v) => (v == null ? null : Number(v.toFixed(METRIC_DIGITS))))
  const measured = shown.filter((v): v is number => v != null)
  if (measured.length < 2) return -1
  const max = Math.max(...measured)
  if (measured.filter((v) => v === max).length > 1) return -1
  return shown.findIndex((v) => v === max)
}

/** Decimales con los que se muestran —y por lo tanto se comparan— las métricas. */
const METRIC_DIGITS = 3

const metric = (v: number | null) => (v == null ? '—' : v.toFixed(METRIC_DIGITS).replace('.', ','))

function MetricRow({ name, values }: { name: ReactNode; values: Array<number | null> }) {
  const best = bestPerRow(values)
  return (
    <tr>
      <td>{name}</td>
      {values.map((v, i) => (
        <td key={i} className={i === best ? 'eo-num eo-best' : 'eo-num'}>
          {metric(v)}
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
    listRuns()
      .then(setRows)
      .catch((e) => setError(String(e)))
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

  const evaluables = useMemo(() => (rows ?? []).filter((r) => r.evaluated), [rows])
  const chosen = evaluables.filter((r) => selected.includes(r.run_id))

  // Comparar dos corridas evaluadas contra conjuntos distintos da una conclusión
  // inválida. El dato ya se carga; callarlo delante de un jurado sería peor.
  const splits = [...new Set(chosen.map((r) => r.bench_split).filter(Boolean))] as string[]
  const mixedSplits = splits.length > 1

  const series = result
    ? result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c]?.[i] ?? null))
    : []

  if (error && !rows) return <ErrorBanner>Error: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  return (
    <>
      <PageHeader
        title="Comparar corridas"
        meta="Solo se comparan corridas ya evaluadas contra un conjunto anotado"
      />

      {mixedSplits && (
        <Banner tone="warn">
          Estás comparando corridas evaluadas contra <b>conjuntos distintos</b> (
          {splits.map((s, i) => (
            <span key={s}>
              {i > 0 && ' y '}
              <span className="eo-mono">{s}</span>
            </span>
          ))}
          ). Los números no son comparables entre sí.
        </Banner>
      )}

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="eo-compare">
        <Card
          title="Corridas evaluadas"
          meta={`${selected.length} de ${evaluables.length} elegidas`}
          flush
        >
          {evaluables.length === 0 ? (
            <EmptyState hint="Se evalúan desde el detalle de cada corrida.">
              Todavía no hay corridas evaluadas
            </EmptyState>
          ) : (
            <ul className="eo-picklist">
              {evaluables.map((r) => (
                <li key={r.run_id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selected.includes(r.run_id)}
                      onChange={() => toggle(r.run_id)}
                      aria-label={r.name ?? r.run_id}
                    />
                    <span className="eo-picklist__name">{r.name ?? r.run_id}</span>
                    <span className="eo-picklist__meta eo-mono">
                      {r.model ?? '—'} · {r.bench_split ?? 'sin conjunto'} · {hace(r)}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          )}
          <p className="eo-cap eo-cap--inset">
            Las corridas sin evaluación no aparecen acá: se evalúan desde el detalle de cada una.
          </p>
        </Card>

        <div className="eo-compare__right">
          {selected.length < 2 ? (
            <EmptyState hint="La comparación necesita al menos dos para tener sentido.">
              Elegí al menos dos corridas
            </EmptyState>
          ) : (
            result && (
              <>
                <Card title="Métricas" meta="Mejor valor por fila en verde" flush>
                  <Table>
                    <thead>
                      <tr>
                        <th>Métrica</th>
                        {result.runs.map((r, i) => (
                          <th key={r.run_id} className="eo-num">
                            <span
                              className="eo-bars__key"
                              style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }}
                            />
                            {r.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.classes.map((cls) => (
                        <MetricRow
                          key={cls}
                          name={
                            <>
                              Precisión · <span className="eo-mono">{cls}</span>
                            </>
                          }
                          values={result.ap_by_class[cls] ?? []}
                        />
                      ))}
                      <MetricRow
                        name="Exhaustividad CR-01"
                        values={result.runs.map((r) => r.cr01_detection_recall)}
                      />
                      <MetricRow
                        name="Precisión media (mAP@0.5)"
                        values={result.runs.map((r) => r.mAP50)}
                      />
                    </tbody>
                  </Table>
                </Card>

                <Card title="Precisión por clase">
                  <GroupedBars
                    groups={result.classes}
                    series={series}
                    labels={result.runs.map((r) => r.label)}
                  />
                  <p className="eo-cap">
                    0 es ninguna detección correcta y 1 es todas. El nombre técnico de la
                    métrica es <span className="eo-mono">AP@0.5</span>.
                  </p>
                </Card>

                {result.skipped.length > 0 && (
                  <p className="eo-cap">
                    Quedaron afuera {result.skipped.length} corridas sin métricas comparables:{' '}
                    <span className="eo-mono">{result.skipped.join(', ')}</span>.
                  </p>
                )}
              </>
            )
          )}
        </div>
      </div>
    </>
  )
}
