import { useEffect, useState } from 'react'
import { getTarget } from './api'
import type { TargetStatus } from './types'

const POLL_MS = 5000

/**
 * Poll `/api/target` y devolver el estado actual. Si el servicio se reinicia con otro
 * `EOVRT_MODEL_REF`, este hook lo refleja en <= POLL_MS sin necesidad de refrescar la
 * página — quien lo consuma puede keyar sus propios efectos (p.ej. recarga de
 * catálogos) en `target?.model?.ref`.
 */
export function useTarget(): TargetStatus | null {
  const [target, setTarget] = useState<TargetStatus | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      getTarget()
        .then((t) => alive && setTarget(t))
        .catch(() => alive && setTarget(null))
    tick()
    const timer = setInterval(tick, POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  return target
}

/** Atajo para el caso común: solo el `ref` del modelo activo en el target. */
export function useTargetModelRef(): string | undefined {
  return useTarget()?.model?.ref
}
