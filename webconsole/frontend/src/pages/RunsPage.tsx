import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
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
import { useDeleteRun, useRunGroups, useRunsEnCurso, useRunsPaged, useRunsTotal } from '../api/queries/runs'
import type { Clase, RunGroup, RunRow } from '../types'
import ClaseChips, { ETIQUETA_CLASE } from '../components/ClaseChips'
import Termino from '../components/Glosario'
import { TERMINO_DE_CLASE } from '../terminos'
import { AvisoRegistro, EvidenceBadge } from '../components/EvidenceViewControl'
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  IconChevron,
  IconGroup,
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
/** Corridas de un grupo que se muestran antes de pedir "Ver todas". */
const GRUPO_PAGE_SIZE = 8
/** La clave del ÚNICO grupo de corridas sin resultado citado (Task 7):
 *  `result_id` viaja en `null`, pero el estado de expansión necesita una
 *  cadena para poder compararse. */
const CLAVE_SIN_CLASIFICAR = '__sin_clasificar__'

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

const claveDe = (g: RunGroup): string => g.result_id ?? CLAVE_SIN_CLASIFICAR

/** El nombre visible de un grupo.
 *
 *  R-30 (7ª aparición del defecto reincidente): antes era
 *  `g.titulo ?? g.etiqueta ?? 'Fuera del registro de evidencia'`, o sea la
 *  AUSENCIA de dos campos editoriales producía la afirmación negativa más
 *  fuerte de la pantalla — y lo hacía para un grupo que sí está en el registro,
 *  con su `result_id` impreso dos líneas más abajo contradiciéndola. El
 *  disparador real: un despliegue desincronizado o un payload cacheado sin
 *  `etiqueta`.
 *
 *  «Fuera del registro» cuelga ahora de `result_id == null`, que es la
 *  condición que de verdad lo significa — la MISMA que ya usa el encabezado
 *  para descontar ese grupo del conteo de resultados. Con `result_id` pero sin
 *  título ni etiqueta se muestra el `result_id`: es lo que se sabe, no una
 *  conclusión sobre lo que falta. */
const nombreDeGrupo = (g: RunGroup): string =>
  g.result_id == null
    ? 'Fuera del registro de evidencia'
    : g.titulo ?? g.etiqueta ?? g.result_id

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
 * Definición de columnas del listado individual (sin agrupar).
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
          subtitle={<>{r.name ? r.run_id : hace(r)} <EvidenceBadge evidence={r.evidence} /></>}
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

/** La cifra de un grupo — leída o citada, nunca fabricada. Sin paso del
 *  argumento (instrumento, ensayo, plataforma, sin_clasificar, o un resultado
 *  que sólo sostiene el respaldo) se DECLARA sin cifra: no se dibuja un cero.
 *  Mismo patrón que `Entrada.tsx`/`Paso.tsx` — `eo-cifra--cit` marca lo citado.
 *
 *  **De quién es este número.** No es del resultado de la fila: es la cifra del
 *  PASO que lo cita, y todos los resultados de un mismo paso muestran la misma
 *  (`paso_de` en `evidence_archive.py`). Sin decirlo, la fila de NA1 imprimía
 *  «precision de E-DIR (veto < 0,5) 0,146» —un número de D1— y la de
 *  `clase_nueva` el mAP50 del paso 1, cuyo número propio es otro: todos los
 *  números correctos y el dueño equivocado, que es el modo de falla que este
 *  proyecto persigue. Por eso el rótulo lleva el paso pegado y el encabezado de
 *  la columna dice «Cifra del paso». */
function CifraDeGrupo({ g }: { g: RunGroup }) {
  if (g.cifra == null) return <span className="eo-na">sin cifra reportada</span>
  const label = g.cifra_label && g.paso != null
    ? `Paso ${g.paso} — ${g.cifra_label}`
    : g.cifra_label
  return (
    <span
      className={g.cifra_origen === 'citada' ? 'eo-cifra eo-cifra--cit' : 'eo-cifra'}
      title={g.fuente ?? undefined}
    >
      {label && <i>{label}</i>}
      {g.cifra}
    </span>
  )
}

/** Las corridas de UN grupo expandido, con "Ver todas" cuando quedan afuera
 *  de la primera página — nunca un link que no lleva a nada real. */
