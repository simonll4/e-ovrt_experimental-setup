import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteRun, evaluateRun, getArtifacts, getEvaluation, getRun, getRunComparison, getTrace,
  getTraceIndex, launchRun, listRuns, listRunsPaged, stopRun,
} from '..'
import { qk } from '../keys'
import { POLL } from '../queryClient'
import { isRunning } from '../../runview'
import type {
  Composition, EvalResult, RunComparison, RunDetail, RunRow, TraceFrame,
  TraceIndex, TraceTotals,
} from '../../types'

/** Historial completo de corridas.
 *
 *  Agota la paginación del servidor, así que cuesta una petición por cada 200
 *  corridas: usalo solo cuando de verdad hagan falta todas (hoy, Comparar, que
 *  necesita el conjunto entero de evaluadas). Para mostrar un listado está
 *  `useRunsPaged()`, que pide una página por vez.
 *
 *  Se refresca solo mientras haya alguna corrida viva. Cuando todas terminaron
 *  el listado es historial y no hay nada que volver a pedir — que es lo que hacía
 *  el `setTimeout` reagendado a mano, ahora expresado como una condición sobre
 *  los datos en caché.
 */
export function useRuns() {
  return useQuery<RunRow[]>({
    queryKey: qk.runs.list(),
    queryFn: listRuns,
    refetchInterval: (query) =>
      query.state.data?.some((r) => r.status === 'running') ? POLL.enCurso : false,
  })
}

/** Filtros del listado, tal como viajan al servidor. */
export interface RunsFiltros {
  /** `running | succeeded | failed | stopped`, o nada para todas. */
  estado?: string
  q?: string
  orden: string
  direccion: 'asc' | 'desc'
  pagina: number
  pageSize: number
}

/** Una página del listado, filtrada y ordenada por el servidor.
 *
 *  Antes la pantalla bajaba todas las corridas y filtraba, ordenaba y paginaba
 *  en el cliente. Eso funciona con nueve corridas y no con novecientas, y el
 *  costo no está en filtrar sino en hidratar: el BFF hace una lectura al motor
 *  de detección por corrida devuelta. Pidiendo una página, hidrata una página.
 *
 *  `placeholderData` conserva la página anterior mientras llega la nueva. Sin
 *  eso, cada cambio de orden o de página vacía la tabla y el encabezado salta.
 */
export function useRunsPaged(filtros: RunsFiltros, hayCorridaViva: boolean) {
  return useQuery({
    queryKey: qk.runs.list({ ...filtros }),
    queryFn: () => listRunsPaged(filtros),
    placeholderData: (anterior) => anterior,
    // Se sigue pidiendo mientras haya una corrida viva en cualquier lado (sus
    // métricas cambian) o mientras quede una en pantalla: esto último es lo que
    // garantiza ver el estado final, porque la página tiene que refrescarse una
    // vez más DESPUÉS de que la corrida dejó de estar viva.
    refetchInterval: (query) =>
      hayCorridaViva || query.state.data?.items.some(isRunning) ? POLL.enCurso : false,
  })
}

/** Corridas en curso: cuántas hay y cuáles son.
 *
 *  Es una consulta propia y no un filtro sobre el listado porque el listado ya
 *  no trae todas las corridas. Preguntarle "¿cuántas están en curso?" a una
 *  página de 25 devuelve las de esa página; el total exacto lo sabe el servidor
 *  y lo manda en `X-Total-Count`. De acá salen la píldora de la barra lateral,
 *  su contador y el banner del listado, con una sola petición liviana.
 */
export function useRunsEnCurso() {
  return useQuery({
    queryKey: qk.runs.list({ estado: 'running' }),
    queryFn: () => listRunsPaged({ estado: 'running', pageSize: 5 }),
    // Mientras haya alguna, se sigue mirando; con cero, el historial está quieto
    // y el próximo lanzamiento invalida la clave por su cuenta.
    refetchInterval: (query) => (query.state.data?.total ? POLL.enCurso : false),
  })
}

