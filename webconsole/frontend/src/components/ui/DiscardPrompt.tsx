import { useEffect, useRef } from 'react'
import Button from './Button'

/** Hay cambios sin guardar y se pidió cerrar o pasar a otro recurso: se
 *  ofrece seguir editando (primero, con el foco) o descartar. No guarda nada
 *  por su cuenta: el borrador vive sólo en el editor. */
export default function DiscardPrompt({
  what,
  onKeep,
  onDiscard,
}: {
  what: string
  onKeep: () => void
  onDiscard: () => void
}) {
  const seguir = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    seguir.current?.focus()
  }, [])
  return (
    <div className="eo-stale eo-discard" role="alert">
      <span>Hay cambios sin guardar en {what}. Si seguís, se pierden.</span>
      <span className="eo-discard__actions">
        <Button ref={seguir} onClick={onKeep}>Seguir editando</Button>
        <Button variant="danger" onClick={onDiscard}>Descartar cambios</Button>
      </span>
    </div>
  )
}
