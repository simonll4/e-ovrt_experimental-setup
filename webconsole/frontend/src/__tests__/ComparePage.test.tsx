import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
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
  {
    run_id: 'run_a',
    name: 'Barrido diurno',
    status: 'succeeded',
    model: 'gdino',
    bench_split: 'bench_v2_test',
    evaluated: true,
  },
  {
    run_id: 'run_b',
    name: 'Perímetro con lluvia',
    status: 'succeeded',
    model: 'yoloe',
    bench_split: 'bench_v2_test',
    evaluated: true,
  },
  // Evaluada contra OTRO conjunto: comparar contra las anteriores no es válido.
  {
    run_id: 'run_otro',
    name: 'Interior pasillo norte',
    status: 'succeeded',
    model: 'gdino',
    bench_split: 'bench_v2_val',
    evaluated: true,
  },
  // Sin evaluar: no debe aparecer.
  { run_id: 'run_c', status: 'succeeded', model: 'mock', bench_split: null, evaluated: false },
]

const COMPARE: CompareResult = {
  runs: [
    {
      run_id: 'run_a',
      label: 'Barrido diurno',
      model: 'gdino',
      bench_split: 'bench_v2_test',
      mAP50: 0.47,
      cr01_detection_recall: 0.64,
    },
    {
      run_id: 'run_b',
      label: 'Perímetro con lluvia',
      model: 'yoloe',
      bench_split: 'bench_v2_test',
      mAP50: 0.3,
      cr01_detection_recall: 0.1,
    },
  ],
  classes: ['person', 'helmet'],
  ap_by_class: { person: [0.72, 0.68], helmet: [0.61, null] },
  skipped: ['run_x'],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listRuns).mockResolvedValue(ROWS)
  vi.mocked(getCompare).mockResolvedValue(COMPARE)
})
afterEach(() => cleanup())

const pick = async (name: string) => {
  fireEvent.click(await screen.findByRole('checkbox', { name }))
}

const pickBoth = async () => {
  await pick('Barrido diurno')
  await pick('Perímetro con lluvia')
  await waitFor(() => expect(screen.getByRole('table')).toBeTruthy())
}

describe('bestPerRow', () => {
  it('devuelve el índice del máximo cuando hay algo que comparar', () => {
    expect(bestPerRow([0.3, 0.7, null])).toBe(1)
    expect(bestPerRow([null, null])).toBe(-1)
  })

  // Con un solo valor medido no hay comparación. En el banco real esto marcaba
  // bare_head 0,000 en verde como "mejor valor" — lo contrario de lo que pasó.
  it('no corona a un valor solo: sin par no hay comparación', () => {
    expect(bestPerRow([0.243, null])).toBe(-1)
    expect(bestPerRow([null, 0])).toBe(-1)
    expect(bestPerRow([0.5])).toBe(-1)
  })

  it('un empate no tiene ganador: no inventa una diferencia', () => {
    expect(bestPerRow([0.785, 0.785])).toBe(-1)
    expect(bestPerRow([0.2, 0.9, 0.9])).toBe(-1)
  })

  it('un cero puede ganar si el otro midió menos — lo que no vale es ganar solo', () => {
    expect(bestPerRow([0, -1])).toBe(0)
  })

  // Los dos se leen "0,785": afirmar un ganador sería afirmar una diferencia que
  // el lector no puede ver en pantalla.
  it('empate a la precisión mostrada tampoco tiene ganador', () => {
    expect(bestPerRow([0.7851, 0.7849])).toBe(-1)
    expect(bestPerRow([0.7856, 0.7849])).toBe(0) // 0,786 contra 0,785: sí se ve
  })
})

describe('ComparePage', () => {
  it('lista las corridas por nombre, no por identificador crudo', async () => {
    render(<ComparePage />)
    expect(await screen.findByText('Barrido diurno')).toBeTruthy()
    // El id sigue disponible como dato, pero no es lo que se lee primero.
    expect(screen.queryByRole('checkbox', { name: 'run_a' })).toBeNull()
  })

  it('deja afuera las corridas sin evaluar y lo explica', async () => {
    render(<ComparePage />)
    await screen.findByText('Barrido diurno')
    expect(screen.queryByText(/run_c/)).toBeNull()
    expect(screen.getByText(/Las corridas sin evaluación no aparecen acá/)).toBeTruthy()
  })

  it('pide al menos dos corridas antes de comparar', async () => {
    render(<ComparePage />)
    await screen.findByText('Barrido diurno')
    expect(screen.getByText('Elegí al menos dos corridas')).toBeTruthy()
    expect(getCompare).not.toHaveBeenCalled()
  })

  it('compara al elegir dos y nombra las métricas en español', async () => {
    render(<ComparePage />)
    await pickBoth()
    expect(getCompare).toHaveBeenCalledWith(['run_a', 'run_b'])
    expect(screen.getByText('Precisión media (mAP@0.5)')).toBeTruthy()
    expect(screen.getByText('Exhaustividad CR-01')).toBeTruthy()
    // La clase se nombra en la tabla y en el eje del gráfico; nunca se traduce.
    expect(screen.getAllByText('person').length).toBeGreaterThanOrEqual(2)
  })

  it('resalta el mejor valor de cada fila', async () => {
    const { container } = render(<ComparePage />)
    await pickBoth()
    const best = container.querySelectorAll('.eo-best')
    expect(best.length).toBeGreaterThan(0)
    // person: 0,72 contra 0,68 → gana la primera columna.
    const row = within(screen.getByRole('table'))
      .getAllByRole('row')
      .find((r) => r.textContent?.includes('person'))
    expect(row?.querySelector('.eo-best')?.textContent).toContain('0,72')
  })

  it('avisa cuando se comparan conjuntos de evaluación distintos', async () => {
    render(<ComparePage />)
    await pick('Barrido diurno')
    await pick('Interior pasillo norte')
    expect(await screen.findByText(/conjuntos distintos/i)).toBeTruthy()
  })

  it('no avisa cuando comparten conjunto de evaluación', async () => {
    render(<ComparePage />)
    await pickBoth()
    expect(screen.queryByText(/conjuntos distintos/i)).toBeNull()
  })

  it('informa las corridas que quedaron afuera en vez de omitirlas en silencio', async () => {
    render(<ComparePage />)
    await pickBoth()
    expect(screen.getByText(/Quedaron afuera/)).toBeTruthy()
    expect(screen.getByText(/run_x/)).toBeTruthy()
  })

  it('dibuja las barras con leyenda nombrada por corrida', async () => {
    render(<ComparePage />)
    await pickBoth()
    expect(screen.getByText('Precisión por clase')).toBeTruthy()
    // El nombre aparece en el encabezado de la tabla y en la leyenda del gráfico.
    expect(screen.getAllByText('Barrido diurno').length).toBeGreaterThanOrEqual(2)
  })
})
