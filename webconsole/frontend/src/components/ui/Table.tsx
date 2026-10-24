import { useEffect, useRef, useState, type ReactNode, type TableHTMLAttributes } from 'react'

export function Table({ className, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  const cls = ['eo-table', 'eo-table--dense', className].filter(Boolean).join(' ')
  return <table className={cls} {...rest} />
}

/**
 * El scroll horizontal de una tabla, acotado a la tabla.
 *
 * Antes una tabla ancha ensanchaba el documento entero y con ella se
 * desplazaban la cabecera, los avisos y las acciones. Acá el desborde queda
 * adentro: el contenedor ocupa el ancho disponible y la tabla se desplaza
 * sola, sin ocultar columnas.
 *
 * Cuando de verdad desborda, el contenedor se vuelve una región con nombre y
 * entra en el orden de tabulación, para poder desplazarlo con el teclado. Si
 * entra entera, es un `div` más y no agrega una parada de foco inútil.
 */
export function TableScroll({ label, children }: { label: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const [desborda, setDesborda] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const medir = () => setDesborda(el.scrollWidth > el.clientWidth + 1)
    medir()
    if (typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(medir)
    ro.observe(el)
    const tabla = el.firstElementChild
    if (tabla) ro.observe(tabla)
    return () => ro.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className="eo-tablewrap"
      {...(desborda ? { role: 'region', 'aria-label': label, tabIndex: 0 } : {})}
    >
      {children}
    </div>
  )
}

export function MonoCell({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <td className="eo-mono" title={title}>
      {children}
    </td>
  )
}

export function NumCell({ children }: { children: ReactNode }) {
  return <td className="eo-num">{children}</td>
}

export interface SortState {
  key: string
  dir: 'asc' | 'desc'
}

/** Encabezado ordenable: el control es un botón dentro del `th`, y el `th`
 *  declara el orden vigente con `aria-sort`. Antes el click vivía en el `th`
 *  mismo y no había forma de ordenar con el teclado. */
export function SortableHeader({
  label,
  sortKey,
  sortState,
  onSort,
  numeric,
}: {
  label: string
  sortKey: string
  sortState: SortState | null
  onSort: (key: string) => void
  numeric?: boolean
}) {
  const active = sortState?.key === sortKey
  const ariaSort = active ? (sortState!.dir === 'asc' ? 'ascending' : 'descending') : 'none'
  return (
    <th
      className={numeric ? 'eo-th--sortable eo-th--numeric' : 'eo-th--sortable'}
      aria-sort={ariaSort}
    >
      <button type="button" className="eo-th__btn" onClick={() => onSort(sortKey)}>
        {label}
        <span className="eo-th__arrow" aria-hidden="true">
          {active ? (sortState!.dir === 'asc' ? '↑' : '↓') : ''}
        </span>
      </button>
    </th>
  )
}

/** Nombre en dos líneas, sin el `<td>`.
 *
 *  Va separado de `RowNameCell` porque la tabla de Corridas arma sus celdas con
 *  TanStack Table: ahí el `<td>` lo pone el cuerpo de la tabla y la columna solo
 *  aporta el contenido. Las tablas escritas a mano siguen usando `RowNameCell`.
 */
export function RowName({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <span className="eo-rowname">
      <b>{title}</b>
      {subtitle && <span className="eo-mono">{subtitle}</span>}
    </span>
  )
}

export function RowNameCell({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <td>
      <RowName title={title} subtitle={subtitle} />
    </td>
  )
}
