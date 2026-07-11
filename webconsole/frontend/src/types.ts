export interface TargetStatus {
  service_url: string
  healthy: boolean
  ready: boolean
  model: ModelInfo | null
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
