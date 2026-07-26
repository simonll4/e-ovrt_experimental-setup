import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Select } from '../../components/ui'
import type { SelectOption } from '../../components/ui'

afterEach(() => cleanup())

const OPTIONS: SelectOption[] = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'archived', label: 'Archivadas', disabled: true, disabledReason: 'sin acceso' },
]

describe('Select', () => {
  it('muestra la etiqueta del valor seleccionado, cerrado por defecto', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    expect(screen.getByText('Todas')).toBeTruthy()
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('abre la lista al hacer click en el control', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('listbox')).toBeTruthy()
    expect(screen.getByRole('option', { name: 'En curso' })).toBeTruthy()
  })

  it('elegir una opción llama a onChange con su value y cierra la lista', () => {
    const onChange = vi.fn()
    render(<Select value="all" options={OPTIONS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button'))
    fireEvent.click(screen.getByRole('option', { name: 'En curso' }))
    expect(onChange).toHaveBeenCalledWith('running')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('una opción deshabilitada no dispara onChange y muestra el motivo', () => {
    const onChange = vi.fn()
    render(<Select value="all" options={OPTIONS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button'))
    const disabledOpt = screen.getByRole('option', { name: 'Archivadas' })
    expect(disabledOpt.getAttribute('title')).toBe('sin acceso')
    fireEvent.click(disabledOpt)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('Escape cierra la lista', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('listbox')).toBeTruthy()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})
