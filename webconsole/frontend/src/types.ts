export interface TargetStatus {
  service_url: string
  healthy: boolean
  ready: boolean
  model: ModelInfo | null
}
export interface PlaneStatus {
  service_url: string
  healthy: boolean
  ready: boolean
  model?: ModelInfo | null
}
export interface PreflightStatus {
  ready: boolean
  blockers: string[]
  media: PlaneStatus
  control: PlaneStatus
}
export interface ModelInfo {
  ref: string
  name: string | null
  adapter: string | null
  device: string | null
  thresholds: Record<string, number | null>
  runtime: Record<string, unknown>
}
export interface PromptClass {
  id: string
  role: string | null
  enabled_by_default: boolean
  phrasings: Record<string, string[]>
}
export interface PromptSet {
  id: string
  description: string | null
  language: string | null
  frozen: boolean
  classes: PromptClass[]
  status?: string
  track?: string | null
}
export interface PromptClassSpec {
  id: string
  canonical?: string | null
  role?: string | null
  strategy?: string | null
  condition_id?: string | null
  enabled_by_default?: boolean
  phrasings: Record<string, string[]>
}
export interface PromptSetSummary {
  id: string
  description?: string | null
  status: string
  track?: string | null
  derives_from?: string | null
  n_classes: number
  n_phrases: number
}
export interface PromptSetDetail {
  id: string
  description?: string | null
  language?: string | null
  status?: string
  track?: string | null
  derives_from?: string | null
  changes?: string | null
  frozen_sha256?: string | null
  classes: PromptClassSpec[]
}
export interface Experiment {
  id: string
  group: string
  manifest: Record<string, unknown>
}
export interface IngestPlugin {
  id: string
  kind: string
  available: boolean
  description: string
  enabled: boolean
}
export interface DatasetEntry {
  id: string
  description: string | null
  path: string
  available: boolean
}
export interface Composition {
  // `source_type` preserva el `source.type` original del manifiesto (varios tipos
  // de video mapean al plugin video_file); se manda al guardar para que el
  // round-trip no colapse el string. No se usa al lanzar (el servicio ignora).
  ingest: { plugin: string; config: Record<string, unknown>; source_type?: string | null }
  prompts: { set_id: string; active_ids: string[] | null }
  run: {
    stride?: number | null
    max_units?: number | null
    save_annotated_video?: boolean
    save_previews?: boolean
    name?: string | null
  }
  manifest_model_ref?: string | null
  confirm_target_model?: boolean
}
export interface FieldError {
  field: string
  message: string
}
export interface RunRow {
  run_id: string
  name?: string | null
  status: string
  model?: string | null
  source_type?: string | null
  prompt_set_id?: string | null
  fps_effective?: number | null
  total_detections?: number | null
  duration_seconds?: number | null
  started_at?: string | null
  bench_split?: string | null
  evaluated?: boolean
  live?: boolean
  topology?: string | null
}
export interface RunDetail {
  run_id: string
  name?: string | null
  status: string
  started_at?: string
  model?: string
  summary?: Record<string, unknown>
  bench_split?: string | null
  evaluated?: boolean
  live?: boolean
}
export interface DetectionsPage {
  page: number
  page_size: number
  total: number
  items: Array<Record<string, unknown>>
}
export type StreamEvent =
  | { type: 'metric'; unit_id: string; fps: number; latency_total_ms: number;
      detections_count: number; gpu_memory_mb: number }
  | { type: 'detection'; unit_id: string; count: number }
  | { type: 'error'; unit_id: string | null; stage: string | null; message: string | null }
  | { type: 'state'; status: string; error: string | null }
