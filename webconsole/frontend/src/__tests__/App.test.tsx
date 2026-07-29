import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '../test-utils'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue(null),
  listRuns: vi.fn().mockResolvedValue([]),
  getExperimentManifests: vi.fn().mockResolvedValue([]),
  getCurrentExperiment: vi.fn().mockResolvedValue(null),
  getPreflight: vi.fn().mockResolvedValue(null),
  getExperiment: vi.fn().mockRejectedValue(new Error('no debería llamarse')),
}))

// Se stubea para no depender de cámaras/prompt sets reales: acá sólo interesa
// qué página monta la ruta, no el contenido del formulario.
vi.mock('../components/DeriveExperimentForm', () => ({
  DeriveExperimentForm: () => <div>fake-derive-form</div>,
}))

afterEach(() => cleanup())

describe('App', () => {
  // La marca aparece dos veces en el DOM: en la barra lateral y en la superior.
  // No se pisan porque cada una vive en un tamaño de pantalla —el CSS esconde la
  // superior por encima de 760 px—, pero jsdom no aplica media queries, así que
  // la consulta se acota a la lateral.
  it('renderiza el título de la consola', () => {
    render(<MemoryRouter><App /></MemoryRouter>)
    const lateral = screen.getByRole('complementary', { name: 'Navegación principal' })
    expect(within(lateral).getByText('E-OVRT')).toBeTruthy()
  })

  it('/experiments/new monta ExperimentsPage, NO ExperimentDetailPage buscando un experimento "new" (trampa de orden de rutas)', async () => {
    render(<MemoryRouter initialEntries={['/experiments/new']}><App /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Experimentos')).toBeTruthy())
    expect(vi.mocked(api.getExperiment)).not.toHaveBeenCalled()
  })
})
