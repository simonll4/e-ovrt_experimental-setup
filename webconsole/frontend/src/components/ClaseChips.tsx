import type { Clase } from '../types'

/** Exportado: la columna «Clase» de la tabla (Corridas, Experimentos) usa la
 *  MISMA etiqueta que el chip que filtra por ella — una sola tabla clase → texto. */
export const ETIQUETA_CLASE: Record<Clase, string> = {
  resultado: 'Resultado',
  instrumento: 'Instrumento',
  ensayo: 'Ensayo',
  plataforma: 'Prueba de plataforma',
  sin_clasificar: 'Fuera del registro',
}

/**
 * Chips de filtro por clase — Corridas (Task 7) y Experimentos (Task 8):
 * genérico a propósito, ninguna de las dos pantallas es más "dueña" que la
 * otra.
 *
 * La clase se lee por ETIQUETA y POSICIÓN, nunca por color: cinco tonos
 * chocarían con los que la consola ya reserva para estado (`--live`, `--ok`,
 * `--wn`, `--er` — ver `palette.ts`). El chip seleccionado sí usa el acento,
 * pero eso es SELECCIÓN, no una condición de la corrida — el violeta acá es
 * acción, la misma regla que en el resto de la consola.
 *
 * `conteos` sólo trae las clases con al menos una corrida: un chip en cero no
 * es un filtro útil, es ruido en la barra.
 */
export default function ClaseChips({
  valor,
  onChange,
  conteos,
}: {
  valor: Clase | null
  onChange: (clase: Clase | null) => void
  conteos: Partial<Record<Clase, number>>
}) {
  const clases = (Object.keys(ETIQUETA_CLASE) as Clase[]).filter((c) => conteos[c])
  return (
    <div className="eo-cchips" role="group" aria-label="Filtrar por clase">
      {clases.map((c) => (
        <button
          key={c}
          type="button"
          aria-pressed={valor === c}
          className={valor === c ? 'eo-cchip eo-cchip--on' : 'eo-cchip'}
          onClick={() => onChange(valor === c ? null : c)}
        >
          {ETIQUETA_CLASE[c]} <b>{conteos[c]}</b>
        </button>
      ))}
    </div>
  )
}
