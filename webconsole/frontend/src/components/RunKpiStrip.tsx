import type { ReactNode } from 'react'
import Meter from './charts/Meter'
import Sparkline from './charts/Sparkline'
import { toneVar, type ChartTone } from '../palette'
import { recentDelta, type RunSeries } from '../runseries'
import type { RunComparison, RunSummary } from '../types'

const dec = (v: number, digits = 1) => v.toFixed(digits).replace('.', ',')

/** Color del delta según si el movimiento fue para el lado bueno.
 *
 *  `better` viene del backend por métrica: subir es bueno en cuadros por
 *  segundo y malo en latencia. Cuando es null (más detecciones no es mejor ni
 *  peor: depende de la escena) el delta va en gris, sin juicio de valor. */
function tonoDelta(delta: number, better: 'mas' | 'menos' | null | undefined): string {
  if (!better || delta === 0) return 'var(--tx3)'
  const mejoro = better === 'mas' ? delta > 0 : delta < 0
  return mejoro ? 'var(--ok)' : 'var(--wn)'
}

export interface KpiDelta {
  value: number
  better?: 'mas' | 'menos' | null
  /** Decimales; la latencia se compara en enteros y los cuadros/s en dos. */
  digits?: number
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
  delta?: KpiDelta | null
}) {
  return (
    <div className="eo-kpi">
      <span className="eo-kpi__label">
        <i className="eo-kpi__dot" style={{ background: toneVar(tone) }} />
        {label}
      </span>
      <span className="eo-kpi__value">
        {value}
        {unit && <small>{unit}</small>}
        {delta != null && (
          <span
            className="eo-kpi__delta"
            style={{ color: tonoDelta(delta.value, delta.better) }}
          >
            {delta.value >= 0 ? '▲' : '▼'} {dec(Math.abs(delta.value), delta.digits ?? 2)}
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
 * La variación tiene dos orígenes según el estado de la corrida, y nunca los dos
 * a la vez: en curso se compara contra sus últimos 30 s —es lo único que existe
 * todavía—, y terminada contra la corrida anterior comparable, que resuelve el
 * backend exigiendo mismo modelo, mismo conjunto de prompts y mismo tipo de
 * fuente. Sin corrida comparable no se muestra variación: un "+0,0" inventado
 * sería un número de más frente a un jurado.
 *
 * La latencia no tiene sparkline porque la API no expone latencia por cuadro;
 * dibujar ahí otra serie sería mostrar una curva que no es la suya.
 */
export default function RunKpiStrip({
  summary,
  series,
  live,
  alerts = null,
  gpuTotalMb = 8192,
  comparison = null,
}: {
  summary: RunSummary | undefined
  series: RunSeries
  live: boolean
  alerts?: number | null
  gpuTotalMb?: number
  /** Variación contra la corrida anterior comparable (misma cámara, mismo
   *  conjunto de prompts, mismo modelo). null cuando no hay con qué comparar:
   *  los indicadores se muestran sin variación, que no es variación cero. */
  comparison?: RunComparison | null
}) {
  const fps = summary?.fps_effective ?? null
  const p50 = summary?.p50_latency_ms ?? null
  const p95 = summary?.p95_latency_ms ?? null
  const gpu = summary?.gpu_memory_peak_mb ?? null
  const duracion = summary?.duration_seconds ?? null
  const dets = summary?.total_detections ?? null
  const processed = summary?.units_processed ?? null
  const dropped = summary?.units_dropped ?? null
  const totalUnits = (processed ?? 0) + (dropped ?? 0)
  const dropPct = dropped != null && totalUnits > 0 ? (dropped / totalUnits) * 100 : null

  // Dos orígenes distintos para la variación, y nunca los dos a la vez:
  // mientras la corrida está viva se compara contra sus últimos 30 s (es lo
  // único que existe); una vez terminada, contra la corrida anterior comparable.
  const enVivo = (serie: Array<number | null>, digits: number): KpiDelta | null => {
    if (!live) return null
    const d = recentDelta(serie, series.elapsedSeconds)
    return d == null ? null : { value: d, digits }
  }
  const contraAnterior = (metrica: string, digits: number): KpiDelta | null => {
    if (live) return null
    const d = comparison?.deltas?.[metrica]
    return d == null ? null : { value: d.delta, better: d.better, digits }
  }
  const variacion = (serie: Array<number | null>, metrica: string, digits: number) =>
    enVivo(serie, digits) ?? contraAnterior(metrica, digits)

  const hayComparacion = !live && Boolean(comparison?.previous_run_id)

  return (
    <section className="eo-kpis-wrap">
      {live && <p className="eo-kpis__note">Variación comparada con los últimos 30 s</p>}
      {hayComparacion && (
        <p className="eo-kpis__note">Variación comparada con la corrida anterior</p>
      )}
      <div className="eo-kpis">
        <Kpi
          label="Cuadros por segundo"
          tone="live"
          value={fps != null ? dec(fps, 2) : '—'}
          spark={series.instantFps}
          delta={variacion(series.instantFps, 'fps_effective', 2)}
        />
        <Kpi
          label="Latencia (mediana)"
          tone="live"
          value={p50 != null ? dec(p50, 0) : '—'}
          unit=" ms"
          delta={contraAnterior('p50_latency_ms', 0)}
        />
        {/* El percentil 95 es indicador propio con la corrida terminada, no un
            subtexto del de la mediana: es la cola —lo que se sintió mal— y se
            compara con el de otra corrida. En vivo todavía no es estable, así
            que ahí sigue acompañando a la mediana. */}
        {!live ? (
          <Kpi
            label="Latencia (percentil 95)"
            tone="live"
            value={p95 != null ? dec(p95, 0) : '—'}
            unit=" ms"
            delta={contraAnterior('p95_latency_ms', 0)}
          />
        ) : null}
        {!live ? (
          <Kpi
            label="Duración"
            tone="accent"
            value={duracion != null ? dec(duracion) : '—'}
            unit=" s"
            delta={contraAnterior('duration_seconds', 1)}
          />
        ) : null}
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
          delta={variacion(series.detectionsPerFrame, 'total_detections', 0)}
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
