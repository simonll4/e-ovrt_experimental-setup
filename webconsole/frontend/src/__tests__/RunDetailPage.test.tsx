import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RunDetailPage from '../pages/RunDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getRun: vi.fn(),
  getDetections: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getEvaluation: vi.fn().mockResolvedValue(null),
  getTrace: vi.fn().mockResolvedValue({
    media_run_id: 'r_1',
    control_run_id: null,
    topology: null,
    control_error: null,
    totals: {
      frames: 0,
      detections: 0,
      dropped_by_reason: {},
      alerts: 0,
      received: null,
      not_received: null,
    },
    page: 1,
    page_size: 50,
    total: 0,
    frames: [],
  }),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPage = (id = 'r_1') =>
  render(
    <MemoryRouter initialEntries={[`/runs/${id}`]}>
      <Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>
    </MemoryRouter>,
  )

describe('RunDetailPage', () => {
  it('muestra el estado del run como badge', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('OK').className).toContain('eo-badge--ok'))
  })

  it('muestra tiles de métricas cuando hay summary', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1',
      status: 'succeeded',
      live: false,
      summary: { fps_effective: 24, total_detections: 100, duration_seconds: 5 },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('24')).toBeTruthy())
    expect(screen.getByText('100')).toBeTruthy()
  })
})
