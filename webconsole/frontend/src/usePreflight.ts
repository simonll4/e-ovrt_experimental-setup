import { useEffect, useState } from 'react'
import { getPreflight } from './api'
import type { PreflightStatus } from './types'

const POLL_MS = 5000

/**
 * Poll `/api/preflight` (estado agregado media-plane + control-plane). Devuelve
 * null mientras carga o si el BFF no responde — quien lo consuma debe tratar
 * null como "no listo" para gatear lanzamientos.
 */
export function usePreflight(): PreflightStatus | null {
  const [status, setStatus] = useState<PreflightStatus | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      getPreflight()
        .then((s) => alive && setStatus(s))
        .catch(() => alive && setStatus(null))
    tick()
    const timer = setInterval(tick, POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  return status
}
