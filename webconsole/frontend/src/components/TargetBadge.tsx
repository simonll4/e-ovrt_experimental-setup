import { useEffect, useState } from 'react'
import { getTarget } from '../api'
import type { TargetStatus } from '../types'

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
  if (!target) return <span style={{ color: '#b00' }}>● BFF inaccesible</span>
  if (!target.healthy) return <span style={{ color: '#b00' }}>● servicio caído</span>
  if (!target.ready) return <span style={{ color: '#c80' }}>● cargando modelo…</span>
  return (
    <span style={{ color: '#080' }}>
      ● {target.model?.ref} <small>({target.model?.device ?? '?'})</small>
    </span>
  )
}
