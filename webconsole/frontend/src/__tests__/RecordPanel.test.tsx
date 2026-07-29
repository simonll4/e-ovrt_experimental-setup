import { cleanup, fireEvent, render, screen, waitFor } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RecordPanel from '../components/RecordPanel'
import * as api from '../api'
import type { CameraPreset } from '../types'

const CAMARAS: CameraPreset[] = [
  { id: 'dvr_test', name: 'RTSP DVR canal 1', plugin: 'rtsp', config: {} },
  { id: 'oak_d_lab', name: 'OAK-D laboratorio', plugin: 'oak_d', config: {} },
]

describe('RecordPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'nextTake').mockResolvedValue({ basename: 'P1-a-take3' })
    vi.spyOn(api, 'getRecording').mockResolvedValue({ state: 'idle' })
  })

  afterEach(() => cleanup())

  it('muestra el proximo basename propuesto', async () => {
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
  })

  it('ofrece los 9 escenarios del guion (P1..P9)', async () => {
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    const select = (await screen.findByLabelText(/escenario/i)) as HTMLSelectElement
    const opciones = Array.from(select.options).map((o) => o.value)
    expect(opciones).toEqual(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'])
  })

  it('ofrece las camaras disponibles como fuente de grabacion', async () => {
    // F-DR5 (dry-run 2026-07-22): sin este selector la única forma de elegir
    // fuente era conectar el preview de esa cámara; el operador veía el botón
    // Grabar en gris y ninguna pista de por qué.
    render(<RecordPanel cameras={CAMARAS} connectedId={null} />)
    const select = (await screen.findByLabelText(/c[áa]mara/i)) as HTMLSelectElement
    const opciones = Array.from(select.options).map((o) => o.value)
    expect(opciones).toEqual(['', 'dvr_test', 'oak_d_lab'])
    expect(screen.getByText(/OAK-D laboratorio/)).toBeTruthy()
  })

  it('preselecciona la camara conectada en el preview', async () => {
    render(<RecordPanel cameras={CAMARAS} connectedId="oak_d_lab" />)
    const select = (await screen.findByLabelText(/c[áa]mara/i)) as HTMLSelectElement
    expect(select.value).toBe('oak_d_lab')
  })

  it('deshabilita grabar y explica por que cuando no hay camara elegida', async () => {
    render(<RecordPanel cameras={CAMARAS} connectedId={null} />)
    const boton = await screen.findByRole('button', { name: /grabar/i })
    expect((boton as HTMLButtonElement).disabled).toBe(true)
    // El botón gris sin motivo es lo que costó tiempo en el dry-run.
    expect(screen.getByText(/eleg[ií] una c[áa]mara/i)).toBeTruthy()
  })

  it('graba con la camara elegida en el selector, no con la conectada', async () => {
    const start = vi
      .spyOn(api, 'startRecording')
      .mockResolvedValue({ state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0 })
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()

    fireEvent.change(screen.getByLabelText(/c[áa]mara/i), { target: { value: 'oak_d_lab' } })
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    await waitFor(() =>
      expect(start).toHaveBeenCalledWith({
        camera_id: 'oak_d_lab',
        scenario: 'P1',
        variant: 'a',
      }),
    )
  })

  it('arranca la grabacion con la camara, escenario y variante elegidos', async () => {
    const start = vi
      .spyOn(api, 'startRecording')
      .mockResolvedValue({ state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0 })
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()

    fireEvent.change(screen.getByLabelText(/escenario/i), { target: { value: 'P2' } })
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    await waitFor(() =>
      expect(start).toHaveBeenCalledWith({
        camera_id: 'dvr_test',
        scenario: 'P2',
        variant: 'a',
      }),
    )
  })

  it('avisa que no se debe actuar mientras la camara todavia inicializa', async () => {
    // F-DR6 (dry-run 2026-07-22): la OAK-D tarda ~9 s en conectar. Si el panel
    // dice "● REC" en ese lapso el operador actúa la infracción antes de que
    // haya video y la toma se pierde (40 s en pantalla -> 28 s de archivo).
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      state: 'starting', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0,
    })
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    expect(await screen.findByText(/no act[uú]es todav[ií]a/i)).toBeTruthy()
    // El cronómetro de grabación NO puede estar corriendo todavía.
    expect(screen.queryByText(/● REC/)).toBeNull()
    // Pero sí se puede cortar, por si el device nunca conecta.
    expect(screen.getByRole('button', { name: /detener/i })).toBeTruthy()
  })

  it('tras un rechazo se resincroniza con el backend en vez de asumir idle', async () => {
    // F-DR8 (dry-run 2026-07-22): con una pestaña vieja el panel ignoró el
    // estado nuevo y siguió mostrando "Grabar"; al reintentar, el backend
    // respondió "ya hay una grabación activa" y el panel se puso en 'idle',
    // dejando de pollear. Resultado: la cámara grabando y la UI diciendo que
    // no pasa nada, sin recuperarse sola (hubo que recargar la página).
    vi.spyOn(api, 'startRecording').mockRejectedValue(
      new api.ApiError(409, { detail: 'ya hay una grabación activa: P1-a-take1' }),
    )
    vi.spyOn(api, 'getRecording')
      .mockResolvedValueOnce({ state: 'idle' }) // consulta al montar
      .mockResolvedValue({
        state: 'recording', basename: 'P1-a-take1', elapsed_ms: 12000, size_bytes: 5_000_000,
      })

    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    expect(await screen.findByText(/ya hay una grabación activa/)).toBeTruthy()
    // El panel tiene que reflejar la toma que SÍ está corriendo.
    expect(await screen.findByText(/● REC/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /detener/i })).toBeTruthy()
  })

  it('muestra el error del backend sin romper el panel', async () => {
    // ApiError real, no un Error plano: su `message` es solo "API 409" y el
    // motivo viaja en payload.detail. Mockear con Error plano hacía que el test
    // pasara mientras el operador veía "API 409" contra el backend de verdad.
    vi.spyOn(api, 'startRecording').mockRejectedValue(
      new api.ApiError(409, {
        detail: 'el media-plane está ocupado por preview:pv_ab12',
      }),
    )
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    expect(await screen.findByText(/ocupado por preview/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /grabar/i })).toBeTruthy()
  })

  it('mientras graba, consulta el backend periodicamente y muestra elapsed_ms/size_bytes de ahi', async () => {
    // Hallazgo F1+F2: el cronometro no debe salir de un setInterval local (eso
    // nunca dispara la evaluacion del corte de seguridad del backend, y si el
    // subproceso muere la UI no se entera). Tiene que venir de pollear
    // getRecording() y usar el elapsed_ms/size_bytes que esa respuesta trae.
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0,
    })
    const polled = vi
      .spyOn(api, 'getRecording')
      .mockResolvedValueOnce({ state: 'idle' }) // consulta inicial al montar
      .mockResolvedValue({
        state: 'recording', basename: 'P1-a-take3', elapsed_ms: 5000, size_bytes: 2_500_000,
      })

    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    await screen.findByRole('button', { name: /detener/i })

    await waitFor(() => expect(polled).toHaveBeenCalledTimes(2), { timeout: 2000 })
    expect(await screen.findByText(/5s/)).toBeTruthy()
    expect(await screen.findByText(/2\.4 MB/)).toBeTruthy()
  })

  it('si el backend informa error, deja de contar y muestra el motivo', async () => {
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0,
    })
    vi.spyOn(api, 'getRecording')
      .mockResolvedValueOnce({ state: 'idle' })
      .mockResolvedValue({
        state: 'error', basename: 'P1-a-take3', error: 'ffmpeg rc=1: no se pudo conectar',
      })

    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))

    expect(await screen.findByText(/no se pudo conectar/, {}, { timeout: 2000 })).toBeTruthy()
    expect(await screen.findByRole('button', { name: /grabar/i })).toBeTruthy()
  })

  it('avisa cuando la toma se corto antes de los 30 s', async () => {
    vi.spyOn(api, 'startRecording').mockResolvedValue({
      state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0,
    })
    vi.spyOn(api, 'stopRecording').mockResolvedValue({
      state: 'finished', basename: 'P1-a-take3', duration_ms: 12000,
      size_bytes: 1024, truncated: false, suspected_substream: false,
      fps: 25, resolution: '320x240', error: null,
    })
    render(<RecordPanel cameras={CAMARAS} connectedId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    expect(await screen.findByRole('button', { name: /detener/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /detener/i }))
    expect(await screen.findByText(/menos de 30 s/i)).toBeTruthy()
  })
})
