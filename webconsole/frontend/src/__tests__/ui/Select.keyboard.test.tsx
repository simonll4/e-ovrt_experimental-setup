import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Field, Select } from '../../components/ui'
import type { SelectOption } from '../../components/ui'

afterEach(() => cleanup())

const OPCIONES: SelectOption[] = [
  { value: 'a', label: 'Alfa' },
  { value: 'b', label: 'Bravo', disabled: true, disabledReason: 'No montado' },
  { value: 'c', label: 'Charlie' },
  { value: 'd', label: 'Delta' },
]

const montar = (onChange = vi.fn(), value = 'a') => {
  render(<Select value={value} options={OPCIONES} onChange={onChange} ariaLabel="Conjunto" />)
  return { boton: screen.getByRole('button', { name: /^Conjunto/ }), onChange }
}

const activa = () => {
  const lista = screen.getByRole('listbox')
  const id = lista.getAttribute('aria-activedescendant')
  return id ? document.getElementById(id)?.getAttribute('aria-label') : null
}

describe('Select con teclado', () => {
  it('el botón se anuncia con el rótulo y el valor elegido; la lista, con el rótulo', () => {
    const { boton } = montar(vi.fn(), 'c')
    expect(screen.getByRole('button', { name: 'Conjunto Charlie' })).toBe(boton)
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    expect(screen.getByRole('listbox', { name: 'Conjunto' })).toBeTruthy()
  })

  it('flecha abajo abre, lleva el foco a la lista y marca la opción elegida como activa', () => {
    const { boton } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    expect(document.activeElement).toBe(lista)
    expect(boton.getAttribute('aria-expanded')).toBe('true')
    expect(boton.getAttribute('aria-controls')).toBe(lista.id)
    expect(activa()).toBe('Alfa')
  })

  it('las flechas saltean las opciones deshabilitadas; Inicio y Fin van a los extremos', () => {
    const { boton } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    fireEvent.keyDown(lista, { key: 'ArrowDown' })
    expect(activa()).toBe('Charlie')
    fireEvent.keyDown(lista, { key: 'End' })
    expect(activa()).toBe('Delta')
    fireEvent.keyDown(lista, { key: 'Home' })
    expect(activa()).toBe('Alfa')
    fireEvent.keyDown(lista, { key: 'ArrowUp' })
    expect(activa()).toBe('Alfa')
  })

  it('escribir las primeras letras busca entre las habilitadas', () => {
    const { boton } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    fireEvent.keyDown(lista, { key: 'd' })
    expect(activa()).toBe('Delta')
    // «b» es Bravo, deshabilitada: no se activa.
    fireEvent.keyDown(lista, { key: 'b' })
    expect(activa()).toBe('Delta')
  })

  it('Enter confirma una sola vez, cierra y devuelve el foco al botón', () => {
    const { boton, onChange } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    fireEvent.keyDown(lista, { key: 'ArrowDown' })
    fireEvent.keyDown(lista, { key: 'Enter' })
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('c')
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(document.activeElement).toBe(boton)
    // El click que el navegador asocia a soltar la tecla no reabre la lista.
    fireEvent.keyUp(boton, { key: 'Enter' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('Espacio confirma y el click de soltar la tecla no reabre ni vuelve a elegir', () => {
    const { boton, onChange } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    fireEvent.keyDown(lista, { key: 'End' })
    fireEvent.keyDown(lista, { key: ' ' })
    fireEvent.keyUp(boton, { key: ' ' })
    fireEvent.click(boton)
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith('d')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('Escape cierra sin cambiar el valor', () => {
    const { boton, onChange } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    const lista = screen.getByRole('listbox')
    fireEvent.keyDown(lista, { key: 'ArrowDown' })
    fireEvent.keyDown(lista, { key: 'Escape' })
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(document.activeElement).toBe(boton)
  })

  it('Tab cierra y deja el foco en el botón para seguir el recorrido', () => {
    const { boton, onChange } = montar()
    fireEvent.keyDown(boton, { key: 'ArrowDown' })
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Tab' })
    expect(screen.queryByRole('listbox')).toBeNull()
    expect(document.activeElement).toBe(boton)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('el motivo de una opción deshabilitada se ve y la describe', () => {
    const { boton } = montar()
    fireEvent.click(boton)
    const bravo = screen.getByRole('option', { name: 'Bravo' })
    expect(bravo.getAttribute('aria-disabled')).toBe('true')
    const motivo = document.getElementById(bravo.getAttribute('aria-describedby') ?? '')
    expect(motivo?.textContent).toBe('No montado')
  })

  it('la lista se monta fuera del control (portal), sin quedar recortada por su contenedor', () => {
    const { container } = render(
      <div style={{ overflow: 'hidden' }}>
        <Select value="a" options={OPCIONES} onChange={() => {}} ariaLabel="Recortado" />
      </div>,
    )
    fireEvent.click(screen.getByRole('button', { name: /^Recortado/ }))
    expect(container.contains(screen.getByRole('listbox'))).toBe(false)
    expect(screen.getByRole('listbox').style.position).toBe('fixed')
  })

  it('dentro de un Field sin ariaLabel toma el rótulo y la ayuda del campo', () => {
    render(
      <Field label="Fuente" hint="Una de las montadas">
        <Select value="a" options={OPCIONES} onChange={() => {}} />
      </Field>,
    )
    const boton = screen.getByRole('button', { name: /Fuente/ })
    const ayuda = document.getElementById(boton.getAttribute('aria-describedby') ?? '')
    expect(ayuda?.textContent).toBe('Una de las montadas')
  })
})
