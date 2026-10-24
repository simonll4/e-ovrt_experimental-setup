import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import * as api from '../api'
import CamerasPage from '../pages/CamerasPage'
import CameraPresetForm from '../components/CameraPresetForm'
import PromptSetEditor from '../components/PromptSetEditor'
import { DeriveExperimentForm } from '../components/DeriveExperimentForm'
import type { CameraPreset, PromptSetDetail } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listCameras: vi.fn(),
  createCamera: vi.fn(),
  updateCamera: vi.fn(),
  deleteCamera: vi.fn(),
  getPreview: vi.fn(),
  stopPreview: vi.fn(),
  startPreview: vi.fn(),
  listPromptSets: vi.fn(),
  getRecording: vi.fn(),
  nextTake: vi.fn(),
  getTarget: vi.fn(),
  updatePromptSet: vi.fn(),
  createPromptSet: vi.fn(),
  requestFreeze: vi.fn(),
  confirmFreeze: vi.fn(),
  deriveExperimentManifest: vi.fn(),
  getDeriveDefaults: vi.fn(),
  getPromptSets: vi.fn(),
}))

const A: CameraPreset = { id: 'cam_a', name: 'Portón', plugin: 'rtsp', config: { url: 'rtsp://a/s' } }
// Un plugin que esta consola no conoce y una configuración con claves anidadas
// desconocidas: tienen que volver al servidor tal cual.
const B: CameraPreset = {
  id: 'cam_b', name: 'Laboratorio', plugin: 'mi_plugin_nuevo',
  config: { url: 'rtsp://b/s', extra: { anidado: [1, { profundo: true }] }, flag: null },
}

