import { useEffect, useState, type RefObject } from 'react'

/** Ancho disponible del contenedor, medido: el gráfico se dibuja en píxeles
 *  reales para que su tipografía no se achique al encoger la pantalla. */
export function useAncho(ref: RefObject<HTMLElement>, inicial: number) {
  const [ancho, setAncho] = useState(inicial)
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const medir = () => {
      const w = el.clientWidth
      if (w > 0) setAncho(w)
    }
    medir()
    const ro = new ResizeObserver(medir)
    ro.observe(el)
    return () => ro.disconnect()
  }, [ref])
  return ancho
}
