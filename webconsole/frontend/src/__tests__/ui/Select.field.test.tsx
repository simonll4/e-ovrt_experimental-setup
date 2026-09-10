import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Field, Select } from '../../components/ui'

afterEach(cleanup)

describe('Select dentro de Field', () => {
  it('cancela la activación del label al elegir, sin reabrir el control', () => {
    const onChange = vi.fn()
    render(<Field label="Fuente"><Select value="a" ariaLabel="Fuente"
      options={[{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }]}
      onChange={onChange} /></Field>)
    fireEvent.click(screen.getByRole('button', { name: 'Fuente' }))
    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    fireEvent(screen.getByRole('option', { name: 'B' }), click)
    expect(click.defaultPrevented).toBe(true)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('b')
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(screen.getByRole('button', { name: 'Fuente' }).getAttribute('aria-expanded')).toBe('false')
  })
})
