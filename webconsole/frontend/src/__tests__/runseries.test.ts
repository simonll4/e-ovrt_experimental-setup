import { describe, expect, it } from 'vitest'
import { buildRunSeries, recentDelta, windowMean } from '../runseries'
import type { TraceDetection, TraceFrame } from '../types'

const dets = (n: number): TraceDetection[] =>
  Array.from({ length: n }, () => ({ label: 'person', confidence: 0.9 }))

const f = (i: number, ts: number | null, n: number): TraceFrame => ({
  frame_index: i,
  unit_id: `frame_${i}`,
  timestamp_ms: ts,
  detections: dets(n),
  control: 'received',
  progress: [],
  alert: [],
  active_patterns: [],
})

describe('buildRunSeries', () => {
  it('cuenta detecciones por cuadro', () => {
    const s = buildRunSeries([f(0, 0, 2), f(1, 500, 0), f(2, 1000, 3)])
    expect(s.detectionsPerFrame).toEqual([2, 0, 3])
  })

  it('el tiempo transcurrido arranca en 0 y es relativo al primer cuadro', () => {
    const s = buildRunSeries([f(0, 1000, 0), f(1, 1500, 0), f(2, 3000, 0)])
    expect(s.elapsedSeconds).toEqual([0, 0.5, 2])
    expect(s.totalSeconds).toBe(2)
  })

  it('el fps instantáneo es el inverso del delta entre cuadros; el primero es null', () => {
    const s = buildRunSeries([f(0, 0, 0), f(1, 500, 0), f(2, 750, 0)])
    expect(s.instantFps[0]).toBeNull()
    expect(s.instantFps[1]).toBeCloseTo(2, 6)
    expect(s.instantFps[2]).toBeCloseTo(4, 6)
  })

  it('un delta de cero da null, no Infinity', () => {
    const s = buildRunSeries([f(0, 1000, 0), f(1, 1000, 0)])
    expect(s.instantFps[1]).toBeNull()
  })

  it('tolera timestamps ausentes sin propagar NaN', () => {
    const s = buildRunSeries([f(0, null, 1), f(1, null, 2)])
    expect(s.detectionsPerFrame).toEqual([1, 2])
    expect(s.elapsedSeconds.every(Number.isFinite)).toBe(true)
    expect(s.totalSeconds).toBe(0)
  })

  it('con cero cuadros devuelve series vacías', () => {
    expect(buildRunSeries([])).toEqual({
      detectionsPerFrame: [],
      instantFps: [],
      elapsedSeconds: [],
      totalSeconds: 0,
    })
  })
})

describe('windowMean', () => {
  it('promedia solo los valores dentro de la ventana', () => {
    expect(windowMean([1, 2, 3, 4], [0, 1, 2, 3], 2, 3)).toBe(3.5)
  })

  it('devuelve null si la ventana no tiene ningún valor', () => {
    expect(windowMean([1, 2], [0, 1], 10, 20)).toBeNull()
  })

  it('ignora los nulos en vez de contarlos como cero', () => {
    expect(windowMean([null, 4], [0, 1], 0, 1)).toBe(4)
  })

  it('openUpper excluye el borde superior, para que dos ventanas no lo compartan', () => {
    expect(windowMean([1, 2, 3], [0, 1, 2], 0, 2)).toBe(2)
    expect(windowMean([1, 2, 3], [0, 1, 2], 0, 2, true)).toBe(1.5)
  })
})

describe('recentDelta', () => {
  it('compara la última ventana contra la anterior', () => {
    const seconds = Array.from({ length: 61 }, (_, i) => i)
    const values = seconds.map((s) => (s < 30 ? 1 : 3))
    expect(recentDelta(values, seconds, 30)).toBeCloseTo(2, 6)
  })

  it('devuelve null si no hay dos ventanas completas — el delta no se inventa', () => {
    expect(recentDelta([1, 2], [0, 1], 30)).toBeNull()
  })
})
