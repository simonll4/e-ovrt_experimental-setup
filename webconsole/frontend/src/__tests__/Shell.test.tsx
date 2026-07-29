import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import { MemoryRouter } from 'react-router-dom'
import Shell from '../components/Shell'
import * as api from '../api'

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
    for (const label of ['Corridas', 'Experimentos', 'Comparar', 'Conjuntos', 'Catálogos', 'Plataforma']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  // "Conjuntos de prompts" no entra en los 214 px de la barra y se cortaba con
  // puntos suspensivos. Se muestra corto, pero el nombre completo sigue siendo el
  // nombre accesible: quien navega con lector de pantalla no pierde información.
  it('acorta la etiqueta que no entra, sin perder el nombre completo', () => {
    renderShell()
    expect(screen.getAllByText('Conjuntos').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Conjuntos de prompts' })).toBeTruthy()
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
    const active = screen.getByRole('link', { name: 'Conjuntos de prompts' })
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

  it('Escape cierra la barra lateral abierta', () => {
    renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    expect(screen.getByRole('complementary').className).toContain('eo-sidebar--open')
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.getByRole('complementary').className).not.toContain('eo-sidebar--open')
  })

  it('hacer click en el scrim cierra la barra lateral', () => {
    const { container } = renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    const scrim = container.querySelector('.eo-sidebar__scrim')
    expect(scrim).toBeTruthy()
    fireEvent.click(scrim as Element)
    expect(screen.getByRole('complementary').className).not.toContain('eo-sidebar--open')
  })

  it('el botón de menú cambia su etiqueta accesible según el estado', () => {
    renderShell()
    const menuButton = screen.getByRole('button', { name: /navegación/i })
    expect(menuButton.getAttribute('aria-label')).toBe('Abrir navegación')
    fireEvent.click(menuButton)
    expect(menuButton.getAttribute('aria-label')).toBe('Cerrar navegación')
  })

  it('no muestra un contador cuando el conteo es 0 o todavia no cargo', () => {
    renderShell()
    const runsLink = screen.getByRole('link', { name: 'Corridas' })
    expect(runsLink.querySelector('.eo-sidebar__count')).toBeNull()
  })

  it('muestra el contador de corridas en curso cuando es mayor a 0', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({
      items: [{ run_id: 'r1', status: 'running' }],
      total: 1,
    } as never)
    renderShell()
    const runsLink = screen.getByRole('link', { name: 'Corridas' })
    await waitFor(() => expect(runsLink.querySelector('.eo-sidebar__count')?.textContent).toBe('1'))
  })

  it('muestra el estado de los motores segun la salud reportada', async () => {
    vi.mocked(api.getPreflight).mockResolvedValue({
      ready: false,
      blockers: ['control down'],
      media: { service_url: 'x', healthy: true, ready: true },
      control: { service_url: 'y', healthy: false, ready: false },
    } as any)
    const { container } = renderShell()
    const services = container.querySelectorAll('.eo-service')
    const [mediaService, controlService] = Array.from(services)
    await waitFor(() =>
      expect(controlService.querySelector('.eo-tip')?.getAttribute('data-tip')).toMatch(
        /Motor de reglas — sin respuesta/i,
      ),
    )
    expect(mediaService.querySelector('.eo-tip')?.getAttribute('data-tip')).toMatch(
      /Motor de detección — operativo/i,
    )
    expect(controlService.querySelector('.eo-service__dot')?.getAttribute('style')).toContain('--er')
    expect(mediaService.querySelector('.eo-service__dot')?.getAttribute('style')).toContain('--ok')
  })

  it('el colapso manual de la barra lateral persiste via localStorage', () => {
    localStorage.removeItem('eovrt-sidebar-collapsed')
    renderShell()
    const collapseButton = screen.getByRole('button', { name: /colapsar barra lateral/i })
    fireEvent.click(collapseButton)
    expect(screen.getByRole('complementary').className).toContain('eo-sidebar--collapsed')
    expect(localStorage.getItem('eovrt-sidebar-collapsed')).toBe('1')
  })
})
