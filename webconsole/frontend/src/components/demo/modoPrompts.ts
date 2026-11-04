import type { DemoCifra, DemoModoClase, DemoModoEvidencia } from '../../types'
import { numero } from './formato'

/** Modos de prompts de la demo (✎ 2026-11-01): textos compartidos por el selector, la proyección, el
 *  Resultado y la capa de evidencia.
 *
 *  `evidencia` dice qué representa el modo, no lo juzga: por eso los rótulos describen y nunca
 *  califican («buena», «mala»). */
export const EVIDENCIA_MODO: Record<DemoModoEvidencia, string> = {
  congelada: 'Configuración del informe',
  descartada: 'Descartada por la evidencia',
  extension: 'Extensión sin entrenar',
  // ✎ 2026-11-04 (doc 134 §13.18): un set todavía sin medir en la generación 2.
  exploratoria: 'Exploración sin medir',
}

/** `person «person» · cr01_spec «construction worker without safety helmet»`: lo que recibe el modelo. */
export function frasesDelModo(clases: DemoModoClase[]): string {
  return clases.map((c) => `${c.id} ${c.frases.map((f) => `«${f}»`).join(', ')}`).join(' · ')
}

/** El aviso de una sesión que no corrió con el campeón. */
export function avisoModo(nombre: string): string {
  return `Modo ${nombre}: no es la configuración congelada; no cuenta como ensayo`
}

/** El valor de una cifra del modo, con el formato de la demo; pendiente, su texto. */
export function valorCifra(c: DemoCifra): string {
  if (c.pendiente || c.valor == null) return c.texto ?? 'cifra pendiente (generación 2)'
  return `${numero(c.valor, 3)}${c.unidad ? ` ${c.unidad}` : ''}`
}
