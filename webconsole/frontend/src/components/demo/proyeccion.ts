import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

/** La demo vive en dos modos (✎ 2026-10-31, a pedido del usuario):
 *
 *  - **En la consola** (por defecto): con la barra lateral, las migas y botones, como
 *    cualquier otra pantalla. Es el modo para preparar, ensayar y revisar sin salir de
 *    la consola.
 *  - **Proyección** (`?proyectar=1`, tecla `P`): oscura, letra grande, sin el armazón
 *    y sin ninguna consulta global (spec 2026-10-23 §5 y §6.5). Es la que se proyecta
 *    el día de la defensa, con el navegador en F11.
 *
 *  El modo va en la URL y no en la pantalla completa del navegador a propósito: la
 *  API de pantalla completa se cierra con `Esc`, que en la demo cierra la capa de
 *  evidencia; atarlos sacaría de la proyección al cerrar la capa delante del tribunal. */
export const PARAM_PROYECTAR = 'proyectar'

/** Lo que se conserva al moverse entre `/demo` y su Resultado. */
const CONSERVAR = ['variante', PARAM_PROYECTAR] as const

export function esProyeccion(search: string): boolean {
  return new URLSearchParams(search).get(PARAM_PROYECTAR) === '1'
}

/** Una ruta de la demo que conserva la variante y el modo de la actual. */
export function rutaDemo(path: string, search: string, extra: Record<string, string> = {}): string {
  const actual = new URLSearchParams(search)
  const siguiente = new URLSearchParams()
  for (const clave of CONSERVAR) {
    const valor = actual.get(clave)
    if (valor) siguiente.set(clave, valor)
  }
  for (const [clave, valor] of Object.entries(extra)) siguiente.set(clave, valor)
  const query = siguiente.toString()
  return query ? `${path}?${query}` : path
}

export function useProyeccion() {
  const [params, setParams] = useSearchParams()
  const proyectando = params.get(PARAM_PROYECTAR) === '1'
  const alternar = useCallback(() => {
    setParams(
      (previos) => {
        const nuevos = new URLSearchParams(previos)
        if (nuevos.get(PARAM_PROYECTAR) === '1') nuevos.delete(PARAM_PROYECTAR)
        else nuevos.set(PARAM_PROYECTAR, '1')
        return nuevos
      },
      { replace: true },
    )
  }, [setParams])
  return { proyectando, alternar }
}