function FilasDeGrupo({
  grupo,
  todas,
  onVerTodas,
  onAbrir,
}: {
  grupo: RunGroup
  todas: boolean
  onVerTodas: () => void
  onAbrir: (runId: string) => void
}) {
  const q = useRunsPaged(
    {
      vista: 'todas',
      orden: 'created_at',
      direccion: 'desc',
      pagina: 1,
      pageSize: todas ? 200 : GRUPO_PAGE_SIZE,
      ...(grupo.result_id ? { resultId: grupo.result_id } : { clase: 'sin_clasificar' as Clase }),
    },
    false,
  )
  if (q.isPending) {
    return (
      <tr className="eo-sub">
        <td colSpan={6}><span className="eo-na">Cargando corridas…</span></td>
      </tr>
    )
  }
  if (q.error) {
    return (
      <tr className="eo-sub">
        <td colSpan={6}><span className="eo-na">No se pudieron leer las corridas de este grupo.</span></td>
      </tr>
    )
  }
  const filas = q.data?.items ?? []
  const faltan = grupo.n_runs - filas.length
  return (
    <>
      {filas.map((r) => (
        <tr key={r.run_id} className="eo-sub eo-row--click" onClick={() => onAbrir(r.run_id)}>
          <td className="eo-mono" style={{ paddingLeft: 35 }}>{r.name ?? r.run_id}</td>
          <td colSpan={2}><Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge></td>
          <td className="eo-mono">{sourceLabel(r.source_type)}</td>
          <td className="eo-num eo-mono">{r.total_detections ?? '—'}</td>
          <td className="eo-num eo-mono">{hace(r)}</td>
        </tr>
      ))}
      {faltan > 0 && (
        <tr className="eo-sub eo-sub--mas">
          <td colSpan={6} style={{ paddingLeft: 35 }}>
            {faltan} corrida{faltan === 1 ? '' : 's'} más de este resultado{' '}
            <Button variant="ghost" onClick={(e) => { e.stopPropagation(); onVerTodas() }}>
              Ver todas
            </Button>
          </td>
        </tr>
      )}
    </>
  )
}

