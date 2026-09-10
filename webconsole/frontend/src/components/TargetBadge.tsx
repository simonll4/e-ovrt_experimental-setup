import { useTarget } from '../api/queries/platform'
import { Badge } from './ui'

export default function TargetBadge() {
  // Comparte caché con el resto de la aplicación: antes este componente tenía su
  // propio intervalo sobre /api/target, en paralelo al de `useTarget` y al del
  // pie de la barra lateral — tres pedidos del mismo endpoint.
  const target = useTarget()
  if (!target) return <Badge tone="error">BFF inaccesible</Badge>
  if (!target.healthy) return <Badge tone="error">servicio caído</Badge>
  if (!target.ready) return <Badge tone="warn">cargando modelo…</Badge>
  return (
    <Badge tone="ok">
      {target.model?.ref} <small>({target.model?.device ?? '?'})</small>
    </Badge>
  )
}
