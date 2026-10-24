import { afterEach, describe, expect, it } from 'vitest'
import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { TabPanel, Tabs } from '../../components/ui'

afterEach(() => cleanup())

type T = 'uno' | 'dos' | 'tres'

function Prueba() {
  const [tab, setTab] = useState<T>('uno')
  return (
    <>
      <Tabs<T>
        idBase="prueba"
        label="Secciones"
        value={tab}
        onChange={setTab}
        items={[
          { id: 'uno', label: 'Uno', count: 3 },
          { id: 'dos', label: 'Dos' },
          { id: 'tres', label: 'Tres' },
        ]}
      />
      <TabPanel idBase="prueba" id={tab}>contenido de {tab}</TabPanel>
    </>
  )
}

describe('Tabs', () => {
  it('relaciona la pestaña activa con su panel en los dos sentidos', () => {
    render(<Prueba />)
    expect(screen.getByRole('tablist', { name: 'Secciones' })).toBeTruthy()
    const uno = screen.getByRole('tab', { name: /Uno/ })
    const panel = screen.getByRole('tabpanel')
    expect(uno.getAttribute('aria-selected')).toBe('true')
    expect(uno.getAttribute('aria-controls')).toBe(panel.id)
    expect(panel.getAttribute('aria-labelledby')).toBe(uno.id)
  })

  it('una sola parada de tabulación: la pestaña activa', () => {
    render(<Prueba />)
    const tabs = screen.getAllByRole('tab')
    expect(tabs.map((t) => t.tabIndex)).toEqual([0, -1, -1])
  })

  it('las flechas, Inicio y Fin recorren, activan y mueven el foco', () => {
    render(<Prueba />)
    const uno = screen.getByRole('tab', { name: /Uno/ })
    fireEvent.keyDown(uno, { key: 'ArrowRight' })
    const dos = screen.getByRole('tab', { name: 'Dos' })
    expect(dos.getAttribute('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(dos)
    expect(screen.getByRole('tabpanel').textContent).toBe('contenido de dos')
    fireEvent.keyDown(dos, { key: 'End' })
    expect(screen.getByRole('tab', { name: 'Tres' }).getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Tres' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: /Uno/ }).getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(screen.getByRole('tab', { name: /Uno/ }), { key: 'ArrowLeft' })
    expect(screen.getByRole('tab', { name: 'Tres' }).getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Tres' }), { key: 'Home' })
    expect(screen.getByRole('tab', { name: /Uno/ }).getAttribute('aria-selected')).toBe('true')
  })
})
