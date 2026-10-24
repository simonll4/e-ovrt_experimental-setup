import type { ReactNode } from 'react'
import { IconChevron } from './icons'

/** Contenido plegable con `<details>` nativo: teclado y lector ya resueltos. El
 *  triángulo del sistema se reemplaza por el chevrón del kit, que gira al
 *  abrir.
 *
 *  Lo plegado sigue montado: plegar un formulario no pierde lo escrito. */
export default function Disclosure({
  summary,
  children,
  open,
  className,
  onToggle,
  id,
}: {
  summary: ReactNode
  children: ReactNode
  open?: boolean
  className?: string
  onToggle?: (open: boolean) => void
  id?: string
}) {
  return (
    <details
      id={id}
      className={['eo-adv', className].filter(Boolean).join(' ')}
      open={open}
      onToggle={onToggle ? (e) => onToggle((e.currentTarget as HTMLDetailsElement).open) : undefined}
    >
      <summary>
        <span className="eo-adv__chev" aria-hidden="true"><IconChevron /></span>
        <span className="eo-adv__sum">{summary}</span>
      </summary>
      <div className="eo-adv__body">{children}</div>
    </details>
  )
}
