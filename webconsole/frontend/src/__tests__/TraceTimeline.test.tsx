import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import TraceTimeline, { MAX_TICKS } from '../components/TraceTimeline'
import type { TraceFrame } from '../types'

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})
afterEach(() => cleanup())

function frame(overrides: Partial<TraceFrame> = {}): TraceFrame {
  return {
    frame_index: 0,
    unit_id: 'u0',
    timestamp_ms: 0,
    detections: [],
    control: 'received',
    progress: [],
    alert: [],
    ...overrides,
  }
}

describe('TraceTimeline', () => {
  it('sin frames no renderiza nada', () => {
    const { container } = render(<TraceTimeline frames={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renderiza un tick por frame', () => {
    render(
      <TraceTimeline
        frames={[frame({ frame_index: 0, unit_id: 'u0' }), frame({ frame_index: 1, unit_id: 'u1' })]}
      />,
    )
    expect(document.querySelectorAll('.eo-timeline__tick').length).toBe(2)
  })

  it('un frame con alerta confirmada lleva el modificador --alert', () => {
    render(
      <TraceTimeline
        frames={[
          frame({ frame_index: 0, unit_id: 'u0' }),
          frame({ frame_index: 1, unit_id: 'u1', alert: [{ condition_id: 'CR-02', severity: 'high' }] }),
        ]}
      />,
    )
    const ticks = document.querySelectorAll('.eo-timeline__tick')
    expect(ticks[0].className).not.toContain('--alert')
    expect(ticks[1].className).toContain('--alert')
  })

  it('clickear un tick hace scrollIntoView sobre la fila del frame correspondiente', () => {
    render(<TraceTimeline frames={[frame({ frame_index: 5, unit_id: 'u5' })]} />)
    const target = document.createElement('tr')
    target.id = 'frame-u5'
    document.body.appendChild(target)
    fireEvent.click(screen.getByRole('button', { name: '#5 · u5' }))
    expect(target.scrollIntoView).toHaveBeenCalled()
    document.body.removeChild(target)
  })

  it('con más cuadros que el tope, agrupa en como máximo MAX_TICKS ticks', () => {
    const frames = Array.from({ length: 5000 }, (_, i) =>
      frame({ frame_index: i, unit_id: `u${i}` }),
    )
    render(<TraceTimeline frames={frames} />)
    const ticks = document.querySelectorAll('.eo-timeline__tick')
    expect(ticks.length).toBeLessThanOrEqual(MAX_TICKS)
    // 5000 / 400 -> tramos de 13 cuadros
    expect(ticks[0].getAttribute('aria-label')).toBe('cuadros #0–#12')
  })

  it('un tramo que contiene una alerta se pinta como alerta', () => {
    const frames = Array.from({ length: 5000 }, (_, i) =>
      frame({
        frame_index: i,
        unit_id: `u${i}`,
        alert: i === 1205 ? [{ condition_id: 'CR-01', severity: 'high' }] : [],
      }),
    )
    render(<TraceTimeline frames={frames} />)
    const ticks = Array.from(document.querySelectorAll('.eo-timeline__tick'))
    const alertTicks = ticks.filter((t) => t.className.includes('--alert'))
    expect(alertTicks.length).toBe(1)
    // el cuadro 1205 cae en el tramo que arranca en 1196 (13 cuadros por tramo)
    expect(alertTicks[0].getAttribute('aria-label')).toBe('cuadros #1196–#1208')
  })

  it('un tramo con descarte sin alerta usa el tono de descarte', () => {
    const frames = Array.from({ length: 800 }, (_, i) =>
      frame({
        frame_index: i,
        unit_id: `u${i}`,
        control: i === 3 ? 'dropped:rate_gate' : 'received',
      }),
    )
    render(<TraceTimeline frames={frames} />)
    const ticks = Array.from(document.querySelectorAll('.eo-timeline__tick')) as HTMLElement[]
    // tramos de 2 cuadros: el 3 cae en el tick índice 1
    expect(ticks[1].style.background).toContain('--status-warn')
    expect(ticks[0].style.background).toContain('--status-ok')
  })

  it('clickear un tick agrupado delega en onTickClick con el primer cuadro del tramo', () => {
    const frames = Array.from({ length: 800 }, (_, i) =>
      frame({ frame_index: i, unit_id: `u${i}` }),
    )
    const onTickClick = vi.fn()
    render(<TraceTimeline frames={frames} onTickClick={onTickClick} />)
    const ticks = document.querySelectorAll('.eo-timeline__tick')
    fireEvent.click(ticks[5])
    expect(onTickClick).toHaveBeenCalledWith(10, 'u10')
  })

  it('cada tick tiene un aria-label no vacío', () => {
    render(
      <TraceTimeline
        frames={[frame({ frame_index: 0, unit_id: 'u0' }), frame({ frame_index: 1, unit_id: 'u1' })]}
      />,
    )
    const ticks = screen.getAllByRole('button')
    expect(ticks.length).toBe(2)
    ticks.forEach((t) => expect(t.getAttribute('aria-label')).toBeTruthy())
  })
})
