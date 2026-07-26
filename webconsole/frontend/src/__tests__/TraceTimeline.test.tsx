import { describe, expect, it, afterEach, beforeEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import TraceTimeline from '../components/TraceTimeline'
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
