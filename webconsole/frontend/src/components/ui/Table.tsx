import type { ReactNode, TableHTMLAttributes } from 'react'

export function Table({ className, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  const cls = ['eo-table', 'eo-table--dense', className].filter(Boolean).join(' ')
  return <table className={cls} {...rest} />
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
  return (
    <th
      className={numeric ? 'eo-th--sortable eo-th--numeric' : 'eo-th--sortable'}
      onClick={() => onSort(sortKey)}
    >
      {label}
      {active && <span className="eo-th__arrow">{sortState!.dir === 'asc' ? '↑' : '↓'}</span>}
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
