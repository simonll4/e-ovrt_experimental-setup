import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react'

const ENFOCABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function abrirModal(d: HTMLDialogElement) {
  if (typeof d.showModal === 'function') d.showModal()
  else d.setAttribute('open', '')
}

function cerrarModal(d: HTMLDialogElement) {
  if (typeof d.close === 'function') d.close()
  else d.removeAttribute('open')
}

/**
 * Diálogo modal nativo.
 *
 * `showModal()` es lo que da la contención de foco y deja el fondo inerte: el
 * cajón anterior era un panel con `transform` que tapaba la pantalla mientras el
 * tabulador seguía recorriendo lo de atrás.
 *
 * - Al abrir, el foco va a `initialFocus` o al primer control del diálogo.
 * - Escape y el click en el fondo llaman a `onClose`.
 * - Al cerrar, el foco vuelve a quien lo abrió, salvo `restoreFocus={false}`
 *   (al navegar, el foco va al encabezado del destino, no al botón de menú).
 * - Cerrado, el diálogo no está en el orden de foco.
 */
export default function Dialog({
  open,
  onClose,
  label,
  className,
  initialFocus,
  restoreFocus = true,
  children,
}: {
  open: boolean
  onClose: () => void
  label: string
  className?: string
  initialFocus?: () => HTMLElement | null
  restoreFocus?: boolean
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const quienAbrio = useRef<HTMLElement | null>(null)
  const restaurar = useRef(restoreFocus)
  restaurar.current = restoreFocus
  const cerrarRef = useRef(onClose)
  cerrarRef.current = onClose

  useLayoutEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.hasAttribute('open')) {
      quienAbrio.current = document.activeElement as HTMLElement | null
      abrirModal(d)
      const destino = initialFocus?.() ?? d.querySelector<HTMLElement>(ENFOCABLE)
      destino?.focus()
    } else if (!open && d.hasAttribute('open')) {
      cerrarModal(d)
      if (restaurar.current) quienAbrio.current?.focus?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  // Desmontado abierto (cambio de modo de navegación, salida de la pantalla):
  // el navegador saca solo el estado modal al quitar el nodo, pero el foco
  // tiene que volver a algún lado que exista.
  useEffect(() => () => {
    if (ref.current?.hasAttribute('open') && restaurar.current) quienAbrio.current?.focus?.()
  }, [])

  // El evento `cancel` es el Escape del diálogo nativo: se cancela el cierre
  // propio del navegador para que el estado de React sea el único que decide.
  useEffect(() => {
    const d = ref.current
    if (!d) return
    const cancelar = (e: Event) => {
      e.preventDefault()
      cerrarRef.current()
    }
    d.addEventListener('cancel', cancelar)
    return () => d.removeEventListener('cancel', cancelar)
  }, [])

  return (
    <dialog
      ref={ref}
      className={['eo-dialog', className].filter(Boolean).join(' ')}
      aria-label={label}
      onClick={(e) => {
        // El fondo de un diálogo modal es el propio elemento <dialog>.
        if (e.target === ref.current) cerrarRef.current()
      }}
      onKeyDown={(e) => {
        // Respaldo para entornos sin `showModal`, donde no existe `cancel`.
        if (e.key === 'Escape' && typeof ref.current?.showModal !== 'function') {
          e.preventDefault()
          cerrarRef.current()
        }
      }}
    >
      {children}
    </dialog>
  )
}
