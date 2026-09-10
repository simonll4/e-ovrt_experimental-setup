import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TraceSection from '../components/TraceSection'
import type { TraceFrame, TraceTotals } from '../types'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  artifactUrl: (id: string, path: string) => `/api/runs/${id}/artifacts/${path}`,
  getTrace: vi.fn(),
}))

afterEach(() => cleanup())

const frame = (i: number, over: Partial<TraceFrame> = {}): TraceFrame => ({
  frame_index: i,
  unit_id: `frame_${String(i).padStart(6, '0')}`,
  timestamp_ms: i * 250,
  detections: [],
  control: 'received',
  progress: [],
  alert: [],
  active_patterns: [],
  ...over,
})

const totals = (frames: number): TraceTotals => ({
  frames,
  detections: 0,
  dropped_by_reason: {},
  alerts: 0,
  received: null,
  not_received: null,
})

const many = Array.from({ length: 1468 }, (_, i) => frame(i))

const few = [
  ...Array.from({ length: 9 }, (_, i) => frame(i)),
  frame(9, { detections: [{ label: 'person', confidence: 0.9 }] }),
]

const withAlert = [
  ...Array.from({ length: 19 }, (_, i) => frame(i)),
  frame(19, {
    detections: [{ label: 'person', confidence: 0.85 }],
    alert: [{ condition_id: 'CR-01', severity: 'high' }],
    progress: [{ condition_id: 'CR-01', progress: 1 }],
  }),
]

const droppedFrames = [
  frame(0, { control: 'dropped:queue_full' }),
  frame(1, { control: 'dropped:lo_que_sea' }),
]

const PAGE = 200

/** Sirve la página pedida aplicando el filtro del lado del "servidor", que es
 *  donde vive ahora: la sección ya no tiene la traza entera para filtrar. */
const renderTrace = async (frames: TraceFrame[]) => {
  vi.mocked(api.getTrace).mockImplementation(
    async (_id, page = 1, pageSize = PAGE, _ctl, solo) => {
      const filtrados =
        solo === 'alertas'
          ? frames.filter((f) => (f.alert?.length ?? 0) > 0)
          : solo === 'actividad'
            ? frames.filter(
                (f) =>
                  (f.detections?.length ?? 0) > 0 ||
                  f.control !== 'received' ||
                  (f.alert?.length ?? 0) > 0 ||
                  (f.progress?.length ?? 0) > 0,
              )
            : frames
      const desde = (page - 1) * pageSize
      return {
        media_run_id: 'r',
        control_run_id: 'c',
        topology: null,
        control_error: null,
        totals: totals(frames.length),
        page,
        page_size: pageSize,
        total: filtrados.length,
        frames: filtrados.slice(desde, desde + pageSize),
      }
    },
  )
  const vista = render(<TraceSection runId="r" totals={totals(frames.length)} />)
  if (frames.length) await screen.findByRole('listbox')
  return vista
}

const list = () => screen.getByRole('listbox')

describe('TraceSection', () => {
  it('no vuelca todos los cuadros: la lista se acota y dice el total', async () => {
    await renderTrace(many)
    expect(screen.getAllByRole('option').length).toBeLessThanOrEqual(200)
    expect(screen.getByText(/1468/)).toBeTruthy()
  })

  it('elegir un cuadro muestra su detalle a la derecha', async () => {
    await renderTrace(few)
    fireEvent.click(within(list()).getByText('frame_000009'))
    expect(screen.getByText('person')).toBeTruthy()
    expect(screen.getByText('0,90')).toBeTruthy()
  })

  it('el banner de alerta nombra la condición, no solo el código', async () => {
    await renderTrace(withAlert)
    fireEvent.click(within(list()).getByText('frame_000019'))
    // Aparece en el banner y en el progreso de condiciones: los dos la nombran.
    const named = screen.getAllByText(/CR-01 — Presencia de persona sin casco/)
    expect(named.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Alerta confirmada/)).toBeTruthy()
  })

  it('traduce el motivo de descarte conocido y muestra crudo el desconocido', async () => {
    await renderTrace(droppedFrames)
    fireEvent.click(within(list()).getByText('frame_000000'))
    expect(screen.getByText('cola llena')).toBeTruthy()
    fireEvent.click(within(list()).getByText('frame_000001'))
    expect(screen.getByText('lo_que_sea')).toBeTruthy()
  })

  it('sin preview explica por qué, en vez de dejar un rectángulo negro', async () => {
    await renderTrace(few)
    fireEvent.error(screen.getByRole('img', { name: /Cuadro 0 de la corrida r/ }))
    expect(screen.getByText(/sin vistas previas de cuadro/i)).toBeTruthy()
  })

  it('el filtro de solo alertas deja únicamente los cuadros con alerta', async () => {
    await renderTrace(withAlert)
    fireEvent.click(screen.getByLabelText('Solo alertas'))
    await waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(1))
  })

  it('el filtro de actividad descarta los cuadros sin nada que mostrar', async () => {
    await renderTrace(few)
    fireEvent.click(screen.getByLabelText('Solo con actividad'))
    await waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(1))
  })

  it('muestra el progreso de las condiciones del cuadro elegido', async () => {
    await renderTrace(withAlert)
    fireEvent.click(within(list()).getByText('frame_000019'))
    expect(screen.getByText('100 %')).toBeTruthy()
  })

  it('las flechas de navegación se deshabilitan en los extremos', async () => {
    await renderTrace(few)
    expect(screen.getByRole('button', { name: 'Cuadro anterior' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Cuadro siguiente' }))
    expect(screen.getByRole('button', { name: 'Cuadro anterior' }).hasAttribute('disabled')).toBe(false)
  })

  it('una corrida sin traza lo dice en vez de mostrar un panel vacío', async () => {
    await renderTrace([])
    expect(await screen.findByText('Esta corrida no tiene traza')).toBeTruthy()
  })
})