beforeEach(() => {
  vi.mocked(api.listCameras).mockResolvedValue([A, B])
  vi.mocked(api.getPreview).mockResolvedValue({ status: 'idle', preview_id: null, mode: null, error: null } as never)
  vi.mocked(api.stopPreview).mockResolvedValue(undefined)
  vi.mocked(api.listPromptSets).mockResolvedValue([])
  vi.mocked(api.getRecording).mockResolvedValue({ state: 'idle' } as never)
  vi.mocked(api.nextTake).mockResolvedValue({ basename: 'P1-a-take1' } as never)
  vi.mocked(api.getTarget).mockResolvedValue({ service_url: 'x', healthy: true, ready: true, model: null } as never)
  vi.mocked(api.updateCamera).mockResolvedValue(undefined as never)
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('Cámaras: identidad del formulario', () => {
  it('pasar de A a B con cambios sin guardar pregunta, y el PUT de B nunca lleva los campos de A', async () => {
    render(<MemoryRouter><CamerasPage /></MemoryRouter>)
    const filaA = (await screen.findByText('Portón')).closest('.eo-lrow') as HTMLElement
    fireEvent.click(within(filaA).getByRole('button', { name: 'Editar' }))
    const nombre = await screen.findByLabelText(/^Nombre/)
    fireEvent.change(nombre, { target: { value: 'Portón editado' } })
    expect(screen.getByText('Cambios sin guardar')).toBeTruthy()

    const filaB = screen.getByText('Laboratorio').closest('.eo-lrow') as HTMLElement
    fireEvent.click(within(filaB).getByRole('button', { name: 'Editar' }))
    // No cambia de cámara sin preguntar.
    expect(await screen.findByText(/Hay cambios sin guardar en la cámara que estás editando/)).toBeTruthy()
    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe('Portón editado')
    fireEvent.click(screen.getByRole('button', { name: 'Descartar cambios' }))

    await waitFor(() => expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe('Laboratorio'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(api.updateCamera).toHaveBeenCalledTimes(1))
    const [id, enviado] = vi.mocked(api.updateCamera).mock.calls[0]
    expect(id).toBe('cam_b')
    // Mismo objeto que llegó: plugin desconocido y claves anidadas intactas.
    expect(enviado).toEqual(B)
  })

  it('"Seguir editando" conserva lo escrito y no cambia de cámara', async () => {
    render(<MemoryRouter><CamerasPage /></MemoryRouter>)
    const filaA = (await screen.findByText('Portón')).closest('.eo-lrow') as HTMLElement
    fireEvent.click(within(filaA).getByRole('button', { name: 'Editar' }))
    fireEvent.change(await screen.findByLabelText(/^Nombre/), { target: { value: 'otro' } })
    const filaB = screen.getByText('Laboratorio').closest('.eo-lrow') as HTMLElement
    fireEvent.click(within(filaB).getByRole('button', { name: 'Editar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Seguir editando' }))
    expect((screen.getByLabelText(/^Nombre/) as HTMLInputElement).value).toBe('otro')
    expect(screen.getByRole('heading', { name: /Editar cam_a/ })).toBeTruthy()
  })
})

describe('Cámaras: validación y envío único', () => {
  it('un doble click en Guardar manda una sola escritura', async () => {
    let resolver!: () => void
    vi.mocked(api.createCamera).mockImplementation(() => new Promise((r) => { resolver = () => r(undefined as never) }))
    const onSaved = vi.fn()
    render(<CameraPresetForm initial={null} onSaved={onSaved} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/^Identificador/), { target: { value: 'nueva_cam' } })
    const guardar = screen.getByRole('button', { name: 'Guardar' })
    fireEvent.click(guardar)
    fireEvent.click(guardar)
    expect(api.createCamera).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Guardando…' })).toBeTruthy()
    resolver()
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
  })

  it('un rechazo del servidor conserva lo escrito', async () => {
    vi.mocked(api.createCamera).mockRejectedValue(new Error('Ya existe'))
    render(<CameraPresetForm initial={null} onSaved={() => {}} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/^Identificador/), { target: { value: 'nueva_cam' } })
    fireEvent.change(screen.getByLabelText(/^Configuración/), { target: { value: '{"url":"rtsp://x"}' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(await screen.findByText('Ya existe')).toBeTruthy()
    expect((screen.getByLabelText(/^Identificador/) as HTMLInputElement).value).toBe('nueva_cam')
    expect((screen.getByLabelText(/^Configuración/) as HTMLTextAreaElement).value).toBe('{"url":"rtsp://x"}')
  })

  it('el identificador sigue el contrato del almacén y la configuración tiene que ser un objeto', async () => {
    render(<CameraPresetForm initial={null} onSaved={() => {}} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/^Identificador/), { target: { value: 'Con Espacios' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(await screen.findByText(/Sólo minúsculas, números, guion y guion bajo/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText(/^Identificador/), { target: { value: 'ok_id' } })
    for (const malo of ['[]', 'null', '42']) {
      fireEvent.change(screen.getByLabelText(/^Configuración/), { target: { value: malo } })
      fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
      expect(await screen.findByText(/tiene que ser un objeto JSON/)).toBeTruthy()
    }
    expect(api.createCamera).not.toHaveBeenCalled()
    // `{}` sigue siendo válido.
    vi.mocked(api.createCamera).mockResolvedValue(undefined as never)
    fireEvent.change(screen.getByLabelText(/^Configuración/), { target: { value: '{}' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(api.createCamera).toHaveBeenCalledWith({ id: 'ok_id', name: '', plugin: 'rtsp', config: {} }))
  })
})

// Un conjunto con metadatos y campos que esta consola no conoce, varios
// backends de frases y campos opcionales ausentes: guardar sin tocar nada
// tiene que devolver EXACTAMENTE lo mismo.
const SET = {
  id: 'exp_set', status: 'exploratory', track: 'core', description: 'd',
  // Campo desconocido del YAML.
  autor: { nombre: 'x', notas: ['a'] },
  classes: [
    { id: 'person', strategy: 'canonical_positive', phrasings: { default: ['person', 'worker'], owlv2: ['a person'] },
      // Campo desconocido de la clase.
      peso: 0.5 },
    { id: 'helmet', phrasings: { default: ['helmet'] } },
  ],
} as PromptSetDetail

describe('Prompts: el payload no se reconstruye', () => {
  it('guardar sin cambios manda el conjunto completo, con metadatos desconocidos, orden y opcionales ausentes', async () => {
    vi.mocked(api.updatePromptSet).mockResolvedValue(SET as never)
    render(<PromptSetEditor initial={SET} onChanged={() => {}} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(api.updatePromptSet).toHaveBeenCalledTimes(1))
    const enviado = vi.mocked(api.updatePromptSet).mock.calls[0][1]
    expect(enviado).toEqual(SET)
    expect('strategy' in enviado.classes[1]).toBe(false)
  })

  it('editar una frase cambia sólo ese backend; escribir «;» no se borra al instante', async () => {
    vi.mocked(api.updatePromptSet).mockResolvedValue(SET as never)
    const { container } = render(<PromptSetEditor initial={SET} onChanged={() => {}} onClose={() => {}} />)
    const primera = container.querySelector('details.eo-classbox') as HTMLElement
    const campo = within(primera).getByLabelText(/Frases — default/) as HTMLInputElement
    fireEvent.change(campo, { target: { value: 'person; worker; ' } })
    expect(campo.value).toBe('person; worker; ')
    fireEvent.change(campo, { target: { value: 'person; worker; obrero' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(api.updatePromptSet).toHaveBeenCalledTimes(1))
    const enviado = vi.mocked(api.updatePromptSet).mock.calls[0][1]
    expect(enviado.classes[0].phrasings).toEqual({ default: ['person', 'worker', 'obrero'], owlv2: ['a person'] })
    expect(enviado.classes[1]).toEqual(SET.classes[1])
  })

  it('con cambios sin guardar no se puede pedir el congelamiento, y no se guarda implícitamente', () => {
    render(<PromptSetEditor initial={SET} onChanged={() => {}} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/^Descripción/), { target: { value: 'otra' } })
    const pedir = screen.getByRole('button', { name: 'Pedir congelamiento' }) as HTMLButtonElement
    expect(pedir.disabled).toBe(true)
    expect(screen.getByText(/primero guardá o descartá los cambios/)).toBeTruthy()
    fireEvent.click(pedir)
    expect(api.requestFreeze).not.toHaveBeenCalled()
    expect(api.updatePromptSet).not.toHaveBeenCalled()
  })

  it('un doble click en Guardar manda una sola escritura', async () => {
    let resolver!: () => void
    vi.mocked(api.updatePromptSet).mockImplementation(() => new Promise((r) => { resolver = () => r(SET as never) }))
    render(<PromptSetEditor initial={SET} onChanged={() => {}} onClose={() => {}} />)
    const guardar = screen.getByRole('button', { name: 'Guardar' })
    fireEvent.click(guardar)
    fireEvent.click(guardar)
    expect(api.updatePromptSet).toHaveBeenCalledTimes(1)
    resolver()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Guardar' })).toBeTruthy())
  })

  it('el identificador de un conjunto nuevo sigue el contrato ^[a-z0-9_]+$', () => {
    render(<PromptSetEditor initial={{ id: '', status: 'exploratory', classes: [] }} isNew onChanged={() => {}} onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/^Identificador del conjunto/), { target: { value: 'con-guion' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    expect(screen.getByText(/Sólo minúsculas, números y guion bajo/)).toBeTruthy()
    expect(api.createPromptSet).not.toHaveBeenCalled()
  })

  it('las clases son plegables, la primera arranca abierta y los campos siguen montados', () => {
    const { container } = render(<PromptSetEditor initial={SET} onChanged={() => {}} onClose={() => {}} />)
    const clases = container.querySelectorAll('details.eo-classbox')
    expect(clases).toHaveLength(2)
    expect((clases[0] as HTMLDetailsElement).open).toBe(true)
    expect((clases[1] as HTMLDetailsElement).open).toBe(false)
    // Plegada no es desmontada: el campo de la segunda clase está en el DOM.
    expect(within(clases[1] as HTMLElement).getAllByDisplayValue('helmet').length).toBe(2)
  })
})

describe('Derivación: herencia, ceros y precarga fallida', () => {
  beforeEach(() => {
    vi.mocked(api.listCameras).mockResolvedValue([])
    vi.mocked(api.getPromptSets).mockResolvedValue([])
    vi.mocked(api.deriveExperimentManifest).mockResolvedValue({ slug: 'nuevo' } as never)
  })

  it('un cero explícito sí se manda, como número', async () => {
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({ warmup_frames: 20 } as never)
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    await waitFor(() => expect((screen.getByLabelText(/warmup_frames/) as HTMLInputElement).value).toBe('20'))
    fireEvent.change(screen.getByLabelText(/nombre nuevo/i), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText(/warmup_frames/), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Derivar' }))
    await waitFor(() => expect(api.deriveExperimentManifest).toHaveBeenCalled())
    expect(vi.mocked(api.deriveExperimentManifest).mock.calls[0][1].overrides).toEqual({ warmup_frames: 0 })
  })

  it('si la precarga falla lo explica, ofrece reintentar y deja crear con herencia y overrides vacíos', async () => {
    vi.mocked(api.getDeriveDefaults).mockRejectedValueOnce(new Error('caído'))
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    expect(await screen.findByText(/No se pudieron leer los valores de/)).toBeTruthy()
    fireEvent.change(screen.getByLabelText(/nombre nuevo/i), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Derivar' }))
    await waitFor(() => expect(api.deriveExperimentManifest).toHaveBeenCalled())
    expect(vi.mocked(api.deriveExperimentManifest).mock.calls[0][1]).toEqual({ new_slug: 'nuevo', overrides: {} })
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({ warmup_frames: 7 } as never)
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }))
    await waitFor(() => expect((screen.getByLabelText(/warmup_frames/) as HTMLInputElement).value).toBe('7'))
  })

  it('los campos numéricos son texto con teclado numérico: una entrada inválida no se vacía ni se omite', async () => {
    vi.mocked(api.getDeriveDefaults).mockResolvedValue({} as never)
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    const stride = screen.getByLabelText(/stride/) as HTMLInputElement
    expect(stride.type).toBe('text')
    expect(stride.inputMode).toBe('numeric')
    fireEvent.change(screen.getByLabelText(/nombre nuevo/i), { target: { value: 'nuevo' } })
    fireEvent.change(stride, { target: { value: '2x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Derivar' }))
    expect(await screen.findByText(/"2x" no es un número válido/)).toBeTruthy()
    expect(stride.value).toBe('2x')
    expect(stride.getAttribute('aria-invalid')).toBe('true')
    expect(api.deriveExperimentManifest).not.toHaveBeenCalled()
  })
})
