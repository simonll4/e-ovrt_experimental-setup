import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { SegmentedControl } from '../../components/ui'

afterEach(() => cleanup())

const OPTS = [
  { value: 'all', label: 'Todas' },
  { value: 'run', label: 'En curso' },
]

describe('SegmentedControl', () => {
  it('marca la opcion activa con aria-pressed', () => {
    render(<SegmentedControl value="all" options={OPTS} onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Todas' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'En curso' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('clic dispara onChange con el value de la opcion', () => {
    const onChange = vi.fn()
    render(<SegmentedControl value="all" options={OPTS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'En curso' }))
    expect(onChange).toHaveBeenCalledWith('run')
  })
})
