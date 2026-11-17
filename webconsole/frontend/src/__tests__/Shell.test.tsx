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

const DESTINOS = ['Inicio', 'Pruebas', 'Tomas en vivo', 'Cómo leer', 'Plataforma', 'Correr un clip', 'Demo con cámara', 'Archivo']
const LABORATORIO = ['Corridas', 'Experimentos', 'Comparar', 'Conjuntos de prompts', 'Catálogos', 'Cámaras', 'Clips']

describe('Shell', () => {
  it('dos zonas en orden, Evidencia y Demostrar, y el Archivo al pie (plan de la consola, §3)', () => {
    renderShell()
    const lateral = within(screen.getByRole('complementary', { name: 'Navegación principal' }))
    expect(lateral.getByRole('group', { name: 'Evidencia' })).toBeTruthy()
    expect(lateral.getByRole('group', { name: 'Demostrar' })).toBeTruthy()
    const nav = lateral.getByRole('navigation', { name: 'Secciones' })
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('aria-label'))).toEqual(DESTINOS)
    expect(within(nav).getByRole('link', { name: 'Archivo' }).getAttribute('href')).toBe('/archivo')
  })

  it('sin «Para el tribunal», sin el laboratorio y sin los botones de nueva corrida y nuevo experimento', () => {
    renderShell()
    expect(screen.queryByText(/tribunal/i)).toBeNull()
    for (const label of LABORATORIO) expect(screen.queryByRole('link', { name: label })).toBeNull()
    expect(screen.queryByRole('link', { name: /nueva corrida/i })).toBeNull()
    expect(screen.queryByRole('link', { name: /nuevo experimento/i })).toBeNull()
  })

  it('marca el destino activo, también en sus hojas', () => {
    // La miga también enlaza «Pruebas»: se mira la barra lateral.
    const barra = () => within(screen.getByRole('navigation', { name: 'Secciones' }))
    renderShell('/resultados/ALR-01')
    const activo = barra().getByRole('link', { name: 'Pruebas' })
    expect(activo.className).toContain('eo-sidebar__link--active')
    expect(activo.getAttribute('aria-current')).toBe('page')
    cleanup()
    renderShell('/demo/resultado/demo_x')
    expect(barra().getByRole('link', { name: 'Tomas en vivo' }).getAttribute('aria-current')).toBe('page')
    expect(barra().getByRole('link', { name: 'Demo con cámara' }).getAttribute('aria-current')).toBeNull()
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
      expect(screen.queryByRole('link', { name: 'Pruebas' })).toBeNull()
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
      fireEvent.click(within(cajon()!).getByRole('link', { name: 'Pruebas' }))
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

    it('mantiene los mismos destinos que la barra persistente, en el mismo orden', () => {
      renderShell()
      fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
      const nav = within(cajon()!).getByRole('navigation', { name: 'Secciones' })
      expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('aria-label'))).toEqual(DESTINOS)
    })
  })

  it('en escritorio no hay barra superior ni cajón: la barra lateral es persistente', () => {
    renderShell()
    expect(screen.queryByRole('button', { name: /navegación/i })).toBeNull()
    expect(screen.getByRole('complementary', { name: 'Navegación principal' }).className).toContain('eo-sidebar')
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

describe('Modo presentación (plan de la consola, §7.3)', () => {
  it('en cualquier pantalla: sin la barra lateral, con los destinos de Demostrar que conservan el modo', () => {
    renderShell('/platform?proyectar=1')
    expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull()
    const franja = within(screen.getByRole('navigation', { name: 'Demostrar' }))
    expect(franja.getAllByRole('link').map((a) => [a.textContent, a.getAttribute('href')])).toEqual([
      ['Plataforma', '/platform?proyectar=1'], ['Correr un clip', '/correr-clip?proyectar=1'],
      ['Demo con cámara', '/demo?proyectar=1'], ['Volver a la consola P', '/platform'],
    ])
    expect(franja.getByRole('link', { name: 'Plataforma' }).getAttribute('aria-current')).toBe('page')
    expect(screen.getByText('contenido')).toBeTruthy()
  })

  it('se entra desde la barra y con la tecla P, y con P se sale; escribir una p en un campo no cuenta', async () => {
    renderShell('/resultados')
    expect(screen.getByRole('link', { name: /Modo presentación/ }).getAttribute('href')).toBe('/resultados?proyectar=1')
    const campo = document.createElement('input')
    document.body.appendChild(campo)
    fireEvent.keyDown(campo, { key: 'p' })
    expect(screen.getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy()
    campo.remove()
    fireEvent.keyDown(window, { key: 'p' })
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Navegación principal' })).toBeNull())
    fireEvent.keyDown(window, { key: 'P' })
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Navegación principal' })).toBeTruthy())
  })
})
