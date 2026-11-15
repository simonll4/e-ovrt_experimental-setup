import { useRef } from 'react'
import { SERIES_COLORS } from '../../palette'
import { useAncho } from './useAncho'

export interface SerieDeLineas {
  nombre: string
  /** Paralelo a las categorías; `null` es un punto que no resolvió y no se dibuja. */
  valores: Array<number | null>
  /** Las cifras ya formateadas, paralelas a `valores`. */
  textos: string[]
}

const TICKS = [0, 0.25, 0.5, 0.75, 1]
const fmtTick = (t: number) => t.toLocaleString('es-AR', { maximumFractionDigits: 2 })

/** Separa en vertical las etiquetas del final de cada línea para que no se pisen. */
export function separarEtiquetas(ys: number[], minimo = 16): number[] {
  const orden = ys.map((y, i) => ({ y, i })).sort((a, b) => a.y - b.y)
  for (let k = 1; k < orden.length; k++) {
    if (orden[k].y - orden[k - 1].y < minimo) orden[k].y = orden[k - 1].y + minimo
  }
  const salida = [...ys]
  orden.forEach(({ y, i }) => { salida[i] = y })
  return salida
}

/** Líneas sobre categorías ordenadas, con el dominio fijo en [0, 1] (un F1, una tasa): dos gráficos
 *  con la misma escala se pueden comparar. Con dos o más series lleva leyenda y, además, el nombre y la
 *  última cifra de cada serie al final de su línea. Las demás cifras están en el título de cada punto. */
export default function LineasPorPunto({ categorias, series, nombre, eje, alto = 280 }: {
  categorias: string[]
  series: SerieDeLineas[]
  nombre: string
  /** El nombre de la magnitud, arriba del eje. */
  eje?: string
  alto?: number
}) {
  const contenedor = useRef<HTMLDivElement>(null)
  const disponible = useAncho(contenedor, 720)
  const izq = 44
  const der = 132
  const arriba = 34
  const abajo = 36
  const plotW = Math.max(categorias.length * 110, disponible - izq - der)
  const ancho = Math.round(plotW + izq + der)
  const plotH = alto - arriba - abajo
  const xDe = (i: number) => ((i + 0.5) * plotW) / Math.max(1, categorias.length)
  const yDe = (v: number) => plotH - Math.max(0, Math.min(1, v)) * plotH
  const finales = series.map((s) => {
    let ultimo = -1
    s.valores.forEach((v, i) => { if (v != null && Number.isFinite(v)) ultimo = i })
    return ultimo
  })
  const yEtiquetas = separarEtiquetas(finales.map((u, si) => (u < 0 ? plotH : yDe(series[si].valores[u] as number))))
  const desborda = ancho > disponible + 1

  return (
    <div className="eo-lineas">
      {series.length > 1 && (
        <ul className="eo-bars__legend eo-lineas__leyenda">
          {series.map((s, si) => (
            <li key={s.nombre}>
              <span className="eo-lineas__clave" style={{ background: SERIES_COLORS[si % SERIES_COLORS.length] }} />
              {s.nombre}
            </li>
          ))}
        </ul>
      )}
      <div
        ref={contenedor}
        className="eo-bars__scroll"
        {...(desborda ? { role: 'region', 'aria-label': nombre, tabIndex: 0 } : {})}
      >
        <svg width={ancho} height={alto} viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label={nombre}>
          <g transform={`translate(${izq}, ${arriba})`}>
            {eje && <text x={-8} y={-18} textAnchor="end" className="eo-bars__tick">{eje}</text>}
            {TICKS.map((t) => (
              <g key={t}>
                <line x1={0} y1={yDe(t)} x2={plotW} y2={yDe(t)} stroke="var(--bd)" />
                <text x={-8} y={yDe(t) + 4} textAnchor="end" className="eo-bars__tick">{fmtTick(t)}</text>
              </g>
            ))}
            {categorias.map((c, i) => (
              <text key={c} x={xDe(i)} y={plotH + 22} textAnchor="middle" className="eo-bars__group">{c}</text>
            ))}
            {series.map((s, si) => {
              const color = SERIES_COLORS[si % SERIES_COLORS.length]
              const puntos = s.valores.map((v, i) => (v != null && Number.isFinite(v) ? [xDe(i), yDe(v), i] as const : null))
                .filter((p): p is readonly [number, number, number] => p !== null)
              const d = puntos.map(([x, y], k) => `${k ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('')
              const u = finales[si]
              return (
                <g key={s.nombre}>
                  {puntos.length > 1 && <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />}
                  {puntos.map(([x, y, i]) => (
                    <g key={i}>
                      <circle cx={x} cy={y} r={4.5} fill={color} stroke="var(--s1)" strokeWidth={2} />
                      <circle cx={x} cy={y} r={12} fill="transparent">
                        <title>{`${s.nombre} — ${categorias[i]}: ${s.textos[i]}`}</title>
                      </circle>
                    </g>
                  ))}
                  {u >= 0 && (
                    <text x={xDe(u) + 12} y={yEtiquetas[si] + 4} className="eo-lineas__final">
                      {s.nombre} <tspan className="eo-lineas__cifra">{s.textos[u]}</tspan>
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </svg>
      </div>
    </div>
  )
}
