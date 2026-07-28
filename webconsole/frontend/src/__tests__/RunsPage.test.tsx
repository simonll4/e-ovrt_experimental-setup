import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  deleteRun: vi.fn(),
  getTrace: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getTrace).mockResolvedValue({
    control_run_id: null,
    totals: { frames: 0, detections: 0, dropped_by_reason: {}, alerts: 0, received: null, not_received: null },
  } as never)
})
afterEach(() => cleanup())

const renderPage = () => render(<MemoryRouter><RunsPage /></MemoryRouter>)

const row = (over: Record<string, unknown> = {}) =>
  ({ run_id: 'r_1', status: 'succeeded', model: 'gdino', ...over }) as never

/**
 * Consultas acotadas a la tabla. Hace falta porque el banner de corrida en vivo
 * también nombra la corrida: buscar en todo el documento encuentra dos.
 */
const table = () => screen.getByRole('table')
const inTable = (text: string) =>
  within(table()).queryAllByText(text)

/** Borra la corrida `id` por el camino nuevo: abrir la confirmación en línea y aceptar. */
const deleteRow = async (id: string) => {
  fireEvent.click(screen.getByRole('button', { name: `Borrar ${id}` }))
  fireEvent.click(await screen.findByRole('button', { name: 'Sí, borrar' }))
}

