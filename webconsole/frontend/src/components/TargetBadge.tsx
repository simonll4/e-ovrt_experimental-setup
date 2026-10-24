import { useTargetQuery } from '../api/queries/platform'
import { Badge } from './ui'

/** La instancia activa, junto a las migas.
 *
 *  Arranca diciendo que está verificando: antes un `null` inicial —la consulta
 *  que todavía no respondió— se leía como «BFF inaccesible» y la consola abría
 *  con una alarma falsa. Distingue tres fallas que piden cosas distintas: la
 *  consola no contesta (no hay conexión con su propio servidor), el motor
 *  contesta que no está sano, o está sano y todavía carga el modelo.
 *
 *  Comparte caché con el resto de la aplicación: una sola petición a
 *  `/api/target` para la insignia, la barra lateral y las pantallas. */
export default function TargetBadge() {
  const q = useTargetQuery()
  const target = q.data
  if (!target) {
    if (q.isError) {
      return <Badge tone="error" title={String(q.error)}>Sin conexión con la consola</Badge>
    }
    return <Badge tone="neutral">Verificando instancia</Badge>
  }
  if (!target.healthy) return <Badge tone="error">Motor de detección sin respuesta</Badge>
  if (!target.ready) return <Badge tone="warn">Cargando el modelo…</Badge>
  return (
    <Badge tone="ok">
      {target.model?.ref ?? 'modelo'} <small>({target.model?.device ?? 'dispositivo sin informar'})</small>
    </Badge>
  )
}
