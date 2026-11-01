import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '../test-utils'
import Ayuda from '../components/ui/Ayuda'

afterEach(cleanup)

describe('Ayuda', () => {
  it('describe al elemento con aria-describedby, para el lector de pantalla', () => {
    render(
      <Ayuda titulo="CR-01" texto="Persona sin casco.">
        {(p) => <button type="button" {...p}>cr01_neg</button>}
      </Ayuda>,
    )
    const boton = screen.getByRole('button', { name: 'cr01_neg' })
    const tip = screen.getByRole('tooltip')
    expect(boton.getAttribute('aria-describedby')).toBe(tip.id)
    expect(tip.textContent).toContain('CR-01')
    expect(tip.textContent).toContain('Persona sin casco.')
  })

  it('un elemento que no es interactivo se vuelve enfocable, para que el teclado llegue', () => {
    render(<Ayuda texto="Congelado: no se modifica."><span>edir_v1</span></Ayuda>)
    const envoltorio = screen.getByText('edir_v1').closest('.eo-ayuda') as HTMLElement
    expect(envoltorio.tabIndex).toBe(0)
    expect(envoltorio.getAttribute('aria-describedby')).toBe(screen.getByRole('tooltip').id)
  })

  it('con un elemento interactivo no suma una segunda parada de tabulación', () => {
    render(
      <Ayuda texto="x">{(p) => <button type="button" {...p}>a</button>}</Ayuda>,
    )
    expect((document.querySelector('.eo-ayuda') as HTMLElement).hasAttribute('tabindex')).toBe(false)
  })

  it('Escape la cierra sin mover el foco, y se vuelve a abrir al salir y volver', () => {
    render(<Ayuda texto="x"><span>a</span></Ayuda>)
    const envoltorio = document.querySelector('.eo-ayuda') as HTMLElement
    expect(envoltorio.hasAttribute('data-oculto')).toBe(false)
    fireEvent.keyDown(envoltorio, { key: 'Escape' })
    expect(envoltorio.hasAttribute('data-oculto')).toBe(true)
    fireEvent.mouseLeave(envoltorio)
    expect(envoltorio.hasAttribute('data-oculto')).toBe(false)
  })

  it('el texto largo conserva sus renglones: título, descripción y ejemplo', () => {
    render(
      <Ayuda titulo="Negación" texto="Pide la ausencia." ejemplo="person without hard hat">
        <span>a</span>
      </Ayuda>,
    )
    const tip = screen.getByRole('tooltip')
    expect(tip.querySelector('.eo-ayuda__tit')?.textContent).toBe('Negación')
    expect(tip.querySelector('.eo-ayuda__ej')?.textContent).toBe('person without hard hat')
  })

  describe('posición — no la recorta una tabla con scroll', () => {
    const rect = (r: Partial<DOMRect>) => ({
      left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0, x: 0, y: 0, toJSON() {}, ...r,
    }) as DOMRect

    it('se ubica con position fixed, debajo, a la altura del elemento', () => {
      render(<Ayuda texto="x"><span>a</span></Ayuda>)
      const envoltorio = document.querySelector('.eo-ayuda') as HTMLElement
      envoltorio.getBoundingClientRect = () => rect({ left: 120, top: 100, bottom: 120 })
      fireEvent.mouseEnter(envoltorio)
      const def = screen.getByRole('tooltip') as HTMLElement
      expect(def.style.position).toBe('fixed')
      expect(def.style.left).toBe('120px')
      expect(def.style.top).toBe('120px')
    })

    it('se da vuelta hacia arriba si abajo no hay lugar', () => {
      render(<Ayuda texto="x"><span>a</span></Ayuda>)
      const envoltorio = document.querySelector('.eo-ayuda') as HTMLElement
      envoltorio.getBoundingClientRect = () =>
        rect({ left: 50, top: window.innerHeight - 30, bottom: window.innerHeight - 10 })
      fireEvent.mouseEnter(envoltorio)
      const def = screen.getByRole('tooltip') as HTMLElement
      expect(def.style.top).toBe('')
      expect(def.style.bottom).toBe('30px') // innerHeight − top del elemento
    })

    it('no se sale por el borde derecho de la ventana', () => {
      render(<Ayuda texto="x"><span>a</span></Ayuda>)
      const envoltorio = document.querySelector('.eo-ayuda') as HTMLElement
      envoltorio.getBoundingClientRect = () =>
        rect({ left: window.innerWidth - 20, top: 100, bottom: 120 })
      fireEvent.focus(envoltorio)
      const izquierda = parseInt((screen.getByRole('tooltip') as HTMLElement).style.left, 10)
      expect(izquierda).toBeLessThan(window.innerWidth - 20)
    })
  })
})
