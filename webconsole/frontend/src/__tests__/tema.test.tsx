import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '../test-utils'
import { MemoryRouter } from 'react-router-dom'
import Shell from '../components/Shell'
import { TEMA_KEY, aplicarTema, leerTema } from '../tema'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue({ service_url: 'x', healthy: true, ready: true, model: null }),
  getPreflight: vi.fn().mockResolvedValue({
    ready: true,
    blockers: [],
    media: { service_url: 'x', healthy: true, ready: true },
    control: { service_url: 'y', healthy: true, ready: true },
  }),
  listRunsPaged: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getExperimentManifests: vi.fn().mockResolvedValue([]),
  listPromptSets: vi.fn().mockResolvedValue([]),
}))

afterEach(() => {
  cleanup()
  localStorage.removeItem(TEMA_KEY)
  delete document.documentElement.dataset.theme
})

const renderShell = () =>
  render(
    <MemoryRouter initialEntries={['/resultados']}>
      <Shell><p>contenido</p></Shell>
    </MemoryRouter>,
  )

describe('los dos temas (plan §10)', () => {
  it('sin preferencia guardada rige el claro: <html> no lleva la marca del oscuro', () => {
    expect(leerTema()).toBe('claro')
    aplicarTema(leerTema())
    expect(document.documentElement.dataset.theme).toBeUndefined()
  })

  it('el selector de la barra lateral pasa al oscuro, lo marca en <html> y lo recuerda', () => {
    renderShell()
    const selector = screen.getByRole('button', { name: 'Tema oscuro' })
    expect(selector.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(selector)
    expect(selector.getAttribute('aria-pressed')).toBe('true')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem(TEMA_KEY)).toBe('oscuro')
  })

  it('la preferencia sobrevive a una recarga, y volver al claro quita la marca', () => {
    localStorage.setItem(TEMA_KEY, 'oscuro')
    renderShell()
    const selector = screen.getByRole('button', { name: 'Tema oscuro' })
    expect(selector.getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(selector)
    expect(document.documentElement.dataset.theme).toBeUndefined()
    expect(localStorage.getItem(TEMA_KEY)).toBe('claro')
  })

  it('un valor desconocido guardado cae al claro', () => {
    localStorage.setItem(TEMA_KEY, 'violeta')
    expect(leerTema()).toBe('claro')
  })
})
