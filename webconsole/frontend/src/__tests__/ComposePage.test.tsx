import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ComposePage from '../pages/ComposePage'
import * as api from '../api'

vi.mock('../api', () => ({
  ApiError: class ApiError extends Error {
    status: number
    payload: unknown
    constructor(status: number, payload: unknown) {
      super(`API ${status}`)
      this.status = status
      this.payload = payload
    }
  },
  getIngestPlugins: vi.fn(async () => [
    { id: 'image_folder', kind: 'bounded', available: true, description: '', enabled: true },
    { id: 'rtsp', kind: 'live', available: true, description: '', enabled: true },
  ]),
  getDatasets: vi.fn(async () => [
    { id: 'demo_v2', description: '', path: '', available: true },
  ]),
  getPromptSets: vi.fn(async () => [
    {
      id: 'demo_set',
      description: null,
      language: null,
      frozen: false,
      classes: [
        { id: 'person', role: null, enabled_by_default: true, phrasings: {} },
        { id: 'helmet', role: null, enabled_by_default: true, phrasings: {} },
      ],
    },
  ]),
  getTarget: vi.fn(async () => ({
    service_url: 'http://x', healthy: true, ready: true,
    model: { ref: 'mock', name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
  })),
  getExperiments: vi.fn(async () => [
    {
      id: 'exp1',
      group: '',
      manifest: {
        source: { ref: 'demo_v2' },
        prompts: { ref: 'demo_set', active_ids: ['person'] },
        model: { ref: 'mock' },
      },
    },
    {
      id: 'expVideo',
      group: '',
      manifest: {
        source: { type: 'video_frame', path: '/data/x.mp4' },
        prompts: { ref: 'demo_set', active_ids: ['person'] },
        model: { ref: 'mock' },
      },
    },
  ]),
  listCameras: vi.fn(async () => []),
  getPreflight: vi.fn(async () => ({
    ready: true,
    blockers: [],
    media: { service_url: 'http://m', healthy: true, ready: true, model: null },
    control: { service_url: 'http://c', healthy: true, ready: true },
  })),
  launchRun: vi.fn(),
  saveManifest: vi.fn(),
}))

describe('ComposePage prefill', () => {
  it('conserva active_ids del manifiesto y no lo pisan los defaults del set', async () => {
    render(
      <MemoryRouter initialEntries={['/compose?from=exp1']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    const personCheckbox = await screen.findByLabelText<HTMLInputElement>(/^person$/)
    const helmetCheckbox = await screen.findByLabelText<HTMLInputElement>(/^helmet$/)

    await waitFor(() => expect(personCheckbox.checked).toBe(true))
    expect(helmetCheckbox.checked).toBe(false)
  })
})

describe('ComposePage prefill de source.type video', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('conserva el source.type original en la composición (round-trip sin colapso a video_file)', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    render(
      <MemoryRouter initialEntries={['/compose?from=expVideo']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )
    // El prefill corre tras cargar catálogos+experiments: esperar a que marque
    // el active_id del manifiesto (person) antes de lanzar.
    const personCheckbox = await screen.findByLabelText<HTMLInputElement>(/^person$/)
    await waitFor(() => expect(personCheckbox.checked).toBe(true))

    // El botón arranca deshabilitado hasta que el poll del target confirma que
    // el media-plane está listo (gate de lanzamiento).
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('video_file')
    expect(comp.ingest.source_type).toBe('video_frame')
    expect(comp.ingest.config).toEqual({ path: '/data/x.mp4' })
  })
})

describe('ComposePage catalog re-fetch on target model change', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.mocked(api.getTarget).mockReset()
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref: 'mock', name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))
  })

  it('re-fetchea plugins/datasets cuando cambia model.ref del target', async () => {
    vi.useFakeTimers()
    let ref = 'model-a'
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref, name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))

    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Deja resolver el mount inicial (fetch de catálogos + primer getTarget).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    const callsBefore = vi.mocked(api.getIngestPlugins).mock.calls.length
    expect(callsBefore).toBeGreaterThanOrEqual(1)

    ref = 'model-b'
    // Dispara el próximo tick del poll de useTarget (cada 5s) -> modelRef cambia.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    expect(vi.mocked(api.getIngestPlugins).mock.calls.length).toBeGreaterThan(callsBefore)
    expect(vi.mocked(api.getDatasets).mock.calls.length).toBeGreaterThan(1)
  })
})

