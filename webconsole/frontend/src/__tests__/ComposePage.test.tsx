import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ComposePage from '../pages/ComposePage'
import * as api from '../api'
import { POLL } from '../api/queryClient'

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
    { id: 'image_folder', kind: 'bounded', available: true, description: 'Un directorio del catálogo', enabled: true },
    { id: 'rtsp', kind: 'live', available: true, description: 'Transmisión en vivo por red', enabled: true },
    {
      id: 'oak_d', kind: 'live', available: false, description: 'RGB vía DepthAI',
      enabled: false, disabled_reason: 'El motor de detección no tiene instalado el SDK DepthAI',
    },
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

const renderCompose = (entrada = '/compose') =>
  render(
    <MemoryRouter initialEntries={[entrada]}>
      <Routes>
        <Route path="/compose" element={<ComposePage />} />
      </Routes>
    </MemoryRouter>,
  )

/* ── Ayudas para los controles del kit ─────────────────────────────────────
   La pantalla ya no usa <select> nativos: el desplegable propio es un <button>
   que abre una lista de role="option", las fuentes son botones-tarjeta y las
   clases son chips con aria-pressed. */

/** Abre el desplegable `etiqueta` y elige la opción `opcion`. */
const elegir = async (etiqueta: string, opcion: string | RegExp) => {
  fireEvent.click(await screen.findByRole('button', { name: etiqueta }))
  fireEvent.click(await screen.findByRole('option', { name: opcion }))
}

const chipDeClase = (id: string) => screen.getByRole('button', { name: id })
const claseActiva = (id: string) => chipDeClase(id).getAttribute('aria-pressed') === 'true'
const botonLanzar = () => screen.getByRole('button', { name: /Lanzar corrida/ }) as HTMLButtonElement

/** Fuente + conjunto de prompts: el mínimo para que el botón se habilite. */
async function completarMinimo() {
  await elegir('Conjunto del catálogo', 'demo_v2')
  await elegir('Conjunto de prompts', 'demo_set')
}

describe('ComposePage prefill', () => {
  beforeEach(() => cleanup())

  it('conserva active_ids del manifiesto y no lo pisan los defaults del set', async () => {
    renderCompose('/compose?from=exp1')
    await waitFor(() => expect(claseActiva('person')).toBe(true))
    expect(claseActiva('helmet')).toBe(false)
  })
})

describe('ComposePage prefill de source.type video', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('conserva el source.type original en la composición (round-trip sin colapso a video_file)', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    renderCompose('/compose?from=expVideo')
    // El prefill corre tras cargar catálogos+experiments: esperar a que marque
    // el active_id del manifiesto (person) antes de lanzar.
    await waitFor(() => expect(claseActiva('person')).toBe(true))

    // El botón arranca deshabilitado hasta que el poll de la instancia activa
    // confirma que el motor de detección está listo (gate de lanzamiento).
    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('video_file')
    expect(comp.ingest.source_type).toBe('video_frame')
    expect(comp.ingest.config).toEqual({ path: '/data/x.mp4' })
  })
})

describe('ComposePage catalog re-fetch on target model change', () => {
  beforeEach(() => cleanup())
  afterEach(() => {
    vi.useRealTimers()
    vi.mocked(api.getTarget).mockReset()
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref: 'mock', name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))
  })

  it('re-fetchea plugins/datasets cuando cambia model.ref de la instancia activa', async () => {
    vi.useFakeTimers()
    let ref = 'model-a'
    vi.mocked(api.getTarget).mockImplementation(async () => ({
      service_url: 'http://x', healthy: true, ready: true,
      model: { ref, name: null, adapter: null, device: null, thresholds: {}, runtime: {} },
    }))

    renderCompose()

    // Deja resolver el mount inicial (fetch de catálogos + primer getTarget).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    const callsBefore = vi.mocked(api.getIngestPlugins).mock.calls.length
    expect(callsBefore).toBeGreaterThanOrEqual(1)

    ref = 'model-b'
    // Dispara el próximo tick del poll de useTarget (POLL.salud) -> cambia
    // modelRef, y con él la clave de caché de los catálogos, que se recargan.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL.salud)
    })

    expect(vi.mocked(api.getIngestPlugins).mock.calls.length).toBeGreaterThan(callsBefore)
    expect(vi.mocked(api.getDatasets).mock.calls.length).toBeGreaterThan(1)
  })
})

