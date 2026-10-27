import { describe, expect, it } from 'vitest'
import { GEN1, NAV_GROUPS, RUNS_PATH, crumbsFor, grupoContiene } from '../nav'

describe('NAV_GROUPS (doc 135 §3.1)', () => {
  it('dos grupos: Evidencia, siempre a la vista, y Laboratorio, plegable', () => {
    expect(NAV_GROUPS.map((g) => g.title)).toEqual(['Evidencia', 'Laboratorio'])
    expect(NAV_GROUPS.find((g) => g.title === 'Evidencia')!.colapsable).toBeFalsy()
    expect(NAV_GROUPS.find((g) => g.title === 'Laboratorio')!.colapsable).toBe(true)
  })

  it('cubre los 12 destinos en el orden del doc y NO incluye /compose (es acción, no destino)', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(tos).toEqual([
      '/', '/resultados', '/demo', '/documentacion', '/platform',
      RUNS_PATH, '/experiments', '/compare', '/prompts', '/catalog', '/cameras', '/clips',
    ])
    expect(tos).not.toContain('/compose')
  })

  it('la entrada es «Para el tribunal» y la lista de corridas vive en /corridas', () => {
    const evidencia = NAV_GROUPS.find((g) => g.title === 'Evidencia')!
    expect(evidencia.items[0]).toMatchObject({ to: '/', label: 'Para el tribunal' })
    expect(RUNS_PATH).toBe('/corridas')
  })

  it('ningún destino aparece dos veces', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(new Set(tos).size).toBe(tos.length)
  })

  it('cada destino tiene icono propio: con la barra colapsada es lo único que queda', () => {
    const iconos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.icon))
    expect(iconos.every(Boolean)).toBe(true)
    expect(new Set(iconos).size).toBe(iconos.length)
  })

  it('el Laboratorio reconoce sus destinos y sus hojas, y no se adueña de la raíz', () => {
    const lab = NAV_GROUPS.find((g) => g.title === 'Laboratorio')!
    expect(grupoContiene(lab, '/prompts')).toBe(true)
    expect(grupoContiene(lab, '/runs/r_1')).toBe(true)
    expect(grupoContiene(lab, '/experiments/new')).toBe(true)
    expect(grupoContiene(lab, '/compose')).toBe(true)
    expect(grupoContiene(lab, '/')).toBe(false)
    expect(grupoContiene(lab, '/resultados')).toBe(false)
  })
})

describe('crumbsFor', () => {
  it('la raíz es «Para el tribunal»', () => {
    expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Para el tribunal' }])
  })

  it('la lista de corridas tiene su miga en /corridas', () => {
    expect(crumbsFor(RUNS_PATH)).toEqual([{ to: RUNS_PATH, label: 'Corridas' }])
  })

  it('detalle de corrida encadena Corridas > id', () => {
    expect(crumbsFor('/runs/r_42')).toEqual([
      { to: RUNS_PATH, label: 'Corridas' },
      { to: '/runs/r_42', label: 'r_42' },
    ])
  })

  it('detalle de una prueba encadena Resultados > id', () => {
    expect(crumbsFor('/resultados/ALR-01')).toEqual([
      { to: '/resultados', label: 'Resultados' },
      { to: '/resultados/ALR-01', label: 'ALR-01' },
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

  it('la generación 1 se llama «Validación inicial» en sus dos URLs', () => {
    expect(crumbsFor('/evidencia')).toEqual([GEN1])
    expect(crumbsFor('/evidencia/generacion-1')).toEqual([GEN1])
    expect(GEN1.label).toBe('Validación inicial (generación 1)')
  })

  it('un paso del recorrido encadena Validación inicial > Paso N, no queda vacío', () => {
    expect(crumbsFor('/evidencia/paso', '?n=3')).toEqual([
      GEN1,
      { to: '/evidencia/paso?n=3', label: 'Paso 3' },
    ])
  })

  it('el respaldo instrumental encadena Validación inicial > Respaldo instrumental', () => {
    expect(crumbsFor('/evidencia/respaldo')).toEqual([
      GEN1,
      { to: '/evidencia/respaldo', label: 'Respaldo instrumental' },
    ])
  })
})
