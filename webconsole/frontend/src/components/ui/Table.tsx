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

export function RowNameCell({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <td>
      <span className="eo-rowname">
        <b>{title}</b>
        {subtitle && <span className="eo-mono">{subtitle}</span>}
      </span>
    </td>
  )
}
