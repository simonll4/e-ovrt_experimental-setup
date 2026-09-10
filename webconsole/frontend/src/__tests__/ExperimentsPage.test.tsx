import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, fireEvent } from '../test-utils'
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
    const button = screen.getByRole('button', { name: 'Ejecutar' }) as HTMLButtonElement
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
      // El glosario traduce los nombres de plano: el operador nunca lee
      // "control-plane" en pantalla, y menos cuando algo se cayó.
      expect(screen.getByText(/el motor de reglas no responde/)).toBeTruthy(),
    )
    const button = screen.getByRole('button', { name: 'Ejecutar' }) as HTMLButtonElement
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
    const button = screen.getByRole('button', { name: 'Ejecutar' }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(false))
    fireEvent.click(button)
    await waitFor(() => expect(screen.getByText(/Plataforma no lista/)).toBeTruthy())
  })

  // Antes esto protegía al desplegable global de mostrar un manifiesto y lanzar
  // otro mientras la recarga estaba en vuelo. Con el lanzamiento por fila esa
  // divergencia ya no puede existir —la fila ES el manifiesto—, así que lo que
  // queda por comprobar es que derivar recarga la lista y que cada botón lanza
  // el suyo, incluso con varias filas en pantalla.
  it('derivar recarga los manifiestos, y cada fila lanza el suyo', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([
      { slug: 'd1', experiment_id: null } as any,
      { slug: 'd2', experiment_id: null } as any,
    ])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.runExperiment).mockResolvedValue({ experiment_id: 'exp_9' })
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)

    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    fireEvent.click(screen.getAllByRole('button', { name: 'Partir de este' })[0])
    fireEvent.click(screen.getByText('fake-derive-done'))
    await waitFor(() => expect(vi.mocked(api.getExperimentManifests)).toHaveBeenCalledTimes(2))

    // El segundo botón lanza el segundo manifiesto, no el preseleccionado.
    fireEvent.click(screen.getAllByRole('button', { name: 'Ejecutar' })[1])
    await waitFor(() => expect(vi.mocked(api.runExperiment)).toHaveBeenCalled())
    expect(vi.mocked(api.runExperiment)).toHaveBeenCalledWith({ slug: 'd2' })
  })

  it('muestra 409 con el experimento activo', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'd1' } as any])
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    const err = new api.ApiError(409, { active_experiment_id: 'exp_prev' })
    vi.mocked(api.runExperiment).mockRejectedValue(err)
    render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)
    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    const button = screen.getByRole('button', { name: 'Ejecutar' }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(false))
    fireEvent.click(button)
    await waitFor(() => expect(screen.getByText(/exp_prev/)).toBeTruthy())
  })
})
