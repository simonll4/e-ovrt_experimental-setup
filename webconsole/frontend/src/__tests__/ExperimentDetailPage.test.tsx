import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ExperimentDetailPage from '../pages/ExperimentDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperiment: vi.fn(),
  getExperimentAlerts: vi.fn(),
  getExperimentReport: vi.fn(),
}))

function renderPage(id = 'exp_1') {
  return render(
    <MemoryRouter initialEntries={[`/experiments/${id}`]}>
      <Routes>
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('ExperimentDetailPage', () => {
  it('muestra las alertas y avisa que el conjunto no es temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([{ alert_id: 'al1', condition_id: 'CR-01', severity: 'high' } as any])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: true, resultados: [] } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('al1')).toBeTruthy())
    // ADR-013: el aviso explica la consecuencia, no solo pone una etiqueta.
    expect(screen.getByText(/no es temporal/i)).toBeTruthy()
    expect(screen.getByText(/sin dato en vez de en cero/i)).toBeTruthy()
  })

  it('nombra la condición de la alerta además del código', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1b', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([
      { alert_id: 'al1', condition_id: 'CR-01', severity: 'high', timestamp_ms: 41200 } as any,
    ])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_1b')
    await waitFor(() => expect(screen.getByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy())
    expect(screen.getByText('Alta')).toBeTruthy()
    expect(screen.getByText('41,2 s')).toBeTruthy()
  })

  it('no avisa de no-temporal cuando el reporte es temporal', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_2', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_2')
    await waitFor(() => expect(screen.getByText('Sin alertas')).toBeTruthy())
    expect(screen.queryByText(/no es temporal/i)).toBeNull()
  })

  // Un 404 acá es "el reporte todavía no se consolidó", no una falla: no va en
  // rojo ni filtra el código de estado a la pantalla.
  it('reporte no consolidado (404) se explica como pendiente, no como error', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_3', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockRejectedValue(new api.ApiError(404, { detail: 'no encontrado' }))
    renderPage('exp_3')
    await waitFor(() => expect(screen.getByText('No hay reporte')).toBeTruthy())
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByText(/error 404/i)).toBeNull()
  })

  it('un error real del reporte sí se muestra como error, con su código', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_3b', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockRejectedValue(new api.ApiError(500, { detail: 'boom' }))
    renderPage('exp_3b')
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('el servicio falló (500)'))
  })

  it('alertas no consolidadas (404) tampoco se muestran como error', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_3c', status: 'running' } as any)
    vi.mocked(api.getExperimentAlerts).mockRejectedValue(new api.ApiError(404, { detail: 'no hay' }))
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_3c')
    await waitFor(() => expect(screen.getByText('No hay alertas registradas')).toBeTruthy())
    expect(screen.queryByText(/error 404/i)).toBeNull()
  })

  it('muestra el nombre crudo de la métrica y traduce estado y causa', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_4', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [{ name: 't_capture->alert', status: 'not_applicable', cause: 'no_ground_truth' }],
    } as any)
    renderPage('exp_4')
    // El nombre de la métrica es un identificador: nunca se traduce.
    await waitFor(() => expect(screen.getByText(/t_capture->alert/)).toBeTruthy())
    expect(screen.getByText(/no aplicable/)).toBeTruthy()
    // Aparece en la celda "Por qué" y en el tile de causa más frecuente.
    expect(screen.getAllByText(/sin ground truth/).length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText('not_applicable')).toBeNull()
    expect(screen.queryByText('no_ground_truth')).toBeNull()
  })

  it('muestra el valor medido con su unidad y marca las que sí se midieron', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_5', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [
        { name: 'ttfd', value: 1.842, unit: 's', status: 'computed', cause: null },
        { name: 'sdr', status: 'not_applicable', cause: 'non_temporal_source' },
      ],
    } as any)
    renderPage('exp_5')
    await waitFor(() => expect(screen.getByText('1,842 s')).toBeTruthy())
    expect(screen.getByText('Medida')).toBeTruthy()
    expect(screen.getByText('Sin dato')).toBeTruthy()
    // El tile parte el número y el "de N" en dos elementos; se lee el bloque entero.
    const tile = screen
      .getByText('Métricas medidas')
      .closest('.eo-kpi') as HTMLElement
    expect(tile.textContent).toContain('1')
    expect(tile.textContent).toContain('de 2')
  })

  // El backend no expone umbrales (MetricResult = name/value/unit/status/cause).
  // Decirlo evita que la tabla se lea como un veredicto de aprobado/reprobado.
  it('aclara que el reporte no trae umbrales de aceptación', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_6', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [{ name: 'ttfd', value: 1, unit: 's', status: 'computed' }],
    } as any)
    renderPage('exp_6')
    await waitFor(() => expect(screen.getByText(/No incluye umbrales de aceptación/)).toBeTruthy())
  })

  it('lee filas viejas del reporte que usan `metrica` en vez de `name`', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_7', status: 'succeeded', ok: true } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({
      non_temporal: false,
      resultados: [{ metrica: 'ttfa_interna', valor: 2.5, unidad: 's', status: 'computed' }],
    } as any)
    renderPage('exp_7')
    await waitFor(() => expect(screen.getByText('ttfa_interna')).toBeTruthy())
    expect(screen.getByText('2,500 s')).toBeTruthy()
  })

  it('enlaza a la corrida de video para poder trazar el resultado', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({
      experiment_id: 'exp_8', status: 'succeeded', ok: true,
      media_run_id: 'run_abc', control_run_id: 'ctl_abc', slug: 'perimetro_v3',
    } as any)
    vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
    vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
    renderPage('exp_8')
    await waitFor(() => expect(screen.getByRole('link', { name: 'Ver la corrida' })).toBeTruthy())
    expect(screen.getByText('ctl_abc')).toBeTruthy()
    expect(screen.getAllByText('perimetro_v3').length).toBeGreaterThan(0)
  })
})
