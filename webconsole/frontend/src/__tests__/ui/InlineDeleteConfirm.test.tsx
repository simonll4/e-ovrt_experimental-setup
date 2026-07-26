import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { InlineDeleteConfirm } from '../../components/ui'

afterEach(() => cleanup())

describe('InlineDeleteConfirm', () => {
  it('"Si, borrar" dispara onConfirm; "No" dispara onCancel', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(<InlineDeleteConfirm onConfirm={onConfirm} onCancel={onCancel} />)
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('No dispara onCancel', () => {
    const onCancel = vi.fn()
    render(<InlineDeleteConfirm onConfirm={() => {}} onCancel={onCancel} />)
    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    expect(onCancel).toHaveBeenCalled()
  })
})
