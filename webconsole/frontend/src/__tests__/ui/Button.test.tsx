import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Button } from '../../components/ui'

afterEach(() => cleanup())

describe('Button', () => {
  it('por defecto es variant secondary', () => {
    render(<Button>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' }).className).toContain('eo-btn--secondary')
  })

  it('variant primary', () => {
    render(<Button variant="primary">Lanzar</Button>)
    expect(screen.getByRole('button', { name: 'Lanzar' }).className).toContain('eo-btn--primary')
  })

  it('variant danger', () => {
    render(<Button variant="danger">Borrar</Button>)
    expect(screen.getByRole('button', { name: 'Borrar' }).className).toContain('eo-btn--danger')
  })

  it('variant ghost', () => {
    render(<Button variant="ghost">Cancelar</Button>)
    expect(screen.getByRole('button', { name: 'Cancelar' }).className).toContain('eo-btn--ghost')
  })

  it('siempre lleva la clase base eo-btn y pasa props nativas (disabled, onClick, type)', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick} disabled type="submit">X</Button>)
    const btn = screen.getByRole('button', { name: 'X' }) as HTMLButtonElement
    expect(btn.className).toContain('eo-btn')
    expect(btn.disabled).toBe(true)
    expect(btn.type).toBe('submit')
    fireEvent.click(btn)
    expect(onClick).not.toHaveBeenCalled() // disabled: no debe disparar
  })
})
