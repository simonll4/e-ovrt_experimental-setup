import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowData,
  type SortingState,
} from '@tanstack/react-table'
import { getTrace } from '../api'
import { qk } from '../api/keys'
import { useDeleteRun, useRunsEnCurso, useRunsPaged, useRunsTotal } from '../api/queries/runs'
import type { RunRow } from '../types'
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  InlineDeleteConfirm,
  PageHeader,
  RowName,
  SearchInput,
  SegmentedControl,
  SortableHeader,
  Table,
} from '../components/ui'
import { hace, isRunning, runStatusLabel, runStatusTone, sourceLabel } from '../runview'

declare module '@tanstack/react-table' {
  // La ampliación tiene que repetir los dos parámetros de la interfaz original
  // aunque acá no se usen; es la forma que documenta TanStack.
  interface ColumnMeta<TData extends RowData, TValue> {
    /** Alinea a la derecha, con cifras tabulares. */
    numeric?: boolean
    /** Monoespaciada: identificadores y nombres de modelo, que son datos. */
    mono?: boolean
  }
}

const PAGE_SIZE = 25

const SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'stopped', label: 'Detenidas' },
  { value: 'failed', label: 'Fallidas' },
] as const
type Segment = (typeof SEGMENTS)[number]['value']

/** Orden por defecto, el mismo que aplica el servidor si no se le pide otro. */
const ORDEN_POR_DEFECTO = { orden: 'created_at', direccion: 'desc' } as const

const dec = (v: number | null | undefined, digits = 1): string =>
  v == null ? '—' : v.toFixed(digits).replace('.', ',')

/**
 * Demora el valor que viaja al servidor sin demorar el campo de texto.
 *
 * Con el filtrado del lado del servidor, cada tecla sería una petición. El input
 * sigue respondiendo al instante; lo único que espera es la consulta.
 */
function useDemorado<T>(valor: T, ms = 250): T {
  const [demorado, setDemorado] = useState(valor)
  useEffect(() => {
    const id = setTimeout(() => setDemorado(valor), ms)
    return () => clearTimeout(id)
  }, [valor, ms])
  return demorado
}

/**
 * Definición de columnas.
 *
 * Los `id` son los nombres de campo que entiende el servidor (`_ORDENABLES` en
 * `routers/runs.py`): el estado de orden de TanStack viaja tal cual, sin una
 * tabla de traducción que se desincronice al agregar una columna.
 *
 * Las ordenables se declaran con `accessorKey`/`accessorFn` aunque el contenido
 * lo dibuje `cell`: TanStack solo deja ordenar una columna que tenga accesor
 * (`getCanSort()` lo exige), así que una columna puramente de presentación queda
 * muda por más que pida `enableSorting`. Las que el servidor no sabe ordenar sí
 * son de presentación, y así el encabezado no ofrece algo que no haría nada.
 */
function columnas(
  confirmId: string | null,
  setConfirmId: (id: string | null) => void,
  deletingId: string | null,
  borrar: (row: RunRow) => void,
): Array<ColumnDef<RunRow>> {
  return [
    {
      id: 'name',
      accessorFn: (r) => r.name ?? r.run_id,
      header: 'Corrida',
      cell: ({ row: { original: r } }) => (
        // El enlace es el camino de teclado y el que permite abrir en otra
        // pestaña; el click en cualquier parte de la fila lleva al mismo lado.
        // Sin nombre, el subtítulo es la antigüedad: el prototipo sacó la
        // columna de fecha y la repartió entre acá y la celda de acción.
        <RowName
          title={<Link to={`/runs/${r.run_id}`}>{r.name ?? r.run_id}</Link>}
          subtitle={r.name ? r.run_id : hace(r)}
        />
      ),
    },
    {
      id: 'status',
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row: { original: r } }) => (
        <Badge tone={runStatusTone(r)} pulse={isRunning(r)}>
          {runStatusLabel(r)}
        </Badge>
      ),
    },
    {
      id: 'model',
      accessorKey: 'model',
      header: 'Modelo',
      meta: { mono: true },
      cell: ({ row: { original: r } }) => r.model ?? '—',
    },
    {
      id: 'source_type',
      header: 'Fuente',
      enableSorting: false,
      cell: ({ row: { original: r } }) => sourceLabel(r.source_type),
    },
    {
      id: 'prompt_set_id',
      header: 'Conjunto de prompts',
      enableSorting: false,
      meta: { mono: true },
      cell: ({ row: { original: r } }) => r.prompt_set_id ?? '—',
    },
    {
      id: 'fps_effective',
      accessorKey: 'fps_effective',
      header: 'Cuadros/s',
      meta: { numeric: true },
      cell: ({ row: { original: r } }) => dec(r.fps_effective, 2),
    },
    {
      id: 'total_detections',
      accessorKey: 'total_detections',
      header: 'Detecciones',
      meta: { numeric: true },
      cell: ({ row: { original: r } }) => r.total_detections ?? '—',
    },
    {
      id: 'duration_seconds',
      accessorKey: 'duration_seconds',
      header: 'Duración',
      meta: { numeric: true },
      cell: ({ row: { original: r } }) =>
        r.duration_seconds != null ? `${dec(r.duration_seconds)} s` : '—',
    },
    {
      id: 'acciones',
      header: '',
      enableSorting: false,
      cell: ({ row: { original: r } }) =>
        // Una corrida en curso no se borra: la celda dice desde cuándo está
        // corriendo, que es el dato que se mira mientras corre.
        isRunning(r) ? (
          <Badge tone="neutral">{hace(r)}</Badge>
        ) : confirmId === r.run_id ? (
          <InlineDeleteConfirm onConfirm={() => borrar(r)} onCancel={() => setConfirmId(null)} />
        ) : (
          <Button
            variant="ghost"
            aria-label={`Borrar ${r.run_id}`}
            disabled={deletingId === r.run_id}
            onClick={() => setConfirmId(r.run_id)}
          >
            Borrar
          </Button>
        ),
    },
  ]
}

