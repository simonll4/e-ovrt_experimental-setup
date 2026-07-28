import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import RunKpiStrip from '../components/RunKpiStrip'
import type { RunSeries } from '../runseries'

afterEach(() => cleanup())

const series: RunSeries = {
  detectionsPerFrame: [1, 2, 3],
  instantFps: [null, 2, 4],
  elapsedSeconds: [0, 0.5, 1],
  totalSeconds: 1,
}

/** Serie larga para que `recentDelta` tenga dos ventanas de 30 s completas. */
const longSeries = (): RunSeries => {
  const elapsedSeconds = Array.from({ length: 61 }, (_, i) => i)
  return {
    elapsedSeconds,
    detectionsPerFrame: elapsedSeconds.map((s) => (s < 30 ? 1 : 3)),
    instantFps: elapsedSeconds.map((s) => (s < 30 ? 1 : 3)),
    totalSeconds: 60,
  }
}

describe('RunKpiStrip', () => {
  it('rotula con el glosario, nunca con la clave cruda del sumario', () => {
    render(
      <RunKpiStrip summary={{ fps_effective: 3.49, p50_latency_ms: 224 }} series={series} live={false} />,
    )
    expect(screen.getByText('Cuadros por segundo')).toBeTruthy()
    expect(screen.getByText('Latencia (mediana)')).toBeTruthy()
    expect(screen.getByText('Memoria de GPU')).toBeTruthy()
    expect(screen.getByText('Descartes de entrega')).toBeTruthy()
    expect(screen.getByText('Alertas confirmadas')).toBeTruthy()
    expect(screen.queryByText('fps_effective')).toBeNull()
    expect(screen.queryByText(/queue_full/i)).toBeNull()
  })

  it('en corrida terminada no muestra variación: el delta no se inventa', () => {
    render(<RunKpiStrip summary={{ fps_effective: 3.49 }} series={longSeries()} live={false} />)
    expect(screen.queryByText(/Variación comparada/)).toBeNull()
  })

  it('en corrida en curso anuncia la ventana de comparación', () => {
    render(<RunKpiStrip summary={{ fps_effective: 3.49 }} series={longSeries()} live />)
    expect(screen.getByText(/Variación comparada con los últimos 30 s/)).toBeTruthy()
  })

  it('un valor ausente se muestra como sin dato, no como cero', () => {
    render(<RunKpiStrip summary={{}} series={series} live={false} />)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

  it('la latencia no lleva sparkline: la API no expone latencia por cuadro', () => {
    const { container } = render(
      <RunKpiStrip summary={{ p50_latency_ms: 224, p95_latency_ms: 292 }} series={series} live={false} />,
    )
    const tiles = container.querySelectorAll('.eo-kpi')
    const latency = Array.from(tiles).find((t) => t.textContent?.includes('Latencia (mediana)'))
    expect(latency?.querySelector('.eo-spark')).toBeNull()
    expect(screen.getByText(/percentil 95/)).toBeTruthy()
  })

  it('el porcentaje de descartes se calcula sobre el total entregado más descartado', () => {
    render(
      <RunKpiStrip
        summary={{ units_processed: 90, units_dropped: 10 }}
        series={series}
        live={false}
      />,
    )
    expect(screen.getByText('10,0')).toBeTruthy()
    expect(screen.getByText(/10 cuadros descartados/)).toBeTruthy()
  })

  it('muestra las alertas confirmadas que le pasan por separado del sumario', () => {
    render(<RunKpiStrip summary={{}} series={series} live={false} alerts={3} />)
    expect(screen.getByText('3')).toBeTruthy()
  })
})
