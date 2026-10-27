import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, simularVentana, waitFor, within } from '../test-utils'
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

afterEach(() => localStorage.removeItem('eovrt-nav-grupos-abiertos'))

const LABORATORIO = ['Corridas', 'Experimentos', 'Comparar', 'Conjuntos de prompts', 'Catálogos', 'Cámaras', 'Clips']

describe('Shell', () => {
  it('renderiza los dos títulos de grupo (doc 135): Evidencia y Laboratorio', () => {
    renderShell()
    expect(screen.getByText('Evidencia')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Laboratorio' })).toBeTruthy()
  })

  it('el grupo Evidencia está siempre a la vista, con la entrada «Para el tribunal»', () => {
    renderShell()
    for (const label of ['Para el tribunal', 'Resultados', 'Demo en vivo', 'Documentación', 'Plataforma']) {
      expect(screen.getByRole('link', { name: label })).toBeTruthy()
    }
    expect(screen.getByRole('link', { name: 'Para el tribunal' }).className).toContain('eo-sidebar__link--active')
  })

  it('el Laboratorio está plegado por defecto y se abre con su botón, que recuerda la preferencia', () => {
    renderShell()
    const toggle = screen.getByRole('button', { name: 'Laboratorio' })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('link', { name: 'Corridas' })).toBeNull()
    fireEvent.click(toggle)
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    for (const label of LABORATORIO) expect(screen.getByRole('link', { name: label })).toBeTruthy()
    expect(JSON.parse(localStorage.getItem('eovrt-nav-grupos-abiertos') ?? '[]')).toEqual(['Laboratorio'])
    cleanup()
    renderShell()
    expect(screen.getByRole('button', { name: 'Laboratorio' }).getAttribute('aria-expanded')).toBe('true')
  })

  it('una pantalla del Laboratorio lo abre sola: el destino activo nunca queda escondido', () => {
    renderShell('/runs/r_1')
    const lateral = within(screen.getByRole('complementary', { name: 'Navegación principal' }))
    expect(lateral.getByRole('button', { name: 'Laboratorio' }).getAttribute('aria-expanded')).toBe('true')
    expect(lateral.getByRole('link', { name: 'Corridas' })).toBeTruthy()
  })

  // "Conjuntos de prompts" no entra en los 214 px de la barra y se cortaba con
  // puntos suspensivos. Se muestra corto, pero el nombre completo sigue siendo el
  // nombre accesible: quien navega con lector de pantalla no pierde información.
  it('acorta la etiqueta que no entra, sin perder el nombre completo', () => {
    renderShell('/prompts')
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

  describe('en pantalla compacta (< 1024 px) la navegación es un cajón modal', () => {
    let restaurar: () => void
    beforeEach(() => { restaurar = simularVentana('compacta') })
    afterEach(() => restaurar())

    const cajon = () => screen.queryByRole('dialog', { name: 'Navegación principal' })

    it('empieza cerrado y sin destinos en el orden de foco', () => {
      renderShell()
      expect(cajon()?.hasAttribute('open') ?? false).toBe(false)
      expect(screen.queryByRole('link', { name: 'Resultados' })).toBeNull()
    })

    it('el botón de menú abre el cajón, lleva el foco adentro y anuncia el estado', () => {
      renderShell()
      const menu = screen.getByRole('button', { name: 'Abrir navegación' })
      expect(menu.getAttribute('aria-expanded')).toBe('false')
      fireEvent.click(menu)
      const dialogo = cajon()!
      expect(dialogo.hasAttribute('open')).toBe(true)
      expect(menu.getAttribute('aria-expanded')).toBe('true')
      expect(dialogo.contains(document.activeElement)).toBe(true)
      expect(within(dialogo).getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
      expect(within(dialogo).getByRole('button', { name: 'Cerrar navegación' })).toBeTruthy()
    })

    it('elegir un destino cierra el cajón y enfoca el encabezado del destino', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <Shell><h1>Destino</h1></Shell>
        </MemoryRouter>,
      )
      fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
      fireEvent.click(within(cajon()!).getByRole('link', { name: 'Resultados' }))
      expect(cajon()).toBeNull() // cerrado, el diálogo no está en el árbol accesible
      await waitFor(() => expect(document.activeElement?.textContent).toBe('Destino'))
    })

    it('Escape cierra el cajón y devuelve el foco al botón de menú', () => {
      renderShell()
      const menu = screen.getByRole('button', { name: 'Abrir navegación' })
      menu.focus()
      fireEvent.click(menu)
      expect(cajon()?.hasAttribute('open')).toBe(true)
      fireEvent.keyDown(cajon()!, { key: 'Escape' })
      expect(cajon()).toBeNull() // cerrado, el diálogo no está en el árbol accesible
      expect(document.activeElement).toBe(menu)
    })

    it('tocar el fondo del cajón lo cierra', () => {
      renderShell()
      fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
      fireEvent.click(cajon()!)
      expect(cajon()).toBeNull() // cerrado, el diálogo no está en el árbol accesible
    })

    it('el botón Cerrar navegación cierra y restaura el foco', () => {
      renderShell()
      const menu = screen.getByRole('button', { name: 'Abrir navegación' })
      menu.focus()
      fireEvent.click(menu)
      fireEvent.click(within(cajon()!).getByRole('button', { name: 'Cerrar navegación' }))
      expect(cajon()).toBeNull() // cerrado, el diálogo no está en el árbol accesible
      expect(document.activeElement).toBe(menu)
    })

    it('mantiene los mismos destinos, conteos y acciones que la barra persistente', () => {
      renderShell()
      fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
      const dialogo = within(cajon()!)
      for (const label of ['Para el tribunal', 'Resultados', 'Demo en vivo', 'Documentación', 'Plataforma']) {
        expect(dialogo.getByRole('link', { name: label })).toBeTruthy()
      }
      // El Laboratorio se pliega y despliega igual que en la barra persistente.
      fireEvent.click(dialogo.getByRole('button', { name: 'Laboratorio' }))
      for (const label of LABORATORIO) expect(dialogo.getByRole('link', { name: label })).toBeTruthy()
      expect(dialogo.getByRole('link', { name: /nueva corrida/i })).toBeTruthy()
      expect(dialogo.getByRole('link', { name: /nuevo experimento/i })).toBeTruthy()
    })
  })

  it('en escritorio no hay barra superior ni cajón: la barra lateral es persistente', () => {
    renderShell()
    expect(screen.queryByRole('button', { name: /navegación/i })).toBeNull()
    expect(screen.getByRole('complementary', { name: 'Navegación principal' }).className).toContain('eo-sidebar')
  })

  it('no muestra un contador cuando el conteo es 0 o todavia no cargo', () => {
    renderShell('/corridas')
    const runsLink = screen.getByRole('link', { name: 'Corridas' })
    expect(runsLink.querySelector('.eo-sidebar__count')).toBeNull()
  })

  it('muestra el contador de corridas en curso cuando es mayor a 0', async () => {
    vi.mocked(api.listRunsPaged).mockResolvedValue({
      items: [{ run_id: 'r1', status: 'running' }],
      total: 1,
    } as never)
    renderShell('/corridas')
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
