// Glosario de interfaz — nombres legibles para códigos que hoy solo existen como
// identificadores crudos en la API. Ver docs/superpowers/specs/2026-07-26-rediseno-consola-design.md §3.
// Los códigos (CR-01, CR-02) nunca se traducen ni se ocultan: se acompañan con su
// nombre, nunca se reemplazan por él.

export const CONDITION_NAMES: Record<string, string> = {
  'CR-01': 'Presencia de persona sin casco',
  'CR-02': 'Presencia de persona sin chaleco',
}

export function conditionLabel(code: string): string {
  const name = CONDITION_NAMES[code]
  return name ? `${code} — ${name}` : code
}

// El backend no garantiza un vocabulario cerrado para los motivos de "dropped:*".
// Un código no reconocido acá cae a mostrarse crudo (ver traceview.ts#controlLabel) —
// nunca en blanco, nunca una cadena en inglés suelta.
export const CONTROL_DROP_REASONS: Record<string, string> = {
  rate_gate: 'límite de tasa',
  overload: 'sobrecarga',
}
