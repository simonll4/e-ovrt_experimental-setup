import { conditionLabel } from './labels'
import type { PromptSet } from './types'

/** Qué significa cada eje de `strategy`. Es la taxonomía del informe (§17.1.5.4.2,
 *  Tabla C.1), copiada de `docs/prompt-strategy.md` §2: no es vocabulario propio de
 *  la consola. Una estrategia que no esté acá NO se traduce a una explicación
 *  inventada: se muestra el código tal cual. */
export const ESTRATEGIAS: Record<string, { nombre: string; que: string }> = {
  canonical_positive: {
    nombre: 'Nombre directo',
    que: 'Etiqueta nominal del objeto, en positivo. Es el vocabulario canónico del detector.',
  },
  syntactic_negation: {
    nombre: 'Negación sintáctica',
    que: 'Pide la ausencia con una negación directa («without»).',
  },
  specificity: {
    nombre: 'Especificidad',
    que: 'Agrega contexto para precisar a quién se refiere (p. ej. «construction worker»).',
  },
  observable_state: {
    nombre: 'Estado observable',
    que: 'Describe lo que se ve cuando la condición ocurre, en vez de negar algo.',
  },
  presence_template: {
    nombre: 'Plantilla de presencia',
    que: 'Busca el objeto presente. Sirve para diagnosticar el fraseo y nunca cuenta como evidencia de ausencia.',
  },
}

export interface TextoAyuda {
  titulo?: string
  texto?: string
  ejemplo?: string
  nota?: string
}

/** La explicación de una clase, armada con lo que el conjunto declara de ella.
 *  Lo que falta se omite: nunca se completa con una suposición. */
export function ayudaDeClase(c: {
  strategy?: string | null
  condition_id?: string | null
  role?: string | null
  enabled_by_default?: boolean
  phrasings?: Record<string, string[]>
}): TextoAyuda {
  const estrategia = c.strategy ? ESTRATEGIAS[c.strategy] : undefined
  const partes = [
    c.condition_id ? conditionLabel(c.condition_id) : null,
    c.strategy ? (estrategia?.nombre ?? c.strategy) : null,
  ].filter(Boolean)
  const frases = Object.values(c.phrasings ?? {}).flat().filter(Boolean)
  const notas = [
    c.enabled_by_default === false ? 'Desactivada por defecto.' : null,
    c.role === 'diagnostic_template' ? 'Es un diagnóstico: no es evidencia de la condición.' : null,
  ].filter(Boolean)
  return {
    titulo: partes.length ? partes.join(' · ') : undefined,
    texto: estrategia?.que,
    ejemplo: frases.length ? frases.join(' · ') : undefined,
    nota: notas.length ? notas.join(' ') : undefined,
  }
}

const MAX_TOOLTIP = 220

/** La primera oración de un texto largo, acotada. Un punto seguido de un dígito o
 *  sin espacio («§2.2», «C.1») no cierra la oración. */
function primeraOracion(texto: string): string {
  const m = texto.match(/^(.+?[.!?])(?=\s+\p{Lu}|$)/su)
  const oracion = m ? m[1] : texto
  return oracion.length <= MAX_TOOLTIP ? oracion : `${oracion.slice(0, MAX_TOOLTIP).trimEnd()}…`
}

/** La explicación de un conjunto: la primera oración de su propia descripción (el
 *  resto vive en la pantalla del conjunto) y qué implica que esté congelado. */
export function ayudaDeConjunto(s: PromptSet): TextoAyuda {
  const descripcion = s.description?.replace(/\s+/g, ' ').trim()
  return {
    texto: descripcion ? primeraOracion(descripcion) : undefined,
    nota: s.frozen
      ? 'Congelado: no se modifica; cualquier cambio es un conjunto nuevo con otro id.'
      : undefined,
  }
}
