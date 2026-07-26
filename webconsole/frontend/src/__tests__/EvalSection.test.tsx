import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EvalSection from '../components/EvalSection'
import { ApiError, evaluateRun, getEvaluation } from '../api'
import type { EvalResult } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  evaluateRun: vi.fn(),
  getEvaluation: vi.fn(),
}))

const EVAL: EvalResult = {
  type: 'perception',
  run_id: 'r1',
  benchmark: 'construction_site_safety_bench',
  iou_threshold: 0.5,
  evaluated_at: '2026-07-04T10:00:00+00:00',
  per_class: [
    { class_name: 'person', AP50: 0.72, n_gt: 82, n_det: 90 },
    { class_name: 'helmet', AP50: null, n_gt: 0, n_det: 3 },
  ],
  cr01_detection_recall: 0.64,
  mAP50: 0.47,
  model: 'mock',
  bench_split: 'bench_v2_test',
}

beforeEach(() => vi.clearAllMocks())

describe('EvalSection', () => {
  it('no renderiza nada si el run no es BENCH', () => {
    const { container } = render(<EvalSection runId="r1" benchSplit={null} evaluated={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('evalúa al click y muestra la tabla con mAP', async () => {
    vi.mocked(evaluateRun).mockResolvedValue(EVAL)
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={false} />)
    fireEvent.click(screen.getByText('Evaluar contra el conjunto de evaluación'))
    await waitFor(() => expect(screen.getByText(/mAP@0\.5/)).toBeTruthy())
    expect(screen.getByText('person')).toBeTruthy()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0) // AP50 null → —
    expect(evaluateRun).toHaveBeenCalledWith('r1')
  })

  it('si ya está evaluado carga el eval con GET (sin botón)', async () => {
    vi.mocked(getEvaluation).mockResolvedValue(EVAL)
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={true} />)
    await waitFor(() => expect(screen.getByText(/mAP@0\.5/)).toBeTruthy())
    expect(getEvaluation).toHaveBeenCalledWith('r1')
    expect(screen.queryByText('Evaluar contra el conjunto de evaluación')).toBeNull()
  })

  it('422 muestra "no evaluable"', async () => {
    vi.mocked(evaluateRun).mockRejectedValue(new ApiError(422, { errors: [] }))
    render(<EvalSection runId="r1" benchSplit="bench_v2_test" evaluated={false} />)
    fireEvent.click(screen.getByText('Evaluar contra el conjunto de evaluación'))
    await waitFor(() => expect(screen.getByText(/no es evaluable/)).toBeTruthy())
  })
})