describe('ComposePage prefill survives catalog re-fetch (no clobber)', () => {
  beforeEach(() => cleanup())
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

    renderCompose('/compose?from=exp1')

    // Deja resolver el mount inicial (fetch de catálogos -> experiments ->
    // efecto de prefill). Son varias promesas encadenadas, así que flusheamos un
    // par de veces en vez de usar waitFor/findBy* (incompatibles con fake timers).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })

    expect(claseActiva('person')).toBe(true)
    expect(claseActiva('helmet')).toBe(false)

    // Edición manual del usuario: activa helmet (el manifiesto solo trae person).
    fireEvent.click(chipDeClase('helmet'))
    expect(claseActiva('helmet')).toBe(true)

    const experimentsCallsBefore = vi.mocked(api.getExperiments).mock.calls.length

    // Dispara un re-fetch real de catálogos: cambia model.ref y avanza el poll de
    // useTarget (POLL.salud) -> cambia la clave de los catálogos y getExperiments(),
    // produciendo un array `experiments` con referencia nueva.
    ref = 'modelB'
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL.salud)
    })
    // Segundo flush, por el mismo motivo que en el mount: el re-fetch es en
    // cadena (tick del poll -> resuelve getTarget -> cambia modelRef -> cambia
    // la clave de los catálogos -> recién ahí se pide getExperiments).
    //
    // 1 ms y no 0: al avanzar el poll, la caché ya tiene el modelo nuevo pero el
    // componente todavía no se re-renderizó (Query agenda la notificación a los
    // observadores). Con 0 ms esa notificación no llega a correr.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })

    expect(vi.mocked(api.getExperiments).mock.calls.length).toBeGreaterThan(experimentsCallsBefore)

    // Mientras los catálogos se recargan con la clave nueva, `sets` viene vacío y
    // los chips se desmontan por un instante: la lista de clases sale del
    // conjunto, no del estado. Se espera a que vuelvan, porque lo que se prueba
    // es que la elección del usuario sobrevivió, no que los chips no parpadeen.
    //
    // Se re-consulta el DOM en vez de guardar el nodo: un nodo desmontado
    // conserva su `.checked`, así que leerlo daría verde aunque la pantalla
    // hubiera perdido la selección.
    for (let i = 0; i < 5 && screen.queryByRole('button', { name: 'helmet' }) == null; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1)
      })
    }

    // La edición del usuario debe sobrevivir: el prefill NO se reaplica sobre el
    // mismo `from=exp1` solo porque `experiments` cambió de referencia.
    expect(claseActiva('helmet')).toBe(true)
    expect(claseActiva('person')).toBe(true)
  })
})

describe('ComposePage nombre opcional de la corrida', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('manda run.name cuando se completa, null cuando se deja vacío', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    renderCompose()
    await completarMinimo()

    fireEvent.change(screen.getByPlaceholderText(/prueba OAK-D laboratorio/i), {
      target: { value: 'mi corrida de prueba' },
    })

    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    expect(vi.mocked(api.launchRun).mock.calls[0][0].run.name).toBe('mi corrida de prueba')
  })

  it('deja run.name en null si el campo queda vacío (usa el id autogenerado)', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r2' })
    renderCompose()
    await completarMinimo()

    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

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
    renderCompose()
    await completarMinimo()
    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    expect(await screen.findByText(/prueba de cámara activa/i)).toBeTruthy()
  })

  it('muestra aviso de corrida activa ante 409 con active_run_id', async () => {
    vi.mocked(api.launchRun).mockRejectedValue(
      new api.ApiError(409, { detail: 'ocupado', active_run_id: 'r99' }),
    )
    renderCompose()
    await completarMinimo()
    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    expect(await screen.findByText(/ya hay una corrida activa/i)).toBeTruthy()
  })
})

