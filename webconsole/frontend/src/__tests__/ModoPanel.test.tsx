import { cleanup, fireEvent, render, screen, within } from '../test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ModoPanel from '../components/demo/ModoPanel'
import { MODOS } from './fixtures/demoModos'

// Los modos de prompts de la demo (✎ 2026-11-01): la tarjeta «Prompts» de /demo.

afterEach(() => cleanup())

const montar = (elegido = 'campeon', soloLectura = false, onElegir = vi.fn()) => {
  render(<ModoPanel modos={MODOS} elegido={elegido} onElegir={onElegir} soloLectura={soloLectura} />)
  return onElegir
}
const radio = (nombre: RegExp) => screen.getByRole('radio', { name: nombre }) as HTMLInputElement

describe('ModoPanel', () => {
  it('lista los tres modos con su rótulo de evidencia, sin calificarlos, y el campeón elegido', () => {
    montar()
    const grupo = screen.getByRole('radiogroup', { name: 'Modo de prompts' })
    const radios = within(grupo).getAllByRole('radio') as HTMLInputElement[]
    expect(radios.map((r) => r.checked)).toEqual([true, false, false])
    expect(radio(/Campeón/).closest('label')?.textContent).toMatch(/Configuración del informe/)
    expect(radio(/E-DIR/).closest('label')?.textContent).toMatch(/Descartada por la evidencia/)
    expect(radio(/Clase nueva/).closest('label')?.textContent).toMatch(/Extensión sin entrenar/)
    expect(grupo.textContent).not.toMatch(/buena|mala/i)
  })

  it('elegir otro modo avisa a la pantalla', () => {
    const onElegir = montar()
    fireEvent.click(radio(/E-DIR/))
    expect(onElegir).toHaveBeenCalledWith('edir')
  })

  it('del modo elegido muestra resumen, nota, frases por clase y cifras con su prueba', () => {
    montar('edir')
    const detalle = screen.getByRole('region', { name: 'Modo E-DIR' })
    expect(detalle.textContent).toMatch(/Pedirle al modelo la infracción/)
    expect(detalle.textContent).toMatch(/ADR-001/)
    expect(detalle.textContent).toMatch(/no cuenta como ensayo/)
    const frases = within(detalle).getByRole('list', { name: 'Frases por clase' })
    expect(within(frases).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'person: «person»',
      'cr01_spec: «construction worker without safety helmet»',
      'cr02_obs: «person without bright colored safety clothing»',
    ])
    const cifras = within(detalle).getByRole('list', { name: 'Cifras del modo' })
    const [alr04, per01] = within(cifras).getAllByRole('listitem')
    expect(alr04.textContent).toBe('F1 de alertas por episodio, mismas reglas temporales: 0,462 ALR-04')
    // Una cifra pendiente muestra su texto, no un número inventado.
    expect(per01.textContent).toBe('CR-02, F1 por persona con la frase E-DIR sola: cifra pendiente (generación 2) PER-01')
  })

  it('el campeón no lleva el aviso de «no cuenta como ensayo»', () => {
    montar()
    const detalle = screen.getByRole('region', { name: 'Modo Campeón' })
    expect(detalle.textContent).not.toMatch(/no cuenta como ensayo/)
    expect(within(detalle).getByRole('list', { name: 'Cifras del modo' }).textContent).toMatch(/0,841/)
  })

  it('un modo con error se ve deshabilitado y con su error', () => {
    montar()
    const r = radio(/Clase nueva/)
    expect(r.disabled).toBe(true)
    expect(r.closest('label')?.textContent).toMatch(/No se puede usar: .*machinery/)
    expect(radio(/E-DIR/).disabled).toBe(false)
  })

  it('un modo exploratorio dice que no está medido y no muestra cifras (doc 134 §13.18)', () => {
    const conDistractora = {
      ...MODOS,
      modos: [...MODOS.modos, {
        id: 'distractora', nombre: 'Distractora «t-shirt»', evidencia: 'exploratoria' as const, por_defecto: false,
        resumen: 'El campeón más una clase que ninguna regla lee.', nota: null,
        prompt_set: 'cr01_cr02_v2_tshirt', pattern_set: 'cr01_cr02_v2', medido_en: null,
        clases: [{ id: 't_shirt', frases: ['t-shirt'], fuente: 'prompts/cr01_cr02_v2_tshirt.yaml' }],
        cifras: [], error: null,
      }],
    }
    render(<ModoPanel modos={conDistractora} elegido="distractora" onElegir={vi.fn()} soloLectura={false} />)
    expect(radio(/Distractora/).closest('label')?.textContent).toMatch(/Exploración sin medir/)
    const detalle = screen.getByRole('region', { name: 'Modo Distractora «t-shirt»' })
    expect(detalle.textContent).toMatch(/Sin medir en la generación 2: es una exploración, no evidencia/)
    expect(within(detalle).queryByRole('list', { name: 'Cifras del modo' })).toBeNull()
  })

  it('en solo lectura (durante la corrida) no deja cambiar y lo dice', () => {
    montar('edir', true)
    const radios = screen.getAllByRole('radio') as HTMLInputElement[]
    expect(radios.every((r) => r.disabled)).toBe(true)
    expect(radio(/E-DIR/).checked).toBe(true)
    expect(screen.getByText(/Es el modo de la sesión en curso/)).toBeTruthy()
  })
})
