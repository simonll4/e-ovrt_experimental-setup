import type { PlaneStatus, PreflightStatus } from '../types'
import { Badge } from './ui'

function planeTone(p: PlaneStatus): 'ok' | 'warn' | 'error' {
  if (!p.healthy) return 'error'
  return p.ready ? 'ok' : 'warn'
}

function planeLabel(p: PlaneStatus): string {
  if (!p.healthy) return 'caído'
  return p.ready ? 'operativo' : 'no operativo'
}

/**
 * Estado compacto de los dos planos para la vista de lanzamiento: dos chips y
 * nada más. El detalle (por qué no se puede lanzar) va en `blockers`, que el
 * caller muestra como una sola línea.
 */
export default function PlatformStatus({ status }: { status: PreflightStatus | null }) {
  if (!status) {
    return <Badge tone="neutral">verificando servicios…</Badge>
  }
  return (
    <span style={{ display: 'inline-flex', gap: 'var(--space-2)', alignItems: 'center' }}>
      <Badge tone={planeTone(status.media)}>
        motor de detección {planeLabel(status.media)}
      </Badge>
      <Badge tone={planeTone(status.control)}>
        motor de reglas {planeLabel(status.control)}
      </Badge>
    </span>
  )
}
