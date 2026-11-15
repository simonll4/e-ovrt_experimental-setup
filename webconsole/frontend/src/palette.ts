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

// Paleta categórica de 8 slots (skill dataviz), un par claro/oscuro por slot: los valores viven
// en styles/tokens.css (--c1…--c8) y cambian con el tema.
// Validada con validate_palette.js en los dos temas:
//   oscuro (superficie #1a1a19): banda L, croma, CVD adyacente (peor ΔE 8.4 protan), visión
//   normal (19.3), contraste >= 3:1;
//   claro (superficie #fcfcfb): banda L, croma, CVD adyacente (peor ΔE 9.1 protan), visión
//   normal (19.6); magenta, amarillo y aqua quedan debajo de 3:1 contra la superficie, así que
//   un gráfico que los use lleva etiquetas visibles (GroupedBars rotula cada barra).
// El ORDEN es el mecanismo de seguridad CVD, no cosmética: no reordenar sin re-validar.
export const SERIES_COLORS = [
  'var(--c1)', // azul
  'var(--c2)', // verde
  'var(--c3)', // magenta
  'var(--c4)', // amarillo
  'var(--c5)', // aqua
  'var(--c6)', // naranja
  'var(--c7)', // violeta
  'var(--c8)', // rojo
]

/** Los mismos ocho tonos para dibujar ENCIMA de un cuadro de video o una imagen (cajas y
 *  rótulos de detección). El video es igual en los dos temas, así que estos no cambian: son los
 *  pasos para fondo oscuro. Un <canvas> no resuelve variables CSS; por eso van en hex. */
export const SERIES_SOBRE_VIDEO = [
  '#3987e5', '#008300', '#d55181', '#c98500', '#199e70', '#d95926', '#9085e9', '#e66767',
]

/** La tinta del rótulo de una detección, sobre el color de su caja. */
export const TINTA_SOBRE_VIDEO = '#0a0a0a'
