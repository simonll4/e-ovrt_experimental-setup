import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Card, ErrorBanner, EmptyState, StatTile, Field, TextInput } from '../../components/ui'

afterEach(() => cleanup())

describe('Card', () => {
  it('muestra título y contenido', () => {
    render(<Card title="Métricas"><p>hola</p></Card>)
    expect(screen.getByText('Métricas')).toBeTruthy()
    expect(screen.getByText('hola')).toBeTruthy()
  })
  it('sin título no renderiza encabezado', () => {
    render(<Card><p>solo</p></Card>)
    expect(screen.queryByRole('heading')).toBeNull()
  })
})

describe('ErrorBanner', () => {
  it('marca el mensaje con role alert', () => {
    render(<ErrorBanner>algo falló</ErrorBanner>)
    expect(screen.getByRole('alert').textContent).toContain('algo falló')
  })
})

describe('EmptyState', () => {
  it('muestra el mensaje', () => {
    render(<EmptyState>Sin corridas todavía.</EmptyState>)
    expect(screen.getByText('Sin corridas todavía.')).toBeTruthy()
  })
  it('con hint, muestra una segunda linea atenuada', () => {
    render(<EmptyState hint="Probá con otro texto.">Ninguna corrida coincide.</EmptyState>)
    expect(screen.getByText('Ninguna corrida coincide.')).toBeTruthy()
    expect(screen.getByText('Probá con otro texto.').className).toContain('eo-empty__hint')
  })
})

describe('StatTile', () => {
  it('muestra label, valor y unidad', () => {
    render(<StatTile label="FPS" value={42} unit="fps" />)
    expect(screen.getByText('FPS')).toBeTruthy()
    expect(screen.getByText('42')).toBeTruthy()
    expect(screen.getByText('fps')).toBeTruthy()
  })
  it('sin unidad no rompe', () => {
    render(<StatTile label="dets" value={7} />)
    expect(screen.getByText('7')).toBeTruthy()
  })
})

describe('Field', () => {
  it('asocia el rótulo con su control por id, sin envolverlo', () => {
    render(<Field label="Stride"><TextInput /></Field>)
    const control = screen.getByLabelText('Stride')
    expect(control.tagName).toBe('INPUT')
    // La ayuda y el error no forman parte del nombre accesible.
    expect(control.closest('label')).toBeNull()
  })
  it('la ayuda y el error describen al control y el error lo marca inválido', () => {
    render(<Field label="Fuente" hint="Una carpeta" error="requerido"><TextInput /></Field>)
    const control = screen.getByLabelText('Fuente')
    const ids = (control.getAttribute('aria-describedby') ?? '').split(' ')
    const textos = ids.map((id) => document.getElementById(id)?.textContent)
    expect(textos).toEqual(['Una carpeta', 'requerido'])
    expect(control.getAttribute('aria-invalid')).toBe('true')
  })
  it('la clave técnica viaja junto al rótulo humano', () => {
    render(<Field label="Cuadros a descartar" labelKey="warmup_frames"><TextInput /></Field>)
    expect(screen.getByLabelText(/Cuadros a descartar.*warmup_frames/)).toBeTruthy()
  })
  it('muestra el error cuando lo hay', () => {
    render(<Field label="Fuente" error="requerido"><input /></Field>)
    expect(screen.getByText('requerido')).toBeTruthy()
  })
  it('sin error no muestra nada de error', () => {
    render(<Field label="Fuente"><input /></Field>)
    expect(screen.queryByText('requerido')).toBeNull()
  })
})
