import { describe, expect, it } from 'vitest'
import { frameAtX, timelineLayout } from '../../components/charts/timeline'
import type { TraceDetection, TraceFrame } from '../../types'

const det = (label = 'person'): TraceDetection => ({ label, confidence: 0.9 })

const f = (over: Partial<TraceFrame> = {}): TraceFrame => ({
  frame_index: 0,
  unit_id: 'u',
  timestamp_ms: 0,
  detections: [],
  control: 'received',
  progress: [],
  alert: [],
  active_patterns: [],
  ...over,
})

describe('timelineLayout', () => {
  it('el área sigue la cantidad de detecciones por cuadro', () => {
    const frames = [
      f({ frame_index: 0, detections: [] }),
      f({ frame_index: 1, detections: [det(), det()] }),
    ]
    const out = timelineLayout(frames, 100, 40)
    expect(out.maxDetections).toBe(2)
    expect(out.line).not.toBe('')
  })

  it('marca un descarte por cada cuadro con control dropped:*', () => {
    const frames = [
      f({ frame_index: 0, control: 'received' }),
      f({ frame_index: 1, control: 'dropped:queue_full' }),
    ]
    const marks = timelineLayout(frames, 100, 40).marks
    expect(marks).toHaveLength(1)
    expect(marks[0].kind).toBe('dropped')
    expect(marks[0].frameIndex).toBe(1)
  })

  it('distingue no recibido de descartado — son cosas distintas', () => {
    const frames = [f({ frame_index: 0, control: 'not_received' })]
    expect(timelineLayout(frames, 100, 40).marks[0].kind).toBe('not_received')
  })

  it('marca alerta además del estado de entrega en el mismo cuadro', () => {
    const frames = [
      f({ frame_index: 0, control: 'dropped:rate_gate', alert: [{ condition_id: 'CR-01', severity: 'high' }] }),
    ]
    const kinds = timelineLayout(frames, 100, 40).marks.map((m) => m.kind).sort()
    expect(kinds).toEqual(['alert', 'dropped'])
  })

  it('no produce marcas de ancho cero con muchos cuadros', () => {
    const frames = Array.from({ length: 5000 }, (_, i) =>
      f({ frame_index: i, control: 'dropped:queue_full' }),
    )
    const marks = timelineLayout(frames, 800, 40).marks
    expect(marks.every((m) => m.width >= 1)).toBe(true)
  })

  it('con cero cuadros devuelve un layout vacío, no NaN', () => {
    expect(timelineLayout([], 100, 40)).toEqual({ line: '', area: '', marks: [], maxDetections: 0 })
  })
})

describe('frameAtX', () => {
  it('mapea el borde izquierdo al primer cuadro y el derecho al último', () => {
    expect(frameAtX(0, 100, 10)).toBe(0)
    expect(frameAtX(100, 100, 10)).toBe(9)
  })

  it('acota fuera de rango en vez de devolver un índice inválido', () => {
    expect(frameAtX(-50, 100, 10)).toBe(0)
    expect(frameAtX(999, 100, 10)).toBe(9)
  })

  it('devuelve -1 sin cuadros', () => {
    expect(frameAtX(10, 100, 0)).toBe(-1)
  })
})
