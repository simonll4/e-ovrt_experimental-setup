import { useEffect, useRef } from 'react'

/** Un único manejador de teclado por pantalla de la demo (spec §6.5). Las letras
 *  llegan en minúscula; las teclas con nombre (`Escape`), tal cual. Se ignoran las
 *  combinaciones con Ctrl/Alt/Meta y lo que se escribe en un campo. */
export function useTeclas(manejar: (tecla: string) => void) {
  const ref = useRef(manejar)
  ref.current = manejar
  useEffect(() => {
    const alPresionar = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return
      const destino = e.target as HTMLElement | null
      if (destino && (destino.tagName === 'INPUT' || destino.tagName === 'TEXTAREA' || destino.isContentEditable)) {
        return
      }
      ref.current(e.key.length === 1 ? e.key.toLowerCase() : e.key)
    }
    window.addEventListener('keydown', alPresionar)
    return () => window.removeEventListener('keydown', alPresionar)
  }, [])
}

/** «F F»: dos veces en menos de 2 s, para no cortar sin querer. */
export const VENTANA_FF_MS = 2_000
