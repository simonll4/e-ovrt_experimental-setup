import { describe, expect, it } from 'vitest'
import { areaPaths, niceTicks } from '../../components/charts/layout'

describe('areaPaths', () => {
  it('devuelve rutas vacías con menos de dos valores finitos', () => {
    expect(areaPaths([], 100, 20)).toEqual({ line: '', area: '' })
    expect(areaPaths([5], 100, 20)).toEqual({ line: '', area: '' })
    expect(areaPaths([null, null], 100, 20)).toEqual({ line: '', area: '' })
  })

  it('mapea el primer y el último punto a los bordes del ancho', () => {
    const { line } = areaPaths([0, 10], 100, 20, 0)
    expect(line.startsWith('M0,')).toBe(true)
    expect(line).toContain('L100,')
  })

  it('invierte el eje Y: el valor máximo queda arriba (y menor)', () => {
    const { line } = areaPaths([0, 10], 100, 20, 0)
    const ys = [...line.matchAll(/[ML](?:[\d.]+),([\d.]+)/g)].map((m) => Number(m[1]))
    expect(ys[0]).toBeGreaterThan(ys[1])
  })

  it('una serie constante se dibuja plana a media altura, no dividiendo por cero', () => {
    const { line } = areaPaths([4, 4, 4], 100, 20, 0)
    const ys = [...line.matchAll(/[ML](?:[\d.]+),([\d.]+)/g)].map((m) => Number(m[1]))
    expect(new Set(ys).size).toBe(1)
    expect(ys[0]).toBeCloseTo(10, 5)
    expect(ys.every(Number.isFinite)).toBe(true)
  })

  it('el área cierra contra la línea base y vuelve al origen', () => {
    const { area } = areaPaths([1, 2], 100, 20, 0)
    expect(area.endsWith('Z')).toBe(true)
    expect(area).toContain('L100,20')
    expect(area).toContain('L0,20')
  })

  it('saltea los nulos sin romper la ruta', () => {
    const { line } = areaPaths([1, null, 3], 90, 20, 0)
    const pts = [...line.matchAll(/[ML]([\d.]+),([\d.]+)/g)]
    expect(pts).toHaveLength(2)
    expect(Number(pts[1][1])).toBe(90)
  })
})

describe('niceTicks', () => {
  it('devuelve marcas redondas que cubren el máximo', () => {
    expect(niceTicks(1)).toEqual([0, 0.25, 0.5, 0.75, 1])
  })

  it('el último tick nunca queda por debajo del máximo', () => {
    for (const max of [0.37, 3, 7, 42, 137, 1468]) {
      const ticks = niceTicks(max)
      expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(max)
      expect(ticks[0]).toBe(0)
    }
  })

  it('no devuelve NaN ni ticks duplicados con máximo cero', () => {
    const ticks = niceTicks(0)
    expect(ticks.every(Number.isFinite)).toBe(true)
    expect(new Set(ticks).size).toBe(ticks.length)
  })
})
