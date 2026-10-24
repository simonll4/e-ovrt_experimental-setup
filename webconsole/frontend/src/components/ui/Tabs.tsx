import { useRef, type KeyboardEvent, type ReactNode } from 'react'

export interface TabItem<T extends string> {
  id: T
  label: ReactNode
  /** Conteo que acompaña al rótulo (cuadros, archivos). */
  count?: ReactNode
}

const tabId = (base: string, id: string) => `${base}-tab-${id}`
const panelId = (base: string, id: string) => `${base}-panel-${id}`

/**
 * Pestañas con la relación tab/tabpanel completa y foco itinerante.
 *
 * Una sola parada de tabulación —la pestaña activa—; flechas izquierda/derecha
 * e Inicio/Fin recorren y activan. Antes eran botones sueltos con
 * `role="tab"`: el lector las anunciaba como pestañas pero el teclado no hacía
 * lo que una pestaña promete.
 */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  label,
  idBase,
}: {
  items: Array<TabItem<T>>
  value: T
  onChange: (value: T) => void
  label: string
  idBase: string
}) {
  const refs = useRef<Array<HTMLButtonElement | null>>([])

  const ir = (i: number) => {
    const n = items.length
    const j = (i + n) % n
    onChange(items[j].id)
    refs.current[j]?.focus()
  }

  const tecla = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (e.key === 'ArrowRight') { e.preventDefault(); ir(i + 1) }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); ir(i - 1) }
    else if (e.key === 'Home') { e.preventDefault(); ir(0) }
    else if (e.key === 'End') { e.preventDefault(); ir(items.length - 1) }
  }

  return (
    <div className="eo-tabs" role="tablist" aria-label={label}>
      {items.map((it, i) => {
        const sel = it.id === value
        return (
          <button
            key={it.id}
            ref={(el) => { refs.current[i] = el }}
            type="button"
            role="tab"
            id={tabId(idBase, it.id)}
            aria-selected={sel}
            aria-controls={sel ? panelId(idBase, it.id) : undefined}
            tabIndex={sel ? 0 : -1}
            onClick={() => onChange(it.id)}
            onKeyDown={(e) => tecla(e, i)}
          >
            {it.label}
            {/* El espacio literal separa el número del rótulo en el nombre
                accesible («Traza 260», no «Traza260»). */}
            {it.count != null && it.count !== '' ? (
              <>{' '}<span className="eo-tabs__count eo-mono">{it.count}</span></>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}

export function TabPanel({ idBase, id, children }: { idBase: string; id: string; children: ReactNode }) {
  return (
    <div
      className="eo-tabpanel"
      role="tabpanel"
      id={panelId(idBase, id)}
      aria-labelledby={tabId(idBase, id)}
    >
      {children}
    </div>
  )
}
