import type { TraceFrame } from './types'

export interface RunSeries {
  detectionsPerFrame: number[]
  /** Inverso del delta entre cuadros consecutivos. null en el primero y cuando el
   *  delta es 0 o faltan timestamps: un fps infinito miente peor que un hueco. */
  instantFps: Array<number | null>
  /** Segundos desde el primer cuadro. 0 cuando no hay timestamps. */
  elapsedSeconds: number[]
  totalSeconds: number
}

/**
 * Deriva las series temporales de una corrida a partir de su traza.
 *
 * El backend no expone series: solo `timestamp_ms` y `detections` por cuadro en
 * `/api/runs/{id}/trace`. Todo lo que dibujan los sparklines sale de acá, y por
 * eso esta función es pura y se testea sola.
 */
export function buildRunSeries(frames: TraceFrame[]): RunSeries {
  if (!frames.length) {
    return { detectionsPerFrame: [], instantFps: [], elapsedSeconds: [], totalSeconds: 0 }
  }

  const detectionsPerFrame = frames.map((fr) => fr.detections?.length ?? 0)

  const base = frames.find((fr) => fr.timestamp_ms != null)?.timestamp_ms ?? null
  const elapsedSeconds = frames.map((fr) =>
    base != null && fr.timestamp_ms != null ? (fr.timestamp_ms - base) / 1000 : 0,
  )

  const instantFps: Array<number | null> = frames.map((fr, i) => {
    if (i === 0) return null
    const prev = frames[i - 1].timestamp_ms
    const cur = fr.timestamp_ms
    if (prev == null || cur == null) return null
    const deltaMs = cur - prev
    if (!Number.isFinite(deltaMs) || deltaMs <= 0) return null
    return 1000 / deltaMs
  })

  const finite = elapsedSeconds.filter(Number.isFinite)
  const totalSeconds = finite.length ? Math.max(...finite) : 0

  return { detectionsPerFrame, instantFps, elapsedSeconds, totalSeconds }
}

/**
 * Promedio de los valores cuyo segundo cae en [fromSec, toSec]. null si no hay
 * ninguno.
 *
 * `openUpper` excluye el borde superior, dejando [fromSec, toSec). Hace falta
 * para comparar dos ventanas consecutivas: con los dos bordes cerrados, la
 * muestra del límite cae en las dos y sesga el promedio de la anterior.
 */
export function windowMean(
  values: Array<number | null>,
  seconds: number[],
  fromSec: number,
  toSec: number,
  openUpper = false,
): number | null {
  let sum = 0
  let n = 0
  for (let i = 0; i < values.length; i++) {
    const s = seconds[i]
    const v = values[i]
    if (s == null || !Number.isFinite(s) || s < fromSec) continue
    if (openUpper ? s >= toSec : s > toSec) continue
    if (v == null || !Number.isFinite(v)) continue
    sum += v
    n++
  }
  return n ? sum / n : null
}

/**
 * Diferencia entre la última ventana y la anterior.
 *
 * Devuelve null si no hay dos ventanas completas. En una corrida terminada o
 * recién arrancada el delta no existe, y mostrar un "+0,0" inventado sería peor
 * que no mostrar nada: en una defensa, un número de más es una pregunta de más.
 */
export function recentDelta(
  values: Array<number | null>,
  seconds: number[],
  windowSec = 30,
): number | null {
  const finite = seconds.filter(Number.isFinite)
  if (!finite.length) return null
  const end = Math.max(...finite)
  if (end < windowSec * 2) return null
  const recent = windowMean(values, seconds, end - windowSec, end)
  // La ventana anterior cierra abierta arriba: la muestra justo en el límite
  // pertenece a la reciente, y contarla en las dos sesga la comparación.
  const prior = windowMean(values, seconds, end - windowSec * 2, end - windowSec, true)
  if (recent == null || prior == null) return null
  return recent - prior
}
