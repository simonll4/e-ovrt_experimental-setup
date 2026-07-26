import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ComparePage, { bestPerRow } from '../pages/ComparePage'
import { getCompare, listRuns } from '../api'
import type { CompareResult, RunRow } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  getCompare: vi.fn(),
}))

const ROWS: RunRow[] = [
  { run_id: 'run_a', status: 'succeeded', model: 'gdino', bench_split: 'bench_v2_test', evaluated: true },
  { run_id: 'run_b', status: 'succeeded', model: 'yoloe', bench_split: 'bench_v2_test', evaluated: true },
  { run_id: 'run_c', status: 'succeeded', model: 'mock', bench_split: null, evaluated: false },
]

const COMPARE: CompareResult = {
  runs: [
    { run_id: 'run_a', label: 'gdino · bench_v2_test', model: 'gdino', bench_split: 'bench_v2_test', mAP50: 0.47, cr01_detection_recall: 0.64 },
    { run_id: 'run_b', label: 'yoloe · bench_v2_test', model: 'yoloe', bench_split: 'bench_v2_test', mAP50: 0.3, cr01_detection_recall: 0.1 },
  ],
  classes: ['person', 'helmet'],
  ap_by_class: { person: [0.72, 0.68], helmet: [0.61, null] },
  skipped: ['run_x'],
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

describe('bestPerRow', () => {
  it('devuelve el índice del máximo no-nulo', () => {
    expect(bestPerRow([0.3, 0.7, null])).toBe(1)
    expect(bestPerRow([null, null])).toBe(-1)
  })
})

describe('ComparePage', () => {
  it('lista solo runs evaluados y compara al seleccionar 2', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText(/run_a/)).toBeTruthy())
    expect(screen.queryByText(/run_c/)).toBeNull()

    fireEvent.click(screen.getByRole('checkbox', { name: /run_a/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /run_b/ }))

    await waitFor(() =>
      expect(screen.getAllByText('gdino · bench_v2_test').length).toBeGreaterThan(0),
    )
    expect(getCompare).toHaveBeenCalledWith(['run_a', 'run_b'])
    expect(screen.getByText(/AP@0\.5 person/)).toBeTruthy()
    expect(screen.getByText(/omitidos/i)).toBeTruthy() // aviso de skipped
  })

  it('corridas con distinto bench_split muestran aviso', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue({
      ...COMPARE,
      runs: [
        { ...COMPARE.runs[0], bench_split: 'bench_v2_test' },
        { ...COMPARE.runs[1], bench_split: 'bench_v3' },
      ],
    })
    render(<ComparePage />)
    await waitFor(() => expect(screen.getAllByRole('checkbox')).toHaveLength(2))
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])
    await waitFor(() => expect(screen.getByText(/conjuntos de evaluación distintos/i)).toBeTruthy())
  })

  it('corridas con el mismo bench_split no muestran aviso', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getAllByRole('checkbox')).toHaveLength(2))
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])
    await waitFor(() => expect(screen.getAllByText('gdino · bench_v2_test').length).toBeGreaterThan(0))
    expect(screen.queryByText(/conjuntos de evaluación distintos/i)).toBeNull()
  })

  it('la fila de CR-01 usa el nombre legible del glosario', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    vi.mocked(getCompare).mockResolvedValue(COMPARE)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getAllByRole('checkbox')).toHaveLength(2))
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])
    await waitFor(() => expect(screen.getByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy())
  })

  it('el id de una corrida en el selector se muestra en monoespaciada', async () => {
    vi.mocked(listRuns).mockResolvedValue(ROWS)
    render(<ComparePage />)
    await waitFor(() => expect(screen.getByText('run_a').className).toContain('eo-mono'))
  })
})
