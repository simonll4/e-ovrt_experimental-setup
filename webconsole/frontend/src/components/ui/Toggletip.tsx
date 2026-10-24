import { useEffect, useId, useRef, useState, type ReactNode } from 'react'

/**
 * Ayuda que se abre con toque, click o teclado — no con hover.
 *
 * La procedencia de una cifra citada y varias ayudas vivían sólo en `title`:
 * invisibles en una pantalla táctil y para el teclado. Acá el botón dice qué
 * abre, el contenido se anuncia al aparecer y Escape lo cierra. El contenido va
 * en el flujo (no flota), así ninguna tabla con scroll lo recorta.
 */
export default function Toggletip({
  label,
  children,
  ariaLabel,
}: {
  label: ReactNode
  children: ReactNode
  ariaLabel?: string
}) {
  const [abierto, setAbierto] = useState(false)
  const id = useId()
  const raiz = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!abierto) return
    const afuera = (e: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener('mousedown', afuera)
    return () => document.removeEventListener('mousedown', afuera)
  }, [abierto])

  return (
    <span
      className="eo-tt"
      ref={raiz}
      onKeyDown={(e) => {
        if (e.key === 'Escape' && abierto) {
          e.stopPropagation()
          setAbierto(false)
        }
      }}
    >
      <button
        type="button"
        className="eo-tt__btn"
        aria-expanded={abierto}
        aria-controls={abierto ? id : undefined}
        aria-label={ariaLabel}
        onClick={(e) => {
          e.stopPropagation()
          setAbierto((v) => !v)
        }}
      >
        {label}
      </button>
      {abierto && (
        <span className="eo-tt__pop" id={id} role="status">
          {children}
        </span>
      )}
    </span>
  )
}
