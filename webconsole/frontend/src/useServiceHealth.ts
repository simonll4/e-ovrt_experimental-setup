import { useEffect, useState } from 'react'
import { getPreflight, getTarget } from './api'

export type ServiceStatus = 'ok' | 'down' | 'checking'

export interface ServiceHealth {
  media: ServiceStatus
  control: ServiceStatus
}

const POLL_MS = 10_000

export function useServiceHealth(): ServiceHealth {
  const [health, setHealth] = useState<ServiceHealth>({ media: 'checking', control: 'checking' })

  useEffect(() => {
    let alive = true

    const poll = () => {
      getTarget()
        .then(() => {
          if (alive) setHealth((h) => ({ ...h, media: 'ok' }))
        })
        .catch(() => {
          if (alive) setHealth((h) => ({ ...h, media: 'down' }))
        })
      getPreflight()
        .then((status) => {
          if (alive) setHealth((h) => ({ ...h, control: status?.control?.healthy ? 'ok' : 'down' }))
        })
        .catch(() => {
          if (alive) setHealth((h) => ({ ...h, control: 'down' }))
        })
    }

    poll()
    const id = setInterval(poll, POLL_MS)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  return health
}
