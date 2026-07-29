import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ClipsPage from '../pages/ClipsPage'

vi.mock('../api', async () => {
  const real = await vi.importActual<typeof import('../api')>('../api')
  return { ...real, getMasters: vi.fn(), getClips: vi.fn() }
})

import { getClips, getMasters } from '../api'

const MASTERS = [
  {
    name: 'P1-a-take1.mp4', scenario: 'P1', size_bytes: 1000,
    duration_ms: 33000, readable: true, clips: [],
  },
  {
    name: 'P2-a-take1.mp4', scenario: 'P2', size_bytes: 1000,
    duration_ms: null, readable: false, clips: [],
  },
]
const CLIPS = [
  {
    clip_id: 'a_p1_c01', fps: 30, duration_ms: 20500, n_frames: 615,
    resolution: '1920x1080', has_yaml: true, master: 'raw/P1-a-take1.mp4',
    warnings: ['solo 2.0 s de cola, se necesitan 3'],
  },
]

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ClipsPage', () => {
  it('lista masters y clips', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: CLIPS })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('P1-a-take1.mp4')).toBeTruthy())
    expect(screen.getByText('a_p1_c01')).toBeTruthy()
  })

  it('el master ilegible queda marcado y sin botón de recorte habilitado', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText(/Ilegible/)).toBeTruthy())
    const botones = screen.getAllByText('Recortar') as HTMLButtonElement[]
    expect(botones[1].disabled).toBe(true)
  })

  it('recortar abre el TrimDialog con el master elegido', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: MASTERS })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('P1-a-take1.mp4')).toBeTruthy())
    fireEvent.click((screen.getAllByText('Recortar') as HTMLButtonElement[])[0])
    expect(screen.getByText(/Recortar P1-a-take1.mp4/)).toBeTruthy()
  })

  it('un clip con advertencias las señala', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: [] })
    vi.mocked(getClips).mockResolvedValue({ clips: CLIPS })
    render(<ClipsPage />)
    await waitFor(() => expect(screen.getByText('a_p1_c01')).toBeTruthy())
    expect(screen.getByText(/solo 2.0 s de cola/)).toBeTruthy()
  })

  it('listas vacías no rompen', async () => {
    vi.mocked(getMasters).mockResolvedValue({ masters: [] })
    vi.mocked(getClips).mockResolvedValue({ clips: [] })
    render(<ClipsPage />)
    await waitFor(() => expect(getMasters).toHaveBeenCalled())
  })
})
