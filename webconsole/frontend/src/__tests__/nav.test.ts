import { describe, expect, it } from 'vitest'
import { NAV_GROUPS, crumbsFor } from '../nav'

describe('NAV_GROUPS', () => {
  it('tiene los tres grupos por rol del spec', () => {
    expect(NAV_GROUPS.map((g) => g.title)).toEqual(['Trabajo', 'Definiciones', 'Sistema'])
  })

  it('cubre los 8 destinos y NO incluye /compose (es acción, no destino)', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(tos).toEqual([
      '/', '/experiments', '/compare', '/prompts', '/catalog', '/platform', '/cameras', '/clips',
    ])
    expect(tos).not.toContain('/compose')
  })

  it('ningún destino aparece dos veces', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(new Set(tos).size).toBe(tos.length)
  })

  it('incluye Cámaras en Sistema', () => {
    const sistema = NAV_GROUPS.find((g) => g.title === 'Sistema')!
    expect(sistema.items.map((i) => i.to)).toContain('/cameras')
  })
})

describe('crumbsFor', () => {
  it('raíz devuelve solo Corridas', () => {
    expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Corridas' }])
  })

  it('detalle de corrida encadena Corridas > id', () => {
    expect(crumbsFor('/runs/r_42')).toEqual([
      { to: '/', label: 'Corridas' },
      { to: '/runs/r_42', label: 'r_42' },
    ])
  })

  it('detalle de experimento encadena Experimentos > id', () => {
    expect(crumbsFor('/experiments/exp_7')).toEqual([
      { to: '/experiments', label: 'Experimentos' },
      { to: '/experiments/exp_7', label: 'exp_7' },
    ])
  })

  it('compose tiene su propio crumb aunque no esté en la nav', () => {
    expect(crumbsFor('/compose')).toEqual([{ to: '/compose', label: 'Nueva corrida' }])
  })

  it('/experiments/new tiene crumb propio, NO se confunde con el detalle de un experimento llamado "new"', () => {
    expect(crumbsFor('/experiments/new')).toEqual([
      { to: '/experiments/new', label: 'Nuevo experimento' },
    ])
  })

  it('ruta desconocida no rompe', () => {
    expect(crumbsFor('/nope')).toEqual([])
  })
})
