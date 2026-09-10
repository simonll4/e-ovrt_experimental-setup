// Datos HTTP sintéticos para comparar presentación. No son evidencia experimental
// ni sustituyen el seed de corridas ejecutadas por el media-plane.
export const runId = 'run_20260909_090000_seed'
export const experimentId = 'exp_seed'
const model = { ref: 'mock', name: 'Mock [seed]', adapter: 'mock', device: 'cpu', thresholds: {}, runtime: {} }
const plane = { service_url: 'http://media.test:8080', healthy: true, ready: true, model }
const prompts = {
  id: 'prompts_seed', description: 'Personas y protección [seed]', language: 'es',
  frozen: false, status: 'exploratory', n_classes: 2, n_phrases: 2,
  classes: ['person', 'helmet'].map(id => ({
    id, role: null, enabled_by_default: true, phrasings: { default: [id] },
  })),
}
const run = {
  run_id: runId, name: 'Inspección de obra [seed]', status: 'succeeded', live: false,
  created_at: '2026-09-09T09:00:00Z', started_at: '2026-09-09T09:00:00Z',
  model: 'mock', bench_split: 'bench_v3', evaluated: true,
  fps_effective: 12, total_detections: 2, duration_seconds: 2,
  summary: {
    name: 'Inspección de obra [seed]', source_type: 'video_file', model_name: 'mock',
    device: 'cpu', prompt_set_id: prompts.id, units_processed: 3, total_detections: 2,
    duration_seconds: 2, fps_effective: 12, p50_latency_ms: 20, p95_latency_ms: 30,
    detections_by_label: { person: 2 },
  },
}
const trace = {
  media_run_id: runId, control_run_id: 'ctl_seed', topology: 'single-host',
  control_error: null, page: 1, page_size: 500, total: 3,
  totals: { frames: 3, detections: 2, dropped_by_reason: {}, alerts: 1, received: 3, not_received: 0 },
  frames: [0, 1, 2].map(i => ({
    frame_index: i, unit_id: `frame_${i}`, timestamp_ms: i * 1000,
    detections: i ? [{ label: 'person', confidence: 0.9 }] : [],
    control: 'received', control_state: 'received', progress: [], active_patterns: [],
    alert: i === 2 ? [{ condition_id: 'CR-01', severity: 'high' }] : [],
  })),
}
const experiment = {
  experiment_id: experimentId, slug: 'experimento_seed', status: 'succeeded', ok: true,
  media_run_id: runId, control_run_id: 'ctl_seed',
}
const responses = {
  '/api/target': plane,
  '/api/preflight': {
    ready: true, blockers: [], media: plane,
    control: { service_url: 'http://control.test:8081', healthy: true, ready: true },
  },
  '/api/catalog/conditions': [],
  '/api/catalog/prompt-sets': [prompts],
  '/api/catalog/experiments': [],
  '/api/catalog/ingest-plugins': [{
    id: 'video_file', description: 'Video local [seed]', kind: 'bounded', available: true, enabled: true,
  }, {
    id: 'image_folder', description: 'Imágenes [seed]', kind: 'bounded', available: true, enabled: true,
  }],
  '/api/catalog/datasets': [{ id: 'imagenes_seed', type: 'image_folder', available: true }],
  '/api/runs': [run],
  [`/api/runs/${runId}`]: run,
  [`/api/runs/${runId}/trace`]: trace,
  [`/api/runs/${runId}/evaluate`]: {
    type: 'perception', run_id: runId, benchmark: 'bench_v3', model: 'mock', bench_split: 'bench_v3',
    evaluated_at: '2026-09-09T09:00:02Z', iou_threshold: 0.5,
    mAP50: 0.72, cr01_detection_recall: 0.64,
    per_class: [{ class_name: 'person', AP50: 0.72, n_gt: 2, n_det: 2 }],
  },
  '/api/prompt-sets': [prompts],
  [`/api/prompt-sets/${prompts.id}`]: prompts,
  '/api/experiments/manifests': [{
    slug: experiment.slug, experiment_id: experimentId, group: 'seed', description: 'Experimento [seed]',
  }],
  [`/api/experiments/${experimentId}`]: experiment,
  [`/api/experiments/${experimentId}/alerts`]: [{
    alert_id: 'alert_seed', condition_id: 'CR-01', severity: 'high', timestamp_ms: 2000,
  }],
  [`/api/experiments/${experimentId}/report`]: {
    non_temporal: false,
    resultados: [{ name: 't_alert-notification', value: 1.8, unit: 'ms', status: 'computed', cause: null }],
    distribucion: { counts: { delivered: 1 }, skipped_invalid_alerts: 0 },
    distribucion_por_alerta: { alert_seed: { alert_id: 'alert_seed', outcome: 'delivered' } },
  },
  [`/api/experiments/manifests/${experiment.slug}/derive-defaults`]: { warmup_frames: 20 },
  '/api/cameras': [],
  '/api/clips': { clips: [] },
  '/api/clips/masters': { masters: [] },
  '/api/recordings': { state: 'idle' },
  '/api/recordings/next': { basename: 'grabacion_seed' },
  '/api/preview': { status: 'idle', preview_id: null, mode: null, error: null },
}

export function fixture(url, method = 'GET') {
  const path = new URL(url).pathname
  if (method === 'DELETE' && path === '/api/preview') return { status: 200, body: {} }
  if (method !== 'GET') return null
  if (Object.hasOwn(responses, path)) return { status: 200, body: responses[path] }
  if (path === '/api/platform/instances') return { status: 501, body: { detail: 'Instancia fija [seed]' } }
  if (['/api/experiments/current', '/api/control/current'].includes(path)
    || path.includes('/artifacts/')) return { status: 404, body: { detail: 'Sin artefacto [seed]' } }
  return null
}
