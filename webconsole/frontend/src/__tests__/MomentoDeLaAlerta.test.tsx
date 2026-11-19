import { afterEach, describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, within } from '../test-utils'
import MomentoDeLaAlerta, { estadoAlConfirmar, jsonLegible } from '../components/demo/MomentoDeLaAlerta'
import type { DemoLineaAlerta, DemoSessionDetail } from '../types'

afterEach(cleanup)

const CONFIRMADA = Date.parse('2026-11-07T16:16:26.000Z')
const iso = (desfaseMs: number) => new Date(CONFIRMADA + desfaseMs).toISOString()
const registro = (desfaseMs: number, estado: string, transcurrido: number) => ({
  t: iso(desfaseMs),
  condiciones: [
    { condicion: 'CR-01', estado, transcurrido_ms: transcurrido, umbral_ms: 4000 },
    { condicion: 'CR-02', estado: 'ok', transcurrido_ms: null, umbral_ms: 4000 },
  ],
})

const ALERTA: DemoLineaAlerta = {
  n: 1, alert_id: 'al-1', condition_id: 'CR-01', severity: 'high',
  frame_primera_evidencia: 47, frame_confirmacion: 68, frame_resolucion: null,
  t_primera_evidencia_ms: 1000, t_confirmacion_ms: 5100, t_resolucion_ms: null,
  confirmed_wall_ms: CONFIRMADA, t_broker_ms: CONFIRMADA + 14, broker_topic: 'eovrt/alerts/high', entrega: 'delivered',
  tramos: { evidencia_a_confirmacion_ms: 4100, confirmacion_a_broker_ms: 14 },
}

const DETALLE = {
  session: { session_id: 'demo_x' },
  resumen: { cuadros_clave: [{ alerta: 1, tipo: 'confirmacion', archivo: 'cuadros/alerta01-confirmacion.jpg', frame_index: 68 }] },
  linea_de_tiempo: [ALERTA],
  testigo: [{ recibido_en: iso(14), topic: 'eovrt/alerts/high', crudo: '{}', payload: { alert_id: 'al-1', severity: 'high' } }],
  state_log: [registro(-570, 'confirmando', 3381), registro(-65, 'confirmando', 3956), registro(443, 'alerta', 4348)],
} as unknown as DemoSessionDetail

const montar = (detalle: DemoSessionDetail = DETALLE, alerta: DemoLineaAlerta = ALERTA) => render(
  <MemoryRouter>
    <MomentoDeLaAlerta detalle={detalle} alerta={alerta}><ol aria-label="Tramos"><li>los tramos</li></ol></MomentoDeLaAlerta>
  </MemoryRouter>,
)

describe('«El momento de la alerta» (plan §6)', () => {
  it('el cuadro de la confirmación con el estado del primer registro desde que se confirmó', () => {
    const { container } = montar()
    const toma = container.querySelector('[data-figura="momento-toma"]') as HTMLElement
    expect(within(toma).getByRole('img').getAttribute('src')).toContain('alerta01-confirmacion.jpg')
    const estados = within(toma).getAllByRole('listitem').map((li) => li.textContent)
    expect(estados).toEqual(['Sin casco CR-01: en alerta (en el informe: confirmado o sostenido)', 'Sin chaleco CR-02: en regla (en el informe: inactivo)'])
    expect(within(toma).getByText('Registro de 0,4 s después de la confirmación.')).toBeTruthy()
  })

  it('el mensaje del broker de esa alerta, con los tramos debajo', () => {
    const { container } = montar()
    const mensaje = container.querySelector('[data-figura="momento-mensaje"]') as HTMLElement
    expect(within(mensaje).getByText('eovrt/alerts/high')).toBeTruthy()
    expect(mensaje.querySelector('pre')?.textContent).toContain('"alert_id": "al-1"')
    expect(within(mensaje).getByRole('list', { name: 'Tramos' })).toBeTruthy()
    expect(mensaje.querySelector('img, video, canvas')).toBeNull()
  })

  it('sin mensaje lo dice; sin registro de estados también', () => {
    montar({ ...DETALLE, testigo: [], state_log: [] } as DemoSessionDetail, { ...ALERTA, entrega: 'suppressed_cooldown' })
    expect(screen.getByText('No hubo mensaje: la notificación se suprimió por el cooldown (la pausa entre avisos).')).toBeTruthy()
    expect(screen.getByText('La sesión no registró el estado en ese instante.')).toBeTruthy()
  })

  it('una alerta sin hora de confirmación lo dice, en lugar de culpar al registro', () => {
    montar(DETALLE, { ...ALERTA, confirmed_wall_ms: null } as unknown as DemoLineaAlerta)
    expect(screen.getByText('Esta alerta no tiene hora de confirmación registrada.')).toBeTruthy()
  })
})

describe('el mensaje se lee entero', () => {
  it('las listas de números van en una línea y lo demás con sangría', () => {
    expect(jsonLegible({ caja: [397.6, -76.1, 5], sub: { a: 'x', l: ['a', 'b'] } })).toBe(
      '{\n  "caja": [397.6, -76.1, 5],\n  "sub": {\n    "a": "x",\n    "l": [\n      "a",\n      "b"\n    ]\n  }\n}')
  })
})

describe('qué registro de estados corresponde a la confirmación', () => {
  it('el primero desde la confirmación; si no hay, el último antes', () => {
    expect(estadoAlConfirmar(DETALLE.state_log, CONFIRMADA)?.desfaseMs).toBe(443)
    expect(estadoAlConfirmar(DETALLE.state_log.slice(0, 2), CONFIRMADA)?.desfaseMs).toBe(-65)
    expect(estadoAlConfirmar(DETALLE.state_log, null)).toBeNull()
  })

  it('un registro lejos de la confirmación no se muestra como su estado (revisión del 2026-11-19)', () => {
    // En una toma larga, el registro más cercano puede estar minutos después: eso no es el estado del instante.
    const lejos = [registro(-300_000, 'ok', 0), registro(289_000, 'alerta', 4000)]
    expect(estadoAlConfirmar(lejos, CONFIRMADA)).toBeNull()
    expect(estadoAlConfirmar([registro(1_900, 'alerta', 4000)], CONFIRMADA)?.desfaseMs).toBe(1900)
  })
})
