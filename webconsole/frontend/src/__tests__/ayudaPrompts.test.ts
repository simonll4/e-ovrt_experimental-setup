import { describe, expect, it } from 'vitest'
import { ayudaDeClase, ayudaDeConjunto, ESTRATEGIAS } from '../ayudaPrompts'
import type { PromptClass, PromptSet } from '../types'

const clase = (extra: Partial<PromptClass> = {}): PromptClass => ({
  id: 'cr01_neg', role: 'condition_evidence', enabled_by_default: true,
  strategy: 'syntactic_negation', condition_id: 'CR-01',
  phrasings: { default: ['person without hard hat'] },
  ...extra,
})

describe('ayudaDeClase — la explicación sale de lo que el propio conjunto declara', () => {
  it('junta condición, estrategia y la frase exacta que se le manda al modelo', () => {
    const a = ayudaDeClase(clase())
    expect(a.titulo).toBe('CR-01 — Presencia de persona sin casco · Negación sintáctica')
    expect(a.texto).toBe(ESTRATEGIAS.syntactic_negation.que)
    expect(a.ejemplo).toBe('person without hard hat')
  })

  it('una clase que no declara estrategia ni condición muestra solo su frase, sin inventar', () => {
    const a = ayudaDeClase(clase({ strategy: null, condition_id: null, role: null }))
    expect(a.titulo).toBeUndefined()
    expect(a.texto).toBeUndefined()
    expect(a.ejemplo).toBe('person without hard hat')
  })

  it('una estrategia que la consola no conoce no se traduce a una explicación falsa', () => {
    const a = ayudaDeClase(clase({ strategy: 'estrategia_nueva' }))
    expect(a.texto).toBeUndefined()
    expect(a.titulo).toBe('CR-01 — Presencia de persona sin casco · estrategia_nueva')
  })

  it('avisa si está desactivada por defecto y si es solo diagnóstico', () => {
    const a = ayudaDeClase(clase({
      id: 'cr01_template', strategy: 'presence_template', role: 'diagnostic_template',
      enabled_by_default: false, phrasings: { default: ['a photo of a hard hat'] },
    }))
    expect(a.nota).toContain('Desactivada por defecto')
    expect(a.nota).toContain('no es evidencia')
  })

  it('con varias frases las lista todas; sin ninguna, no hay ejemplo', () => {
    expect(ayudaDeClase(clase({ phrasings: { default: ['a', 'b'] } })).ejemplo).toBe('a · b')
    expect(ayudaDeClase(clase({ phrasings: {} })).ejemplo).toBeUndefined()
  })
})

describe('ayudaDeConjunto', () => {
  const conjunto = (extra: Partial<PromptSet> = {}): PromptSet => ({
    id: 'edir_v1', description: 'Set del carril E-DIR. Un prompt por eje.\nSegunda línea.',
    language: 'en', frozen: true, classes: [], status: 'frozen', track: 'comparative', ...extra,
  })

  it('usa el texto del propio conjunto y explica qué implica estar congelado', () => {
    const a = ayudaDeConjunto(conjunto())
    // Un tooltip es breve: la descripción completa vive en la pantalla del conjunto.
    expect(a.texto).toBe('Set del carril E-DIR.')
    expect(a.nota).toContain('Congelado')
  })

  it('no corta en un punto de una cifra o una sección («§2.2», «C.1»)', () => {
    const a = ayudaDeConjunto(conjunto({
      description: 'Set del carril E-DIR (doc 12 §2.2): tabla C.1 del informe. Segunda oración.',
    }))
    expect(a.texto).toBe('Set del carril E-DIR (doc 12 §2.2): tabla C.1 del informe.')
  })

  it('una descripción sin punto o demasiado larga se acota con puntos suspensivos', () => {
    const larga = 'palabra '.repeat(80).trim()
    const a = ayudaDeConjunto(conjunto({ description: larga }))
    expect(a.texto!.length).toBeLessThanOrEqual(221)
    expect(a.texto!.endsWith('…')).toBe(true)
  })

  it('sin descripción no la inventa', () => {
    expect(ayudaDeConjunto(conjunto({ description: null })).texto).toBeUndefined()
  })
})