describe('ComposePage gate del motor de detección', () => {
  beforeEach(() => cleanup())

  it('bloquea el lanzamiento con el motivo cuando el motor no está listo', async () => {
    // mockResolvedValueOnce: solo el tick inicial del poll (el test dura menos
    // que el intervalo) y sin contaminar los describes siguientes.
    vi.mocked(api.getTarget).mockResolvedValueOnce({
      service_url: 'http://x', healthy: true, ready: false, model: null,
    } as any)
    renderCompose()
    await waitFor(() =>
      expect(screen.getByText(/no terminó de cargar el modelo/i)).toBeTruthy(),
    )
    expect(botonLanzar().disabled).toBe(true)
    expect(vi.mocked(api.launchRun)).not.toHaveBeenCalled()
  })
})

// §3.5: el panel lateral muestra los cuatro requisitos a la vez, mientras que el
// texto bajo el botón dice cuál arreglar primero. Son la misma verdad con dos
// niveles de detalle, y por eso conviene comprobar que no se contradicen.
describe('ComposePage panel «Antes de lanzar»', () => {
  beforeEach(() => cleanup())

  it('lista los cuatro requisitos y marca cuáles faltan', async () => {
    renderCompose()
    expect(await screen.findByText('Antes de lanzar')).toBeTruthy()
    expect(screen.getByText('El motor de detección está listo')).toBeTruthy()
    expect(screen.getByText('Elegiste un origen')).toBeTruthy()
    expect(screen.getByText('Elegiste un conjunto de prompts')).toBeTruthy()
    expect(screen.getByText('Activaste al menos una clase')).toBeTruthy()

    // Sin completar nada, el origen y el conjunto figuran como pendientes.
    expect(screen.getByText('Ni conjunto del catálogo ni ruta')).toBeTruthy()
    expect(screen.getByText('Sin elegir')).toBeTruthy()
  })

  it('los requisitos se van cumpliendo y el botón se habilita al final', async () => {
    renderCompose()
    await elegir('Conjunto del catálogo', 'demo_v2')
    await waitFor(() => expect(screen.getByText('Conjunto demo_v2')).toBeTruthy())
    expect(botonLanzar().disabled).toBe(true)

    await elegir('Conjunto de prompts', 'demo_set')
    // Al elegir el conjunto se activan sus clases por defecto: 2 de 2.
    await waitFor(() => expect(screen.getByText('2 de 2 activas')).toBeTruthy())
    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    expect(screen.getByText(/Todo listo/)).toBeTruthy()
  })

  it('desactivar todas las clases vuelve a bloquear, diciendo qué falta', async () => {
    renderCompose()
    await completarMinimo()
    await waitFor(() => expect(botonLanzar().disabled).toBe(false))

    fireEvent.click(chipDeClase('person'))
    fireEvent.click(chipDeClase('helmet'))

    await waitFor(() => expect(screen.getByText('Ninguna activa')).toBeTruthy())
    expect(botonLanzar().disabled).toBe(true)
    expect(screen.getByText(/Falta: activá al menos una clase/)).toBeTruthy()
  })
})

