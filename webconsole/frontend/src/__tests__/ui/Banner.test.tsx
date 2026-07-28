import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Banner } from '../../components/ui'

afterEach(() => cleanup())

describe('Banner', () => {
  it('tono warn con boton de cerrar', () => {
    const onClose = vi.fn()
    render(<Banner tone="warn" onClose={onClose}>El motor de reglas no responde.</Banner>)
    expect(screen.getByText('El motor de reglas no responde.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /cerrar aviso/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('tono live con accion, sin boton de cerrar si no se pasa onClose', () => {
    render(
      <Banner tone="live" action={<button>Ver en vivo</button>}>
        Ronda nocturna — cámara 04 está procesando ahora.
      </Banner>,
    )
    expect(screen.getByRole('button', { name: 'Ver en vivo' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /cerrar aviso/i })).toBeNull()
  })

  it('tono error sin accion ni cierre no rompe', () => {
    render(<Banner tone="error">Hay una corrida en curso.</Banner>)
    expect(screen.getByText('Hay una corrida en curso.')).toBeTruthy()
  })
})
