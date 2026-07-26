import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import TraceSection from '../components/TraceSection'
import * as api from '../api'
import type { TracePage } from '../types'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTrace: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

function basePage(overrides: Partial<TracePage> = {}): TracePage {
  return {
    media_run_id: 'r_1',
    control_run_id: 'ctrl_1',
    topology: 'one_node',
    control_error: null,
    totals: {
      frames: 3,
      detections: 1,
      dropped_by_reason: { rate_gate: 1 },
      alerts: 1,
      received: 1,
      not_received: 0,
    },
    page: 1,
    page_size: 50,
    total: 3,
    frames: [
      {
        frame_index: 0,
        unit_id: 'u0',
        timestamp_ms: 0,
        detections: [{ label: 'person', confidence: 0.91 }],
        control: 'received',
        progress: [{ condition_id: 'CR-01', progress: 0.5 }],
        alert: [],
      },
      {
        frame_index: 1,
        unit_id: 'u1',
        timestamp_ms: 100,
        detections: null,
        control: 'dropped:rate_gate',
        progress: [],
        alert: [],
      },
      {
        frame_index: 2,
        unit_id: null,
        timestamp_ms: 200,
        detections: [],
        control: 'received',
        progress: [],
        alert: [{ condition_id: 'CR-02', severity: 'high' }],
      },
    ],
    ...overrides,
  }
}

