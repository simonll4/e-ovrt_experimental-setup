import { act, cleanup, render, screen } from '../test-utils'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ExperimentDetailPage from '../pages/ExperimentDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getExperiment: vi.fn(),
  getExperimentAlerts: vi.fn(),
  getExperimentReport: vi.fn(),
  getControlCurrent: vi.fn(),
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

// Deja correr los .then encolados de las promesas ya resueltas (los mocks de
// fetch) para que el estado termine de asentarse antes de asertar.
//
// Avanza 1 ms además de drenar microtasks: TanStack Query no notifica a los
// observadores en el mismo tick en que resuelve la petición, lo agenda. Con
// solo `await Promise.resolve()` la caché ya tiene el dato pero el componente
// todavía no se re-renderizó, y la pantalla sigue diciendo "Cargando…".
// Dos rondas porque las peticiones están encadenadas: la del estado vivo del
// motor de reglas solo se habilita una vez que se sabe que el experimento está
// corriendo, o sea después de que resolvió la primera.
async function flush() {
  for (let ronda = 0; ronda < 2; ronda++) {
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
      await Promise.resolve()
      await vi.advanceTimersByTimeAsync(1)
    })
  }
}

const CR01_PATTERN = {
  pattern_id: 'CR-01',
  condition_id: 'CR-01',
  severity: 'high',
  subject_key: 'CR-01:169.254.31.137',
  state: 'sustained',
  // active_ms es tiempo transcurrido REAL calculado por el control-plane con
  // su propio reloj monotonico -- no depende del system time falso de este
  // test (a diferencia del since_timestamp_ms viejo, que si dependia de
  // vi.setSystemTime y por eso era el campo equivocado para esto).
  since_timestamp_ms: 0,
  active_ms: 12_345,
  subjects_in_evidence: 1,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
  vi.setSystemTime(1_000_000)
  vi.mocked(api.getExperimentAlerts).mockResolvedValue([])
  vi.mocked(api.getExperimentReport).mockResolvedValue({ non_temporal: false, resultados: [] } as any)
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('ExperimentDetailPage — banner de riesgo activo', () => {
  it('muestra el banner con el condition_id cuando patterns no esta vacio y el experimento corre', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent).mockResolvedValue({
      control_run_id: 'control_1',
      status: 'running',
      patterns: [CR01_PATTERN],
    } as any)

    renderPage()
    await flush()

    expect(screen.getByText('CR-01')).toBeTruthy()
  })

  it('el banner desaparece cuando el patron ya no esta en la respuesta (el motor lo resolvio)', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent)
      .mockResolvedValueOnce({ control_run_id: 'control_1', status: 'running', patterns: [CR01_PATTERN] } as any)
      .mockResolvedValueOnce({ control_run_id: 'control_1', status: 'running', patterns: [] } as any)

    renderPage()
    await flush()
    expect(screen.getByText('CR-01')).toBeTruthy()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    await flush()

    expect(screen.queryByText('CR-01')).toBeNull()
  })

  it('un 404 de /api/control/current (sin corrida activa) no muestra banner ni rompe la pagina', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent).mockResolvedValue(null)

    renderPage()
    await flush()

    // La pagina sigue mostrando el badge de estado, no un error.
    expect(screen.getByText(/en curso/i)).toBeTruthy()
    expect(screen.queryByText('CR-01')).toBeNull()
  })

  it('un error transitorio de red no rompe la pagina ni borra el badge de estado', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent).mockRejectedValue(new Error('network down'))

    renderPage()
    await flush()

    expect(screen.getByText(/en curso/i)).toBeTruthy()
    expect(screen.queryByText('CR-01')).toBeNull()
  })

  it('no poll y sin banner cuando el experimento no esta running', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'succeeded' } as any)

    renderPage()
    await flush()

    expect(api.getControlCurrent).not.toHaveBeenCalled()
  })

  it('calcula el contador de segundos activos desde active_ms (no desde since_timestamp_ms)', async () => {
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent).mockResolvedValue({
      control_run_id: 'control_1',
      status: 'running',
      patterns: [CR01_PATTERN],
    } as any)

    renderPage()
    await flush()

    expect(screen.getByText(/12s/)).toBeTruthy()
  })

  it('no revienta el contador cuando since_timestamp_ms es 0 (bug real: video_file relativo al archivo)', async () => {
    // Reproduce el humo real que motivo este campo: una corrida video_file
    // tiene since_timestamp_ms=0.0 en la primera unidad (tiempo de fuente,
    // no wallclock). Con el codigo viejo (Date.now() - since_timestamp_ms)
    // esto mostraba "hace 1785005982s". Con active_ms ya calculado por el
    // motor, el resultado es el elapsed real sin importar el reloj del cliente.
    vi.mocked(api.getExperiment).mockResolvedValue({ experiment_id: 'exp_1', status: 'running' } as any)
    vi.mocked(api.getControlCurrent).mockResolvedValue({
      control_run_id: 'control_1',
      status: 'running',
      patterns: [{ ...CR01_PATTERN, since_timestamp_ms: 0, active_ms: 42_000 }],
    } as any)

    renderPage()
    await flush()

    expect(screen.getByText(/42s/)).toBeTruthy()
    expect(screen.queryByText(/1785/)).toBeNull()
  })
})
