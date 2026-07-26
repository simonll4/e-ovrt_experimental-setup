import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Shell from '../components/Shell'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue(null),
  listRuns: vi.fn().mockResolvedValue([]),
}))

afterEach(() => cleanup())

const renderShell = (path = '/') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Shell><p>contenido</p></Shell>
    </MemoryRouter>,
  )

describe('Shell', () => {
  it('renderiza los tres títulos de grupo', () => {
    renderShell()
    expect(screen.getByText('Trabajo')).toBeTruthy()
    expect(screen.getByText('Definiciones')).toBeTruthy()
    expect(screen.getByText('Sistema')).toBeTruthy()
  })

  it('renderiza los 6 destinos', () => {
    renderShell()
    for (const label of ['Corridas', 'Experimentos', 'Comparar', 'Prompt sets', 'Catálogos', 'Plataforma']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  it('"Nueva corrida" es acción primaria y apunta a /compose', () => {
    renderShell()
    const link = screen.getByRole('link', { name: /nueva corrida/i })
    expect(link.getAttribute('href')).toContain('/compose')
    expect(link.className).toContain('eo-sidebar__action')
  })

  it('"Nuevo experimento" es acción primaria y apunta a /experiments/new', () => {
    renderShell()
    const link = screen.getByRole('link', { name: /nuevo experimento/i })
    expect(link.getAttribute('href')).toContain('/experiments/new')
    expect(link.className).toContain('eo-sidebar__action')
  })

  it('marca el destino activo', () => {
    renderShell('/prompts')
    const active = screen.getByRole('link', { name: 'Prompt sets' })
    expect(active.className).toContain('eo-sidebar__link--active')
  })

  it('renderiza el contenido hijo', () => {
    renderShell()
    expect(screen.getByText('contenido')).toBeTruthy()
  })

  it('la barra lateral empieza cerrada (modo pantalla chica)', () => {
    renderShell()
    const aside = screen.getByRole('complementary')
    expect(aside.className).not.toContain('eo-sidebar--open')
  })

  it('el botón de menú abre la barra lateral', () => {
    renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    expect(screen.getByRole('complementary').className).toContain('eo-sidebar--open')
  })

  it('elegir un destino de la nav cierra la barra lateral', () => {
    renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    fireEvent.click(screen.getByRole('link', { name: 'Experimentos' }))
    expect(screen.getByRole('complementary').className).not.toContain('eo-sidebar--open')
  })
})
