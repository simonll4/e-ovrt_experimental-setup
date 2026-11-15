import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import CorrerClipPage from '../pages/CorrerClipPage'
import { correrClip, dejarPlataformaLista, getClipsDemostracion, getPreparacionClip } from '../api'
import type { CorridaClip, PreparacionClip, VistaClips } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getClipsDemostracion: vi.fn(),
  getPreparacionClip: vi.fn(),
  correrClip: vi.fn(),
  dejarPlataformaLista: vi.fn(),
}))

const CLIPS: VistaClips = {
  actual: null,
  cadencia: { uno_de_cada: 6, cuadros_por_segundo: 5 },
  clips: [
    { id: 'a_p1_c04', titulo: 'Sin casco', disponible: true, duracion_ms: 30667,
      referencia: [{ condicion: 'CR-01', desde_ms: 3133, hasta_ms: 27652 }] },
    { id: 'a_p2_c03', titulo: 'Sin chaleco', disponible: true, duracion_ms: 37500,
      referencia: [{ condicion: 'CR-02', desde_ms: 3300, hasta_ms: 30000 }] },
    { id: 'a_p3_c01', titulo: 'Sin infracción', disponible: false, duracion_ms: 18400, referencia: [] },
  ],
}
const LISTO: PreparacionClip = { listo: true, items: [{ id: 'deteccion', nombre: 'Motor de detección', ok: true, detalle: '' }] }

const corrida = (over: Partial<CorridaClip>): CorridaClip => ({
  id: 'clip_x', clip: { id: 'a_p1_c04', titulo: 'Sin casco' }, experiment_id: 'exp_x', fase: 'corriendo',
  iniciada_en: '2026-11-15T12:00:00Z', terminada_en: null, cuadros_esperados: 154,
  pasos: { deteccion: { estado: 'en_curso', cuadros: 60 }, reglas: { estado: 'en_curso', cuadros: 58 },
           distribucion: { estado: 'en_curso' }, broker: { estado: 'espera', mensajes: 0 } },
  resultado: null, error: null, demostracion: true, ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getClipsDemostracion).mockResolvedValue(CLIPS)
  vi.mocked(getPreparacionClip).mockResolvedValue(LISTO)
})
afterEach(() => cleanup())

describe('Correr un clip (plan de la consola, §7.2)', () => {
  it('tres clips del rodaje con lo que espera la referencia; dice que no es evidencia', async () => {
    render(<CorrerClipPage />)
    const grupo = await screen.findByRole('radiogroup', { name: 'El clip' })
    const opciones = within(grupo).getAllByRole('radio')
    expect(opciones.map((o) => o.querySelector('.eo-clip__titulo')?.textContent)).toEqual(['Sin casco', 'Sin chaleco', 'Sin infracción'])
    expect(opciones[0].textContent).toContain('Sin casco CR-01 desde el segundo 3,1')
    expect(opciones[2].textContent).toContain('no está en este equipo')
    expect((opciones[2] as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('demostración: no es evidencia')).toBeTruthy()
  })

  it('elegir y correr', async () => {
    vi.mocked(correrClip).mockResolvedValue({ id: 'clip_x', experiment_id: 'exp_x' })
    render(<CorrerClipPage />)
    const correr = await screen.findByRole('button', { name: 'Correr' })
    expect((correr as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('radio', { name: /Sin chaleco/ }))
    await waitFor(() => expect((correr as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(correr)
    await waitFor(() => expect(correrClip).toHaveBeenCalledWith('a_p2_c03'))
  })

  it('si la plataforma no está lista lo dice y ofrece dejarla lista', async () => {
    vi.mocked(getPreparacionClip).mockResolvedValue({ listo: false, items: [
      { id: 'deteccion', nombre: 'Motor de detección', ok: false, detalle: 'tiene que estar activo mp-gdino-tiny-560 (ahora: ninguno)' }] })
    vi.mocked(dejarPlataformaLista).mockResolvedValue({ t: '', accion: 'dejar lista', servicio: null, resultado: 'ok', detalle: null, duracion_s: 30 })
    render(<CorrerClipPage />)
    expect(await screen.findByText(/tiene que estar activo mp-gdino-tiny-560/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Dejar la plataforma lista' }))
    await waitFor(() => expect(dejarPlataformaLista).toHaveBeenCalled())
  })

  it('mientras corre se ve el avance por la cadena', async () => {
    vi.mocked(getClipsDemostracion).mockResolvedValue({ ...CLIPS, actual: corrida({}) })
    render(<CorrerClipPage />)
    const cadena = await screen.findByRole('list', { name: 'El clip por la cadena' })
    const pasos = within(cadena).getAllByRole('listitem').map((li) => li.textContent)
    expect(pasos).toEqual(['Detecciónen curso60 de 154 cuadros', 'Reglasen curso58 cuadros', 'Distribuciónen curso', 'Brokeren espera0 mensajes'])
    expect((screen.getByRole('button', { name: 'Corriendo…' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('el resultado: las alertas contra la referencia, cuánto tardó cada una y el mensaje del broker', async () => {
    vi.mocked(getClipsDemostracion).mockResolvedValue({ ...CLIPS, actual: corrida({
      fase: 'terminada',
      resultado: {
        evaluacion: { expected: 1, observed: 1, matched: 1, missed: 0, unexpected: 0 },
        alertas: [{ alert_id: 'a1', condicion: 'CR-01', confirmada_ms: 7300, primera_evidencia_ms: 3300,
                    episodio: { condicion: 'CR-01', desde_ms: 3133, hasta_ms: 27652 }, demora_ms: 4167,
                    broker: { topic: 'eovrt/alerts/high', recibido_en: 'x', payload: { alert_id: 'a1' }, demora_ms: 13.5 } }],
        sin_alerta: [], consolidado: 'runs/exp_x',
      } }) })
    render(<CorrerClipPage />)
    expect(await screen.findByText(/La referencia esperaba/)).toBeTruthy()
    const tabla = screen.getByRole('table', { name: 'Las alertas de la corrida' })
    expect(within(tabla).getAllByRole('row')[1].textContent).toBe('Sin casco CR-017,3 sdesde el segundo 3,14,2 s14 ms')
    expect(screen.getByText(/El mensaje que llegó al broker/)).toBeTruthy()
  })

  it('la cadencia sale del clip y un clip sin infracción lo dice en llano', async () => {
    vi.mocked(getClipsDemostracion).mockResolvedValue({ ...CLIPS, actual: corrida({
      clip: { id: 'a_p3_c01', titulo: 'Sin infracción' }, fase: 'terminada',
      resultado: { evaluacion: { expected: 0, observed: 0, matched: 0, missed: 0, unexpected: 0 },
                   alertas: [], sin_alerta: [], consolidado: null } }) })
    render(<CorrerClipPage />)
    expect(await screen.findByText('Perfil operativo y configuración del informe, a 5 cuadros por segundo')).toBeTruthy()
    expect(screen.getByText('La referencia no espera alertas y la corrida no dio ninguna.')).toBeTruthy()
    expect(screen.queryByText(/acertada/)).toBeNull()
  })
})
