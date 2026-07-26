import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import Badge from '../../components/ui/Badge'

afterEach(() => cleanup())

describe('Badge', () => {
  it('aplica la clase del tono', () => {
    render(<Badge tone="error">falló</Badge>)
    expect(screen.getByText('falló').className).toContain('eo-badge--error')
  })

  it('siempre lleva la clase base', () => {
    render(<Badge tone="ok">listo</Badge>)
    const el = screen.getByText('listo')
    expect(el.className).toContain('eo-badge')
    expect(el.className).toContain('eo-badge--ok')
  })

  it('soporta el tono alert (alerta confirmada, distinto de warn)', () => {
    render(<Badge tone="alert">alerta</Badge>)
    expect(screen.getByText('alerta').className).toContain('eo-badge--alert')
  })
})
