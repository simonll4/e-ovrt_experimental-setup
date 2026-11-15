export interface BarraHorizontal {
  etiqueta: string
  /** El largo de la barra; `null` si la cifra no resolvió (se dibuja sin barra). */
  valor: number | null
  /** La cifra ya formateada, que va al final de la barra. */
  texto: string
  /** Se muestra separada del resto: no es parte del mismo reparto. */
  aparte?: boolean
}

/** Barras horizontales de una sola serie, con la etiqueta a la izquierda y la cifra al final de cada barra:
 *  se lee sin eje. Una sola serie no lleva leyenda (el título la nombra). Es HTML, no SVG, para que las
 *  etiquetas largas se partan solas en pantallas angostas. */
export default function BarrasHorizontales({ barras, unidad, nombre }: {
  barras: BarraHorizontal[]
  unidad?: string | null
  /** Para el lector de pantalla: qué muestra el gráfico. */
  nombre: string
}) {
  const max = Math.max(0, ...barras.map((b) => b.valor ?? 0))
  const fila = (b: BarraHorizontal) => {
    const fraccion = max > 0 && b.valor != null ? Math.max(0, b.valor) / max : 0
    return (
      <li key={b.etiqueta} className="eo-hbars__fila" title={`${b.etiqueta}: ${b.texto}`}>
        <span className="eo-hbars__etiqueta">{b.etiqueta}</span>
        <span className="eo-hbars__pista">
          <span
            className={b.aparte ? 'eo-hbars__barra eo-hbars__barra--aparte' : 'eo-hbars__barra'}
            style={{ width: `calc((100% - 7ch) * ${fraccion.toFixed(4)})` }}
          />
          <span className="eo-hbars__valor">{b.texto}</span>
        </span>
      </li>
    )
  }
  const principales = barras.filter((b) => !b.aparte)
  const aparte = barras.filter((b) => b.aparte)
  return (
    <div className="eo-hbars">
      {unidad && <p className="eo-hbars__unidad">{unidad}</p>}
      <ul className="eo-hbars__lista" aria-label={nombre}>{principales.map(fila)}</ul>
      {aparte.length > 0 && <ul className="eo-hbars__lista eo-hbars__lista--aparte" aria-label={`${nombre}, aparte`}>{aparte.map(fila)}</ul>}
    </div>
  )
}
