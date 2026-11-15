import { useCallback, useState } from 'react'

/** Los dos temas de la consola (plan de la consola de evidencia, §10). El claro es el de por
 *  defecto y el de las capturas y la presentación; el oscuro se elige con el selector de la
 *  barra lateral y queda recordado en este navegador. */
export type Tema = 'claro' | 'oscuro'

/** Clave de la preferencia. `index.html` la lee antes de pintar, para que una recarga en el
 *  tema oscuro no muestre un destello claro: si cambia acá, cambia allá. */
export const TEMA_KEY = 'eovrt-tema'

export function leerTema(): Tema {
  try {
    return localStorage.getItem(TEMA_KEY) === 'oscuro' ? 'oscuro' : 'claro'
  } catch {
    return 'claro'
  }
}

/** Marca el tema en <html>: los colores del oscuro cuelgan de `data-theme="dark"`
 *  (styles/tokens.css). Sin la marca rige el claro. */
export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement
  if (tema === 'oscuro') raiz.dataset.theme = 'dark'
  else delete raiz.dataset.theme
}

export function guardarTema(tema: Tema): void {
  try {
    localStorage.setItem(TEMA_KEY, tema)
  } catch {
    /* sin almacenamiento (modo privado): el tema dura lo que dura la página */
  }
}

/** El tema actual y cómo cambiarlo. Cambiarlo lo aplica y lo recuerda. */
export function useTema(): [Tema, (tema: Tema) => void] {
  const [tema, setTema] = useState<Tema>(leerTema)
  const elegir = useCallback((nuevo: Tema) => {
    aplicarTema(nuevo)
    guardarTema(nuevo)
    setTema(nuevo)
  }, [])
  return [tema, elegir]
}
