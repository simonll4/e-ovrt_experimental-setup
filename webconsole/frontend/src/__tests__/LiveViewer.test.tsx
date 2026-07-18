import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import LiveViewer from '../components/LiveViewer'
import type { PreviewFrameHeader } from '../types'

class FakeImage {
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  naturalWidth = 640
  naturalHeight = 480
  private _src = ''
  get src() {
    return this._src
  }
  set src(value: string) {
    this._src = value
    FakeImage.instances.push(this)
    if (FakeImage.autoLoad) this.onload?.()
  }
  static instances: FakeImage[] = []
  static autoLoad = true
}

function makeCtx() {
  return {
    clearRect: vi.fn(),
    drawImage: vi.fn(),
    strokeRect: vi.fn(),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    measureText: vi.fn(() => ({ width: 40 })),
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 0,
    font: '',
  }
}

const header: PreviewFrameHeader = {
  seq: 1,
  ts: 0,
  width: 640,
  height: 480,
  mode: 'detect',
  detections: [
    { label: 'person', score: 0.91, bbox_norm_xyxy: [0.1, 0.1, 0.4, 0.6] },
    { label: 'helmet', score: 0.75, bbox_norm_xyxy: [0.5, 0.2, 0.7, 0.35] },
  ],
}

let ctx: ReturnType<typeof makeCtx>

beforeEach(() => {
  FakeImage.instances = []
  FakeImage.autoLoad = true
  vi.stubGlobal('Image', FakeImage as unknown as typeof Image)
  ctx = makeCtx()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    ctx as unknown as CanvasRenderingContext2D,
  )
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('LiveViewer', () => {
  it('muestra "sin señal" cuando no hay frameUrl', () => {
    render(<LiveViewer frameUrl={null} header={null} connected={false} fps={0} mode="raw" />)
    expect(screen.getByText(/sin señal/i)).toBeTruthy()
  })

  it('dibuja el frame y las cajas en el canvas al recibir un frameUrl', () => {
    render(
      <LiveViewer frameUrl="blob:frame-1" header={header} connected fps={12} mode="detect" />,
    )
    expect(ctx.drawImage).toHaveBeenCalledTimes(1)
    expect(ctx.strokeRect).toHaveBeenCalledTimes(2)
  })

  it('muestra los indicadores en vivo: conectado, fps, resolución y modo', () => {
    render(
      <LiveViewer frameUrl="blob:frame-1" header={header} connected fps={12} mode="detect" />,
    )
    expect(screen.getByText('conectado')).toBeTruthy()
    expect(screen.getByText(/12 fps/)).toBeTruthy()
    expect(screen.getByText('640×480')).toBeTruthy()
    expect(screen.getByText(/modo: detect/)).toBeTruthy()
  })

  it('descarta un frame viejo que termina de decodificar después de uno más nuevo', () => {
    FakeImage.autoLoad = false
    const { rerender } = render(
      <LiveViewer frameUrl="blob:frame-1" header={header} connected fps={12} mode="detect" />,
    )
    rerender(
      <LiveViewer frameUrl="blob:frame-2" header={header} connected fps={12} mode="detect" />,
    )
    expect(FakeImage.instances).toHaveLength(2)
    // El frame nuevo (2) termina de decodificar primero...
    FakeImage.instances[1].onload?.()
    expect(ctx.drawImage).toHaveBeenCalledTimes(1)
    // ...y cuando el viejo (1) finalmente decodifica, se descarta: no vuelve a dibujar.
    FakeImage.instances[0].onload?.()
    expect(ctx.drawImage).toHaveBeenCalledTimes(1)
  })
})
