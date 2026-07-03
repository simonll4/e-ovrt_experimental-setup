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
  mvp_enabled: boolean
}
export interface DatasetEntry {
  id: string
  description: string | null
  path: string
  available: boolean
}
export interface Composition {
  ingest: { plugin: string; config: Record<string, unknown> }
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
}
export interface RunDetail {
  run_id: string
  status: string
  started_at?: string
  model?: string
  summary?: Record<string, unknown>
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
