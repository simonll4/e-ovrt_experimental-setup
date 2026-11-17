import { describe, expect, it } from 'vitest'
import { GEN1, NAV_ARCHIVO, NAV_GROUPS, RUNS_PATH, crumbsFor, destinoActivo } from '../nav'

const destino = (to: string) => [...NAV_GROUPS.flatMap((g) => g.items), NAV_ARCHIVO].find((i) => i.to === to)!

describe('NAV_GROUPS (plan de la consola de evidencia, §3)', () => {
  it('dos zonas en este orden, Evidencia y Demostrar, y el Archivo al pie', () => {
    expect(NAV_GROUPS.map((g) => g.title)).toEqual(['Evidencia', 'Demostrar'])
    expect(NAV_GROUPS.flatMap((g) => g.items.map((i) => i.label))).toEqual([
      'Inicio', 'Pruebas', 'Tomas en vivo', 'Cómo leer', 'Plataforma', 'Correr un clip', 'Demo con cámara',
    ])
    expect(NAV_ARCHIVO).toMatchObject({ to: GEN1.to, label: 'Archivo' })
  })

  it('las pantallas de laboratorio y las acciones salen de la barra, sin borrarse', () => {
    const tos = [...NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to)), NAV_ARCHIVO.to]
    for (const fuera of [RUNS_PATH, '/experiments', '/compare', '/prompts', '/catalog', '/cameras', '/clips', '/compose']) {
      expect(tos).not.toContain(fuera)
    }
    // Siguen respondiendo por su dirección, con su miga.
    expect(crumbsFor(RUNS_PATH)).toEqual([{ to: RUNS_PATH, label: 'Corridas' }])
    expect(crumbsFor('/prompts')).toEqual([{ to: '/prompts', label: 'Conjuntos de prompts' }])
  })

  it('no hay «Para el tribunal» ni ningún destino repetido', () => {
    const items = [...NAV_GROUPS.flatMap((g) => g.items), NAV_ARCHIVO]
    expect(items.map((i) => i.label).join(' ')).not.toMatch(/tribunal/i)
    expect(new Set(items.map((i) => i.to)).size).toBe(items.length)
  })

  it('cada destino tiene icono propio: con la barra colapsada es lo único que queda', () => {
    const iconos = [...NAV_GROUPS.flatMap((g) => g.items), NAV_ARCHIVO].map((i) => i.icon)
    expect(iconos.every(Boolean)).toBe(true)
    expect(new Set(iconos).size).toBe(iconos.length)
  })

  it('cada pantalla enciende un solo destino: la demo, las tomas y las preguntas no se pisan', () => {
    expect(destinoActivo(destino('/'), '/')).toBe(true)
    expect(destinoActivo(destino('/'), '/preguntas/en-vivo')).toBe(true)
    expect(destinoActivo(destino('/'), '/resultados')).toBe(false)
    expect(destinoActivo(destino('/resultados'), '/resultados/ALR-01')).toBe(true)
    expect(destinoActivo(destino('/demo'), '/demo')).toBe(true)
    expect(destinoActivo(destino('/demo'), '/demo/sesiones')).toBe(false)
    expect(destinoActivo(destino('/demo/sesiones'), '/demo/sesiones')).toBe(true)
    expect(destinoActivo(destino('/demo/sesiones'), '/demo/resultado/demo_x')).toBe(true)
    expect(destinoActivo(NAV_ARCHIVO, '/evidencia/paso')).toBe(true)
    expect(destinoActivo(NAV_ARCHIVO, '/')).toBe(false)
  })
})

describe('crumbsFor', () => {
  it('la raíz es «Inicio»', () => {
    expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Inicio' }])
  })

  it('una pregunta cuelga de Inicio (su título lo pone Breadcrumbs con la vista cargada)', () => {
    expect(crumbsFor('/preguntas/en-vivo')).toEqual([
      { to: '/', label: 'Inicio' },
      { to: '/preguntas/en-vivo', label: 'en-vivo' },
    ])
  })

  it('detalle de corrida encadena Corridas > id', () => {
    expect(crumbsFor('/runs/r_42')).toEqual([
      { to: RUNS_PATH, label: 'Corridas' },
      { to: '/runs/r_42', label: 'r_42' },
    ])
  })

  it('detalle de una prueba encadena Pruebas > su nombre llano', () => {
    expect(crumbsFor('/resultados/ALR-01')).toEqual([
      { to: '/resultados', label: 'Pruebas' },
      { to: '/resultados/ALR-01', label: 'Alerta por episodio, por escena' },
    ])
    expect(crumbsFor('/resultados/ZZZ-99')[1]).toEqual({ to: '/resultados/ZZZ-99', label: 'ZZZ-99' })
  })

  it('las tomas guardadas y su resultado cuelgan de «Tomas en vivo»', () => {
    expect(crumbsFor('/demo/sesiones')).toEqual([{ to: '/demo/sesiones', label: 'Tomas en vivo' }])
    expect(crumbsFor('/demo/resultado/demo_x')).toEqual([
      { to: '/demo/sesiones', label: 'Tomas en vivo' },
      { to: '/demo/resultado/demo_x', label: 'demo_x' },
    ])
    expect(crumbsFor('/demo')).toEqual([{ to: '/demo', label: 'Demo con cámara' }])
  })

  it('detalle de experimento encadena Experimentos > id', () => {
    expect(crumbsFor('/experiments/exp_7')).toEqual([
      { to: '/experiments', label: 'Experimentos' },
      { to: '/experiments/exp_7', label: 'exp_7' },
    ])
  })

  it('compose y /experiments/new tienen su miga aunque no estén en la nav', () => {
    expect(crumbsFor('/compose')).toEqual([{ to: '/compose', label: 'Nueva corrida' }])
    expect(crumbsFor('/experiments/new')).toEqual([{ to: '/experiments/new', label: 'Nuevo experimento' }])
  })

  it('ruta desconocida no rompe', () => {
    expect(crumbsFor('/nope')).toEqual([])
  })

  it('/documentacion es «Cómo leer»: se llega desde cualquier término marcado', () => {
    expect(crumbsFor('/documentacion')).toEqual([{ to: '/documentacion', label: 'Cómo leer' }])
  })

  it('la etapa de desarrollo es el «Archivo», en /archivo y en sus dos URLs anteriores (plan §4 y §5)', () => {
    expect(GEN1.to).toBe('/archivo')
    expect(crumbsFor('/archivo')).toEqual([GEN1])
    expect(crumbsFor('/evidencia')).toEqual([GEN1])
    expect(crumbsFor('/evidencia/generacion-1')).toEqual([GEN1])
    expect(GEN1.label).toBe('Archivo')
  })

  it('un paso del recorrido encadena Archivo > Paso N, no queda vacío', () => {
    expect(crumbsFor('/evidencia/paso', '?n=3')).toEqual([GEN1, { to: '/evidencia/paso?n=3', label: 'Paso 3' }])
  })

  it('el respaldo instrumental encadena Archivo > Respaldo instrumental', () => {
    expect(crumbsFor('/evidencia/respaldo')).toEqual([GEN1, { to: '/evidencia/respaldo', label: 'Respaldo instrumental' }])
  })
})