describe('ComposePage prefill survives catalog re-fetch (no clobber)', () => {
  beforeEach(() => {
    // Este archivo no usa `globals: true` en vitest.config.ts, así que
    // @testing-library/react no engancha su cleanup automático entre tests: el DOM
    // de los describe anteriores (con sus propios checkboxes "person"/"helmet")
    // sigue montado. Limpiamos antes de renderizar para no colisionar con esos
    // nodos al hacer queries por label.
    cleanup()
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.mocked(api.getTarget).mockReset()
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref: 'mock', name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))
    vi.mocked(api.getExperiments).mockClear()
  })

  it('no reaplica el manifiesto cuando `experiments` cambia de referencia tras un re-fetch', async () => {
    vi.useFakeTimers()
    let ref = 'modelA'
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref, name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))

    render(
      <MemoryRouter initialEntries={['/compose?from=exp1']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    // Deja resolver el mount inicial (fetch de catálogos + prefill desde exp1). Los
    // fetches encadenan varias promesas (catálogos -> experiments -> efecto de
    // prefill), así que flusheamos un par de veces para dejarlas asentar sin
    // depender de los timers reales de `waitFor`/`findBy*` (incompatibles con
    // fake timers).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    const personCheckbox = screen.getByLabelText<HTMLInputElement>(/^person$/)
    const helmetCheckbox = screen.getByLabelText<HTMLInputElement>(/^helmet$/)
    expect(personCheckbox.checked).toBe(true)
    expect(helmetCheckbox.checked).toBe(false)

    // Edición manual del usuario: marca helmet (el manifiesto solo trae person).
    fireEvent.click(helmetCheckbox)
    expect(helmetCheckbox.checked).toBe(true)

    const experimentsCallsBefore = vi.mocked(api.getExperiments).mock.calls.length

    // Dispara un re-fetch real de catálogos: cambia model.ref del target y avanza el
    // poll de useTarget (5s) -> el efecto keyado en modelRef vuelve a llamar
    // getExperiments(), produciendo un array `experiments` con referencia nueva.
    ref = 'modelB'
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    expect(vi.mocked(api.getExperiments).mock.calls.length).toBeGreaterThan(experimentsCallsBefore)

    // La edición del usuario debe sobrevivir: el prefill NO se reaplica sobre el
    // mismo `from=exp1` solo porque `experiments` cambió de referencia.
    expect(helmetCheckbox.checked).toBe(true)
    expect(personCheckbox.checked).toBe(true)
  })
})

// El botón Lanzar ahora exige el form mínimo completo (fuente + prompt set):
// completa dataset demo_v2 y set demo_set con el mismo patrón label-vecino que
// usa el describe de RTSP (los <label> no están asociados por htmlFor).
async function completeMinimalForm() {
  const datasetSelect = await waitFor(() => {
    const label = screen.getByText(/Dataset del catálogo/i)
    const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
    expect(select.querySelector('option[value="demo_v2"]')).toBeTruthy()
    return select
  })
  fireEvent.change(datasetSelect, { target: { value: 'demo_v2' } })
  const setSelect = await waitFor(() => {
    const label = screen.getByText(/^Conjunto de prompts$/i)
    const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
    expect(select.querySelector('option[value="demo_set"]')).toBeTruthy()
    return select
  })
  fireEvent.change(setSelect, { target: { value: 'demo_set' } })
}

describe('ComposePage nombre opcional del run', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('manda run.name cuando se completa, null cuando se deja vacío', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )
    await completeMinimalForm()

    const nameInput = screen.getByPlaceholderText(/prueba OAK-D laboratorio/i)
    fireEvent.change(nameInput, { target: { value: 'mi corrida de prueba' } })

    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    expect(vi.mocked(api.launchRun).mock.calls[0][0].run.name).toBe('mi corrida de prueba')
  })

  it('deja run.name en null si el campo queda vacío (usa el id autogenerado)', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r2' })
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )
    await completeMinimalForm()

    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    expect(vi.mocked(api.launchRun).mock.calls[0][0].run.name).toBeNull()
  })
})

describe('ComposePage aviso de 409 al lanzar', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('muestra aviso de prueba de cámara activa ante 409 preview_active', async () => {
    vi.mocked(api.launchRun).mockRejectedValue(
      new api.ApiError(409, { detail: 'ocupado', reason: 'preview_active' }),
    )
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await completeMinimalForm()
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    expect(await screen.findByText(/prueba de cámara activa/i)).toBeTruthy()
  })

  it('muestra aviso de run activo ante 409 con active_run_id', async () => {
    vi.mocked(api.launchRun).mockRejectedValue(
      new api.ApiError(409, { detail: 'ocupado', active_run_id: 'r99' }),
    )
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    await completeMinimalForm()
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    expect(await screen.findByText(/ya hay una corrida activa/i)).toBeTruthy()
  })
})

describe('ComposePage gate de media-plane', () => {
  beforeEach(() => cleanup())

  it('bloquea Lanzar con el motivo cuando el media-plane no está listo', async () => {
    // mockResolvedValueOnce: solo el tick inicial del poll (el test dura menos
    // que el intervalo de 5s) y sin contaminar los describes siguientes.
    vi.mocked(api.getTarget).mockResolvedValueOnce({
      service_url: 'http://x', healthy: true, ready: false, model: null,
    } as any)
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(screen.getByText(/no terminó de cargar el modelo/i)).toBeTruthy(),
    )
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    expect(launch.disabled).toBe(true)
    expect(vi.mocked(api.launchRun)).not.toHaveBeenCalled()
  })
})

