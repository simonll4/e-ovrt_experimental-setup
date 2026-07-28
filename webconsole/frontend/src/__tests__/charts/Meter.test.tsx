import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import Meter from '../../components/charts/Meter'

afterEach(() => cleanup())

describe('Meter', () => {
  it('cada segmento lleva su etiqueta accesible — nunca solo color', () => {
    render(
      <Meter
        segments={[
          { value: 2, tone: 'ok', label: 'cumplen' },
          { value: 1, tone: 'error', label: 'no cumple' },
        ]}
      />,
    )
    expect(screen.getByTitle('cumplen: 2')).toBeTruthy()
    expect(screen.getByTitle('no cumple: 1')).toBeTruthy()
  })

  it('reparte el ancho en proporción al valor', () => {
    const { container } = render(
      <Meter
        segments={[
          { value: 3, tone: 'ok', label: 'a' },
          { value: 1, tone: 'warn', label: 'b' },
        ]}
      />,
    )
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect((parts[0] as HTMLElement).style.width).toBe('75%')
    expect((parts[1] as HTMLElement).style.width).toBe('25%')
  })

  it('con `total` explícito el resto queda vacío, no estirado', () => {
    const { container } = render(<Meter total={4} segments={[{ value: 1, tone: 'ok', label: 'a' }]} />)
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect(parts).toHaveLength(1)
    expect((parts[0] as HTMLElement).style.width).toBe('25%')
  })

  it('no divide por cero cuando todos los valores son 0', () => {
    const { container } = render(<Meter segments={[{ value: 0, tone: 'ok', label: 'a' }]} />)
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect((parts[0] as HTMLElement).style.width).toBe('0%')
  })

  it('describe el conjunto para lectores de pantalla', () => {
    render(
      <Meter
        segments={[
          { value: 1, tone: 'error', label: 'alta' },
          { value: 2, tone: 'warn', label: 'media' },
        ]}
      />,
    )
    expect(screen.getByRole('img', { name: 'alta: 1, media: 2' })).toBeTruthy()
  })
})