/** Cuántas corridas hay en total, sin ningún filtro.
 *
 *  Es una petición aparte, de una sola fila, porque una página filtrada solo
 *  conoce el total *de su filtro*: para decir "3 de 47" hacen falta los dos
 *  números y el 47 no está en ninguna respuesta filtrada.
 */
export function useRunsTotal() {
  return useQuery({
    queryKey: [...qk.runs.list(), 'total'],
    queryFn: async () => (await listRunsPaged({ pageSize: 1 })).total,
  })
}

export function useRun(id: string) {
  return useQuery<RunDetail>({
    queryKey: qk.runs.detail(id),
    queryFn: () => getRun(id),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === 'running' ? POLL.enCurso : false),
  })
}

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

const PAGE_SIZE = 500
/** Tope duro: 40 páginas = 20 000 cuadros. Es un cinturón contra una traza
 *  patológica, no un límite de diseño; cuando se alcanza, `truncated` lo dice. */
const MAX_PAGES = 40

/**
 * Traza completa de una corrida, paginando `/api/runs/{id}/trace`.
 *
 * La línea de tiempo necesita el índice de actividad de la corrida entera y el
 * backend solo pagina, así que el índice se arma en el cliente. Sigue siendo una
 * sola lectura compartida por la línea de tiempo y la lista de cuadros, pero
 * ahora vive en la caché: volver al detalle de una corrida terminada ya no
 * vuelve a bajar las 40 páginas.
 *
 * Cuando exista `GET /api/runs/{id}/trace/index` esto pasa a ser una sola
 * petición y el bucle desaparece.
 */
export function useFullTrace(runId: string, enabled: boolean): FullTrace {
  const { data, isPending, error, isFetching } = useQuery({
    queryKey: qk.runs.trace(runId),
    queryFn: async ({ signal }) => {
      const primera = await getTrace(runId, 1, PAGE_SIZE)
      const frames = [...primera.frames]
      const paginas = Math.ceil(primera.total / PAGE_SIZE)
      const tope = Math.min(paginas, MAX_PAGES)
      for (let p = 2; p <= tope; p++) {
        // Query cancela el `signal` al desmontar; sin este corte, salir del
        // detalle de una corrida larga seguía bajando páginas de fondo.
        if (signal.aborted) break
        const pagina = await getTrace(runId, p, PAGE_SIZE, primera.control_run_id ?? undefined)
        frames.push(...pagina.frames)
      }
      return {
        frames,
        totals: primera.totals,
        controlRunId: primera.control_run_id,
        controlError: primera.control_error,
        truncated: paginas > MAX_PAGES,
      }
    },
    enabled: enabled && Boolean(runId),
    // Una corrida terminada no cambia su traza: no tiene sentido revalidarla.
    staleTime: Infinity,
  })

  return {
    frames: data?.frames ?? [],
    totals: data?.totals ?? null,
    controlRunId: data?.controlRunId ?? null,
    controlError: data?.controlError ?? null,
    loading: enabled && (isPending || isFetching) && !data,
    error: error ? `No se pudo leer la traza: ${String(error)}` : null,
    truncated: data?.truncated ?? false,
  }
}

/** Actividad de la corrida completa para la línea de tiempo.
 *
 *  Una sola petición contra `/trace/index` en vez de paginar la traza entera:
 *  para 200 cuadros son 8 KB en lugar de 247. Los datos van en arrays paralelos
 *  porque repetir los nombres de clave por cuadro era la mayor parte del peso.
 *
 *  `viva` cambia el régimen: una corrida en curso agrega cuadros, así que el
 *  índice se repregunta; una terminada no cambia y se cachea para siempre. Antes
 *  la línea de tiempo directamente no se pedía mientras la corrida corría, que
 *  es justo cuando más se la mira.
 */
export function useTraceIndex(runId: string, enabled: boolean, viva = false) {
  return useQuery<TraceIndex>({
    // La última lectura debe ser posterior al fin: la caché viva puede contener
    // cero cuadros si el proceso terminó antes del siguiente tick de polling.
    queryKey: [...qk.runs.traceIndex(runId), viva ? 'live' : 'final'],
    queryFn: () => getTraceIndex(runId),
    enabled: enabled && Boolean(runId),
    staleTime: viva ? 0 : Infinity,
    refetchInterval: viva ? POLL.enCurso : false,
  })
}

