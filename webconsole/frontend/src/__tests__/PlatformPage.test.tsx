import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PlatformPage from '../pages/PlatformPage'
import { activateInstance, getInstances } from '../api'
import type { PlatformInstance } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getInstances: vi.fn(),
  activateInstance: vi.fn(),
  stopPlatform: vi.fn(),
}))

const FLEET: PlatformInstance[] = [
  { name: 'mp-mock', model_ref: 'mock', state: 'exited', ready: false, is_target: false },
  { name: 'mp-gdino-tiny', model_ref: 'grounding-dino/gdino-tiny', state: 'absent', ready: false, is_target: false },
]

const FLEET_ACTIVE: PlatformInstance[] = [
  { ...FLEET[0], state: 'running', ready: true, is_target: true },
  FLEET[1],
]

beforeEach(() => vi.clearAllMocks())
// Sin esto el DOM de un test sigue montado en el siguiente, y las consultas
// encuentran los nodos de los dos.
afterEach(() => cleanup())

/** La tabla de instancias. Hace falta acotar porque el encabezado de instancia
 *  activa nombra la misma instancia y repite su chip de estado. */
const tabla = () => screen.getByRole('table')

describe('PlatformPage', () => {
  it('lista el fleet y activa una instancia', async () => {
    vi.mocked(getInstances)
      .mockResolvedValueOnce(FLEET)         // carga inicial
      .mockResolvedValue(FLEET_ACTIVE)      // refresh post-activate
    vi.mocked(activateInstance).mockResolvedValue({ target: 'mp-mock', model_ref: 'mock' })

    render(<PlatformPage />)
    await waitFor(() => expect(within(tabla()).getByText('mp-mock')).toBeTruthy())

    fireEvent.click(screen.getAllByText('Activar')[0])

    await waitFor(() => expect(activateInstance).toHaveBeenCalledWith('mp-mock'))
    // "TARGET" era jerga: la instancia activa y lista se llama "Operativa".
    await waitFor(() => expect(within(tabla()).getByText('Operativa')).toBeTruthy())
  })

  it('409 muestra el mensaje de run activo', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET)
    const { ApiError } = await import('../api')
    vi.mocked(activateInstance).mockRejectedValue(
      new ApiError(409, { detail: 'Hay un run activo en el target actual', run_id: 'run_x' }),
    )
    render(<PlatformPage />)
    await waitFor(() => expect(within(tabla()).getByText('mp-mock')).toBeTruthy())
    fireEvent.click(screen.getAllByText('Activar')[0])
    await waitFor(() => expect(screen.getByText(/run activo/i)).toBeTruthy())
  })

  // §10.1 y §10.2: antes la pantalla arrancaba directo en la tabla y para saber
  // cuál instancia estaba activa había que leer la columna Estado fila por fila.
  it('destaca la instancia activa en el encabezado, con su modelo y el botón de apagado', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET_ACTIVE)
    render(<PlatformPage />)
    expect(await screen.findByText('Instancia activa')).toBeTruthy()
    const destacada = screen.getByText('Instancia activa').closest('section') as HTMLElement
    expect(within(destacada).getByText('mp-mock')).toBeTruthy()
    expect(within(destacada).getByText('mock')).toBeTruthy()
    expect(within(destacada).getByText('Operativa')).toBeTruthy()
    expect(within(destacada).getByRole('button', { name: /Apagar/ })).toBeTruthy()
  })

  it('sin ninguna instancia activa lo dice, en vez de dejar el encabezado vacío', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET)
    render(<PlatformPage />)
    expect(await screen.findByText(/Ninguna instancia está activa/)).toBeTruthy()
  })

  it('muestra los dos motores con su estado y su puerto', async () => {
    vi.mocked(getInstances).mockResolvedValue(FLEET_ACTIVE)
    render(<PlatformPage />)
    expect(await screen.findByText('Motor de detección')).toBeTruthy()
    expect(screen.getByText('Motor de reglas')).toBeTruthy()
  })

  it('501 muestra el hint de orquestación no habilitada', async () => {
    const { ApiError } = await import('../api')
    vi.mocked(getInstances).mockRejectedValue(new ApiError(501, { detail: 'x' }))
    render(<PlatformPage />)
    await waitFor(() => expect(screen.getByText(/orquestación no está habilitada/i)).toBeTruthy())
  })
})
