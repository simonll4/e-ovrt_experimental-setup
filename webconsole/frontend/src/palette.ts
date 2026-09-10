/**
 * El sistema de color como código: una sola tabla de tonos y una sola paleta de
 * series.
 *
 * Antes la correspondencia tono → variable CSS estaba escrita tres veces
 * (`Sparkline`, `RunKpiStrip`, `TraceSection`) con tres uniones de tono casi
 * iguales. Tres copias de la misma tabla son tres oportunidades de que un tono
 * nuevo entre en dos lugares y falte en el tercero, y el síntoma sería un color
 * silenciosamente equivocado — que en una consola de seguridad es exactamente el
 * tipo de error que el diseño trata de evitar.
 */

/** Todos los tonos del sistema con su variable CSS. */
export const TONE_VAR = {
  /** En vivo / en curso. */
  live: '--live',
  /** Operativo / completado. */
  ok: '--ok',
  /** Degradado / advertencia. */
  warn: '--wn',
  /** Alerta confirmada. */
  alert: '--sr',
  /** Caído / fallido. */
  error: '--er',
  /** Acción, selección, foco: el violeta. */
  accent: '--ac',
  /** Sin dato / inactivo. */
  neutral: '--nt',
} as const

export type Tone = keyof typeof TONE_VAR

/** Los tonos de un chip de estado. No existe un estado "acento": el violeta es
 *  acción, no condición. */
export type BadgeTone = Exclude<Tone, 'accent'>

/** Los tonos de una marca de gráfico. No existe una serie "neutra": lo que no
 *  tiene dato no se dibuja, se dice. */
export type ChartTone = Exclude<Tone, 'neutral'>

/** Un medidor sí puede tener un tramo neutro (la parte libre). */
export type MeterTone = Tone

/** La variable CSS del tono, lista para un `style`. */
export const toneVar = (tone: Tone): string => `var(${TONE_VAR[tone]})`

// Paleta categórica de 8 slots (skill dataviz), stepped para superficie oscura #1a1a19.
// Validada: banda L, croma, CVD adyacente (peor ΔE 8.4 protan), visión normal (19.3), contraste >=3:1.
// El ORDEN es el mecanismo de seguridad CVD, no cosmética: no reordenar sin re-validar.
export const SERIES_COLORS = [
  '#3987e5', // azul
  '#008300', // verde
  '#d55181', // magenta
  '#c98500', // amarillo
  '#199e70', // aqua
  '#d95926', // naranja
  '#9085e9', // violeta
  '#e66767', // rojo
]
