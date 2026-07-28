import { useEffect, useState } from 'react'
import { getTrace } from './api'
import type { TraceFrame, TraceTotals } from './types'

const PAGE_SIZE = 500
/** Tope duro: 40 páginas = 20 000 cuadros. La corrida más larga del banco dura
 *  minutos; esto es un cinturón contra una traza patológica, no un límite de
 *  diseño. Cuando se alcanza, `truncated` lo dice y la interfaz lo muestra. */
const MAX_PAGES = 40

export interface FullTrace {
  frames: TraceFrame[]
  totals: TraceTotals | null
  controlRunId: string | null
  controlError: string | null
  loading: boolean
  error: string | null
  /** true si se llegó al tope de páginas y la traza quedó incompleta. */
  truncated: boolean
}

const EMPTY: FullTrace = {
  frames: [],
  totals: null,
  controlRunId: null,
  controlError: null,
  loading: false,
  error: null,
  truncated: false,
}

/**
 * Trae la traza completa paginando `/api/runs/{id}/trace`.
 *
 * La línea de tiempo necesita el índice de actividad de toda la corrida, y el
 * backend solo pagina. Por decisión del diseño no se toca el backend: se arma el
 * índice en el cliente, una sola vez al abrir el detalle, y lo comparten la línea
 * de tiempo y la lista de cuadros en vez de pedirlo dos veces.
 */
export function useFullTrace(runId: string, enabled: boolean): FullTrace {
  const [state, setState] = useState<FullTrace>(EMPTY)

  useEffect(() => {
    if (!enabled || !runId) {
      setState(EMPTY)
      return
    }
    let alive = true
    setState({ ...EMPTY, loading: true })

    const load = async () => {
      try {
        const first = await getTrace(runId, 1, PAGE_SIZE)
        if (!alive) return
        const frames = [...first.frames]
        const pages = Math.ceil(first.total / PAGE_SIZE)
        const limit = Math.min(pages, MAX_PAGES)
        for (let p = 2; p <= limit; p++) {
          const page = await getTrace(runId, p, PAGE_SIZE, first.control_run_id ?? undefined)
          if (!alive) return
          frames.push(...page.frames)
        }
        setState({
          frames,
          totals: first.totals,
          controlRunId: first.control_run_id,
          controlError: first.control_error,
          loading: false,
          error: null,
          truncated: pages > MAX_PAGES,
        })
      } catch (e) {
        if (alive) setState({ ...EMPTY, error: `No se pudo leer la traza: ${String(e)}` })
      }
    }

    void load()
    return () => {
      alive = false
    }
  }, [runId, enabled])

  return state
}
