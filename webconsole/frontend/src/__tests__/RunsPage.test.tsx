import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  deleteRun: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPage = () => render(<MemoryRouter><RunsPage /></MemoryRouter>)

describe('RunsPage', () => {
  it('lista corridas y marca la viva con badge', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_1', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.getByText('en curso').className).toContain('eo-badge--live')
    expect(screen.getByText('completada').className).toContain('eo-badge--ok')
  })

  it('el filtro de estado por defecto muestra todas, y filtra al elegir un estado', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_running', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_ok', status: 'succeeded', model: 'gdino' } as any,
      { run_id: 'r_failed', status: 'failed', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_running')).toBeTruthy())
    expect(screen.getByText('r_ok')).toBeTruthy()
    expect(screen.getByText('r_failed')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Todas' }))
    fireEvent.click(screen.getByRole('option', { name: 'En curso' }))

    expect(screen.getByText('r_running')).toBeTruthy()
    expect(screen.queryByText('r_ok')).toBeNull()
    expect(screen.queryByText('r_failed')).toBeNull()
  })

  it('muestra el nombre en vez del run_id cuando está presente, con el id como subtítulo', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_named', name: 'mi corrida', status: 'succeeded', model: 'gdino' } as any,
      { run_id: 'r_sin_nombre', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('mi corrida')).toBeTruthy())
    expect(screen.getByText('r_named')).toBeTruthy() // subtítulo con el id real
    expect(screen.getByText('r_sin_nombre')).toBeTruthy() // sin nombre: se ve el id, sin duplicar
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

  it('no muestra botón de borrado para un run corriendo, sí para uno terminado', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_1', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.queryAllByRole('button', { name: 'Borrar' })).toHaveLength(1)
  })

  it('cancelar el confirm no borra nada', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(api.deleteRun).not.toHaveBeenCalled()
  })

  it('confirmar borra el run y refresca la lista', async () => {
    vi.mocked(api.listRuns)
      .mockResolvedValueOnce([{ run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any])
      .mockResolvedValueOnce([])
    vi.mocked(api.deleteRun).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_2'))
    await waitFor(() => expect(screen.getByText('Sin corridas todavía.')).toBeTruthy())
  })

  it('borrado parcial muestra el detalle de los planos que fallaron, y persiste tras el refresh de la lista', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))

    // El `finally` de handleDelete dispara un refresh() de la lista (listRuns) que
    // resuelve exitosamente. Ese refresh no debe borrar el mensaje de borrado parcial:
    // esperamos a que el refresh termine de asentarse y volvemos a comprobar que el
    // alert sigue presente (regresión del bug: refresh() pisaba `error` con `null`).
    await waitFor(() => expect(vi.mocked(api.listRuns).mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
  })
})
