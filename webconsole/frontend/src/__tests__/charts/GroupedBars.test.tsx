import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import GroupedBars, { groupedBarsLayout, SERIES_COLORS } from '../../components/charts/GroupedBars'

// Sin `globals: true` en vite.config, el auto-cleanup de Testing Library no corre
// y el DOM se acumula entre tests. Convención del repo: limpiarlo a mano.
afterEach(() => cleanup())

describe('groupedBarsLayout', () => {
  it('genera un rect por valor no-nulo, escalado al alto del plot', () => {
    const rects = groupedBarsLayout(['person', 'helmet'], [[1, 0.5], [null, 0.25]], 200, 100)
    // serie 0: person=1, helmet=0.5; serie 1: person=null (sin barra), helmet=0.25
    expect(rects).toHaveLength(3)
    expect(rects[0].height).toBe(100)
    expect(rects[0].y).toBe(0)
    expect(rects[1].height).toBe(50)
    expect(rects[1].y).toBe(50)
  })

  it('el color sigue el índice de serie, no el orden de aparición', () => {
    const rects = groupedBarsLayout(['a'], [[null], [0.5]], 100, 100)
    expect(rects).toHaveLength(1)
    expect(rects[0].color).toBe(SERIES_COLORS[1])
  })

  it('las barras quedan dentro del slot de su grupo', () => {
    const width = 200
    const rects = groupedBarsLayout(['a', 'b'], [[0.5, 0.5], [0.5, 0.5]], width, 100)
    const slot = width / 2
    for (const r of rects.filter((r) => r.group === 0)) {
      expect(r.x).toBeGreaterThanOrEqual(0)
      expect(r.x + r.width).toBeLessThanOrEqual(slot)
    }
    for (const r of rects.filter((r) => r.group === 1)) {
      expect(r.x).toBeGreaterThanOrEqual(slot)
      expect(r.x + r.width).toBeLessThanOrEqual(width)
    }
  })

  it('clampa valores fuera de [0,1]', () => {
    const rects = groupedBarsLayout(['a'], [[1.5]], 100, 100)
    expect(rects[0].height).toBe(100)
  })
})

describe('GroupedBars — render', () => {
  it('etiqueta cada barra con su valor: no hace falta leer contra el eje', () => {
    render(
      <GroupedBars
        groups={['person']}
        series={[[0.78], [0.71]]}
        labels={['Barrido diurno', 'Perímetro con lluvia']}
      />,
    )
    expect(screen.getByText('0,78')).toBeTruthy()
    expect(screen.getByText('0,71')).toBeTruthy()
  })

  it('dibuja el eje con marcas redondas de 0 a 1, con coma decimal', () => {
    render(<GroupedBars groups={['person']} series={[[0.5]]} labels={['a']} />)
    expect(screen.getByText('1,00')).toBeTruthy()
    expect(screen.getByText('0,00')).toBeTruthy()
  })

  it('la leyenda nombra cada serie — la identidad nunca es solo color', () => {
    render(
      <GroupedBars
        groups={['person']}
        series={[[0.5], [0.6]]}
        labels={['Barrido diurno', 'Perímetro con lluvia']}
      />,
    )
    expect(screen.getByText('Barrido diurno')).toBeTruthy()
    expect(screen.getByText('Perímetro con lluvia')).toBeTruthy()
  })

  it('nombra las clases del eje horizontal', () => {
    render(<GroupedBars groups={['person', 'helmet']} series={[[0.5, 0.6]]} labels={['a']} />)
    expect(screen.getByText('person')).toBeTruthy()
    expect(screen.getByText('helmet')).toBeTruthy()
  })
})
