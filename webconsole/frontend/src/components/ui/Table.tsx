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
