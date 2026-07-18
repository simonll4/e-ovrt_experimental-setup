import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RunDetailPage from '../pages/RunDetailPage'
import * as api from '../api'

const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigateMock,
}))

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getRun: vi.fn(),
  deleteRun: vi.fn(),
  getDetections: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getEvaluation: vi.fn().mockResolvedValue(null),
  getTrace: vi.fn().mockResolvedValue({
    media_run_id: 'r_1',
    control_run_id: null,
    topology: null,
    control_error: null,
    totals: {
      frames: 0,
      detections: 0,
      dropped_by_reason: {},
      alerts: 0,
      received: null,
      not_received: null,
    },
    page: 1,
    page_size: 50,
    total: 0,
    frames: [],
  }),
}))

beforeEach(() => {
  vi.clearAllMocks()
  navigateMock.mockClear()
})
afterEach(() => cleanup())

const renderPage = (id = 'r_1') =>
  render(
    <MemoryRouter initialEntries={[`/runs/${id}`]}>
      <Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>
    </MemoryRouter>,
  )

describe('RunDetailPage', () => {
  it('muestra el estado del run como badge', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('OK').className).toContain('eo-badge--ok'))
  })

  it('muestra tiles de métricas cuando hay summary', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1',
      status: 'succeeded',
      live: false,
      summary: { fps_effective: 24, total_detections: 100, duration_seconds: 5 },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('24')).toBeTruthy())
    expect(screen.getByText('100')).toBeTruthy()
  })

  it('no muestra el botón de borrado mientras el run está corriendo', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'running', live: true } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.queryByRole('button', { name: 'Borrar' })).toBeNull()
  })

  it('cancelar el confirm no borra nada', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(api.deleteRun).not.toHaveBeenCalled()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('confirmar borra el run y navega a /runs', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    vi.mocked(api.deleteRun).mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_1'))
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/runs'))
  })

  it('borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega)', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
    expect(navigateMock).not.toHaveBeenCalled()

    // Este componente no dispara ningún refresh automático (polling/WS) cuando el run
    // no está corriendo ni es streamable, así que no hay ruta por la que el mensaje de
    // borrado parcial pueda ser pisado por un `refresh()` posterior (a diferencia del
    // bug encontrado en RunsPage/Task 6). Verificamos que el mensaje siga presente
    // tras dejar correr los timers/microtasks pendientes.
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.getByRole('alert').textContent).toContain('control')
  })
})
