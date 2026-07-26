import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ExperimentsPage from '../pages/ExperimentsPage'
import * as api from '../api'
import type { PreflightStatus } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperimentManifests: vi.fn(),
  getCurrentExperiment: vi.fn(),
  getPreflight: vi.fn(),
  runExperiment: vi.fn(),
}))
// El formulario de derivación se stubea: acá interesa sólo el orden de
// recarga/selección que hace la página cuando el derive termina.
vi.mock('../components/DeriveExperimentForm', () => ({
  DeriveExperimentForm: ({ onDone }: { onDone: (slug: string) => void }) => (
    <button onClick={() => onDone('nuevo')}>fake-derive-done</button>
  ),
}))
beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const PREFLIGHT_OK: PreflightStatus = {
  ready: true,
  blockers: [],
  media: { service_url: 'http://m', healthy: true, ready: true, model: null },
  control: { service_url: 'http://c', healthy: true, ready: true },
}

const PREFLIGHT_CONTROL_DOWN: PreflightStatus = {
  ready: false,
  blockers: ['el control-plane no responde'],
  media: { service_url: 'http://m', healthy: true, ready: true, model: null },
  control: { service_url: 'http://c', healthy: false, ready: false },
}

describe('ExperimentsPage', () => {
  it('lista manifiestos y dispara un experimento con preflight verde', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1', experiment_id: null } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_9' })
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    const button = screen.getByRole('button', { name: /lanzar/i }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(false))
    fireEvent.click(button)
    await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
    expect(vi.mocked(api.runExperiment)).toHaveBeenCalledWith({ slug: 'd1' })
  })

  it('bloquea el lanzamiento con el motivo cuando el control-plane está caído', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_CONTROL_DOWN)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    await waitFor(() =>
      expect(screen.getByText(/el control-plane no responde/)).toBeTruthy(),
    )
    const button = screen.getByRole('button', { name: /lanzar/i }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
    expect(vi.mocked(api.runExperiment)).not.toHaveBeenCalled()
  })

  it('muestra el detalle del 503 si el gate del BFF rechaza el lanzamiento', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    const err = new api.ApiError(503, { detail: 'Plataforma no lista: el control-plane no responde' })
    vi.mocked(api.runExperiment).mockRejectedValue(err)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    const button = screen.getByRole('button', { name: /lanzar/i }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(false))
    fireEvent.click(button)
    await waitFor(() => expect(screen.getByText(/Plataforma no lista/)).toBeTruthy())
  })

  it('espera la recarga de manifiestos antes de seleccionar el slug derivado', async () => {
    // Sin esperar la recarga, el <select> queda por un instante con un value sin
    // <option> que lo matchee y el browser muestra la primera opción — justo
    // cuando el operador quiere confirmar qué va a lanzar.
    let resolveReload: (rows: any[]) => void = () => {}
    vi.mocked(api.getExperimentManifests)
      .mockResolvedValueOnce([{ slug: 'd1', experiment_id: null } as any])
      .mockReturnValueOnce(new Promise((res) => { resolveReload = res as any }) as any)
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_9' })
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    fireEvent.click(screen.getByRole('button', { name: 'Derivar' }))
    fireEvent.click(screen.getByText('fake-derive-done'))

    const select = () => screen.getByRole('combobox') as HTMLSelectElement
    await waitFor(() => expect(vi.mocked(api.getExperimentManifests)).toHaveBeenCalledTimes(2))

    // Mientras la recarga está en vuelo no existe la <option> del slug nuevo, así
    // que el select MUESTRA 'd1' (el browser cae en la primera opción). Lo que se
    // lanza tiene que ser eso mismo: si el estado ya fuera 'nuevo', el operador
    // vería una cosa y lanzaría otra.
    expect(screen.queryByRole('option', { name: 'nuevo' })).toBeNull()
    expect(select().value).toBe('d1')
    fireEvent.click(screen.getByRole('button', { name: /lanzar/i }))
    await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
    expect(vi.mocked(api.runExperiment)).toHaveBeenCalledWith({ slug: select().value })

    resolveReload([
      { slug: 'd1', experiment_id: null } as any,
      { slug: 'nuevo', experiment_id: null } as any,
    ])
    await waitFor(() => expect(select().value).toBe('nuevo'))
  })

  it('el slug de un manifiesto en la tabla se muestra en monoespaciada', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1', experiment_id: null } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => {
      const cells = screen.getAllByText('d1')
      expect(cells.some((el) => el.className.includes('eo-mono'))).toBe(true)
    })
  })

  it('muestra 409 con el experimento activo', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    const err = new api.ApiError(409, { active_experiment_id: 'exp_prev' })
    vi.mocked(api.runExperiment).mockRejectedValue(err)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    const button = screen.getByRole('button', { name: /lanzar/i }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(false))
    fireEvent.click(button)
    await waitFor(() => expect(screen.getByText(/exp_prev/)).toBeTruthy())
  })
})
