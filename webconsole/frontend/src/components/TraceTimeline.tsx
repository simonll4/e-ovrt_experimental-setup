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

const TONE_VAR: Record<string, string> = {
  live: 'var(--status-live)',
  ok: 'var(--status-ok)',
  warn: 'var(--status-warn)',
  alert: 'var(--status-alert)',
  error: 'var(--status-error)',
  neutral: 'var(--status-neutral)',
}

export default function TraceTimeline({ frames }: { frames: TraceFrame[] }) {
  if (frames.length === 0) return null

  return (
    <div className="eo-timeline" role="list" aria-label="línea de tiempo de la corrida">
      {frames.map((f) => {
        const key = frameKey(f)
        const hasAlert = f.alert.length > 0
        const tone = hasAlert ? 'alert' : controlTone(f.control)
        return (
          <button
            key={key}
            type="button"
            role="listitem"
            className={`eo-timeline__tick${hasAlert ? ' eo-timeline__tick--alert' : ''}`}
            style={{ background: TONE_VAR[tone] }}
            title={frameLabel(f)}
            onClick={() => document.getElementById(`frame-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
          />
        )
      })}
    </div>
  )
}
