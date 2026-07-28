import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ExperimentsPage from '../pages/ExperimentsPage'
import * as api from '../api'
import type { PreflightStatus } from '../types'

// A diferencia de ExperimentsPage.test.tsx, acá NO se stubea
// DeriveExperimentForm: el bug a cubrir (reprecarga al cambiar la fuente) vive
// en el ida-y-vuelta real entre la página y el formulario.
vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperimentManifests: vi.fn(),
  getCurrentExperiment: vi.fn(),
  getPreflight: vi.fn(),
  runExperiment: vi.fn(),
  getDeriveDefaults: vi.fn(),
  listCameras: vi.fn(),
  getPromptSets: vi.fn(),
  deriveExperimentManifest: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listCameras).mockResolvedValue([])
  vi.mocked(api.getPromptSets).mockResolvedValue([])
})
afterEach(() => cleanup())

const PREFLIGHT_OK: PreflightStatus = {
  ready: true,
  blockers: [],
  media: { service_url: 'http://m', healthy: true, ready: true, model: null },
  control: { service_url: 'http://c', healthy: true, ready: true },
}

const MANIFESTS = [
  { slug: 'd1', experiment_id: null },
  { slug: 'd2', experiment_id: null },
] as any

describe('ExperimentsPage - crear nuevo experimento (/experiments/new)', () => {
  it('abre el formulario con un selector "basado en" precargado con el primer manifiesto', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue(MANIFESTS)
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({} as any)

    render(
      <MemoryRouter initialEntries={['/experiments/new']}>
        <ExperimentsPage />
      </MemoryRouter>,
    )

    // El desplegable es propio: se lo encuentra por su nombre accesible y lo
    // elegido se lee del texto del control.
    await waitFor(() => expect(screen.getByRole('button', { name: 'Basado en' })).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Basado en' }).textContent).toContain('d1')
    await waitFor(() => expect(api.getDeriveDefaults).toHaveBeenCalledWith('d1'))
  })

  it('al cambiar la fuente en el selector, vuelve a pedir los defaults y reprecarga los campos (bug central)', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue(MANIFESTS)
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.getDeriveDefaults).mockImplementation(async (slug: string) =>
      slug === 'd1' ? ({ warmup_frames: 10 } as any) : ({ warmup_frames: 99 } as any),
    )

    render(
      <MemoryRouter initialEntries={['/experiments/new']}>
        <ExperimentsPage />
      </MemoryRouter>,
    )

    await waitFor(() =>
      expect((screen.getByLabelText('warmup_frames') as HTMLInputElement).value).toBe('10'),
    )

    // Abrir el desplegable y elegir d2 (dos clics, como haría el operador).
    fireEvent.click(screen.getByRole('button', { name: 'Basado en' }))
    fireEvent.click(screen.getByRole('option', { name: 'd2' }))

    await waitFor(() => expect(api.getDeriveDefaults).toHaveBeenCalledWith('d2'))
    await waitFor(() =>
      expect((screen.getByLabelText('warmup_frames') as HTMLInputElement).value).toBe('99'),
    )
  })

  it('en modo nuevo la card dice "Nuevo experimento" y el botón "Crear" (no "Derivar de...")', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue(MANIFESTS)
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({} as any)

    render(
      <MemoryRouter initialEntries={['/experiments/new']}>
        <ExperimentsPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByRole('button', { name: 'Basado en' })).toBeTruthy())
    // Título de la card del formulario: nada de "Derivar de <source>".
    expect(screen.getByText('Nuevo experimento')).toBeTruthy()
    expect(screen.queryByText(/^Derivar de/)).toBeNull()
    // El botón de submit del formulario es "Crear", único en la página: los
    // "Derivar" que sigan viéndose son los de la tabla de filas (no tocados).
    expect(screen.getByRole('button', { name: 'Crear' })).toBeTruthy()
  })

  it('el "Derivar" de una fila NO muestra el selector "basado en" (fuente fija, igual que antes)', async () => {
    vi.mocked(api.getExperimentManifests).mockResolvedValue(MANIFESTS)
    vi.mocked(api.getCurrentExperiment).mockResolvedValue(null)
    vi.mocked(api.getPreflight).mockResolvedValue(PREFLIGHT_OK)
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({} as any)

    render(
      <MemoryRouter initialEntries={['/experiments']}>
        <ExperimentsPage />
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getAllByText('d1').length).toBeGreaterThan(0))
    fireEvent.click(screen.getAllByRole('button', { name: 'Derivar' })[0])

    await waitFor(() => expect(screen.getByText('Derivar de d1')).toBeTruthy())
    expect(screen.queryByRole('button', { name: 'Basado en' })).toBeNull()
    // El modo "derivar" no cambia: sigue habiendo botones "Derivar" (uno por
    // fila + el de submit del formulario) y ninguno "Crear".
    expect(screen.getAllByRole('button', { name: 'Derivar' }).length).toBeGreaterThan(0)
    expect(screen.queryByText('Nuevo experimento')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Crear' })).toBeNull()
  })
})
