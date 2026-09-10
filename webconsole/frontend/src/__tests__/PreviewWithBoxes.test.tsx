import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render } from '../test-utils'
import PreviewWithBoxes from '../components/PreviewWithBoxes'
import type { TraceDetection } from '../types'

afterEach(() => cleanup())

describe('PreviewWithBoxes', () => {
  it('dibuja una caja por cada detección con bbox_norm_xyxy', () => {
    const detections: TraceDetection[] = [
      { label: 'person', confidence: 0.9, bbox_norm_xyxy: [0.1, 0.1, 0.5, 0.5] },
      { label: 'helmet', confidence: 0.8, bbox_norm_xyxy: [0.2, 0.2, 0.6, 0.6] },
    ]
    const { container } = render(<PreviewWithBoxes src="x.jpg" alt="u0" detections={detections} />)
    expect(container.querySelectorAll('.eo-preview__box').length).toBe(2)
  })

  it('renderiza la preview a un tamaño legible por defecto (no un thumbnail diminuto)', () => {
    const { container } = render(<PreviewWithBoxes src="x.jpg" alt="u0" detections={[]} />)
    const img = container.querySelector('img') as HTMLImageElement
    expect(Number(img.getAttribute('width'))).toBeGreaterThanOrEqual(200)
  })

  it('respeta un width explícito', () => {
    const { container } = render(
      <PreviewWithBoxes src="x.jpg" alt="u0" detections={[]} width={120} />,
    )
    const img = container.querySelector('img') as HTMLImageElement
    expect(img.getAttribute('width')).toBe('120')
  })

  it('no dibuja cajas si bbox_norm_xyxy es null o está ausente', () => {
    const detections: TraceDetection[] = [
      { label: 'person', confidence: 0.9, bbox_norm_xyxy: null },
      { label: 'helmet', confidence: 0.8 },
    ]
    const { container } = render(<PreviewWithBoxes src="x.jpg" alt="u0" detections={detections} />)
    expect(container.querySelectorAll('.eo-preview__box').length).toBe(0)
  })

  it('calcula left/top/width/height en % para una caja conocida', () => {
    const detections: TraceDetection[] = [
      { label: 'person', confidence: 0.9, bbox_norm_xyxy: [0.1, 0.2, 0.5, 0.9] },
    ]
    const { container } = render(<PreviewWithBoxes src="x.jpg" alt="u0" detections={detections} />)
    const box = container.querySelector('.eo-preview__box') as HTMLElement
    expect(box.style.left).toBe('10%')
    expect(box.style.top).toBe('20%')
    expect(box.style.width).toBe('40%')
    expect(box.style.height).toBe('70%')
  })

  it('el title incluye el label y la confidence', () => {
    const detections: TraceDetection[] = [
      { label: 'vest', confidence: 0.876, bbox_norm_xyxy: [0, 0, 1, 1] },
    ]
    const { container } = render(<PreviewWithBoxes src="x.jpg" alt="u0" detections={detections} />)
    const box = container.querySelector('.eo-preview__box') as HTMLElement
    expect(box.getAttribute('title')).toBe('vest 0.88')
  })

  it('si la imagen no carga muestra un texto explícito, no un hueco', () => {
    const { container, getByText } = render(
      <PreviewWithBoxes src="no-existe.jpg" alt="u0" detections={[]} />,
    )
    fireEvent.error(container.querySelector('img') as HTMLImageElement)
    expect(getByText('sin vista previa')).toBeTruthy()
    expect(container.querySelector('.eo-preview--empty')).toBeTruthy()
    expect(container.querySelector('img')).toBeNull()
  })

  // El visor grande del detalle de corrida explica POR QUÉ no hay imagen; la
  // miniatura de una lista no tiene lugar para esa frase. De ahí la prop.
  it('el mensaje de vacío es configurable', () => {
    const { container, getByText } = render(
      <PreviewWithBoxes
        src="no-existe.jpg"
        alt="u0"
        detections={[]}
        emptyMessage="Esta corrida se grabó sin vistas previas de cuadro."
      />,
    )
    fireEvent.error(container.querySelector('img') as HTMLImageElement)
    expect(getByText('Esta corrida se grabó sin vistas previas de cuadro.')).toBeTruthy()
  })
})
