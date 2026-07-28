import { useMemo, useState } from 'react'
import FrameInspector from './FrameInspector'
import { Badge, Button, Card, EmptyState } from './ui'
import { controlTone, frameHasActivity } from '../traceview'
import type { BadgeTone, TraceFrame, TraceTotals } from '../types'

/** Cuántos cuadros se renderizan a la vez. Una traza de 1468 cuadros no puede
 *  volcarse entera: ese scroll infinito es justo lo que este panel reemplaza. */
const WINDOW = 200

const DOT_VAR: Record<BadgeTone, string> = {
  ok: '--ok',
  warn: '--wn',
  error: '--er',
  live: '--live',
  alert: '--sr',
  neutral: '--nt',
}

/**
 * Panel de traza en maestro-detalle: la lista de cuadros a la izquierda, el
 * cuadro elegido completo a la derecha.
 *
 * Recibe los cuadros por props en vez de pedirlos: la línea de tiempo y esta
 * lista comparten el mismo índice, que trae `useFullTrace` una sola vez en la
 * página. Pedirlo dos veces sería traer miles de cuadros dos veces.
 */
export default function TraceSection({
  runId,
  frames,
  totals,
  selected,
  onSelect,
}: {
  runId: string
  frames: TraceFrame[]
  totals: TraceTotals | null
  /** Posición seleccionada dentro de los cuadros visibles. Controlada desde la
   *  página para que la línea de tiempo y la lista se muevan juntas. */
  selected?: number | null
  onSelect?: (position: number) => void
}) {
  const [onlyActivity, setOnlyActivity] = useState(false)
  const [onlyAlerts, setOnlyAlerts] = useState(false)
  const [innerPos, setInnerPos] = useState(0)
  const [anchor, setAnchor] = useState(0)

  const visible = useMemo(
    () =>
      frames.filter(
        (f) => (!onlyActivity || frameHasActivity(f)) && (!onlyAlerts || (f.alert?.length ?? 0) > 0),
      ),
    [frames, onlyActivity, onlyAlerts],
  )

  const clamp = (p: number) => Math.min(Math.max(0, p), Math.max(0, visible.length - 1))
  const pos = clamp(selected ?? innerPos)

  const setPos = (p: number) => {
    const c = clamp(p)
    setInnerPos(c)
    onSelect?.(c)
  }

  const from = Math.max(0, Math.min(anchor, Math.max(0, visible.length - WINDOW)))
  const slice = visible.slice(from, from + WINDOW)

  const applyFilter = (fn: () => void) => {
    fn()
    setAnchor(0)
    setPos(0)
  }

  if (!frames.length) {
    return (
      <EmptyState hint="Sin traza no se puede inspeccionar cuadro a cuadro.">
        Esta corrida no tiene traza
      </EmptyState>
    )
  }

  return (
    <div className="eo-trace">
      <Card className="eo-trace__master" flush>
        <div className="eo-trace__filters">
          <label>
            <input
              type="checkbox"
              checked={onlyActivity}
              onChange={(e) => applyFilter(() => setOnlyActivity(e.target.checked))}
            />{' '}
            Solo con actividad
          </label>
          <label>
            <input
              type="checkbox"
              checked={onlyAlerts}
              onChange={(e) => applyFilter(() => setOnlyAlerts(e.target.checked))}
            />{' '}
            Solo alertas
          </label>
          <span className="eo-mono">
            {visible.length} de {totals?.frames ?? frames.length}
          </span>
        </div>

        {from > 0 && (
          <div className="eo-trace__more">
            <Button onClick={() => setAnchor(Math.max(0, from - WINDOW))}>Cuadros anteriores</Button>
          </div>
        )}

        <ul className="eo-trace__list" role="listbox" aria-label="Cuadros de la traza">
          {slice.map((f, i) => {
            const idx = from + i
            return (
              <li
                key={f.unit_id ?? idx}
                role="option"
                aria-selected={idx === pos}
                className={idx === pos ? 'is-selected' : undefined}
                onClick={() => setPos(idx)}
              >
                <span className="eo-trace__idx eo-mono">{f.frame_index ?? idx}</span>
                <span className="eo-trace__unit eo-mono">{f.unit_id}</span>
                <span className="eo-trace__dets">{f.detections?.length || '—'}</span>
                {(f.alert?.length ?? 0) > 0 ? (
                  <Badge tone="alert">Alerta</Badge>
                ) : (
                  <i
                    className="eo-trace__dot"
                    title={f.control}
                    style={{ background: `var(${DOT_VAR[controlTone(f.control)]})` }}
                  />
                )}
              </li>
            )
          })}
        </ul>

        {from + WINDOW < visible.length && (
          <div className="eo-trace__more">
            <Button onClick={() => setAnchor(from + WINDOW)}>Cuadros siguientes</Button>
          </div>
        )}

        {visible.length === 0 && (
          <EmptyState hint="Sacá alguno de los dos filtros.">Ningún cuadro pasa el filtro</EmptyState>
        )}
      </Card>

      <div className="eo-trace__detail">
        <FrameInspector
          frame={visible[pos] ?? null}
          runId={runId}
          position={pos}
          total={visible.length}
          onStep={(d) => setPos(pos + d)}
        />
      </div>
    </div>
  )
}
