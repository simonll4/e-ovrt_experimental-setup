import { useId, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { RUNS_PATH } from '../nav'
import { useQuery } from '@tanstack/react-query'
import { getCompare } from '../api'
import { qk } from '../api/keys'
import { useRuns } from '../api/queries/runs'
import GroupedBars from '../components/charts/GroupedBars'
import { SERIES_COLORS } from '../palette'
import {
  Banner, Card, EmptyState, ErrorBanner, LoadingState, PageHeader, StaleNotice, Table, TableScroll,
} from '../components/ui'
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

/** El servidor compara hasta ocho corridas (`MAX_COMPARE_RUNS` en
 *  `routers/compare.py`). La pantalla lo dice y no deja elegir una novena: el
 *  pedido volvería con un 422. */
export const MAX_CORRIDAS = 8

export default function ComparePage() {
  const ids = useId()
  const [selected, setSelected] = useState<string[]>([])

  const consultaCorridas = useRuns()
  const rows: RunRow[] | null = consultaCorridas.data ?? null

  // La comparación se pide sola al cambiar la selección, y la clave ordena los
  // ids: elegir A y B, o B y A, es la misma comparación y no debe pedirse dos
  // veces. Con menos de dos corridas no hay nada que comparar.
  const consultaComparacion = useQuery<CompareResult>({
    queryKey: qk.compare(selected),
    queryFn: () => getCompare(selected),
    enabled: selected.length >= 2,
    staleTime: Infinity,
  })
  const result = selected.length >= 2 ? consultaComparacion.data ?? null : null

  const toggle = (id: string) =>
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= MAX_CORRIDAS) return prev
      return [...prev, id]
    })

  const evaluables = useMemo(() => (rows ?? []).filter((r) => r.evaluated), [rows])
  const chosen = evaluables.filter((r) => selected.includes(r.run_id))
  const lleno = selected.length >= MAX_CORRIDAS

  // Comparar dos corridas evaluadas contra conjuntos distintos da una conclusión
  // inválida. El dato ya se carga; callarlo delante de un jurado sería peor.
  const splits = [...new Set(chosen.map((r) => r.bench_split).filter(Boolean))] as string[]
  const mixedSplits = splits.length > 1

  const series = result
    ? result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c]?.[i] ?? null))
    : []

  const header = (
    <PageHeader
      title="Comparar corridas"
      meta={`Solo se comparan corridas ya evaluadas contra un conjunto anotado · hasta ${MAX_CORRIDAS} a la vez`}
    />
  )

  // Sin listado: la cabecera queda y el contenido espera o explica el fallo.
  if (!rows) {
    return (
      <>
        {header}
        {consultaCorridas.error ? (
          <ErrorBanner
            detail={String(consultaCorridas.error)}
            onRetry={() => void consultaCorridas.refetch()}
            retrying={consultaCorridas.isFetching}
          >
            Error: no se pudo leer el listado de corridas.
          </ErrorBanner>
        ) : (
          <LoadingState lines={4}>Cargando las corridas evaluadas…</LoadingState>
        )}
      </>
    )
  }

  // Ninguna evaluada: una sola explicación, con el camino para resolverlo.
  if (evaluables.length === 0) {
    return (
      <>
        {header}
        <Card>
          <EmptyState
            hint="Se evalúan desde el detalle de cada corrida, en la pestaña Evaluación. Las corridas sin evaluación no aparecen acá."
            action={<Link className="eo-btn eo-btn--primary" to={RUNS_PATH}>Ir a Corridas</Link>}
          >
            Todavía no hay corridas evaluadas
          </EmptyState>
        </Card>
      </>
    )
  }

  let derecha
  if (selected.length === 0) {
    derecha = (
      <Card>
        <EmptyState hint="La comparación necesita al menos dos para tener sentido.">
          Elegí al menos dos corridas
        </EmptyState>
      </Card>
    )
  } else if (selected.length === 1) {
    derecha = (
      <Card>
        <EmptyState hint="Ya elegiste una. Marcá otra de la lista para ver sus métricas lado a lado.">
          Elegí otra corrida para comparar
        </EmptyState>
      </Card>
    )
  } else if (consultaComparacion.isPending && !result) {
    derecha = (
      <Card title="Métricas" flush>
        <LoadingState lines={4}>Comparando {selected.length} corridas…</LoadingState>
      </Card>
    )
  } else if (consultaComparacion.error && !result) {
    derecha = (
      <ErrorBanner
        detail={String(consultaComparacion.error)}
        onRetry={() => void consultaComparacion.refetch()}
        retrying={consultaComparacion.isFetching}
      >
        No se pudo comparar la selección.
      </ErrorBanner>
    )
  } else if (result) {
    derecha = (
      <>
        <Card title="Métricas" meta="Mejor valor por fila en verde" flush>
          <TableScroll label="Métricas de las corridas elegidas">
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
          </TableScroll>
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
  }

  return (
    <>
      {header}

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

      {consultaCorridas.error && (
        <StaleNotice
          what="el listado de corridas"
          onRetry={() => void consultaCorridas.refetch()}
          retrying={consultaCorridas.isFetching}
        />
      )}

      <div className="eo-compare">
        <Card
          title="Corridas evaluadas"
          meta={`${selected.length} de ${evaluables.length} elegidas · máximo ${MAX_CORRIDAS}`}
          flush
        >
          {lleno && (
            <p className="eo-picklist__limit" role="status" id={`${ids}limite`}>
              Ya elegiste {MAX_CORRIDAS}, el máximo que compara el servidor. Desmarcá una para
              elegir otra.
            </p>
          )}
          <ul className="eo-picklist">
            {evaluables.map((r, i) => {
              const marcada = selected.includes(r.run_id)
              const bloqueada = lleno && !marcada
              // Modelo y conjunto deciden si dos corridas se comparan: se
              // anuncian con la casilla, y la bloqueada dice por qué.
              const metaId = `${ids}meta${i}`
              return (
                <li key={r.run_id}>
                  <label className={bloqueada ? 'is-blocked' : undefined}>
                    <input
                      type="checkbox"
                      checked={marcada}
                      disabled={bloqueada}
                      onChange={() => toggle(r.run_id)}
                      aria-label={r.name ?? r.run_id}
                      aria-describedby={bloqueada ? `${metaId} ${ids}limite` : metaId}
                    />
                    <span className="eo-picklist__name">{r.name ?? r.run_id}</span>
                    <span className="eo-picklist__meta eo-mono" id={metaId}>
                      {r.model ?? '—'} · {r.bench_split ?? 'sin conjunto'} · {hace(r)}
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          <p className="eo-cap eo-cap--inset">
            Las corridas sin evaluación no aparecen acá: se evalúan desde el detalle de cada una.
          </p>
        </Card>

        <div className="eo-compare__right">{derecha}</div>
      </div>
    </>
  )
}
