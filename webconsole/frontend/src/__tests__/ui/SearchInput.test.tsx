import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { SearchInput } from '../../components/ui'

afterEach(() => cleanup())

describe('SearchInput', () => {
  it('dispara onChange con cada tecleo', () => {
    const onChange = vi.fn()
    render(<SearchInput value="" onChange={onChange} placeholder="Buscar…" ariaLabel="Buscar corridas" />)
    fireEvent.change(screen.getByLabelText('Buscar corridas'), { target: { value: 'noc' } })
    expect(onChange).toHaveBeenCalledWith('noc')
  })
})
