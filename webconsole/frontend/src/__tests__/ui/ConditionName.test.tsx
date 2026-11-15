import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ConditionName } from '../../components/ui'

afterEach(() => cleanup())

describe('ConditionName', () => {
  it('renderiza el código en su propia marca, más chica (eo-codigo)', () => {
    render(<ConditionName code="CR-01" />)
    const el = screen.getByText('CR-01')
    expect(el.className).toContain('eo-codigo')
  })

  it('pone el nombre llano antes del código para un código conocido (plan §4.2)', () => {
    const { container } = render(<ConditionName code="CR-01" />)
    expect(container.textContent).toBe('Sin casco CR-01')
  })

  it('un codigo desconocido muestra solo el codigo, sin separador colgando', () => {
    const { container } = render(<ConditionName code="CR-99" />)
    expect(container.textContent).toBe('CR-99')
  })
})
