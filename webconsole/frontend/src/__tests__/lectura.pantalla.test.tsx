// Lo que encontró la lectura de pantalla sobre el árbol de accesibilidad de
// Chrome: nombres que se leían pegados o ambiguos, foco que caía al documento
// al abrir un editor y la falta de un salto al contenido.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import * as api from '../api'
import Shell from '../components/Shell'
import TraceSection from '../components/TraceSection'
import PromptSetEditor from '../components/PromptSetEditor'
import CameraPresetForm from '../components/CameraPresetForm'
import { Tabs } from '../components/ui'
import type { PromptSetDetail, TraceFrame } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  artifactUrl: (id: string, path: string) => `/api/runs/${id}/artifacts/${path}`,
  getTrace: vi.fn(),
  getTarget: vi.fn().mockResolvedValue({ service_url: 'x', healthy: true, ready: true, model: null }),
  getPreflight: vi.fn().mockResolvedValue({
    ready: true, blockers: [],
    media: { service_url: 'x', healthy: true, ready: true },
    control: { service_url: 'y', healthy: true, ready: true },
  }),
  listRunsPaged: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getExperimentManifests: vi.fn().mockResolvedValue([]),
  listPromptSets: vi.fn().mockResolvedValue([]),
}))

afterEach(() => cleanup())

describe('Nombres que se leen bien', () => {
  it('la pestaña con contador se anuncia «Traza 260», no «Traza260»', () => {
    render(<Tabs label="Secciones" idBase="t" value="a" onChange={() => {}}
      items={[{ id: 'a', label: 'Traza', count: 260 }, { id: 'b', label: 'Resumen' }]} />)
    expect(screen.getByRole('tab', { name: 'Traza 260' })).toBeTruthy()
  })

  it('cada cuadro de la traza se lee como una frase: cuadro, unidad, detecciones y estado', async () => {
    const frame = (i: number, over: Partial<TraceFrame> = {}): TraceFrame => ({
      frame_index: i, unit_id: `frame_${String(i).padStart(6, '0')}`, timestamp_ms: i * 250,
      detections: [], control: 'received', progress: [], alert: [], active_patterns: [], ...over,
    })
    const frames = [frame(0), frame(1, { detections: [{ label: 'person', confidence: 0.9 }] }), frame(2, { control: 'dropped:stride' })]
    const totals = { frames: 3, detections: 1, dropped_by_reason: {}, alerts: 0, received: null, not_received: null }
    vi.mocked(api.getTrace).mockResolvedValue({
      media_run_id: 'r', control_run_id: 'c', topology: null, control_error: null,
      totals, page: 1, page_size: 200, total: 3, frames,
    } as never)
    render(<TraceSection runId="r" totals={totals} />)
    expect(await screen.findByRole('option', { name: /^Cuadro 0\s*,\s*frame_000000\s*,\s*sin detecciones,\s*recibido$/ })).toBeTruthy()
    expect(screen.getByRole('option', { name: /^Cuadro 1\s*,\s*frame_000001\s*,\s*1 detección,\s*recibido$/ })).toBeTruthy()
    expect(screen.getByRole('option', { name: /^Cuadro 2\s*,\s*frame_000002\s*,\s*sin detecciones,\s*descartado$/ })).toBeTruthy()
  })
})

describe('Foco', () => {
  it('la primera parada de Tab salta al contenido y enfoca su h1', async () => {
    render(<MemoryRouter><Shell><h1>Destino</h1></Shell></MemoryRouter>)
    const saltar = screen.getByRole('button', { name: 'Saltar al contenido' })
    // Es lo primero enfocable del documento.
    const enfocables = document.querySelectorAll<HTMLElement>('button, a[href], input, select, textarea, [tabindex="0"]')
    expect(enfocables[0]).toBe(saltar)
    fireEvent.click(saltar)
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Destino' })))
  })

  it('al abrir el editor de prompts el foco va a su título', async () => {
    const set = { id: 'exp_set', status: 'exploratory', classes: [{ id: 'person', phrasings: { default: ['person'] } }] } as PromptSetDetail
    render(<PromptSetEditor initial={set} onChanged={() => {}} onClose={() => {}} />)
    await waitFor(() => expect(document.activeElement?.textContent).toBe('exp_set'))
    expect(document.activeElement?.tagName).toBe('H2')
  })

  it('al abrir el formulario de cámara el foco va a su título', async () => {
    render(<CameraPresetForm initial={null} onSaved={() => {}} onClose={() => {}} />)
    await waitFor(() => expect(document.activeElement?.textContent).toBe('Agregar cámara'))
  })
})
