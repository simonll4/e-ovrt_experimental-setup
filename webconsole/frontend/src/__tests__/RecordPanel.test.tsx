import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import RecordPanel from '../components/RecordPanel'
import * as api from '../api'

describe('RecordPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'nextTake').mockResolvedValue({ basename: 'P1-a-take3' })
    vi.spyOn(api, 'getRecording').mockResolvedValue({ state: 'idle' })
  })

  afterEach(() => cleanup())

  it('muestra el proximo basename propuesto', async () => {
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
  })

  it('ofrece los 9 escenarios del guion (P1..P9)', async () => {
    render(<RecordPanel cameraId="dvr_test" />)
    const select = (await screen.findByLabelText(/escenario/i)) as HTMLSelectElement
    const opciones = Array.from(select.options).map((o) => o.value)
    expect(opciones).toEqual(['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9'])
  })

  it('deshabilita grabar si no hay camara elegida', async () => {
    render(<RecordPanel cameraId={null} />)
    const boton = await screen.findByRole('button', { name: /grabar/i })
    expect((boton as HTMLButtonElement).disabled).toBe(true)
  })

  it('arranca la grabacion con la camara, escenario y variante elegidos', async () => {
    const start = vi
      .spyOn(api, 'startRecording')
      .mockResolvedValue({ state: 'recording', basename: 'P1-a-take3', elapsed_ms: 0, size_bytes: 0 })
    render(<RecordPanel cameraId="dvr_test" />)
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

  it('muestra el error del backend sin romper el panel', async () => {
    // ApiError real, no un Error plano: su `message` es solo "API 409" y el
    // motivo viaja en payload.detail. Mockear con Error plano hacía que el test
    // pasara mientras el operador veía "API 409" contra el backend de verdad.
    vi.spyOn(api, 'startRecording').mockRejectedValue(
      new api.ApiError(409, {
        detail: 'el media-plane está ocupado por preview:pv_ab12',
      }),
    )
    render(<RecordPanel cameraId="dvr_test" />)
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

    render(<RecordPanel cameraId="dvr_test" />)
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

    render(<RecordPanel cameraId="dvr_test" />)
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
    render(<RecordPanel cameraId="dvr_test" />)
    expect(await screen.findByText(/P1-a-take3/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /grabar/i }))
    expect(await screen.findByRole('button', { name: /detener/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /detener/i }))
    expect(await screen.findByText(/menos de 30 s/i)).toBeTruthy()
  })
})
