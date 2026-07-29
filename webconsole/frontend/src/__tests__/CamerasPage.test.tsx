import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CamerasPage from '../pages/CamerasPage'

const mocks = vi.hoisted(() => ({
  listCameras: vi.fn(),
  getPreview: vi.fn(),
  listPromptSets: vi.fn(),
  getPromptSetDetail: vi.fn(),
  startPreview: vi.fn(),
  stopPreview: vi.fn(),
  deleteCamera: vi.fn(),
  usePreviewStream: vi.fn(),
}))

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  ...mocks,
}))

vi.mock('../preview', () => ({
  usePreviewStream: mocks.usePreviewStream,
}))

beforeEach(() => {
  vi.clearAllMocks()
  mocks.listCameras.mockResolvedValue([
    { id: 'oak_d_lab', name: 'OAK-D laboratorio', plugin: 'oak_d', config: {} },
  ])
  mocks.getPreview.mockResolvedValue({ status: 'idle', preview_id: null, mode: null, error: null })
  mocks.listPromptSets.mockResolvedValue([])
  mocks.stopPreview.mockResolvedValue(undefined)
  mocks.deleteCamera.mockResolvedValue(undefined)
  mocks.usePreviewStream.mockReturnValue({
    connected: false, frameUrl: null, header: null, fps: 0, finalState: null,
  })
})

afterEach(() => cleanup())

function renderPage() {
  return render(
    <MemoryRouter>
      <CamerasPage />
    </MemoryRouter>,
  )
}

describe('CamerasPage', () => {
  it('lista los presets de cámara', async () => {
    renderPage()
    expect(await screen.findByText('OAK-D laboratorio')).toBeTruthy()
  })

  it('muestra empty state sin stream', async () => {
    renderPage()
    await waitFor(() => expect(mocks.getPreview).toHaveBeenCalled())
    expect(screen.getByText(/sin señal/i)).toBeTruthy()
  })

  it('muestra banner y deshabilita conectar ante 409 run_active', async () => {
    const { ApiError } = await import('../api')
    mocks.startPreview.mockRejectedValue(
      new ApiError(409, { detail: 'ocupado', reason: 'run_active', active_run_id: 'run_7' }),
    )
    renderPage()
    const conectar = await screen.findByRole('button', { name: /probar/i })
    conectar.click()
    expect(await screen.findByText(/corrida en curso/i)).toBeTruthy()
    expect(screen.getByText(/run_7/)).toBeTruthy()
  })

  it('muestra banner ante 409 preview_active (sesión de preview ya activa)', async () => {
    const { ApiError } = await import('../api')
    mocks.startPreview.mockRejectedValue(
      new ApiError(409, { detail: 'ocupado', reason: 'preview_active' }),
    )
    renderPage()
    const conectar = await screen.findByRole('button', { name: /probar/i })
    fireEvent.click(conectar)
    expect(await screen.findByText(/ya hay una prueba de cámara activa/i)).toBeTruthy()
  })

  it('muestra un banner de error cuando la fuente falla (finalState del WS)', async () => {
    mocks.usePreviewStream.mockReturnValue({
      connected: false,
      frameUrl: null,
      header: null,
      fps: 0,
      finalState: { status: 'error', error: 'RTSP caída' },
    })
    renderPage()
    expect(await screen.findByText(/RTSP caída/)).toBeTruthy()
  })

  it('activa por defecto las clases sin enabled_by_default declarado en el YAML', async () => {
    mocks.listPromptSets.mockResolvedValue([
      { id: 'cr01_cr02_v2_short', status: 'active', n_classes: 2, n_phrases: 4 },
    ])
    mocks.getPromptSetDetail.mockResolvedValue({
      id: 'cr01_cr02_v2_short',
      classes: [
        { id: 'person', phrasings: { gdino: ['person'] } },
        { id: 'helmet', phrasings: { gdino: ['helmet'] } },
      ],
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Con detecciones' }))
    const select = await screen.findByRole('combobox', { name: /conjunto de prompts/i })
    fireEvent.change(select, { target: { value: 'cr01_cr02_v2_short' } })
    const personCheckbox = await screen.findByRole('checkbox', { name: /person/i })
    const helmetCheckbox = await screen.findByRole('checkbox', { name: /helmet/i })
    expect((personCheckbox as HTMLInputElement).checked).toBeTruthy()
    expect((helmetCheckbox as HTMLInputElement).checked).toBeTruthy()
  })

  it('deshabilita Probar en modo detect sin conjunto de prompts cargado', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Con detecciones' }))
    const conectar = await screen.findByRole('button', { name: /probar/i })
    expect((conectar as HTMLButtonElement).disabled).toBeTruthy()
  })

  // §11.1: sin ninguna cámara la pantalla no es una línea gris, sino una
  // explicación de para qué sirve tenerlas y el botón para crear la primera.
  it('sin cámaras muestra el estado vacío grande y ofrece crear la primera', async () => {
    mocks.listCameras.mockResolvedValue([])
    renderPage()
    expect(await screen.findByText('Todavía no guardaste ninguna cámara')).toBeTruthy()
    expect(screen.getByText(/verificar el encuadre antes de lanzar una corrida/i)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Agregar la primera cámara' })).toBeTruthy()
    // Con el estado vacío ocupando la pantalla, el botón del encabezado sobra.
    expect(screen.queryByRole('button', { name: 'Agregar cámara' })).toBeNull()
  })

  it('con cámaras, el alta se ofrece desde el encabezado', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Agregar cámara' })).toBeTruthy()
    expect(screen.queryByText('Todavía no guardaste ninguna cámara')).toBeNull()
  })

  // §11.3: el `window.confirm()` nativo corta el hilo de la pantalla con un
  // diálogo del sistema operativo, que además no se puede estilar.
  it('borrar pide confirmación en línea, no un diálogo del navegador', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /Eliminar OAK-D laboratorio/ }))
    expect(await screen.findByRole('button', { name: 'Sí, borrar' })).toBeTruthy()
    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('cancelar la confirmación no borra nada', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /Eliminar OAK-D laboratorio/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'No' }))
    expect(mocks.deleteCamera).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /Eliminar OAK-D laboratorio/ })).toBeTruthy()
  })

  it('confirmar borra la cámara y refresca el listado', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /Eliminar OAK-D laboratorio/ }))
    mocks.listCameras.mockResolvedValue([])
    fireEvent.click(await screen.findByRole('button', { name: 'Sí, borrar' }))
    await waitFor(() => expect(mocks.deleteCamera).toHaveBeenCalledWith('oak_d_lab'))
    await waitFor(() =>
      expect(screen.getByText('Todavía no guardaste ninguna cámara')).toBeTruthy(),
    )
  })

  it('muestra el tipo legible de la cámara y su dirección', async () => {
    mocks.listCameras.mockResolvedValue([
      { id: 'rtsp_sur', name: 'Portón sur', plugin: 'rtsp', config: { url: 'rtsp://10.0.0.5/s' } },
    ])
    renderPage()
    expect(await screen.findByText(/Cámara RTSP · rtsp:\/\/10\.0\.0\.5\/s/)).toBeTruthy()
    // El identificador crudo del plugin no es texto de interfaz.
    expect(screen.queryByText(/^rtsp$/)).toBeNull()
  })

  it('una cámara sin dirección lo dice en vez de dejar el renglón cortado', async () => {
    mocks.listCameras.mockResolvedValue([
      { id: 'oak', name: 'OAK sin IP', plugin: 'oak_d', config: {} },
    ])
    renderPage()
    expect(await screen.findByText(/Cámara OAK-D Pro · sin dirección/)).toBeTruthy()
  })
})
