import type { ReactNode } from 'react'
import Meter from './charts/Meter'
import Sparkline, { type ChartTone } from './charts/Sparkline'
import { recentDelta, type RunSeries } from '../runseries'

const TONE_VAR: Record<ChartTone, string> = {
  live: '--live',
  ok: '--ok',
  warn: '--wn',
  alert: '--sr',
  error: '--er',
  accent: '--ac',
}

const dec = (v: number, digits = 1) => v.toFixed(digits).replace('.', ',')

const num = (s: Record<string, unknown> | undefined, k: string): number | null => {
  const v = s?.[k]
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function Kpi({
  label,
  tone,
  value,
  unit,
  spark,
  foot,
  delta,
}: {
  label: string
  tone: ChartTone
  value: string
  unit?: string
  spark?: Array<number | null>
  foot?: ReactNode
  delta?: number | null
}) {
  return (
    <div className="eo-kpi">
      <span className="eo-kpi__label">
        <i className="eo-kpi__dot" style={{ background: `var(${TONE_VAR[tone]})` }} />
        {label}
      </span>
      <span className="eo-kpi__value">
        {value}
        {unit && <small>{unit}</small>}
        {delta != null && (
          <span className="eo-kpi__delta">
            {delta >= 0 ? '▲' : '▼'} {dec(Math.abs(delta), 2)}
          </span>
        )}
      </span>
      <span className="eo-kpi__foot">
        {spark && <Sparkline values={spark} tone={tone} />}
        {foot}
      </span>
    </div>
  )
}

/**
 * Tira de indicadores de una corrida.
 *
 * Los deltas solo aparecen en corridas en curso: en una terminada no hay dos
 * ventanas para comparar y un "+0,0" inventado sería un número de más frente a
 * un jurado. Lo mismo con la latencia — la API no expone latencia por cuadro, así
 * que ese tile va sin sparkline en vez de dibujar una serie que no es la suya.
 */
export default function RunKpiStrip({
  summary,
  series,
  live,
  alerts = null,
  gpuTotalMb = 8192,
}: {
  summary: Record<string, unknown> | undefined
  series: RunSeries
  live: boolean
  alerts?: number | null
  gpuTotalMb?: number
}) {
  const fps = num(summary, 'fps_effective')
  const p50 = num(summary, 'p50_latency_ms')
  const p95 = num(summary, 'p95_latency_ms')
  const gpu = num(summary, 'gpu_memory_peak_mb')
  const dets = num(summary, 'total_detections')
  const processed = num(summary, 'units_processed')
  const dropped = num(summary, 'units_dropped')
  const totalUnits = (processed ?? 0) + (dropped ?? 0)
  const dropPct = dropped != null && totalUnits > 0 ? (dropped / totalUnits) * 100 : null

  const fpsDelta = live ? recentDelta(series.instantFps, series.elapsedSeconds) : null
  const detDelta = live ? recentDelta(series.detectionsPerFrame, series.elapsedSeconds) : null

  return (
    <section className="eo-kpis-wrap">
      {live && <p className="eo-kpis__note">Variación comparada con los últimos 30 s</p>}
      <div className="eo-kpis">
        <Kpi
          label="Cuadros por segundo"
          tone="live"
          value={fps != null ? dec(fps, 2) : '—'}
          spark={series.instantFps}
          delta={fpsDelta}
        />
        <Kpi
          label="Latencia (mediana)"
          tone="live"
          value={p50 != null ? dec(p50, 0) : '—'}
          unit=" ms"
          foot={
            p95 != null ? (
              <span className="eo-kpi__sub">percentil 95: {dec(p95, 0)} ms</span>
            ) : undefined
          }
        />
        <Kpi
          label="Memoria de GPU"
          tone="accent"
          value={gpu != null ? dec(gpu, 0) : '—'}
          unit=" MB"
          foot={
            gpu != null ? (
              <>
                <Meter
                  total={gpuTotalMb}
                  segments={[{ value: gpu, tone: 'accent', label: 'en uso' }]}
                />
                <span className="eo-kpi__sub">
                  {Math.round((gpu / gpuTotalMb) * 100)} % de {gpuTotalMb} MB
                </span>
              </>
            ) : undefined
          }
        />
        <Kpi
          label="Detecciones"
          tone="accent"
          value={dets != null ? String(dets) : '—'}
          spark={series.detectionsPerFrame}
          delta={detDelta}
        />
        <Kpi
          label="Descartes de entrega"
          tone="warn"
          value={dropPct != null ? dec(dropPct) : '—'}
          unit=" %"
          foot={
            dropped != null ? (
              <span className="eo-kpi__sub">{dropped} cuadros descartados</span>
            ) : undefined
          }
        />
        <Kpi
          label="Alertas confirmadas"
          tone="alert"
          value={alerts != null ? String(alerts) : '—'}
          foot={
            alerts === 0 ? (
              <span className="eo-kpi__sub">ninguna condición se confirmó</span>
            ) : undefined
          }
        />
      </div>
    </section>
  )
}
