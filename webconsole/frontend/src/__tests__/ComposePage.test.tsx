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
    { id: 'image_folder', kind: 'bounded', available: true, description: '', mvp_enabled: true },
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

    fireEvent.click(screen.getByText('Lanzar'))

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