export interface EvalClassRow {
  class_name: string
  AP50: number | null
  n_gt: number
  n_det: number
}
export interface EvalResult {
  type: string
  run_id: string
  benchmark: string
  iou_threshold: number
  evaluated_at: string
  per_class: EvalClassRow[]
  cr01_detection_recall: number | null
  mAP50: number | null
  model: string | null
  bench_split: string | null
}
export interface CompareRunEntry {
  run_id: string
  label: string
  model: string | null
  bench_split: string | null
  mAP50: number | null
  cr01_detection_recall: number | null
}
export interface CompareResult {
  runs: CompareRunEntry[]
  classes: string[]
  ap_by_class: Record<string, Array<number | null>>
  skipped: string[]
}
export interface PlatformInstance {
  name: string
  model_ref: string
  state: string // running | exited | created | absent
  ready: boolean
  is_target: boolean
}
export interface ExperimentManifestSummary {
  slug: string
  experiment_id?: string | null
  description?: string | null
  group?: string | null
}
export interface ExperimentRunState {
  experiment_id: string
  status: string
  ok?: boolean
  media_run_id?: string
  control_run_id?: string
  slug?: string | null
  started_at?: string | null
  error?: string | null
}
export interface ExperimentAlert {
  alert_id: string
  condition_id: string
  severity: string
  timestamp_ms?: number | null
  message?: string | null
}
export interface ExperimentReport {
  non_temporal: boolean
  resultados?: unknown[]
  identificacion?: Record<string, unknown>
}

/** Vocabulario de estado de la UI. Vive acá —y no en Badge.tsx— porque lo consumen
 *  runview.ts y experimentview.ts, que son lógica pura y no deben importar de un .tsx. */
export type BadgeTone = 'live' | 'ok' | 'warn' | 'error' | 'neutral'

export interface TraceDetection {
  label: string
  confidence: number
  bbox_norm_xyxy?: number[] | null
}
export interface TraceProgress {
  condition_id: string
  progress: number
  elapsed_ms?: number | null
  threshold_ms?: number | null
  mode?: string | null
}
export interface TraceAlert {
  condition_id: string
  severity: string
}
export interface TraceFrame {
  frame_index: number | null
  unit_id: string | null
  timestamp_ms: number | null
  detections: TraceDetection[] | null
  control: string
  progress: TraceProgress[]
  alert: TraceAlert[]
}
export interface TraceTotals {
  frames: number
  detections: number
  dropped_by_reason: Record<string, number>
  alerts: number
  received: number | null
  not_received: number | null
}
export interface TracePage {
  media_run_id: string
  control_run_id: string | null
  topology: string | null
  control_error: string | null
  totals: TraceTotals
  page: number
  page_size: number
  total: number
  frames: TraceFrame[]
}

export interface CameraPreset {
  id: string
  name: string
  plugin: string
  config: Record<string, unknown>
}
export interface PreviewDetection {
  label: string
  score: number
  bbox_norm_xyxy: [number, number, number, number]
}
export interface PreviewFrameHeader {
  seq: number
  ts: number
  width: number
  height: number
  mode: 'raw' | 'detect'
  detections: PreviewDetection[]
}
export interface PreviewStatus {
  status: 'idle' | 'streaming' | 'error'
  preview_id: string | null
  mode: string | null
  error: string | null
}
export interface PreviewStartBody {
  mode: 'raw' | 'detect'
  ingest: { plugin: string; config: Record<string, unknown> }
  prompts?: { set_inline: Record<string, unknown>; active_ids?: string[] }
  params?: { score_threshold?: number | null }
}

export interface RecordingStatus {
  // 'starting': el subproceso arrancó pero la cámara todavía no captura (la
  // OAK-D PoE tarda ~9 s en conectar). No se debe actuar la escena todavía.
  state: 'idle' | 'starting' | 'recording' | 'finished' | 'error'
  basename?: string | null
  elapsed_ms?: number
  size_bytes?: number
  duration_ms?: number
  fps?: number | null
  resolution?: string | null
  truncated?: boolean
  suspected_substream?: boolean
  error?: string | null
}

export interface StartRecordingBody {
  camera_id: string
  scenario: string
  variant: string
  max_duration_s?: number
}

export interface MasterEntry {
  name: string
  scenario: string | null
  size_bytes: number
  duration_ms: number | null
  readable: boolean
  clips: string[]
}

export interface ClipEntry {
  clip_id: string
  fps: number | null
  duration_ms: number | null
  n_frames: number | null
  resolution: string | null
  has_yaml: boolean
  master: string | null
  warnings: string[]
}

export interface GenerateClipBody {
  master: string
  t_event_s: number
  t_end_s: number
  scenario?: string
  clip_id?: string
}

export interface GenerateClipResult {
  clip_id: string
  info: { fps: number; duration_ms: number; n_frames: number; resolution: string }
  warnings: string[]
  regenerated: boolean
  invalidated: string[]
}
