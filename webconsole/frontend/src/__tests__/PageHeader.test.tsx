import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '../test-utils'
import PageHeader from '../components/ui/PageHeader'

afterEach(cleanup)

describe('PageHeader', () => {
  it('muestra la bajada como texto visible bajo el título, sin depender del hover', () => {
    render(<PageHeader title="Corridas" meta="405 corridas" bajada="Una corrida es la ejecución de un solo plano." />)
    expect(screen.getByRole('heading', { name: 'Corridas' })).toBeTruthy()
    const bajada = screen.getByText('Una corrida es la ejecución de un solo plano.')
    expect(bajada.closest('header')).toBeTruthy()
    expect(bajada.getAttribute('title')).toBeNull()
  })

  it('sin bajada no agrega nada', () => {
    const { container } = render(<PageHeader title="X" />)
    expect(container.querySelector('.eo-pageheader__bajada')).toBeNull()
  })
})
