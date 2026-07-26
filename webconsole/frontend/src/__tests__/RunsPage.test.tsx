import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  deleteRun: vi.fn(),
  getTrace: vi.fn().mockResolvedValue({
    media_run_id: 'r_1', control_run_id: null, topology: null, control_error: null,
    totals: { frames: 0, detections: 0, dropped_by_reason: {}, alerts: 0, received: null, not_received: null },
    page: 1, page_size: 1, total: 0, frames: [],
  }),
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
    const table = await screen.findByRole('table')
    await waitFor(() => expect(within(table).getByText('r_1')).toBeTruthy())
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
    const table = await screen.findByRole('table')
    await waitFor(() => expect(within(table).getByText('r_running')).toBeTruthy())
    expect(within(table).getByText('r_ok')).toBeTruthy()
    expect(within(table).getByText('r_failed')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'En curso' }))

    expect(within(table).getByText('r_running')).toBeTruthy()
    expect(within(table).queryByText('r_ok')).toBeNull()
    expect(within(table).queryByText('r_failed')).toBeNull()
  })

  // `stopped` es ~21% del corpus real: sin la opción de filtro esas corridas
  // solo se podían ver mezcladas en "Todas".
  it('el filtro ofrece Detenidas y aísla las corridas stopped', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_stopped', status: 'stopped', model: 'gdino' } as any,
      { run_id: 'r_ok', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_stopped')).toBeTruthy())
    expect(screen.getByText('detenida').className).toContain('eo-badge--neutral')

    fireEvent.click(screen.getByRole('button', { name: 'Detenidas' }))

    expect(screen.getByText('r_stopped')).toBeTruthy()
    expect(screen.queryByText('r_ok')).toBeNull()
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
    await waitFor(() => expect(screen.getByText(/todavía no lanzaste ninguna corrida/i)).toBeTruthy())
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
    const table = await screen.findByRole('table')
    await waitFor(() => expect(within(table).getByText('r_1')).toBeTruthy())
    expect(screen.queryAllByRole('button', { name: 'Borrar' })).toHaveLength(1)
  })

  it('cancelar el confirm no borra nada', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    expect(screen.queryByText('¿Borrar?')).toBeNull()
    expect(api.deleteRun).not.toHaveBeenCalled()
  })

  it('confirmar borra el run y refresca la lista', async () => {
    vi.mocked(api.listRuns)
      .mockResolvedValueOnce([{ run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any])
      .mockResolvedValueOnce([])
    vi.mocked(api.deleteRun).mockResolvedValue(undefined)
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('r_2'))
    await waitFor(() => expect(screen.getByText(/todavía no lanzaste ninguna corrida/i)).toBeTruthy())
  })

  it('borrado parcial muestra el detalle de los planos que fallaron, y persiste tras el refresh de la lista', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    vi.mocked(api.deleteRun).mockResolvedValue({
      detail: 'partial',
      errors: { control: 'no encontrado' },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText('r_2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))

    // El `finally` de handleDelete dispara un refresh() de la lista (listRuns) que
    // resuelve exitosamente. Ese refresh no debe borrar el mensaje de borrado parcial:
    // esperamos a que el refresh termine de asentarse y volvemos a comprobar que el
    // alert sigue presente (regresión del bug: refresh() pisaba `error` con `null`).
    await waitFor(() => expect(vi.mocked(api.listRuns).mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('control'))
  })

  it('el encabezado muestra el total y, si hay alguna en curso, el conteo en vivo', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r1', status: 'running', model: 'gdino' } as any,
      { run_id: 'r2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('2 en total')).toBeTruthy())
    expect(screen.getByText('1 en curso')).toBeTruthy()
  })

  it('sin corridas en curso, no muestra el fragmento "en curso"', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'r1', status: 'succeeded', model: 'gdino' } as any])
    renderPage()
    await waitFor(() => expect(screen.getByText('1 en total')).toBeTruthy())
    expect(screen.queryByText(/en curso/)).toBeNull()
  })

  it('la busqueda filtra por nombre e identificador', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', name: 'Ronda nocturna', status: 'succeeded', model: 'gdino' } as any,
      { run_id: 'run_b', name: 'Barrido diurno', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('Ronda nocturna')).toBeTruthy())
    fireEvent.change(screen.getByLabelText('Buscar corridas'), { target: { value: 'nocturna' } })
    expect(screen.queryByText('Barrido diurno')).toBeNull()
    expect(screen.getByText('Ronda nocturna')).toBeTruthy()
  })

  it('el segmentado filtra por estado y el contador N de M se actualiza', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'running', model: 'gdino' } as any,
      { run_id: 'run_b', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('2 de 2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'En curso' }))
    expect(screen.getByText('1 de 2')).toBeTruthy()
  })

  it('clic en el encabezado de una columna numerica ordena, segundo clic invierte', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino', fps_effective: 1.5 } as any,
      { run_id: 'run_b', status: 'succeeded', model: 'gdino', fps_effective: 5.5 } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    let rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('run_a') // ascendente: menor primero
    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('run_b') // descendente: mayor primero
  })

  it('la fuente se muestra traducida', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino', source_type: 'oak_d' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('Cámara OAK-D Pro')).toBeTruthy())
  })

  it('borrar pide confirmacion en linea antes de llamar a la API', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'run_a', status: 'succeeded', model: 'gdino' } as any])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    expect(api.deleteRun).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('run_a'))
  })

  it('lista vacia por falta de datos muestra un texto distinto que vacia por filtro', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/todavía no lanzaste ninguna corrida/i)).toBeTruthy())
  })

  it('las corridas sin metricas (no hidratadas) quedan siempre al final al ordenar, en ambas direcciones', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_sin_metricas', status: 'succeeded' } as any, // sin fps_effective: no hidratada
      { run_id: 'run_baja', status: 'succeeded', model: 'gdino', fps_effective: 1.5 } as any,
      { run_id: 'run_alta', status: 'succeeded', model: 'gdino', fps_effective: 5.5 } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_baja')).toBeTruthy())

    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    let rows = screen.getAllByRole('row').slice(1)
    expect(rows[rows.length - 1].textContent).toContain('run_sin_metricas') // ascendente: al final

    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    rows = screen.getAllByRole('row').slice(1)
    expect(rows[rows.length - 1].textContent).toContain('run_sin_metricas') // descendente: tambien al final
  })

  it('nota al pie "N corridas sin metricas cargadas" solo aparece si alguna fila visible no esta hidratada', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded' } as any,
      { run_id: 'run_b', status: 'succeeded', model: 'gdino', fps_effective: 2 } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('1 corrida sin métricas cargadas.')).toBeTruthy())
  })

  it('sin filas sin hidratar, no muestra la nota al pie', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino', fps_effective: 2 } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    expect(screen.queryByText(/sin métricas cargadas/)).toBeNull()
  })

  it('sin nombre ni started_at, la fecha se deriva del run_id', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_20260723_143012_dbe_grounding_dino_abc123', status: 'succeeded' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText(/hace \d+ [dh]|recién/)).toBeTruthy())
  })

  it('confirmar borrado y despues buscar, cierra la confirmacion pendiente', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Buscar corridas'), { target: { value: 'x' } })
    expect(screen.queryByText('¿Borrar?')).toBeNull()
  })

  it('confirmar borrado y despues cambiar el segmentado, cierra la confirmacion pendiente', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Todas' }))
    expect(screen.queryByText('¿Borrar?')).toBeNull()
  })
})
