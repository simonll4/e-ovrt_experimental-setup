import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { ConditionName } from '../../components/ui'

afterEach(() => cleanup())

describe('ConditionName', () => {
  it('renderiza el código en un elemento eo-mono', () => {
    render(<ConditionName code="CR-01" />)
    const el = screen.getByText('CR-01')
    expect(el.className).toContain('eo-mono')
  })

  it('agrega el nombre despues del codigo para un codigo conocido', () => {
    const { container } = render(<ConditionName code="CR-01" />)
    expect(container.textContent).toBe('CR-01 — Presencia de persona sin casco')
  })

  it('un codigo desconocido muestra solo el codigo, sin separador colgando', () => {
    const { container } = render(<ConditionName code="CR-99" />)
    expect(container.textContent).toBe('CR-99')
  })
})
