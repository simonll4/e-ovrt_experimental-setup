import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TraceSection from '../components/TraceSection'
import type { TraceFrame, TraceTotals } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  artifactUrl: (id: string, path: string) => `/api/runs/${id}/artifacts/${path}`,
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

const renderTrace = (frames: TraceFrame[]) =>
  render(<TraceSection runId="r" frames={frames} totals={totals(frames.length)} />)

const list = () => screen.getByRole('listbox')

describe('TraceSection', () => {
  it('no vuelca todos los cuadros: la lista se acota y dice el total', () => {
    renderTrace(many)
    expect(screen.getAllByRole('option').length).toBeLessThanOrEqual(200)
    expect(screen.getByText(/1468/)).toBeTruthy()
  })

  it('elegir un cuadro muestra su detalle a la derecha', () => {
    renderTrace(few)
    fireEvent.click(within(list()).getByText('frame_000009'))
    expect(screen.getByText('person')).toBeTruthy()
    expect(screen.getByText('0,90')).toBeTruthy()
  })

  it('el banner de alerta nombra la condición, no solo el código', () => {
    renderTrace(withAlert)
    fireEvent.click(within(list()).getByText('frame_000019'))
    // Aparece en el banner y en el progreso de condiciones: los dos la nombran.
    const named = screen.getAllByText(/CR-01 — Presencia de persona sin casco/)
    expect(named.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Alerta confirmada/)).toBeTruthy()
  })

  it('traduce el motivo de descarte conocido y muestra crudo el desconocido', () => {
    renderTrace(droppedFrames)
    fireEvent.click(within(list()).getByText('frame_000000'))
    expect(screen.getByText('cola llena')).toBeTruthy()
    fireEvent.click(within(list()).getByText('frame_000001'))
    expect(screen.getByText('lo_que_sea')).toBeTruthy()
  })

  it('sin preview explica por qué, en vez de dejar un rectángulo negro', () => {
    renderTrace(few)
    fireEvent.error(screen.getByRole('img', { name: /Cuadro 0 de la corrida r/ }))
    expect(screen.getByText(/sin vistas previas de cuadro/i)).toBeTruthy()
  })

  it('el filtro de solo alertas deja únicamente los cuadros con alerta', () => {
    renderTrace(withAlert)
    fireEvent.click(screen.getByLabelText('Solo alertas'))
    expect(screen.getAllByRole('option')).toHaveLength(1)
  })

  it('el filtro de actividad descarta los cuadros sin nada que mostrar', () => {
    renderTrace(few)
    fireEvent.click(screen.getByLabelText('Solo con actividad'))
    expect(screen.getAllByRole('option')).toHaveLength(1)
  })

  it('muestra el progreso de las condiciones del cuadro elegido', () => {
    renderTrace(withAlert)
    fireEvent.click(within(list()).getByText('frame_000019'))
    expect(screen.getByText('100 %')).toBeTruthy()
  })

  it('las flechas de navegación se deshabilitan en los extremos', () => {
    renderTrace(few)
    expect(screen.getByRole('button', { name: 'Cuadro anterior' }).hasAttribute('disabled')).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Cuadro siguiente' }))
    expect(screen.getByRole('button', { name: 'Cuadro anterior' }).hasAttribute('disabled')).toBe(false)
  })

  it('una corrida sin traza lo dice en vez de mostrar un panel vacío', () => {
    render(<TraceSection runId="r" frames={[]} totals={totals(0)} />)
    expect(screen.getByText('Esta corrida no tiene traza')).toBeTruthy()
  })
})