export default function RunsPage() {
  const nav = useNavigate()
  const [agrupar, setAgrupar] = useState(true)
  const [clase, setClase] = useState<Clase | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [page, setPage] = useState(1)
  const [sorting, setSorting] = useState<SortingState>([])
  const [expandido, setExpandido] = useState<{ clave: string; resultId: string | null } | null>(null)
  const [expandidoTodas, setExpandidoTodas] = useState(false)

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

  // El total REAL de corridas: nunca se deriva sumando los grupos (una corrida
  // citada por dos resultados aparece en los dos). Viene de `X-Total-Count`,
  // independiente de cómo esté agrupado o filtrado el listado.
  const totalGeneral = useRunsTotal()
  const total = totalGeneral.data ?? null

  // Sin filtrar: el listado completo de grupos y, en sus cabeceras, los conteos
  // por clase y la disponibilidad del registro.
  const gruposTodos = useRunGroups()
  // La lista que se muestra: filtra del lado del servidor cuando hay clase elegida.
  const gruposFiltrados = useRunGroups(clase ?? undefined)

  // Los conteos NO se agregan acá: los manda el servidor en `X-Class-Counts`,
  // contando corridas DISTINTAS —lo mismo que devuelve el filtro—. Sumar
  // `g.n_runs` contaba citaciones y prometía 693 donde el filtro trae 412.
  // Si la cabecera no llegó, no hay chips: un chip con un número inventado es
  // peor que ningún chip.
  const conteos = gruposTodos.conteos

  const aguja = busqueda.trim().toLowerCase()
  const gruposVisibles = useMemo(() => {
    const base = gruposFiltrados.data ?? []
    if (!aguja) return base
    return base.filter((g) =>
      (g.titulo ?? '').toLowerCase().includes(aguja) ||
      (g.result_id ?? 'fuera del registro de evidencia').toLowerCase().includes(aguja))
  }, [gruposFiltrados.data, aguja])

  const listado = useRunsPaged(
    {
      estado: segment === 'all' ? undefined : segment,
      q: busqueda.trim() || undefined,
      clase: clase ?? undefined,
      ...orden,
      pagina: page,
      pageSize: PAGE_SIZE,
    },
    Boolean(liveRun),
    !agrupar,
  )

  const rows = listado.data?.items ?? null
  const totalFiltrado = listado.data?.total ?? 0
  const errorFlat = listado.error ? String(listado.error) : null

  const borrado = useDeleteRun()
  const deletingId = borrado.isPending ? borrado.variables : null

  const resetView = useCallback(() => {
    setPage(1)
    setConfirmId(null)
  }, [])

  // Un grupo que ya no está en `gruposVisibles` (cambió el filtro mientras
  // estaba abierto) queda huérfano: mejor colapsarlo que mostrar sub-filas sin
  // encabezado a la vista.
  const colapsar = useCallback(() => {
    setExpandido(null)
    setExpandidoTodas(false)
  }, [])

  const alternarGrupo = useCallback((g: RunGroup) => {
    const clave = claveDe(g)
    setExpandidoTodas(false)
    setExpandido((prev) => (prev?.clave === clave ? null : { clave, resultId: g.result_id }))
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

  // El toolbar (buscador, chips, toggle) se ve desde el primer render, sin
  // esperar a que resuelva ninguna consulta: sólo el CONTENIDO de abajo —la
  // tabla agrupada o la individual— se reemplaza por su propio estado de
  // carga/error, cada una en su tarjeta. Antes toda la pantalla desaparecía
  // detrás de un "Cargando…" mientras cargaba, toggle incluido.
  const cargandoGrupos = gruposFiltrados.isPending
  const errorGrupos = gruposFiltrados.error && !gruposFiltrados.data
    ? String(gruposFiltrados.error) : null

  const hayFiltroFlat = segment !== 'all' || busqueda.trim() !== ''
  const hayFiltroGrupos = clase != null || busqueda.trim() !== ''
  const sumaGrupos = (gruposTodos.data ?? []).reduce((n, g) => n + g.n_runs, 0)

  return (
    <>
      <PageHeader
        title="Corridas"
        meta={
          <>
            {total != null && <span>{total} corridas del plano de medios</span>}
            {agrupar && gruposTodos.data && (
              <>
                <span className="eo-sep">·</span>
                {/* «Fuera del registro de evidencia» es un grupo de la tabla,
                    NO un resultado: se descuenta y se nombra aparte, en vez de
                    inflar el conteo de resultados con él. */}
                <span>
                  agrupadas en {gruposTodos.data.filter((g) => g.result_id != null).length} resultados
                  de respaldo{gruposTodos.data.some((g) => g.result_id == null) && ' y las de fuera del registro'}
                </span>
              </>
            )}
            {enCurso.data != null && enCurso.data.total > 0 && (
              <>
                {(total != null || agrupar) && <span className="eo-sep">·</span>}
                <span style={{ color: 'var(--live)' }}>{enCurso.data.total} en curso</span>
              </>
            )}
          </>
        }
        actions={<Button variant="primary" onClick={() => nav('/compose')}>Nueva corrida</Button>}
      />

      {/* Antes de cualquier cifra de esta pantalla: si el registro o la
          taxonomía no están, todo lo de abajo es una clasificación fabricada. */}
      <AvisoRegistro meta={gruposTodos.visibility} noun="corridas" />

      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      {agrupar && errorGrupos && <ErrorBanner>{errorGrupos}</ErrorBanner>}
      {!agrupar && errorFlat && <ErrorBanner>{errorFlat}</ErrorBanner>}

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
          onChange={(v) => { setQuery(v); resetView(); colapsar() }}
          placeholder="Buscar corrida"
          ariaLabel="Buscar corridas por nombre o identificador"
        />
        {conteos && (
          <ClaseChips
            valor={clase}
            onChange={(c) => { setClase(c); resetView(); colapsar() }}
            conteos={conteos}
          />
        )}
        {!agrupar && (
          <SegmentedControl
            value={segment}
            options={SEGMENTS as unknown as Array<{ value: Segment; label: string }>}
            onChange={(v) => {
              setSegment(v)
              resetView()
            }}
          />
        )}
        <button
          type="button"
          className="eo-toggle"
          aria-pressed={agrupar}
          onClick={() => {
            setAgrupar((v) => !v)
            resetView()
            colapsar()
          }}
        >
          <IconGroup /> Agrupar por resultado
        </button>
        <span className="eo-toolbar__count eo-mono">
          {agrupar
            ? `${gruposVisibles.length} de ${gruposTodos.data?.length ?? gruposVisibles.length} grupos`
            : `${totalFiltrado} de ${total ?? totalFiltrado}`}
        </span>
      </div>

      {agrupar ? (
        <>
          <Card flush>
            <Table>
              <thead>
                <tr>
                  <th>Resultado que la cita</th>
                  {/* «del paso», no del resultado: ver `CifraDeGrupo`. */}
                  <th>Cifra del paso</th>
                  <th>Paso</th>
                  <th>Clase</th>
                  <th className="eo-th--numeric">Corridas</th>
                  <th className="eo-th--numeric">Última</th>
                </tr>
              </thead>
              <tbody>
                {gruposVisibles.map((g) => {
                  const clave = claveDe(g)
                  const abierto = expandido?.clave === clave
                  return (
                    <Fragment key={clave}>
                      <tr className="eo-row--click" onClick={() => alternarGrupo(g)}>
                        <td>
                          <div className="eo-grp">
                            <span
                              className={abierto ? 'eo-grp__icon eo-grp__icon--open' : 'eo-grp__icon'}
                              aria-hidden="true"
                            >
                              <IconChevron />
                            </span>
                            <span className="eo-grp__n">
                              <b>{nombreDeGrupo(g)}</b>
                              <span>{g.result_id ?? 'sin resultado citado'}</span>
                            </span>
                          </div>
                        </td>
                        <td><CifraDeGrupo g={g} /></td>
                        <td>{g.paso != null ? <span className="eo-paso">{g.paso}</span> : <span className="eo-na">—</span>}</td>
                        <td>
                          <Badge tone="neutral">
                            <Termino id={TERMINO_DE_CLASE[g.clase]}>{ETIQUETA_CLASE[g.clase]}</Termino>
                          </Badge>
                        </td>
                        <td className="eo-num eo-mono">{g.n_runs}</td>
                        <td className="eo-num eo-mono">{hace({ run_id: '', created_at: g.last_run_at })}</td>
                      </tr>
                      {abierto && (
                        <FilasDeGrupo
                          grupo={g}
                          todas={expandidoTodas}
                          onVerTodas={() => setExpandidoTodas(true)}
                          onAbrir={(runId) => nav(`/runs/${runId}`)}
                        />
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </Table>
            {cargandoGrupos ? (
              <p className="eo-empty">Cargando…</p>
            ) : gruposVisibles.length === 0 && !errorGrupos && (
              hayFiltroGrupos ? (
                <EmptyState hint="Probá con otro texto o quitá el filtro de clase.">
                  Ningún grupo coincide
                </EmptyState>
              ) : (
                <EmptyState hint="Empezá por elegir una fuente y un conjunto de prompts.">
                  Todavía no hay corridas registradas
                </EmptyState>
              )
            )}
          </Card>
          {total != null && (
            <p className="eo-cap">
              {total} corridas en total, {sumaGrupos} citaciones en {gruposTodos.data?.length ?? 0} grupos:
              una corrida citada por dos resultados aparece en los dos, así que la suma de los grupos NO es
              el total — leelo siempre de la cabecera de la pantalla, nunca sumando esta tabla.
            </p>
          )}
        </>
      ) : (
        <>
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
                        const clasePlana = esAccion
                          ? 'eo-cell--actions'
                          : [numeric && 'eo-num', mono && 'eo-mono'].filter(Boolean).join(' ')
                        return (
                          <td
                            key={celda.id}
                            className={clasePlana || undefined}
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
            {rows === null && !errorFlat ? (
              <p className="eo-empty">Cargando…</p>
            ) : totalFiltrado === 0 && !errorFlat && (
              hayFiltroFlat ? (
                <EmptyState hint="Probá con otro texto o quitá el filtro.">
                  Ninguna corrida coincide con el filtro
                </EmptyState>
              ) : (
                <EmptyState hint="Empezá por elegir una fuente y un conjunto de prompts.">
                  Todavía no lanzaste ninguna corrida
                </EmptyState>
              )
            )}
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
      )}
    </>
  )
}
