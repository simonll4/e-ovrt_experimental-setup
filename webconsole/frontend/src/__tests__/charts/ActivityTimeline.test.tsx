import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '../../test-utils'
import ActivityTimeline from '../../components/charts/ActivityTimeline'
import type { TraceFrame } from '../../types'

afterEach(() => cleanup())

/** Cuadros a 10 por segundo: 20 cuadros = 2,0 s exactos. */
const cuadros = (n: number, over: (i: number) => Partial<TraceFrame> = () => ({})): TraceFrame[] =>
  Array.from({ length: n }, (_, i) => ({
    frame_index: i,
    unit_id: `u${i}`,
    timestamp_ms: i * 100,
    detections: [],
    control: 'received',
    progress: [],
    alert: [],
    ...over(i),
  })) as TraceFrame[]

describe('ActivityTimeline', () => {
  it('sin cuadros lo dice en vez de dibujar un eje vacío', () => {
    render(<ActivityTimeline frames={[]} />)
    expect(screen.getByText(/Todavía no hay cuadros/)).toBeTruthy()
  })

  // §4.5: los tres carriles son la idea central de la pantalla. Antes iban
  // apilados en un solo bloque y había que deducir cuál era cuál por la leyenda.
  it('dibuja tres carriles rotulados', () => {
    render(<ActivityTimeline frames={cuadros(20)} />)
    expect(screen.getByText(/Detecciones/, { selector: '.eo-timeline__label' })).toBeTruthy()
    expect(screen.getByText(/motor de reglas/, { selector: '.eo-timeline__label' })).toBeTruthy()
    expect(screen.getByText('Alertas', { selector: '.eo-timeline__label' })).toBeTruthy()
  })

  // El eje en segundos es lo que permite correlacionar con el video; en cuadros
  // no se podía saltar al mismo instante.
  it('el eje va en segundos, con el punto medio y el total', () => {
    render(<ActivityTimeline frames={cuadros(21)} />)
    expect(screen.getByText('0,0 s')).toBeTruthy()
    expect(screen.getByText('1,0 s')).toBeTruthy()
    expect(screen.getByText('2,0 s')).toBeTruthy()
  })

  it('sin marcas de tiempo utilizables cae a cuadros, en vez de inventar un eje temporal', () => {
    const sinReloj = cuadros(5, () => ({ timestamp_ms: 0 }))
    render(<ActivityTimeline frames={sinReloj} />)
    expect(screen.getByText('5 cuadros')).toBeTruthy()
    expect(screen.queryByText(/0,0 s/)).toBeNull()
  })

  it('separa las marcas de entrega de las de alerta, cada una en su carril', () => {
    const frames = cuadros(4, (i) => ({
      control: i === 1 ? 'dropped:rate_gate' : 'received',
      alert: i === 3 ? [{ condition_id: 'CR-01', severity: 'high' }] : [],
    })) as TraceFrame[]
    render(<ActivityTimeline frames={frames} />)
    const entrega = screen.getByRole('img', { name: 'Estado de entrega por cuadro' })
    const alertas = screen.getByRole('img', { name: 'Alertas confirmadas por cuadro' })
    expect(entrega.querySelectorAll('rect')).toHaveLength(1)
    expect(alertas.querySelectorAll('rect')).toHaveLength(1)
  })

  it('avisa el cuadro elegido al hacer click', () => {
    const onSelect = vi.fn()
    const { container } = render(<ActivityTimeline frames={cuadros(10)} onSelect={onSelect} />)
    // jsdom no hace layout: getBoundingClientRect da ancho 0 y `pick` devuelve
    // -1. Se fuerza un ancho para poder ejercitar el mapeo x → cuadro.
    const det = container.querySelector('.eo-timeline__det') as SVGSVGElement
    det.getBoundingClientRect = () => ({ left: 0, width: 100, top: 0, height: 42 }) as DOMRect
    fireEvent.click(container.querySelector('.eo-timeline__lanes') as Element, { clientX: 50 })
    expect(onSelect).toHaveBeenCalledWith(5, 5)
  })

  it('el cursor marca dónde está parada la lista', () => {
    const { container } = render(<ActivityTimeline frames={cuadros(10)} selected={3} />)
    const cursor = container.querySelector('.eo-timeline__cursor') as HTMLElement
    expect(cursor).toBeTruthy()
    expect(cursor.style.left).toBe('30%')
  })
})
