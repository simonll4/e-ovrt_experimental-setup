import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ExperimentsPage from '../../pages/ExperimentsPage'
import ExperimentDetailPage from '../../pages/ExperimentDetailPage'
import ComparePage from '../../pages/ComparePage'
import {
  corrida, experimento, instalarHttp, json, manifiestos, montar, preflight,
} from './soporte'

async function abrirExperimentos(ruta = '/experiments') {
  await montar(<Routes>
    <Route path="/experiments" element={<ExperimentsPage />} />
    <Route path="/experiments/new" element={<ExperimentsPage />} />
    <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
  </Routes>, ruta)
}

describe('Contrato: experimentos y distribución', () => {
  it('lista y abre un experimento con outcomes vinculados a cada alerta', async () => {
    const path = `/api/experiments/${experimento.experiment_id}`
    const http = instalarHttp((p) => {
      if (p.url.pathname === `${path}/alerts`) return json([
        { alert_id: 'alerta_entregada', condition_id: 'CR-01', severity: 'high', timestamp_ms: 100 },
        { alert_id: 'alerta_fallida', condition_id: 'CR-02', severity: 'medium', timestamp_ms: 200 },
      ])
      if (p.url.pathname === `${path}/report`) return json({
        non_temporal: false,
        resultados: [{ name: 't_alert-notification', value: 1.8, unit: 'ms', status: 'computed', cause: null }],
        distribucion: { counts: { delivered: 1, failed: 1 }, skipped_invalid_alerts: 4 },
        distribucion_por_alerta: {
          alerta_entregada: { alert_id: 'alerta_entregada', outcome: 'delivered' },
          alerta_fallida: { alert_id: 'alerta_fallida', outcome: 'failed' },
        },
      })
    })
    await abrirExperimentos()
    fireEvent.click(await screen.findByRole('link', { name: experimento.experiment_id }))
    expect(await screen.findByRole('row', { name: /alerta_entregada.*entregada/ })).toBeTruthy()
    expect(screen.getByRole('row', { name: /alerta_fallida.*falló, reintentando/ })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Distribución de alertas/i })).toBeTruthy()
    expect(screen.getAllByText(/1,800 ms/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Alertas descartadas por datos inválidos: 4/)).toBeTruthy()
    for (const endpoint of ['/api/experiments/manifests', path, `${path}/alerts`, `${path}/report`]) {
      expect(http.a('GET', endpoint).length).toBeGreaterThan(0)
    }
  })

  it('deriva un manifiesto con overrides y lanza la derivación seleccionada', async () => {
    let derivado = false
    const http = instalarHttp((p) => {
      if (p.url.pathname.endsWith('/derive-defaults')) return json({ warmup_frames: 20 })
      if (p.method === 'POST' && p.url.pathname.endsWith('/derive')) {
        derivado = true
        return json({ slug: 'contrato_derivado' }, 201)
      }
      if (p.url.pathname === '/api/experiments/manifests') return json([
        ...manifiestos, ...(derivado ? [{ slug: 'contrato_derivado', group: 'contrato' }] : []),
      ])
      if (p.method === 'POST' && p.url.pathname === '/api/experiments/run') {
        return json({ experiment_id: experimento.experiment_id }, 201)
      }
    })
    await abrirExperimentos()
    const abrirDerivacion = await screen.findByRole('button', { name: /^(Partir de este|Derivar)$/i })
    fireEvent.click(abrirDerivacion)
    const warmup = await screen.findByRole('textbox', { name: 'warmup_frames' })
    await waitFor(() => expect(warmup).toHaveProperty('value', '20'))
    fireEvent.change(screen.getByRole('textbox', { name: /nombre nuevo/i }), {
      target: { value: 'contrato_derivado' },
    })
    fireEvent.change(warmup, { target: { value: '30' } })
    // Confirmar la derivación, no volver a abrir el formulario de la fila.
    const confirmar = screen.getAllByRole('button', { name: /^Derivar$/i })
      .find((b) => b !== abrirDerivacion)
    expect(confirmar).toBeDefined()
    fireEvent.click(confirmar!)
    const derivePath = '/api/experiments/manifests/contrato_base/derive'
    await waitFor(() => expect(http.a('POST', derivePath)).toHaveLength(1))
    expect(http.a('POST', derivePath)[0].body).toMatchObject({
      new_slug: 'contrato_derivado', overrides: { warmup_frames: 30 },
    })
    await waitFor(() => expect(screen.queryByRole('textbox', { name: /nombre nuevo/i })).toBeNull())
    const ejecutarFila = within(screen.getByRole('row', { name: /contrato_derivado/ }))
      .queryByRole('button', { name: /^Ejecutar$/i })
    // La UI anterior lanza desde un selector global; la nueva, desde la fila.
    if (!ejecutarFila) {
      fireEvent.click(screen.getByRole('button', { name: /^contrato_(base|derivado)$/ }))
      fireEvent.click(await screen.findByRole('option', { name: 'contrato_derivado' }))
    }
    const lanzar = ejecutarFila
      ?? screen.getByRole('button', { name: /^Lanzar experimento$/i })
    await waitFor(() => expect(lanzar).toHaveProperty('disabled', false))
    fireEvent.click(lanzar)
    await waitFor(() => expect(http.a('POST', '/api/experiments/run')).toHaveLength(1))
    expect(http.a('POST', '/api/experiments/run')[0].body).toMatchObject({ slug: 'contrato_derivado' })
    await screen.findByRole('link', { name: /Ver la corrida/i })
    expect(http.a('GET', `/api/experiments/${experimento.experiment_id}`).length).toBeGreaterThan(0)
  })

  it('bloquea lanzar experimentos y expone el motivo del preflight', async () => {
    const http = instalarHttp((p) => p.url.pathname === '/api/preflight'
      ? json({ ...preflight, ready: false, blockers: ['Motivo sintético del bloqueo'] }) : undefined)
    await abrirExperimentos()
    const lanzar = await screen.findByRole('button', { name: /^(Ejecutar|Lanzar experimento)$/i })
    await screen.findByText(/Motivo sintético del bloqueo/)
    expect(lanzar).toHaveProperty('disabled', true)
    fireEvent.click(lanzar)
    expect(http.a('POST', '/api/experiments/run')).toHaveLength(0)
  })

  it('seleccionar dos corridas evaluadas pide su comparación por HTTP', async () => {
    const http = instalarHttp((p) => {
      if (p.url.pathname === '/api/runs') return json([
        { ...corrida, run_id: 'contrato_a', evaluated: true },
        { ...corrida, run_id: 'contrato_b', evaluated: true },
      ])
      if (p.url.pathname === '/api/compare') return json({
        runs: ['contrato_a', 'contrato_b'].map((run_id) => ({
          run_id, label: run_id, cr01_detection_recall: 0.64, mAP50: 0.47,
        })),
        classes: ['person'], ap_by_class: { person: [0.72, 0.75] }, skipped: [],
      })
    })
    await montar(<ComparePage />, '/compare')
    fireEvent.click(await screen.findByRole('checkbox', { name: 'contrato_a' }))
    expect(http.a('GET', '/api/compare')).toHaveLength(0)
    fireEvent.click(screen.getByRole('checkbox', { name: 'contrato_b' }))
    await waitFor(() => expect(http.a('GET', '/api/compare')).toHaveLength(1))
    expect(http.a('GET', '/api/compare')[0].url.searchParams.get('runs')?.split(',').sort())
      .toEqual(['contrato_a', 'contrato_b'])
    expect(await screen.findByRole('row', { name: /person.*0,720.*0,750/ })).toBeTruthy()
  })
})
