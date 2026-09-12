import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import type { RunRow } from '../types'
import type { RunsQuery } from '../api/endpoints'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRunsPaged: vi.fn(),
  listRunGroups: vi.fn(),
  deleteRun: vi.fn(),
  getTrace: vi.fn(),
}))

/** El historial que "tiene el servidor". Los tests lo reasignan; borrar lo achica. */
let corridas: RunRow[] = []

/**
 * Servidor de mentira que filtra, ordena y pagina como el de verdad.
 *
 * Es más largo que devolver una lista fija, y es la única forma de probar lo que
 * importa ahora: que la pantalla mande los filtros correctos y muestre lo que le
 * contestan, en vez de recortar en el cliente. Las tres consultas de la pantalla
 * —página, corridas en curso y total— salen todas de acá, distinguidas por sus
 * filtros, igual que contra el backend real.
 */
const servidor = () =>
  vi.mocked(api.listRunsPaged).mockImplementation(async (f: RunsQuery = {}) => {
    let base = corridas
    if (f.estado) base = base.filter((r) => r.status === f.estado)
    if (f.q) {
      const aguja = f.q.toLowerCase()
      base = base.filter((r) => `${r.run_id} ${r.name ?? ''}`.toLowerCase().includes(aguja))
    }
    const campo = (f.orden ?? 'created_at') as keyof RunRow
    base = [...base].sort((a, b) => String(a[campo] ?? '').localeCompare(String(b[campo] ?? '')))
    if (f.direccion !== 'asc') base.reverse()
    const size = f.pageSize ?? 25
    const desde = ((f.pagina ?? 1) - 1) * size
    return { items: base.slice(desde, desde + size), total: base.length }
  })

beforeEach(() => {
  vi.clearAllMocks()
  corridas = []
  servidor()
  // Task 7 agrupa por resultado por defecto: este archivo prueba el listado
  // individual (sort/paginación/borrado), no la agrupación (ver
  // RunsClases.test.tsx), así que `renderPage()` apaga el toggle apenas monta.
  // Sin datos de grupos que mostrar mientras tanto (irrelevantes acá).
  vi.mocked(api.listRunGroups).mockResolvedValue({ items: [] })
  vi.mocked(api.getTrace).mockResolvedValue({
    control_run_id: null,
    totals: { frames: 0, detections: 0, dropped_by_reason: {}, alerts: 0, received: null, not_received: null },
  } as never)
})
afterEach(() => cleanup())

function Detalle() {
  const { id } = useParams()
  return <p>detalle de {id}</p>
}

/** Monta la pantalla y apaga "Agrupar por resultado": este archivo cubre el
 *  listado individual (Task 7 lo dejó como vista alternativa, no la de
 *  arranque). La agrupación tiene su propia cobertura en RunsClases.test.tsx. */
const renderPage = () => {
  const utils = render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/runs/:id" element={<Detalle />} />
      </Routes>
    </MemoryRouter>,
  )
  fireEvent.click(screen.getByRole('button', { name: /Agrupar por resultado/ }))
  return utils
}

const row = (over: Partial<RunRow> = {}): RunRow =>
  ({ run_id: 'r_1', status: 'succeeded', model: 'gdino', ...over }) as RunRow

/**
 * Consultas acotadas a la tabla. Hace falta porque el banner de corrida en vivo
 * también nombra la corrida: buscar en todo el documento encuentra dos.
 */
const table = () => screen.getByRole('table')
const inTable = (text: string) => within(table()).queryAllByText(text)

/** Los filtros del último pedido del listado (no el de en-curso ni el del total). */
const ultimoListado = (): RunsQuery => {
  const llamadas = vi.mocked(api.listRunsPaged).mock.calls.map(([f]) => f ?? {})
  const listados = llamadas.filter((f) => f.pageSize === 25)
  return listados[listados.length - 1]
}

/** Borra la corrida `id`: abrir la confirmación en línea y aceptar. */
const deleteRow = async (id: string) => {
  fireEvent.click(screen.getByRole('button', { name: `Borrar ${id}` }))
  fireEvent.click(await screen.findByRole('button', { name: 'Sí, borrar' }))
}