export default function RunsPage() {
  const nav = useNavigate()
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [page, setPage] = useState(1)
  const [sorting, setSorting] = useState<SortingState>([])

  const busqueda = useDemorado(query)

  // TanStack cicla descendente → ascendente → sin orden, y "sin orden" es el
  // orden por fecha del servidor. Es la única forma de volver a él, porque la
  // columna de fecha no existe: su encabezado no está para poder clickearlo.
  const orden = sorting[0]
    ? { orden: sorting[0].id, direccion: sorting[0].desc ? ('desc' as const) : ('asc' as const) }
    : ORDEN_POR_DEFECTO

  const enCurso = useRunsEnCurso()
  const liveRun = enCurso.data?.items.find((r) => isRunning(r)) ?? null
  const liveRunId = liveRun?.run_id ?? null

  const totalGeneral = useRunsTotal()
  const total = totalGeneral.data ?? null

  const listado = useRunsPaged(
    {
      estado: segment === 'all' ? undefined : segment,
      q: busqueda.trim() || undefined,
      ...orden,
      pagina: page,
      pageSize: PAGE_SIZE,
    },
    Boolean(liveRun),
  )

  const rows = listado.data?.items ?? null
  const totalFiltrado = listado.data?.total ?? 0
  const error = listado.error ? String(listado.error) : null

  const borrado = useDeleteRun()
  const deletingId = borrado.isPending ? borrado.variables : null

  const resetView = useCallback(() => {
    setPage(1)
    setConfirmId(null)
  }, [])

  const handleDelete = useCallback(
    async (row: RunRow) => {
      setConfirmId(null)
      setDeleteError(null)
      try {
        // El BFF contesta 207 cuando borró en un plano y falló en el otro: no es
        // éxito ni error, y hay que decir en cuál quedó a medias.
        const result = await borrado.mutateAsync(row.run_id)
        if (result?.errors) {
          setDeleteError(
            `Borrado parcial de ${row.run_id}: ${Object.entries(result.errors)
              .map(([plane, detail]) => `${plane}: ${detail}`)
              .join('; ')}`,
          )
        }
      } catch (e) {
        setDeleteError(`No se pudo borrar ${row.run_id}: ${String(e)}`)
      }
    },
    [borrado],
  )

  const cols = useMemo(
    () => columnas(confirmId, setConfirmId, deletingId, (r) => void handleDelete(r)),
    [confirmId, deletingId, handleDelete],
  )

  const table = useReactTable({
    data: rows ?? [],
    columns: cols,
    getCoreRowModel: getCoreRowModel(),
    // Todo el trabajo lo hace el servidor: la tabla dibuja lo que llega y avisa
    // los cambios de orden. Sin esto, TanStack reordenaría la página actual
    // sobre sí misma y el resultado sería un orden por página.
    manualSorting: true,
    manualFiltering: true,
    manualPagination: true,
    rowCount: totalFiltrado,
    state: { sorting, pagination: { pageIndex: page - 1, pageSize: PAGE_SIZE } },
    onSortingChange: (updater) => {
      setSorting((prev) => (typeof updater === 'function' ? updater(prev) : updater))
      resetView()
    },
    getRowId: (r) => r.run_id,
  })

  const paginas = Math.max(1, table.getPageCount())

  // Borrar la última corrida de la última página dejaba la tabla vacía sin decir
  // por qué: el servidor contesta una página que ya no existe. Se retrocede.
  useEffect(() => {
    if (page > paginas) setPage(paginas)
  }, [page, paginas])

  // Alertas de la corrida en vivo: un pedido liviano (page_size=1) solo por los
  // totales. Se omite si el motor de reglas no evaluó la corrida.
  const { data: liveAlerts = null } = useQuery({
    queryKey: [...qk.runs.trace(liveRunId ?? ''), 'alertas'],
    queryFn: async () => {
      const t = await getTrace(liveRunId as string, 1, 1)
      return t.control_run_id ? t.totals.alerts : null
    },
    enabled: Boolean(liveRunId),
  })

  if (error && !rows) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const hayFiltro = segment !== 'all' || busqueda.trim() !== ''

  return (
    <>
      <PageHeader
        title="Corridas"
        meta={
          <>
            {total != null && <span>{total} en total</span>}
            {enCurso.data != null && enCurso.data.total > 0 && (
              <>
                {total != null && <span className="eo-sep">·</span>}
                <span style={{ color: 'var(--live)' }}>{enCurso.data.total} en curso</span>
              </>
            )}
          </>
        }
        actions={<Button variant="primary" onClick={() => nav('/compose')}>Nueva corrida</Button>}
      />

      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {liveRun && (
        <Banner
          tone="live"
          action={<Button onClick={() => nav(`/runs/${liveRun.run_id}`)}>Ver en vivo</Button>}
        >
          <b>{liveRun.name ?? liveRun.run_id}</b> está procesando ahora
          {liveRun.total_detections != null && ` — ${liveRun.total_detections} detecciones`}
          {liveAlerts != null && `, ${liveAlerts} alertas confirmadas`}
        </Banner>
      )}

      <div className="eo-toolbar">
        <SearchInput
          value={query}
          onChange={(v) => {
            setQuery(v)
            resetView()
          }}
          placeholder="Buscar por nombre o identificador"
          ariaLabel="Buscar corridas por nombre o identificador"
        />
        <SegmentedControl
          value={segment}
          options={SEGMENTS as unknown as Array<{ value: Segment; label: string }>}
          onChange={(v) => {
            setSegment(v)
            resetView()
          }}
        />
        <span className="eo-toolbar__count eo-mono">
          {totalFiltrado} de {total ?? totalFiltrado}
        </span>
      </div>

      <Card flush>
        <Table>
          <thead>
            {table.getHeaderGroups().map((grupo) => (
              <tr key={grupo.id}>
                {grupo.headers.map((header) => {
                  const { numeric } = header.column.columnDef.meta ?? {}
                  // Los encabezados son texto plano, así que se leen del propio
                  // `columnDef`: `SortableHeader` necesita la etiqueta como
                  // cadena para poder acomodarle la flecha de orden al lado.
                  const label = String(header.column.columnDef.header ?? '')
                  return header.column.getCanSort() ? (
                    <SortableHeader
                      key={header.id}
                      label={label}
                      sortKey={header.column.id}
                      sortState={
                        sorting[0]
                          ? { key: sorting[0].id, dir: sorting[0].desc ? 'desc' : 'asc' }
                          : null
                      }
                      onSort={() => header.column.toggleSorting()}
                      numeric={numeric}
                    />
                  ) : (
                    <th
                      key={header.id}
                      className={numeric ? 'eo-th--numeric' : undefined}
                      aria-label={label || (header.column.id === 'acciones' ? 'Acciones' : undefined)}
                    >
                      {label}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((fila) => {
              const r = fila.original
              return (
                <tr
                  key={fila.id}
                  className={isRunning(r) ? 'eo-row--click eo-row--live' : 'eo-row--click'}
                  onClick={() => nav(`/runs/${r.run_id}`)}
                >
                  {fila.getVisibleCells().map((celda) => {
                    const { numeric, mono } = celda.column.columnDef.meta ?? {}
                    const esAccion = celda.column.id === 'acciones'
                    const clase = esAccion
                      ? 'eo-cell--actions'
                      : [numeric && 'eo-num', mono && 'eo-mono'].filter(Boolean).join(' ')
                    return (
                      <td
                        key={celda.id}
                        className={clase || undefined}
                        // Borrar no es navegar: sin esto, confirmar el borrado
                        // abriría el detalle de la corrida que se está borrando.
                        onClick={esAccion ? (e) => e.stopPropagation() : undefined}
                      >
                        {flexRender(celda.column.columnDef.cell, celda.getContext())}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </Table>
        {totalFiltrado === 0 &&
          (hayFiltro ? (
            <EmptyState hint="Probá con otro texto o volvé a «Todas».">
              Ninguna corrida coincide con el filtro
            </EmptyState>
          ) : (
            <EmptyState hint="Empezá por elegir una fuente y un conjunto de prompts.">
              Todavía no lanzaste ninguna corrida
            </EmptyState>
          ))}
      </Card>

      {paginas > 1 && (
        <nav className="eo-pager" aria-label="Paginación de corridas">
          <Button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Anterior
          </Button>
          <span className="eo-mono">
            Página {page} de {paginas}
          </span>
          <Button disabled={page === paginas} onClick={() => setPage(page + 1)}>
            Siguiente
          </Button>
        </nav>
      )}
    </>
  )
}
