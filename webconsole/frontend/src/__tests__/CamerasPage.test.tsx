import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    const conectar = await screen.findByRole('button', { name: /conectar/i })
    conectar.click()
    expect(await screen.findByText(/run en ejecución/i)).toBeTruthy()
    expect(screen.getByText(/run_7/)).toBeTruthy()
  })

  it('muestra banner ante 409 preview_active (sesión de preview ya activa)', async () => {
    const { ApiError } = await import('../api')
    mocks.startPreview.mockRejectedValue(
      new ApiError(409, { detail: 'ocupado', reason: 'preview_active' }),
    )
    renderPage()
    const conectar = await screen.findByRole('button', { name: /conectar/i })
    fireEvent.click(conectar)
    expect(await screen.findByText(/ya hay una sesión de preview activa/i)).toBeTruthy()
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
    fireEvent.click(await screen.findByLabelText(/detección \(desmarcado/i))
    const select = await screen.findByRole('combobox', { name: /prompt set/i })
    fireEvent.change(select, { target: { value: 'cr01_cr02_v2_short' } })
    const personCheckbox = await screen.findByRole('checkbox', { name: /person/i })
    const helmetCheckbox = await screen.findByRole('checkbox', { name: /helmet/i })
    expect((personCheckbox as HTMLInputElement).checked).toBeTruthy()
    expect((helmetCheckbox as HTMLInputElement).checked).toBeTruthy()
  })

  it('deshabilita Conectar en modo detect sin prompt set cargado', async () => {
    renderPage()
    fireEvent.click(await screen.findByLabelText(/detección \(desmarcado/i))
    const conectar = await screen.findByRole('button', { name: /conectar/i })
    expect((conectar as HTMLButtonElement).disabled).toBeTruthy()
  })

  it('"Nuevo preset" es el primitivo Button', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo preset' }).className).toContain('eo-btn'))
  })
})
