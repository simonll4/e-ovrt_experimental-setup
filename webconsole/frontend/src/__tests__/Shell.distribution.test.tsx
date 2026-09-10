import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, waitFor } from '../test-utils'
import Shell from '../components/Shell'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue({ healthy: true, ready: true, model: null }),
  getPreflight: vi.fn(),
  listRunsPaged: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getExperimentManifests: vi.fn().mockResolvedValue([]),
  listPromptSets: vi.fn().mockResolvedValue([]),
}))

afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('Salud del distribuidor en la barra lateral', () => {
  it.each([true, false])('informa healthy=%s y conserva los dos motores', async (healthy) => {
    vi.mocked(api.getPreflight).mockResolvedValue({
      ready: true, blockers: [],
      media: { service_url: 'media', healthy: true, ready: true },
      control: { service_url: 'control', healthy: true, ready: true },
      distribution: { service_url: 'distribution', healthy, ready: healthy },
    })
    const { container } = render(<MemoryRouter><Shell>contenido</Shell></MemoryRouter>)
    const title = `Distribución de alertas — ${healthy ? 'operativo' : 'sin respuesta'}`
    await waitFor(() => expect(screen.getByTitle(title)).toBeTruthy())
    expect(container.querySelectorAll('.eo-service')).toHaveLength(3)
    expect(screen.getByText(':8082')).toBeTruthy()
    expect(screen.getByTitle('Motor de detección — operativo')).toBeTruthy()
    expect(screen.getByTitle('Motor de reglas — operativo')).toBeTruthy()
    expect(screen.getByTitle(title).querySelector('.eo-service__dot')).toHaveProperty(
      'style.background', healthy ? 'var(--ok)' : 'var(--er)',
    )
  })

  it('informa caída si el BFF rechaza la consulta', async () => {
    vi.mocked(api.getPreflight).mockRejectedValue(new Error('BFF sin respuesta'))
    render(<MemoryRouter><Shell>contenido</Shell></MemoryRouter>)
    await waitFor(() => expect(screen.getByTitle('Distribución de alertas — sin respuesta')).toBeTruthy())
  })
})
