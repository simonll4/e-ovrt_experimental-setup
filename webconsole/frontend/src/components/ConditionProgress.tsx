import Meter from './charts/Meter'
import { conditionLabel } from '../labels'
import Termino from './Glosario'
import type { TraceFrame } from '../types'

/**
 * Avance de cada condición de riesgo en el cuadro seleccionado.
 *
 * `progress` viene normalizado en [0,1] desde el motor de reglas. Al 100 % la
 * condición se confirma, y por eso el medidor cambia de tono ahí: es el instante
 * que explica de dónde salió la alerta.
 */
export default function ConditionProgress({ frame }: { frame: TraceFrame | null }) {
  const rows = frame?.progress ?? []
  if (!rows.length) {
    return <p className="eo-cap">Ninguna condición en progreso en este cuadro.</p>
  }
  return (
    <ul className="eo-condprog">
      {rows.map((p) => {
        const pct = Math.round(Math.min(1, Math.max(0, p.progress ?? 0)) * 100)
        return (
          <li key={p.condition_id}>
            <span className="eo-condprog__name">
              <Termino id={p.condition_id}>{conditionLabel(p.condition_id)}</Termino>
            </span>
            <Meter
              total={100}
              segments={[{ value: pct, tone: pct >= 100 ? 'alert' : 'warn', label: 'avance' }]}
            />
            <span className="eo-condprog__pct eo-mono">{pct} %</span>
          </li>
        )
      })}
    </ul>
  )
}
