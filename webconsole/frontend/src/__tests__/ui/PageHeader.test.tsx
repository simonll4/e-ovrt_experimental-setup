import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { PageHeader } from '../../components/ui'

afterEach(() => cleanup())

describe('PageHeader', () => {
  it('renderiza titulo, meta y acciones', () => {
    render(
      <PageHeader
        title="Corridas"
        meta={<span>9 en total</span>}
        actions={<button>Nueva corrida</button>}
      />,
    )
    expect(screen.getByRole('heading', { name: 'Corridas' })).toBeTruthy()
    expect(screen.getByText('9 en total')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Nueva corrida' })).toBeTruthy()
  })

  it('sin acciones no rompe', () => {
    render(<PageHeader title="Catálogos" meta={<span>Todo lo disponible</span>} />)
    expect(screen.getByRole('heading', { name: 'Catálogos' })).toBeTruthy()
  })
})
