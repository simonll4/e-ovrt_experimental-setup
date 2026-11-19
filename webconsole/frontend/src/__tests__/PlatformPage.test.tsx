import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PlatformPage, { desdeCuando, estadoServicio } from '../pages/PlatformPage'
import { accionPlataforma, ApiError, dejarPlataformaLista, getPlataforma } from '../api'
import type { EstadoPlataforma, ServicioPlataforma } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getPlataforma: vi.fn(),
  accionPlataforma: vi.fn(),
  dejarPlataformaLista: vi.fn(),
  getPreflight: vi.fn(async () => ({ media: null, control: null })),
  getGen2Prueba: vi.fn(async () => { throw new Error('sin PLAT-01') }),
}))

const svc = (over: Partial<ServicioPlataforma>): ServicioPlataforma => ({
  servicio: 'x', nombre: null, grupo: 'nucleo', modelo: null, estado: 'running', salud: 'healthy',
  imagen: 'img', desde: '2026-11-15T10:00:00Z', puerto: null, activa: false, orquestable: true, ...over,
})

const ESTADO: EstadoPlataforma = {
  orquestada: true,
  nucleo: [
    svc({ servicio: 'console', nombre: 'Consola', puerto: '8090', orquestable: false }),
    svc({ servicio: 'control-plane', nombre: 'Motor de reglas', puerto: '8081' }),
    svc({ servicio: 'distribution', nombre: 'Distribución de alertas', estado: 'exited', salud: null, desde: null }),
    svc({ servicio: 'mosquitto', nombre: 'Broker MQTT', estado: 'ausente', salud: null, desde: null, imagen: null }),
  ],
  deteccion: [
    svc({ servicio: 'mp-gdino-tiny-560', grupo: 'deteccion', modelo: 'grounding-dino/gdino-tiny-560', activa: true, puerto: '8080 (red interna)' }),
    svc({ servicio: 'mp-yoloe-26s', grupo: 'deteccion', modelo: 'yoloe/yoloe-26s', estado: 'exited', salud: null, desde: null }),
  ],
  activa: 'mp-gdino-tiny-560',
  perfil_operativo: 'mp-gdino-tiny-560',
  gpu: { disponible: true, instancia: 'mp-gdino-tiny-560', nombre: 'RTX 4060', usada_mb: 2355, total_mb: 8188 },
  en_curso: null,
  acciones: [{ t: '2026-11-15T12:00:00Z', accion: 'activar', servicio: 'mp-gdino-tiny-560', resultado: 'ok', detalle: null, duracion_s: 41.2 }],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getPlataforma).mockResolvedValue(ESTADO)
})
afterEach(() => cleanup())

const tabla = (nombre: string) => screen.getByRole('table', { name: nombre })