export type TraceFilter = 'actividad' | 'alertas' | null

/** Una página de la traza, con el filtro aplicado del lado del servidor.
 *
 *  El filtro va en la petición y no en el cliente: filtrar acá obligaría a tener
 *  la traza entera en memoria, y entonces "solo alertas" mostraría las de la
 *  página cargada en vez de las de la corrida.
 *
 *  `placeholderData` conserva la página anterior mientras llega la nueva: sin
 *  eso, cambiar de página vacía la lista y el panel de detalle parpadea.
 */
export function useTracePage(
  runId: string,
  pagina: number,
  pageSize: number,
  solo: TraceFilter,
  enabled: boolean,
  viva = false,
) {
  return useQuery({
    queryKey: [...qk.runs.trace(runId, pagina), pageSize, solo, viva ? 'live' : 'final'],
    queryFn: () => getTrace(runId, pagina, pageSize, undefined, solo ?? undefined),
    enabled: enabled && Boolean(runId),
    staleTime: viva ? 0 : Infinity,
    refetchInterval: viva ? POLL.enCurso : false,
    placeholderData: (anterior) => anterior,
  })
}

/** Archivos que dejó la corrida, con tamaño y descripción. */
export function useArtifacts(runId: string, enabled: boolean) {
  return useQuery({
    queryKey: qk.runs.artifacts(runId),
    queryFn: () => getArtifacts(runId),
    enabled: enabled && Boolean(runId),
    staleTime: Infinity,
  })
}

/** Variación de los indicadores contra la corrida anterior comparable.
 *
 *  Devuelve `previous_run_id: null` cuando no hay con qué comparar, que la
 *  interfaz muestra como indicadores sin variación — distinto de variación cero.
 */
export function useRunComparison(runId: string, enabled: boolean) {
  return useQuery<RunComparison>({
    queryKey: [...qk.runs.detail(runId), 'comparison'],
    queryFn: () => getRunComparison(runId),
    enabled: enabled && Boolean(runId),
    staleTime: Infinity,
  })
}

export function useEvaluation(runId: string, enabled: boolean) {
  return useQuery<EvalResult>({
    queryKey: qk.runs.evaluation(runId),
    queryFn: () => getEvaluation(runId),
    enabled: enabled && Boolean(runId),
    staleTime: Infinity,
  })
}

export function useEvaluateRun(runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => evaluateRun(runId),
    onSuccess: (resultado) => {
      // La evaluación devuelve el resultado: se siembra en vez de invalidar, así
      // la pestaña lo muestra sin una segunda vuelta a la red.
      qc.setQueryData(qk.runs.evaluation(runId), resultado)
      void qc.invalidateQueries({ queryKey: qk.runs.artifacts(runId) })
      void qc.invalidateQueries({ queryKey: qk.runs.detail(runId) })
      void qc.invalidateQueries({ queryKey: qk.runs.list() })
    },
  })
}

export function useLaunchRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (composicion: Composition) => launchRun(composicion),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: qk.runs.all })
      void qc.invalidateQueries({ queryKey: qk.preflight })
    },
  })
}

export function useStopRun(runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => stopRun(runId),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.runs.detail(runId) })
      void qc.invalidateQueries({ queryKey: qk.runs.list() })
    },
  })
}

export function useDeleteRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) => deleteRun(runId),
    onSettled: (_datos, _error, runId) => {
      // Se quita el detalle de la caché: si quedara, volver atrás mostraría una
      // corrida que ya no existe hasta que el refetch la desmienta.
      qc.removeQueries({ queryKey: qk.runs.detail(runId) })
      qc.removeQueries({ queryKey: qk.runs.trace(runId) })
      void qc.invalidateQueries({ queryKey: qk.runs.list() })
    },
  })
}
