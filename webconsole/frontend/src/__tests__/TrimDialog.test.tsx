import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import TrimDialog from '../components/TrimDialog'
import type { MasterEntry } from '../types'

vi.mock('../api', async () => {
  const real = await vi.importActual<typeof import('../api')>('../api')
  return { ...real, generateClip: vi.fn() }
})

import { generateClip } from '../api'

const MASTER: MasterEntry = {
  name: 'P1-a-take1.mp4',
  scenario: 'P1',
  size_bytes: 1000,
  duration_ms: 33000,
  readable: true,
  clips: [],
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function marcar(video: HTMLVideoElement, evento: number, fin: number) {
  Object.defineProperty(video, 'currentTime', { value: evento, writable: true })
  fireEvent.click(screen.getByText('casco_fuera'))
  video.currentTime = fin
  fireEvent.click(screen.getByText('casco_puesto'))
}

describe('TrimDialog', () => {
  it('generar queda deshabilitado hasta tener las dos marcas', () => {
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    const boton = screen.getByText('Generar clip') as HTMLButtonElement
    expect(boton.disabled).toBe(true)
  })

  it('las marcas salen del currentTime del video y se postean', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p1_c01',
      info: { fps: 30, duration_ms: 20500, n_frames: 615, resolution: '1920x1080' },
      warnings: [],
      regenerated: false,
      invalidated: [],
    })
    const onGenerated = vi.fn()
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={onGenerated} />)
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    marcar(video, 10.5, 24.5)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() => expect(onGenerated).toHaveBeenCalled())
    expect(vi.mocked(generateClip).mock.calls[0][0]).toEqual({
      master: 'P1-a-take1.mp4',
      marks: [10.5, 24.5],
    })
    expect(screen.getByText(/a_p1_c01/)).toBeTruthy()
  })

  it('muestra las advertencias devueltas (D7: avisa fuerte, genera igual)', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p1_c01',
      info: { fps: 30, duration_ms: 15000, n_frames: 450, resolution: '1920x1080' },
      warnings: ['clip de 15.0 s, el guion pide ~20 s para este escenario'],
      regenerated: false,
      invalidated: [],
    })
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    marcar(screen.getByTestId('trim-video') as HTMLVideoElement, 5, 12)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() =>
      expect(screen.getByText(/el guion pide ~20 s/)).toBeTruthy(),
    )
  })

  it('muestra el detail real del backend cuando falla', async () => {
    const { ApiError } = await vi.importActual<typeof import('../api')>('../api')
    vi.mocked(generateClip).mockRejectedValue(
      new ApiError(502, { detail: 'ffmpeg: fuente.mp4: No such file or directory' }),
    )
    render(<TrimDialog master={MASTER} onClose={() => {}} onGenerated={() => {}} />)
    marcar(screen.getByTestId('trim-video') as HTMLVideoElement, 5, 12)
    fireEvent.click(screen.getByText('Generar clip'))
    await waitFor(() =>
      expect(screen.getByText(/No such file or directory/)).toBeTruthy(),
    )
  })

  it('material ajeno exige elegir escenario', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, name: '4.1.mp4', scenario: null }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    expect(screen.getByLabelText('Escenario')).toBeTruthy()
  })

  it('un master con clips ofrece regenerar y avisa por la pre-anotación', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, clips: ['a_p1_c01'] }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const select = screen.getByLabelText('Regenerar') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'a_p1_c01' } })
    expect(screen.getByText(/invalida la pre-anotación/)).toBeTruthy()
  })

  it('P6 pide cuatro marcas y las postea en orden', async () => {
    vi.mocked(generateClip).mockResolvedValue({
      clip_id: 'a_p6_c01',
      info: { fps: 30, duration_ms: 42500, n_frames: 1275, resolution: '1920x1080' },
      warnings: [],
      regenerated: false,
      invalidated: [],
    })
    render(
      <TrimDialog
        master={{ ...MASTER, name: 'P6-a-take2.mp4', scenario: 'P6' }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    const boton = screen.getByText('Generar clip') as HTMLButtonElement
    expect(boton.disabled).toBe(true)
    for (const [label, t] of [
      ['casco_fuera', 10], ['chaleco_fuera', 13], ['chaleco_puesto', 23], ['casco_puesto', 33],
    ] as const) {
      Object.defineProperty(video, 'currentTime', { value: t, writable: true })
      fireEvent.click(screen.getByText(label))
    }
    expect(boton.disabled).toBe(false)
    fireEvent.click(boton)
    await waitFor(() => expect(generateClip).toHaveBeenCalled())
    expect(vi.mocked(generateClip).mock.calls[0][0]).toEqual({
      master: 'P6-a-take2.mp4',
      marks: [10, 13, 23, 33],
    })
  })

  it('P6: el segundo boton esta deshabilitado hasta marcar el primero', () => {
    render(
      <TrimDialog
        master={{ ...MASTER, name: 'P6-a-take2.mp4', scenario: 'P6' }}
        onClose={() => {}}
        onGenerated={() => {}}
      />,
    )
    const segundo = screen.getByText('chaleco_fuera') as HTMLButtonElement
    expect(segundo.disabled).toBe(true)
    const video = screen.getByTestId('trim-video') as HTMLVideoElement
    Object.defineProperty(video, 'currentTime', { value: 10, writable: true })
    fireEvent.click(screen.getByText('casco_fuera'))
    expect(segundo.disabled).toBe(false)
  })
})