// §3.2: las fuentes son botones-tarjeta con nombre legible, no un <select> con
// los identificadores crudos. Una fuente no disponible dice por qué.
describe('ComposePage rejilla de fuentes', () => {
  beforeEach(() => cleanup())

  it('muestra el nombre legible de cada fuente, no su identificador', async () => {
    renderCompose()
    expect(await screen.findByRole('button', { name: /Carpeta de imágenes/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Cámara RTSP/ })).toBeTruthy()
    expect(screen.queryByText('image_folder')).toBeNull()
  })

  it('una fuente deshabilitada explica el motivo que manda el backend', async () => {
    renderCompose()
    const oak = await screen.findByRole('button', { name: /Cámara OAK-D Pro/ })
    expect((oak as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText(/no tiene instalado el SDK DepthAI/)).toBeTruthy()
  })

  it('la fuente elegida queda marcada con aria-pressed', async () => {
    renderCompose()
    const carpeta = await screen.findByRole('button', { name: /Carpeta de imágenes/ })
    expect(carpeta.getAttribute('aria-pressed')).toBe('true')

    fireEvent.click(screen.getByRole('button', { name: /Cámara RTSP/ }))
    await waitFor(() => expect(carpeta.getAttribute('aria-pressed')).toBe('false'))
  })
})

describe('ComposePage fuente RTSP', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('bloquea el lanzamiento si la dirección RTSP trae credenciales censuradas (***)', async () => {
    renderCompose()
    fireEvent.click(await screen.findByRole('button', { name: /Cámara RTSP/ }))
    const urlInput = await screen.findByPlaceholderText<HTMLInputElement>(/^rtsp:\/\//)
    fireEvent.change(urlInput, { target: { value: 'rtsp://user:***@10.0.0.5:554/s' } })
    await elegir('Conjunto de prompts', 'demo_set')

    await waitFor(() =>
      expect(screen.getByText(/recompletá las credenciales de la dirección RTSP/i)).toBeTruthy(),
    )
    expect(botonLanzar().disabled).toBe(true)
    expect(vi.mocked(api.launchRun)).not.toHaveBeenCalled()
  })

  it('al elegir rtsp muestra el campo de dirección y arma config { url }', async () => {
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    renderCompose()
    fireEvent.click(await screen.findByRole('button', { name: /Cámara RTSP/ }))

    const urlInput = await screen.findByPlaceholderText<HTMLInputElement>(/^rtsp:\/\//)
    fireEvent.change(urlInput, { target: { value: 'rtsp://u:p@10.0.0.5:554/s' } })
    await elegir('Conjunto de prompts', 'demo_set')

    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('rtsp')
    expect(comp.ingest.config).toEqual({ url: 'rtsp://u:p@10.0.0.5:554/s' })
  })
})

describe('ComposePage cámara guardada (oak_d)', () => {
  beforeEach(() => cleanup())
  afterEach(() => vi.mocked(api.launchRun).mockReset())

  it('lanza con la config de la cámara guardada elegida', async () => {
    // mockResolvedValue persistente (no Once): los catálogos se piden dos veces
    // (modelRef undefined -> 'mock') y la segunda pisaría la lista.
    // Es el último describe del archivo, no contamina a nadie.
    vi.mocked(api.getIngestPlugins).mockResolvedValue([
      { id: 'image_folder', kind: 'bounded', available: true, description: '', enabled: true },
      { id: 'oak_d', kind: 'live', available: true, description: '', enabled: true },
    ] as any)
    vi.mocked(api.listCameras).mockResolvedValue([
      { id: 'oak_lab', name: 'OAK-D Lab', plugin: 'oak_d', config: { url: '192.168.1.50', fps: 30 } },
    ] as any)
    vi.mocked(api.launchRun).mockResolvedValue({ run_id: 'r1' })
    renderCompose()

    fireEvent.click(await screen.findByRole('button', { name: /Cámara OAK-D Pro/ }))
    await elegir('Cámara', 'OAK-D Lab')
    await elegir('Conjunto de prompts', 'demo_set')

    await waitFor(() => expect(botonLanzar().disabled).toBe(false))
    fireEvent.click(botonLanzar())

    await waitFor(() => expect(api.launchRun).toHaveBeenCalled())
    const comp = vi.mocked(api.launchRun).mock.calls[0][0]
    expect(comp.ingest.plugin).toBe('oak_d')
    expect(comp.ingest.config).toEqual({ url: '192.168.1.50', fps: 30 })
  })
})
