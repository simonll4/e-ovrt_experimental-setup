import type { ReactElement } from 'react'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, vi } from 'vitest'

// Sólo infraestructura de render: cuando el tramo 2 incorpore el provider real,
// se usa su utilidad de render. Las pantallas y la API nunca se mockean.
const renderers = import.meta.glob<{ render: typeof render }>('../../test-utils.tsx')
export async function montar(ui: ReactElement, ruta: string) {
  const cargar = renderers['../../test-utils.tsx']
  const renderizar = cargar ? (await cargar()).render : render
  return renderizar(<MemoryRouter initialEntries={[ruta]}>{ui}</MemoryRouter>)
}

export interface Peticion {
  url: URL
  method: string
  body: unknown
}

export function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export const target = {
  service_url: 'http://media.test:8080', healthy: true, ready: true,
  model: { ref: 'mock', name: 'mock', adapter: 'mock', device: 'cpu', thresholds: {}, runtime: {} },
}
export const preflight = {
  ready: true, blockers: [], media: target,
  control: { service_url: 'http://control.test:8081', healthy: true, ready: true },
}
export const prompts = [{
  id: 'contrato_prompts', description: 'Fixture sintética', language: 'es', frozen: false,
  classes: ['person', 'helmet'].map((id) => ({
    id, role: null, enabled_by_default: true, phrasings: { default: [id] },
  })),
}]
export const corrida = {
  run_id: 'contrato_run', status: 'succeeded', live: false, evaluated: false,
  bench_split: 'bench_v3', model: 'mock',
  summary: { source_type: 'image_folder', total_detections: 1, total_units: 2 },
}
export const traza = {
  media_run_id: corrida.run_id, control_run_id: 'contrato_control',
  topology: 'single-host', control_error: null, page: 1, page_size: 500, total: 2,
  totals: {
    frames: 2, detections: 1, dropped_by_reason: {}, alerts: 0,
    received: 2, not_received: 0,
  },
  frames: [0, 1].map((i) => ({
    frame_index: i, unit_id: `frame_${i}`, timestamp_ms: i * 250,
    detections: i ? [{ label: 'person', confidence: 0.9 }] : [],
    control: 'received', progress: [], alert: [], active_patterns: [],
  })),
}
export const evaluacion = {
  type: 'perception', run_id: corrida.run_id, benchmark: 'bench_v3',
  iou_threshold: 0.5, evaluated_at: '2026-09-09T00:00:00Z',
  per_class: [{ class_name: 'person', AP50: 0.72, n_gt: 82, n_det: 90 }],
  cr01_detection_recall: 0.64, mAP50: 0.47, model: 'mock', bench_split: 'bench_v3',
}
export const experimento = {
  experiment_id: 'contrato_exp', slug: 'contrato_base', status: 'succeeded', ok: true,
  media_run_id: corrida.run_id, control_run_id: 'contrato_control',
}
export const manifiestos = [{
  slug: 'contrato_base', group: 'contrato', description: 'Fixture sintética',
  experiment_id: experimento.experiment_id,
}]

let inesperadas: string[] = []

/** Respuestas HTTP sintéticas. Una ruta imprevista se registra y hace fallar el
 * test al cerrar, incluso si la pantalla absorbe el error en un catch. */
export function instalarHttp(responder: (p: Peticion) => Response | undefined = () => undefined) {
  const llamadas: Peticion[] = []
  inesperadas = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : null
    const body = init?.body ?? (request ? await request.clone().text() : null)
    const p = {
      url: new URL(request?.url ?? String(input), 'http://localhost'),
      method: init?.method ?? request?.method ?? 'GET',
      body: body ? JSON.parse(String(body)) : null,
    }
    llamadas.push(p)
    const respuesta = responder(p)
    if (respuesta) return respuesta
    const path = p.url.pathname
    const comunes: Record<string, unknown> = {
      '/api/target': target,
      '/api/preflight': preflight,
      '/api/catalog/prompt-sets': prompts,
      '/api/catalog/experiments': [],
      '/api/catalog/ingest-plugins': [{
        id: 'image_folder', kind: 'bounded', available: true, enabled: true, description: '',
      }],
      '/api/catalog/datasets': [{ id: 'contrato_dataset', available: true }],
      '/api/cameras': [],
      '/api/runs': [],
      '/api/prompt-sets': [],
      '/api/experiments/manifests': manifiestos,
      [`/api/runs/${corrida.run_id}`]: corrida,
      [`/api/runs/${corrida.run_id}/trace`]: traza,
      [`/api/runs/${corrida.run_id}/trace/index`]: {
        media_run_id: traza.media_run_id, control_run_id: traza.control_run_id,
        topology: traza.topology, control_error: null, totals: traza.totals,
        total: traza.total,
        unit_id: traza.frames.map((f) => f.unit_id),
        frame_index: traza.frames.map((f) => f.frame_index),
        timestamp_ms: traza.frames.map((f) => f.timestamp_ms),
        detections: traza.frames.map((f) => f.detections.length),
        control_state: traza.frames.map(() => 'received'),
        alert: traza.frames.map(() => 0),
      },
      [`/api/runs/${corrida.run_id}/artifacts`]: { run_id: corrida.run_id, items: [] },
      [`/api/runs/${corrida.run_id}/comparison`]: {
        run_id: corrida.run_id, previous_run_id: null, matched_on: [], deltas: {},
      },
      [`/api/experiments/${experimento.experiment_id}`]: experimento,
      [`/api/experiments/${experimento.experiment_id}/alerts`]: [],
      [`/api/experiments/${experimento.experiment_id}/report`]: {
        non_temporal: false, resultados: [],
      },
    }
    if (p.method === 'GET' && Object.prototype.hasOwnProperty.call(comunes, path)) {
      return json(comunes[path])
    }
    if (p.method === 'GET' && [
      '/api/experiments/current', '/api/control/current',
      `/api/runs/${corrida.run_id}/artifacts/annotated.mp4`,
    ].includes(path)) return json({ detail: 'No disponible en esta fixture' }, 404)
    inesperadas.push(`${p.method} ${p.url.pathname}${p.url.search}`)
    return json({ detail: 'Petición sin fixture' }, 500)
  }))
  return {
    llamadas,
    a: (method: string, path: string) => llamadas.filter(
      (p) => p.method === method && p.url.pathname === path,
    ),
  }
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  localStorage.clear()
  expect(inesperadas).toEqual([])
})