describe('Plataforma (plan de la consola, §7.1)', () => {
  it('los servicios en dos grupos, con estado, imagen, desde cuándo y puerto; la activa destacada y la GPU', async () => {
    render(<PlatformPage />)
    const nucleo = await screen.findByRole('table', { name: 'Núcleo' })
    const filas = within(nucleo).getAllByRole('row').slice(1)
    expect(filas.map((f) => within(f).getByRole('rowheader').textContent)).toEqual([
      'Consolaconsole', 'Motor de reglascontrol-plane', 'Distribución de alertasdistribution', 'Broker MQTTmosquitto'])
    expect(within(filas[1]).getByText('Corriendo')).toBeTruthy()
    expect(within(filas[1]).getByText('8081')).toBeTruthy()
    expect(within(filas[3]).getByText('Sin crear')).toBeTruthy()
    const det = tabla('Detección')
    expect(within(det).getByText('activa')).toBeTruthy()
    expect(screen.getByText('GPU: 2,3 de 8,0 GB en uso (RTX 4060)')).toBeTruthy()
    expect(screen.getByText('3 de 6 servicios corriendo')).toBeTruthy()
    expect(document.querySelector('[data-figura="plataforma-servicios"]')).not.toBeNull()
  })

  it('cada servicio ofrece lo que se puede hacer con él', async () => {
    render(<PlatformPage />)
    await screen.findByRole('table', { name: 'Núcleo' })
    expect(screen.getByRole('button', { name: 'Reiniciar Motor de reglas' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Detener Motor de reglas' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Levantar Distribución de alertas' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Detener mp-gdino-tiny-560' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Activar mp-yoloe-26s' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Detener Consola' })).toBeNull()
  })

  it('la consola no se detiene a sí misma: muestra el comando', async () => {
    vi.mocked(accionPlataforma).mockRejectedValue(new ApiError(409, {
      detail: 'La consola no se detiene a sí misma', comando: 'docker compose --project-name eovrt restart console' }))
    render(<PlatformPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Reiniciar Consola' }))
    expect(await screen.findByText('docker compose --project-name eovrt restart console')).toBeTruthy()
  })

  it('con algo en curso pide confirmación y recién ahí lo hace', async () => {
    vi.mocked(accionPlataforma)
      .mockRejectedValueOnce(new ApiError(409, { detail: 'está en curso la corrida exp_clip: confirmalo para seguir', confirmar: true }))
      .mockResolvedValueOnce({ t: '', accion: 'detener', servicio: 'control-plane', resultado: 'ok', detalle: null, duracion_s: 1 })
    render(<PlatformPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Detener Motor de reglas' }))
    expect(await screen.findByText('está en curso la corrida exp_clip: confirmalo para seguir')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Detener igual' }))
    await waitFor(() => expect(accionPlataforma).toHaveBeenLastCalledWith('control-plane', 'detener', true))
  })

  it('«Dejar la plataforma lista» y el registro de acciones', async () => {
    vi.mocked(dejarPlataformaLista).mockResolvedValue({ t: '', accion: 'dejar lista', servicio: null, resultado: 'ok', detalle: 'ya estaba lista', duracion_s: 0 })
    render(<PlatformPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'Dejar la plataforma lista' }))
    await waitFor(() => expect(dejarPlataformaLista).toHaveBeenCalled())
    const registro = screen.getByText('Registro de acciones').closest('section') ?? document.body
    expect(within(registro as HTMLElement).getByText('mp-gdino-tiny-560')).toBeTruthy()
  })

  it('en nativo avisa que la orquestación necesita los contenedores', async () => {
    vi.mocked(getPlataforma).mockResolvedValue({ ...ESTADO, orquestada: false, nucleo: [], deteccion: [], gpu: null, acciones: [] })
    render(<PlatformPage />)
    expect(await screen.findByText(/necesita la consola en contenedor/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Dejar la plataforma lista' })).toBeNull()
    expect(screen.getByText('Plano de medios')).toBeTruthy()
  })
})

describe('el estado y el tiempo, en llano', () => {
  it('traduce el estado del contenedor con su salud', () => {
    expect(estadoServicio({ estado: 'running', salud: 'healthy' }).texto).toBe('Corriendo')
    expect(estadoServicio({ estado: 'running', salud: 'unhealthy' })).toEqual({ tono: 'error', texto: 'Corre con problemas' })
    expect(estadoServicio({ estado: 'exited', salud: null }).texto).toBe('Detenido')
    expect(estadoServicio({ estado: 'ausente', salud: null }).texto).toBe('Sin crear')
  })

  it('dice desde qué hora y hace cuánto', () => {
    const ahora = Date.parse('2026-11-15T12:10:00Z')
    expect(desdeCuando('2026-11-15T10:00:00Z', ahora)).toMatch(/ · hace 2 h 10 min$/)
    expect(desdeCuando('2026-11-15T12:09:50Z', ahora)).toMatch(/ · recién$/)
    expect(desdeCuando(null, ahora)).toBe('—')
  })
})
