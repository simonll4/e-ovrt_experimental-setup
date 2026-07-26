import { controlTone } from '../traceview'
import type { TraceFrame } from '../types'

function frameKey(f: TraceFrame): string {
  return String(f.unit_id ?? f.frame_index)
}

function frameLabel(f: TraceFrame): string {
  return [f.frame_index !== null ? `#${f.frame_index}` : null, f.unit_id]
    .filter((x) => x !== null && x !== '')
    .join(' · ')
}

function frameShortLabel(f: TraceFrame): string {
  if (f.frame_index !== null) return `#${f.frame_index}`
  return f.unit_id ?? ''
}

const TONE_VAR: Record<string, string> = {
  live: 'var(--status-live)',
  ok: 'var(--status-ok)',
  warn: 'var(--status-warn)',
  alert: 'var(--status-alert)',
  error: 'var(--status-error)',
  neutral: 'var(--status-neutral)',
}

// Tope de ticks dibujados. Una corrida de 5000 cuadros con un tick por cuadro no solo
// infla el DOM: la franja deja de ser legible (los ticks quedan sub-pixel). Por encima
// de este tope cada tick representa un tramo de cuadros consecutivos.
export const MAX_TICKS = 400

// Prioridad de severidad dentro de un tramo: una alerta confirmada nunca puede
// desaparecer por agrupamiento.
function severityRank(f: TraceFrame): number {
  if (f.alert.length > 0) return 3
  if (f.control === 'not_received') return 2
  if (f.control.startsWith('dropped:')) return 1
  return 0
}

export default function TraceTimeline({
  frames,
  onTickClick,
}: {
  frames: TraceFrame[]
  onTickClick?: (startIndex: number, frameKey: string) => void
}) {
  if (frames.length === 0) return null

  const groupSize = Math.max(1, Math.ceil(frames.length / MAX_TICKS))
  const groups: { start: number; slice: TraceFrame[] }[] = []
  for (let i = 0; i < frames.length; i += groupSize) {
    groups.push({ start: i, slice: frames.slice(i, i + groupSize) })
  }

  return (
    <div className="eo-timeline" role="group" aria-label="línea de tiempo de la corrida">
      {groups.map(({ start, slice }) => {
        const first = slice[0]
        const key = frameKey(first)
        // El tick toma el estado más severo del tramo (alerta > descarte/no recibido > normal).
        const worst = slice.reduce((a, b) => (severityRank(b) > severityRank(a) ? b : a), first)
        const hasAlert = worst.alert.length > 0
        const tone = hasAlert ? 'alert' : controlTone(worst.control)
        const label =
          slice.length === 1
            ? frameLabel(first)
            : `cuadros ${frameShortLabel(first)}–${frameShortLabel(slice[slice.length - 1])}`
        return (
          <button
            key={key}
            type="button"
            className={`eo-timeline__tick${hasAlert ? ' eo-timeline__tick--alert' : ''}`}
            style={{ background: TONE_VAR[tone] }}
            title={label}
            aria-label={label}
            onClick={() => {
              if (onTickClick) {
                // El contenedor decide: puede tener que ampliar el tope de filas
                // antes de que la fila destino exista en el DOM.
                onTickClick(start, key)
                return
              }
              document
                .getElementById(`frame-${key}`)
                ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
            }}
          />
        )
      })}
    </div>
  )
}