describe('RunsPage', () => {
  it('lista corridas y marca la que está en curso', async () => {
    corridas = [row({ run_id: 'r_1', status: 'running', live: true }), row({ run_id: 'r_2' })]
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))
    // Acotado a la tabla: "En curso" también es una opción del segmentado.
    expect(inTable('En curso')[0].className).toContain('eo-badge--live')
    expect(inTable('Completada')[0].className).toContain('eo-badge--ok')
  })

  it('traduce los estados: nunca muestra el código crudo del backend', async () => {
    corridas = [row({ run_id: 'r_a', status: 'stopped' }), row({ run_id: 'r_b', status: 'failed' })]
    renderPage()
    await waitFor(() => expect(screen.getByText('r_a')).toBeTruthy())
    expect(screen.getByText('Detenida')).toBeTruthy()
    expect(screen.getByText('Fallida')).toBeTruthy()
    expect(screen.queryByText('stopped')).toBeNull()
    expect(screen.queryByText('failed')).toBeNull()
  })

  it('traduce el tipo de fuente', async () => {
    corridas = [row({ source_type: 'video_file' })]
    renderPage()
    await waitFor(() => expect(screen.getByText('Archivo de video')).toBeTruthy())
    expect(screen.queryByText('video_file')).toBeNull()
  })

  it('muestra el nombre en vez del run_id cuando está presente, con el id como subtítulo', async () => {
    corridas = [row({ run_id: 'r_named', name: 'mi corrida' }), row({ run_id: 'r_sin_nombre' })]
    renderPage()
    await waitFor(() => expect(screen.getByText('mi corrida')).toBeTruthy())
    expect(screen.getByText('r_named')).toBeTruthy()
    expect(screen.getByText('r_sin_nombre')).toBeTruthy()
  })

  // §2.2 de la auditoría: se sacó la columna "Creada" y la antigüedad volvió al
  // subtítulo. Una corrida con nombre muestra su identificador; una sin nombre,
  // que ya usa el identificador de título, muestra cuándo se creó.
  it('sin nombre, el subtítulo es la antigüedad en vez del identificador repetido', async () => {
    const reciente = new Date(Date.now() - 5 * 60_000).toISOString()
    corridas = [row({ run_id: 'r_sin', created_at: reciente })]
    renderPage()
    await waitFor(() => expect(screen.getByText('r_sin')).toBeTruthy())
    expect(within(table()).getByText('hace 5 min')).toBeTruthy()
    expect(screen.queryByText('Creada')).toBeNull()
  })

  // §2.5: la fila entera navega, no solo el título.
  it('un click en cualquier parte de la fila abre el detalle', async () => {
    corridas = [row({ run_id: 'r_click', model: 'owlv2' })]
    renderPage()
    await waitFor(() => expect(inTable('r_click')).toHaveLength(1))
    fireEvent.click(within(table()).getByText('owlv2'))
    await waitFor(() => expect(screen.getByText('detalle de r_click')).toBeTruthy())
  })

  it('el pedido de la página lleva el filtro, el orden y la página al servidor', async () => {
    corridas = Array.from({ length: 30 }, (_, i) =>
      row({ run_id: `r_${String(i).padStart(2, '0')}`, created_at: `2026-07-28T00:${String(i).padStart(2, '0')}:00Z` }),
    )
    renderPage()
    await waitFor(() => expect(inTable('r_29')).toHaveLength(1))

    // Por defecto: lo más nuevo arriba, 25 filas, sin filtro de estado.
    expect(ultimoListado()).toMatchObject({ orden: 'created_at', direccion: 'desc', pagina: 1 })
    expect(screen.getAllByRole('row')).toHaveLength(26) // 25 filas + encabezado
    expect(inTable('r_00')).toHaveLength(0)
    expect(screen.getByText('Página 1 de 2')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(ultimoListado().pagina).toBe(2))
    await waitFor(() => expect(inTable('r_00')).toHaveLength(1))
    expect(screen.getByText('Página 2 de 2')).toBeTruthy()
  })

  it('el buscador manda `q` al servidor en vez de filtrar en el cliente', async () => {
    corridas = [row({ run_id: 'r_uno', name: 'telemetría' }), row({ run_id: 'r_dos', name: 'otra cosa' })]
    renderPage()
    await waitFor(() => expect(screen.getByText('telemetría')).toBeTruthy())

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'telemetr' } })
    await waitFor(() => expect(ultimoListado().q).toBe('telemetr'))
    await waitFor(() => expect(screen.queryByText('otra cosa')).toBeNull())

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'r_dos' } })
    await waitFor(() => expect(screen.getByText('otra cosa')).toBeTruthy())
    expect(screen.queryByText('telemetría')).toBeNull()
  })

  it('el segmentado manda `estado` al servidor', async () => {
    corridas = [row({ run_id: 'r_run', status: 'running', live: true }), row({ run_id: 'r_ok' })]
    renderPage()
    await waitFor(() => expect(inTable('r_run')).toHaveLength(1))
    fireEvent.click(screen.getByRole('button', { name: 'Completadas' }))
    await waitFor(() => expect(ultimoListado().estado).toBe('succeeded'))
    await waitFor(() => expect(inTable('r_run')).toHaveLength(0))
    expect(inTable('r_ok')).toHaveLength(1)
  })

  // El orden es del servidor: la tabla no reordena la página sobre sí misma,
  // que daría un orden por página en vez de un orden del listado.
  it('ordenar cambia `orden` y `direccion`, y el tercer click vuelve al orden por fecha', async () => {
    corridas = [row({ run_id: 'r_1' }), row({ run_id: 'r_2' })]
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))

    const encabezado = screen.getByText('Cuadros/s')
    fireEvent.click(encabezado)
    await waitFor(() => expect(ultimoListado()).toMatchObject({ orden: 'fps_effective', direccion: 'desc' }))
    fireEvent.click(encabezado)
    await waitFor(() => expect(ultimoListado()).toMatchObject({ orden: 'fps_effective', direccion: 'asc' }))
    fireEvent.click(encabezado)
    await waitFor(() => expect(ultimoListado()).toMatchObject({ orden: 'created_at', direccion: 'desc' }))
  })

  it('no ofrece ordenar por las columnas que el servidor no sabe ordenar', async () => {
    corridas = [row()]
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))
    const th = (t: string) => within(table()).getByText(t).closest('th')
    expect(th('Cuadros/s')?.className).toContain('eo-th--sortable')
    expect(th('Fuente')?.className ?? '').not.toContain('eo-th--sortable')
    expect(th('Conjunto de prompts')?.className ?? '').not.toContain('eo-th--sortable')
  })

  it('anuncia cuántas corridas hay en total y cuántas en curso', async () => {
    corridas = [row({ run_id: 'r_run', status: 'running', live: true }), row({ run_id: 'r_ok' })]
    renderPage()
    // Task 7: el encabezado dice "N corridas del plano de medios" (mismo
    // texto que el mockup), no "N en total".
    await waitFor(() => expect(screen.getByText(/2 corridas del plano de medios/)).toBeTruthy())
    expect(screen.getByText(/1 en curso/)).toBeTruthy()
  })

  // El total viene de `X-Total-Count`, no de contar filas: contando la página,
  // un historial de 60 corridas diría "25 corridas del plano de medios".
  it('el total es el del servidor, no la cantidad de filas de la página', async () => {
    corridas = Array.from({ length: 60 }, (_, i) => row({ run_id: `r_${i}` }))
    renderPage()
    await waitFor(() => expect(screen.getByText(/60 corridas del plano de medios/)).toBeTruthy())
  })

  it('estado vacío cuando no hay corridas', async () => {
    corridas = []
    renderPage()
    await waitFor(() => expect(screen.getByText('Todavía no lanzaste ninguna corrida')).toBeTruthy())
  })

  it('estado vacío distinto cuando lo que no coincide es el filtro', async () => {
    corridas = [row({ run_id: 'r_ok' })]
    renderPage()
    await waitFor(() => expect(inTable('r_ok')).toHaveLength(1))
    fireEvent.click(screen.getByRole('button', { name: 'Fallidas' }))
    await waitFor(() => expect(screen.getByText('Ninguna corrida coincide con el filtro')).toBeTruthy())
  })

  it('muestra el error con role alert', async () => {
    vi.mocked(api.listRunsPaged).mockRejectedValue(new Error('boom'))
    renderPage()
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })

  it('no ofrece borrar una corrida en curso, sí una terminada', async () => {
    corridas = [row({ run_id: 'r_1', status: 'running', live: true }), row({ run_id: 'r_2' })]
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))
    expect(screen.queryByRole('button', { name: 'Borrar r_1' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Borrar r_2' })).toBeTruthy()
  })

  it('la confirmación es en línea, no un diálogo del navegador', async () => {
    corridas = [row({ run_id: 'r_2' })]
    const confirmSpy = vi.spyOn(window, 'confirm')
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar r_2' }))
    expect(await screen.findByRole('button', { name: 'Sí, borrar' })).toBeTruthy()
    expect(confirmSpy).not.toHaveBeenCalled()
  })

  // Con la fila entera navegable, borrar tiene que quedarse en el listado:
  // confirmar el borrado no puede además abrir el detalle de lo que se borra.
  it('borrar no navega al detalle de la corrida', async () => {
    corridas = [row({ run_id: 'r_2' })]
    vi.mocked(api.deleteRun).mockImplementation(async (id: string) => {
      corridas = corridas.filter((r) => r.run_id !== id)
      return undefined as never
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    await deleteRow('r_2')
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_2'))
    expect(screen.queryByText('detalle de r_2')).toBeNull()
  })

  it('cancelar la confirmación no borra nada', async () => {
    corridas = [row({ run_id: 'r_2' })]
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar r_2' }))
    fireEvent.click(await screen.findByRole('button', { name: 'No' }))
    expect(api.deleteRun).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Borrar r_2' })).toBeTruthy()
  })

  it('confirmar borra la corrida y refresca la lista', async () => {
    corridas = [row({ run_id: 'r_2' })]
    vi.mocked(api.deleteRun).mockImplementation(async (id: string) => {
      corridas = corridas.filter((r) => r.run_id !== id)
      return undefined as never
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    await deleteRow('r_2')
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_2'))
    await waitFor(() => expect(screen.getByText('Todavía no lanzaste ninguna corrida')).toBeTruthy())
  })

  it('borrado parcial muestra los planos que fallaron, y persiste tras el refresh', async () => {
    corridas = [row({ run_id: 'r_2' })]
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    } as never)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    const antes = vi.mocked(api.listRunsPaged).mock.calls.length
    await deleteRow('r_2')
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))

    // El refresh que dispara la invalidación no debe pisar el mensaje de borrado
    // parcial (regresión: refresh() ponía `error` en null).
    await waitFor(() =>
      expect(vi.mocked(api.listRunsPaged).mock.calls.length).toBeGreaterThan(antes),
    )
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
  })
})
