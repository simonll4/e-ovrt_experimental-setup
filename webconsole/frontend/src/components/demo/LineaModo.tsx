import type { DemoModoSesion } from '../../types'
import { avisoModo, frasesDelModo } from './modoPrompts'

/** La línea de la proyección (y del Resultado proyectado) cuando la sesión no corrió con el campeón:
 *  el nombre del modo, que no es la configuración congelada y las frases que recibió el modelo. Con
 *  el campeón no se dibuja nada: la proyección queda como siempre. */
export default function LineaModo({ modo }: { modo: DemoModoSesion | null | undefined }) {
  if (!modo) return null
  return (
    <p className="eo-demo__modo" role="note" aria-label="Modo de prompts">
      {avisoModo(modo.nombre)}. Frases: {frasesDelModo(modo.clases)}
    </p>
  )
}
