import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
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
  // La pantalla ahora se alimenta del índice de traza y del inventario de
  // artefactos; sin mockearlos, en jsdom fallan por URL relativa y meten un
  // segundo role="alert" que rompe las búsquedas por rol.
  getTraceIndex: vi.fn().mockResolvedValue({
    media_run_id: 'r_1',
    control_run_id: null,
    topology: null,
    control_error: null,
    totals: { frames: 0, detections: 0, dropped_by_reason: {}, alerts: 0, received: null, not_received: null },
    total: 0,
    unit_id: [],
    frame_index: [],
    timestamp_ms: [],
    detections: [],
    control_state: [],
    alert: [],
  }),
  getArtifacts: vi.fn().mockResolvedValue({ run_id: 'r_1', items: [] }),
  getRunComparison: vi.fn().mockResolvedValue({
    run_id: 'r_1', previous_run_id: null, matched_on: [], deltas: {},
  }),
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

/** Borra por el camino nuevo: abrir la confirmación en línea y aceptar. */
const deleteRun = async () => {
  fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Sí, borrar' }))
}

describe('RunDetailPage', () => {
  it('muestra el estado de la corrida con el glosario, no con el código crudo', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('Completada').className).toContain('eo-badge--ok'))
    expect(screen.queryByText('succeeded')).toBeNull()
  })

  it('muestra el nombre del run (top-level, run vivo) con el id como subtítulo', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1', name: 'mi corrida en vivo', status: 'running', live: true,
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('mi corrida en vivo')).toBeTruthy())
    expect(screen.getByText('r_1')).toBeTruthy()
  })

  it('muestra el nombre desde summary (run terminado) cuando no viene top-level', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1', status: 'succeeded', live: false,
      summary: { name: 'corrida ya terminada' },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('corrida ya terminada')).toBeTruthy())
  })

  it('sin nombre, muestra solo el run_id (sin duplicar)', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    renderPage()
    await waitFor(() => expect(screen.getAllByText('r_1')).toHaveLength(1))
  })

  it('muestra la tira de indicadores con los rótulos del glosario', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1',
      status: 'succeeded',
      live: false,
      summary: { fps_effective: 24, total_detections: 100, duration_seconds: 5 },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('Cuadros por segundo')).toBeTruthy())
    expect(screen.getByText('24,00')).toBeTruthy()
    expect(screen.getByText('100')).toBeTruthy()
    expect(screen.getByText('Latencia (mediana)')).toBeTruthy()
  })

  it('las pestañas separan traza, resumen, evaluación y archivos', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1',
      status: 'succeeded',
      live: false,
      summary: { model_name: 'gdino', prompt_set_id: 'ps_v1' },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByRole('tab', { name: /Traza/ })).toBeTruthy())
    fireEvent.click(screen.getByRole('tab', { name: 'Resumen' }))
    expect(screen.getByText('Conjunto de prompts')).toBeTruthy()
    expect(screen.getByText('ps_v1')).toBeTruthy()
  })

  it('no muestra el botón de borrado mientras el run está corriendo', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'running', live: true } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.queryByRole('button', { name: 'Borrar' })).toBeNull()
  })

  it('cancelar la confirmación no borra nada', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    const confirmSpy = vi.spyOn(window, 'confirm')
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'No' }))
    expect(api.deleteRun).not.toHaveBeenCalled()
    expect(navigateMock).not.toHaveBeenCalled()
    // La confirmación es en línea: no se usa el diálogo del navegador.
    expect(confirmSpy).not.toHaveBeenCalled()
  })

  // Al listado, que vive en '/'. Antes navegaba a '/runs', una ruta que no
  // existe en App.tsx: borrar desde el detalle dejaba el contenido en blanco.
  it('confirmar borra la corrida y vuelve al listado', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    vi.mocked(api.deleteRun).mockResolvedValue(undefined)
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    await deleteRun()
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_1'))
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/'))
  })

  it('borrado parcial muestra el detalle de los planos que fallaron y persiste (no navega)', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    })
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy())
    await deleteRun()
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
    expect(navigateMock).not.toHaveBeenCalled()

    // El error de borrado se guarda en un estado separado (`deleteError`) del error de
    // carga (`error`), y se renderiza como un banner inline junto al resto de la página
    // en lugar de reemplazarla vía el `if (error) return <ErrorBanner>...` de arriba: el
    // resto del detalle del run (incluido el propio botón "Borrar", para poder
    // reintentar) sigue visible.
    expect(screen.getByRole('button', { name: 'Borrar' })).toBeTruthy()
    expect(screen.getByText('r_1')).toBeTruthy()

    // Este componente no dispara ningún refresh automático (polling/WS) cuando el run
    // no está corriendo ni es streamable, así que no hay ruta por la que el mensaje de
    // borrado parcial pueda ser pisado por un `refresh()` posterior (a diferencia del
    // bug encontrado en RunsPage/Task 6). Verificamos que el mensaje siga presente
    // tras dejar correr los timers/microtasks pendientes.
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.getByRole('alert').textContent).toContain('control')
  })
})