describe('ComposePage fuente RTSP', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('bloquea Lanzar si la URL RTSP trae credenciales censuradas (***)', async () => {
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )
    const pluginSelect = await waitFor(() => {
      const label = screen.getByText(/Tipo de fuente/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="rtsp"]')).toBeTruthy()
      return select
    })
    fireEvent.change(pluginSelect, { target: { value: 'rtsp' } })
    const urlInput = await screen.findByPlaceholderText<HTMLInputElement>(/^rtsp:\/\//)
    fireEvent.change(urlInput, { target: { value: 'rtsp://user:***@10.0.0.5:554/s' } })
    const setSelect = await waitFor(() => {
      const label = screen.getByText(/^Conjunto de prompts$/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="demo_set"]')).toBeTruthy()
      return select
    })
    fireEvent.change(setSelect, { target: { value: 'demo_set' } })

    await waitFor(() =>
      expect(screen.getByText(/recompletá las credenciales de la URL RTSP/i)).toBeTruthy(),
    )
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    expect(launch.disabled).toBe(true)
    expect(vi.mocked(api.launchRun)).not.toHaveBeenCalled()
  })

  it('al elegir rtsp muestra el campo URL y arma config { url }', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    // NOTA (adaptación respecto al brief): los <label> de ComposePage no están
    // asociados por htmlFor ni anidan el control, así que findByLabelText no
    // resuelve (confirmado: falla igual que sin los cambios de producción).
    // En su lugar ubicamos el <select>/<input> por el texto del <label> vecino
    // dentro de su contenedor. Para el plugin, además esperamos a que la opción
    // "rtsp" esté poblada (carga async de getIngestPlugins) antes de disparar el
    // change, porque jsdom no aplica un value sin una <option> que lo respalde.
    const pluginSelect = await waitFor(() => {
      const label = screen.getByText(/Tipo de fuente/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="rtsp"]')).toBeTruthy()
      return select
    })
    fireEvent.change(pluginSelect, { target: { value: 'rtsp' } })

    const urlInput = await screen.findByPlaceholderText<HTMLInputElement>(/^rtsp:\/\//)
    fireEvent.change(urlInput, { target: { value: 'rtsp://u:p@10.0.0.5:554/s' } })

    // Elegir prompt set para no bloquear el lanzamiento por campos ajenos.
    const setSelect = await waitFor(() => {
      const label = screen.getByText(/^Conjunto de prompts$/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="demo_set"]')).toBeTruthy()
      return select
    })
    fireEvent.change(setSelect, { target: { value: 'demo_set' } })

    // El botón arranca deshabilitado hasta que el poll del target confirma que
    // el media-plane está listo (gate de lanzamiento).
    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('rtsp')
    expect(comp.ingest.config).toEqual({ url: 'rtsp://u:p@10.0.0.5:554/s' })
  })
})

describe('ComposePage cámara guardada (oak_d)', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('lanza con la config del preset de cámara elegido', async () => {
    // mockResolvedValue persistente (no Once): el efecto de catálogos corre dos
    // veces (modelRef undefined -> 'mock') y la segunda llamada pisaría la lista.
    // Es el último describe del archivo, no contamina a nadie.
    vi.mocked(api.getIngestPlugins).mockResolvedValue([
      { id: 'image_folder', kind: 'bounded', available: true, description: '', enabled: true },
      { id: 'oak_d', kind: 'live', available: true, description: '', enabled: true },
    ] as any)
    vi.mocked(api.listCameras).mockResolvedValue([
      { id: 'oak_lab', name: 'OAK-D Lab', plugin: 'oak_d', config: { url: '192.168.1.50', fps: 30 } },
    ] as any)
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    render(
      <MemoryRouter initialEntries={['/compose']}>
        <Routes>
          <Route path="/compose" element={<ComposePage />} />
        </Routes>
      </MemoryRouter>,
    )

    const pluginSelect = await waitFor(() => {
      const label = screen.getByText(/Tipo de fuente/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="oak_d"]')).toBeTruthy()
      return select
    })
    fireEvent.change(pluginSelect, { target: { value: 'oak_d' } })

    const camSelect = await waitFor(() => {
      const label = screen.getByText(/^Cámara guardada$/)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="oak_lab"]')).toBeTruthy()
      return select
    })
    fireEvent.change(camSelect, { target: { value: 'oak_lab' } })

    const setSelect = await waitFor(() => {
      const label = screen.getByText(/^Conjunto de prompts$/i)
      const select = label.closest('div')!.querySelector('select') as HTMLSelectElement
      expect(select.querySelector('option[value="demo_set"]')).toBeTruthy()
      return select
    })
    fireEvent.change(setSelect, { target: { value: 'demo_set' } })

    const launch = screen.getByText('Lanzar') as HTMLButtonElement
    await waitFor(() => expect(launch.disabled).toBe(false))
    fireEvent.click(launch)

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('oak_d')
    expect(comp.ingest.config).toEqual({ url: '192.168.1.50', fps: 30 })
  })
})
