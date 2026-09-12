import { describe, expect, it } from 'vitest'
import { NAV_GROUPS, crumbsFor } from '../nav'

describe('NAV_GROUPS', () => {
  it('tiene los tres grupos por rol del spec', () => {
    expect(NAV_GROUPS.map((g) => g.title)).toEqual(['Trabajo', 'Definiciones', 'Sistema'])
  })

  it('cubre los 10 destinos y NO incluye /compose (es acción, no destino)', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(tos).toEqual([
      '/documentacion', '/evidencia', '/', '/experiments', '/compare', '/prompts', '/catalog', '/platform', '/cameras', '/clips',
    ])
    expect(tos).not.toContain('/compose')
  })

  it('Documentación abre el grupo Trabajo: se lee antes que todo lo demás', () => {
    const trabajo = NAV_GROUPS.find((g) => g.title === 'Trabajo')!
    expect(trabajo.items[0].to).toBe('/documentacion')
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
  it('/evidencia resuelve por NAV_GROUPS', () => {
    const item = NAV_GROUPS.flatMap((group) => group.items).find((entry) => entry.to === '/evidencia')!
    expect(crumbsFor('/evidencia')).toEqual([{ to: item.to, label: item.label }])
  })

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

  it('/documentacion tiene miga propia: se llega desde cualquier término marcado', () => {
    expect(crumbsFor('/documentacion')).toEqual([
      { to: '/documentacion', label: 'Documentación' },
    ])
  })

  it('un paso del recorrido encadena Evidencia > Paso N, no queda vacío', () => {
    expect(crumbsFor('/evidencia/paso', '?n=3')).toEqual([
      { to: '/evidencia', label: 'Evidencia' },
      { to: '/evidencia/paso?n=3', label: 'Paso 3' },
    ])
  })

  it('el respaldo instrumental encadena Evidencia > Respaldo instrumental', () => {
    expect(crumbsFor('/evidencia/respaldo')).toEqual([
      { to: '/evidencia', label: 'Evidencia' },
      { to: '/evidencia/respaldo', label: 'Respaldo instrumental' },
    ])
  })
})