describe('RunsPage', () => {
  it('lista corridas y marca la que está en curso', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_1', status: 'running', live: true }),
      row({ run_id: 'r_2' }),
    ])
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))
    // Acotado a la tabla: "En curso" también es una opción del segmentado.
    expect(inTable('En curso')[0].className).toContain('eo-badge--live')
    expect(inTable('Completada')[0].className).toContain('eo-badge--ok')
  })

  it('traduce los estados: nunca muestra el código crudo del backend', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_a', status: 'stopped' }),
      row({ run_id: 'r_b', status: 'failed' }),
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_a')).toBeTruthy())
    expect(screen.getByText('Detenida')).toBeTruthy()
    expect(screen.getByText('Fallida')).toBeTruthy()
    expect(screen.queryByText('stopped')).toBeNull()
    expect(screen.queryByText('failed')).toBeNull()
  })

  it('traduce el tipo de fuente', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([row({ source_type: 'video_file' })])
    renderPage()
    await waitFor(() => expect(screen.getByText('Archivo de video')).toBeTruthy())
    expect(screen.queryByText('video_file')).toBeNull()
  })

  it('muestra el nombre en vez del run_id cuando está presente, con el id como subtítulo', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_named', name: 'mi corrida' }),
      row({ run_id: 'r_sin_nombre' }),
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('mi corrida')).toBeTruthy())
    expect(screen.getByText('r_named')).toBeTruthy()
    expect(screen.getByText('r_sin_nombre')).toBeTruthy()
  })

  it('pagina el listado en vez de volcar todas las filas', async () => {
    // started_at explícito: el orden por defecto es por fecha descendente, así que
    // r_29 (la más nueva) encabeza la primera página y r_00 cae en la segunda.
    vi.mocked(api.listRuns).mockResolvedValue(
      Array.from({ length: 30 }, (_, i) =>
        row({
          run_id: `r_${String(i).padStart(2, '0')}`,
          started_at: new Date(Date.UTC(2026, 6, 28, 0, i)).toISOString(),
        }),
      ),
    )
    renderPage()
    await waitFor(() => expect(inTable('r_29')).toHaveLength(1))
    // 25 filas + la fila de encabezado
    expect(screen.getAllByRole('row')).toHaveLength(26)
    expect(inTable('r_00')).toHaveLength(0)
    expect(screen.getByText('Página 1 de 2')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(screen.getByText('Página 2 de 2')).toBeTruthy()
    expect(screen.getAllByRole('row')).toHaveLength(6)
    expect(inTable('r_00')).toHaveLength(1)
  })

  it('el buscador filtra por nombre y por identificador', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_uno', name: 'telemetría' }),
      row({ run_id: 'r_dos', name: 'otra cosa' }),
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('telemetría')).toBeTruthy())
    const search = screen.getByRole('searchbox')
    fireEvent.change(search, { target: { value: 'telemetr' } })
    expect(screen.queryByText('otra cosa')).toBeNull()
    fireEvent.change(search, { target: { value: 'r_dos' } })
    expect(screen.getByText('otra cosa')).toBeTruthy()
    expect(screen.queryByText('telemetría')).toBeNull()
  })

  it('el segmentado filtra por estado', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_run', status: 'running', live: true }),
      row({ run_id: 'r_ok' }),
    ])
    renderPage()
    await waitFor(() => expect(inTable('r_run')).toHaveLength(1))
    fireEvent.click(screen.getByRole('button', { name: 'Completadas' }))
    expect(inTable('r_ok')).toHaveLength(1)
    expect(inTable('r_run')).toHaveLength(0)
  })

  it('anuncia cuántas corridas hay en total y cuántas en curso', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_run', status: 'running', live: true }),
      row({ run_id: 'r_ok' }),
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText(/2 en total/)).toBeTruthy())
    expect(screen.getByText(/1 en curso/)).toBeTruthy()
  })

  // Regresión: el BFF solo hidrata las primeras corridas, así que la lista mezcla
  // filas con `started_at` y filas sin él. Comparadas como texto, "run_2026…"
  // ordenaba por encima de "2026-07-25T…" y las más nuevas caían a la última página.
  it('ordena por fecha aunque falte started_at en parte de las filas', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'run_20260725_120000_x', started_at: '2026-07-25T12:00:00Z' }),
      row({ run_id: 'run_20260728_120000_x' }), // sin hidratar: la fecha sale del id
      row({ run_id: 'run_20260720_120000_x', started_at: '2026-07-20T12:00:00Z' }),
    ])
    renderPage()
    await waitFor(() => expect(inTable('run_20260728_120000_x')).toHaveLength(1))
    const ids = screen
      .getAllByRole('row')
      .slice(1)
      .map((tr) => tr.querySelector('.eo-rowname')?.textContent ?? '')
    expect(ids[0]).toContain('20260728')
    expect(ids[1]).toContain('20260725')
    expect(ids[2]).toContain('20260720')
  })

  it('estado vacío cuando no hay corridas', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText('Sin corridas todavía.')).toBeTruthy())
  })

  it('muestra el error con role alert', async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error('boom'))
    renderPage()
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })

  it('no ofrece borrar una corrida en curso, sí una terminada', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      row({ run_id: 'r_1', status: 'running', live: true }),
      row({ run_id: 'r_2' }),
    ])
    renderPage()
    await waitFor(() => expect(inTable('r_1')).toHaveLength(1))
    expect(screen.queryByRole('button', { name: 'Borrar r_1' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Borrar r_2' })).toBeTruthy()
  })

  it('la confirmación es en línea, no un diálogo del navegador', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([row({ run_id: 'r_2' })])
    const confirmSpy = vi.spyOn(window, 'confirm')
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar r_2' }))
    expect(await screen.findByRole('button', { name: 'Sí, borrar' })).toBeTruthy()
    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('cancelar la confirmación no borra nada', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([row({ run_id: 'r_2' })])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar r_2' }))
    fireEvent.click(await screen.findByRole('button', { name: 'No' }))
    expect(api.deleteRun).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Borrar r_2' })).toBeTruthy()
  })

  it('confirmar borra la corrida y refresca la lista', async () => {
    vi.mocked(api.listRuns)
      .mockResolvedValueOnce([row({ run_id: 'r_2' })])
      .mockResolvedValue([])
    vi.mocked(api.deleteRun).mockResolvedValue(undefined as never)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    await deleteRow('r_2')
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_2'))
    await waitFor(() => expect(screen.getByText('Sin corridas todavía.')).toBeTruthy())
  })

  it('borrado parcial muestra los planos que fallaron, y persiste tras el refresh', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([row({ run_id: 'r_2' })])
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    } as never)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    await deleteRow('r_2')
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))

    // El refresh que dispara el `finally` no debe pisar el mensaje de borrado
    // parcial (regresión: refresh() ponía `error` en null).
    await waitFor(() => expect(vi.mocked(api.listRuns).mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
  })
})
