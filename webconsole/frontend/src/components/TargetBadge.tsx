import { useEffect, useState } from 'react'
import { getTarget } from '../api'
import type { TargetStatus } from '../types'
import { Badge } from './ui'

export default function TargetBadge() {
  const [target, setTarget] = useState<TargetStatus | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      getTarget().then((t) => alive && setTarget(t)).catch(() => alive && setTarget(null))
    tick()
    const timer = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  if (!target) return <Badge tone="error">BFF inaccesible</Badge>
  if (!target.healthy) return <Badge tone="error">servicio caído</Badge>
  if (!target.ready) return <Badge tone="warn">cargando modelo…</Badge>
  return (
    <Badge tone="ok">
      {target.model?.ref} <small>({target.model?.device ?? '?'})</small>
    </Badge>
  )
}
