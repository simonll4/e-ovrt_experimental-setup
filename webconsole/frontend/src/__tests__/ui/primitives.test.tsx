import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Card, ErrorBanner, EmptyState, StatTile, Field } from '../../components/ui'

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
  it('envuelve el control en un <label>', () => {
    const { container } = render(<Field label="Stride"><input id="stride" /></Field>)
    const label = container.querySelector('label')
    expect(label?.tagName).toBe('LABEL')
    expect(label?.textContent).toContain('Stride')
    expect(label?.querySelector('#stride')).toBeTruthy()
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