describe('TraceSection', () => {
  it('renderiza tiles, badges y la barra de progreso', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(screen.getAllByText('1', { selector: '.eo-stat__value' }).length).toBe(2)
    expect(screen.getAllByText('recibido')[0].closest('.eo-badge')?.className).toContain('eo-badge--ok')
    const rateGateBadge = screen
      .getAllByText('límite de tasa')
      .map((el) => el.closest('.eo-badge'))
      .find((el) => el !== null)
    expect(rateGateBadge?.className).toContain('eo-badge--warn')
    const fill = document.querySelector('.eo-progressbar__fill') as HTMLElement
    expect(fill.style.width).toBe('50%')
  })

  it('frame_index null (corrida image_folder) muestra el unit_id en vez de "#null"', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: null,
            unit_id: 'img_000002',
            timestamp_ms: null,
            detections: [{ label: 'helmet', confidence: 0.8 }],
            control: 'received',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('img_000002')).toBeTruthy())
  })

  it('sin control_run_id muestra EmptyState', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        control_run_id: null,
        control_error: null,
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [{ label: 'person', confidence: 0.9 }],
            control: 'n/d',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('no evaluado por el control-plane')).toBeTruthy())
    expect(screen.queryByText('control')).toBeNull()
    expect(screen.queryByText('patrón')).toBeNull()
  })

  it('control_error muestra ErrorBanner y la tabla sigue presente', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({ control_error: 'control-plane no responde' }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() =>
      expect(screen.getByText(/control-plane no disponible/)).toBeTruthy(),
    )
    expect(document.querySelector('.eo-table')).toBeTruthy()
  })

  it('filtro solo frames con actividad oculta la fila inactiva', async () => {
    const page = basePage()
    page.frames.push({
      frame_index: 3,
      unit_id: 'u3',
      timestamp_ms: 300,
      detections: [],
      control: 'received',
      progress: [],
      alert: [],
    })
    vi.mocked(api.getTrace).mockResolvedValue(page)
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#3 · u3')).toBeTruthy())
    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)
    await waitFor(() => expect(screen.queryByText('#3 · u3')).toBeFalsy())
  })

  it('solo pinta --alert en la barra cuya condition_id coincide con la alerta', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [{ label: 'person', confidence: 0.91 }],
            control: 'received',
            progress: [
              { condition_id: 'CR-01', progress: 0.5 },
              { condition_id: 'CR-02', progress: 0.3 },
            ],
            alert: [{ condition_id: 'CR-02', severity: 'high' }],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    const fills = document.querySelectorAll('.eo-progressbar__fill')
    expect(fills.length).toBe(2)
    expect((fills[0] as HTMLElement).className).not.toContain('--alert')
    expect((fills[1] as HTMLElement).className).toContain('--alert')
  })

  it('un frame sin alerta/progreso propios pero con active_patterns muestra "activo" (el bug real: frame_000456)', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 456,
            unit_id: 'u456',
            timestamp_ms: 15400,
            detections: [{ label: 'person', confidence: 0.9 }],
            control: 'received',
            progress: [],
            alert: [],
            active_patterns: [
              { pattern_id: 'CR-01', condition_id: 'CR-01', severity: 'high', subject_key: 'k1' },
            ],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText(/activo/i)).toBeTruthy())
    expect(screen.getByText('CR-01 — Presencia de persona sin casco', { selector: '.eo-badge' })).toBeTruthy()
  })

  it('un frame sin active_patterns no muestra "activo"', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(screen.queryByText(/riesgo activo/i)).toBeNull()
  })

  it('la fila con alerta lleva eo-row--alert, la fila sin alerta no', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    const rows = document.querySelectorAll('.eo-table tbody tr')
    // frame 0: alert=[] -> sin clase; frame 2: alert=[CR-02] -> con clase
    expect(rows[0].className).not.toContain('eo-row--alert')
    expect(rows[2].className).toContain('eo-row--alert')
  })

  it('muestra la línea de tiempo con un tick por frame', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('ctrl_1')).toBeTruthy())
    expect(document.querySelectorAll('.eo-timeline__tick').length).toBe(3)
  })

  it('trae todas las páginas y acumula los frames de cada una', async () => {
    const page1 = basePage({
      total: 4,
      page: 1,
      page_size: 2,
      frames: [
        { frame_index: 0, unit_id: 'u0', timestamp_ms: 0, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 1, unit_id: 'u1', timestamp_ms: 100, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    const page2 = basePage({
      total: 4,
      page: 2,
      page_size: 2,
      frames: [
        { frame_index: 2, unit_id: 'u2', timestamp_ms: 200, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 3, unit_id: 'u3', timestamp_ms: 300, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    vi.mocked(api.getTrace).mockResolvedValueOnce(page1).mockResolvedValueOnce(page2)
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#3 · u3')).toBeTruthy())
    expect(api.getTrace).toHaveBeenNthCalledWith(1, 'r_1', 1, 50)
    expect(api.getTrace).toHaveBeenNthCalledWith(2, 'r_1', 2, 2)
    expect(screen.getByText('#0 · u0')).toBeTruthy()
    expect(screen.getByText('#1 · u1')).toBeTruthy()
    expect(screen.getByText('#2 · u2')).toBeTruthy()
  })

  it('un motivo de descarte no reconocido se muestra crudo y en monoespaciada', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(
      basePage({
        frames: [
          {
            frame_index: 0,
            unit_id: 'u0',
            timestamp_ms: 0,
            detections: [],
            control: 'dropped:queue_full',
            progress: [],
            alert: [],
          },
        ],
      }),
    )
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('queue_full')).toBeTruthy())
    expect(screen.getByText('queue_full').className).toContain('eo-mono')
  })

  it('la fila con alerta confirmada usa el tono alert, no error', async () => {
    vi.mocked(api.getTrace).mockResolvedValue(basePage())
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText(/ALERTA/)).toBeTruthy())
    expect(screen.getByText(/ALERTA/).closest('.eo-badge')?.className).toContain('eo-badge--alert')
  })

  it('si falla una página intermedia, muestra banner de traza incompleta pero mantiene lo ya cargado', async () => {
    const page1 = basePage({
      total: 4,
      page: 1,
      page_size: 2,
      frames: [
        { frame_index: 0, unit_id: 'u0', timestamp_ms: 0, detections: [], control: 'received', progress: [], alert: [] },
        { frame_index: 1, unit_id: 'u1', timestamp_ms: 100, detections: [], control: 'received', progress: [], alert: [] },
      ],
    })
    vi.mocked(api.getTrace).mockResolvedValueOnce(page1).mockRejectedValueOnce(new Error('timeout'))
    render(<TraceSection runId="r_1" />)
    await waitFor(() => expect(screen.getByText('#1 · u1')).toBeTruthy())
    await waitFor(() => expect(screen.getByText(/línea de tiempo incompleta/)).toBeTruthy())
    expect(screen.getByText('#0 · u0')).toBeTruthy()
  })
})
