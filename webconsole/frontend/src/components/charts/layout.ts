// Funciones puras de layout de gráficos. Sin React, sin DOM: acá vive la
// aritmética que puede estar sutilmente mal, y por eso se testea sola.

export interface AreaPaths {
  /** Ruta de la línea. '' si no hay al menos dos puntos finitos. */
  line: string
  /** Ruta del área cerrada contra la línea base. '' en el mismo caso. */
  area: string
}

const fmt = (n: number): string => (Number.isInteger(n) ? String(n) : Number(n.toFixed(2)).toString())

/**
 * Mapea `values` a rutas SVG en una caja de `width` x `height`.
 *
 * El dominio Y va de min a max de la serie; una serie constante se dibuja plana a
 * media altura en vez de dividir por cero. Los nulos se saltean: la línea une los
 * puntos válidos en vez de cortarse, porque un hueco en la serie no es un cero.
 * `pad` reserva píxeles arriba y abajo para que el trazo no se corte contra el borde.
 */
export function areaPaths(
  values: Array<number | null>,
  width: number,
  height: number,
  pad = 2,
): AreaPaths {
  const idx: number[] = []
  values.forEach((v, i) => {
    if (v != null && Number.isFinite(v)) idx.push(i)
  })
  if (idx.length < 2) return { line: '', area: '' }

  const nums = idx.map((i) => values[i] as number)
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const span = max - min
  const top = pad
  const bottom = height - pad
  const usable = bottom - top

  const xOf = (i: number) => (values.length <= 1 ? 0 : (i / (values.length - 1)) * width)
  const yOf = (v: number) => (span === 0 ? top + usable / 2 : bottom - ((v - min) / span) * usable)

  const pts = idx.map((i) => `${fmt(xOf(i))},${fmt(yOf(values[i] as number))}`)
  const line = `M${pts[0]}` + pts.slice(1).map((p) => `L${p}`).join('')
  const firstX = fmt(xOf(idx[0]))
  const lastX = fmt(xOf(idx[idx.length - 1]))
  const area = `${line}L${lastX},${fmt(height)}L${firstX},${fmt(height)}Z`
  return { line, area }
}

/**
 * Marcas de eje redondas desde 0 hasta cubrir `max`, en al menos `count`
 * intervalos. Devuelve siempre valores finitos y sin repetidos.
 */
export function niceTicks(max: number, count = 4): number[] {
  if (!Number.isFinite(max) || max <= 0) {
    return Array.from({ length: count + 1 }, (_, i) => i / count)
  }
  const raw = max / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const norm = raw / mag
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag
  const ticks: number[] = []
  for (let i = 0; i <= count; i++) ticks.push(Number((step * i).toFixed(10)))
  while (ticks[ticks.length - 1] < max) {
    ticks.push(Number((ticks[ticks.length - 1] + step).toFixed(10)))
  }
  return ticks
}
