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
  /** Diff calculado contra el conjunto del que deriva. null si no deriva de
   *  ninguno, o si el padre ya no está en el repositorio. */
  diff?: PromptSetDiff | null
}
/** GET /api/experiments/manifests/{slug}/derive-defaults: 1:1 con las claves de
 *  `overrides`. Sin `url` de cámara a propósito (credenciales en claro). */
export interface DeriveDefaults {
  warmup_frames: number | null
  fps: number | null
  camera_id: string | null
  prompt_set_id: string | null
  stride: number | null
  max_units: number | null
  pattern_set_file: string | null
  pattern_active_ids: string[] | null
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
  /** Por qué no se puede elegir, o null si sí se puede. Distingue "la consola no
   *  lo ofrece" de "falta un SDK en el motor de detección". */
  disabled_reason?: string | null
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
  /** Instante de creación, siempre presente: el backend lo reconstruye del
   *  `run_id` cuando la corrida no llegó a persistir `started_at`. */
  created_at?: string | null
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
/**
 * Resumen que persiste el motor de detección al terminar una corrida
 * (`media.summary.v2`).
 *
 * Estuvo tipado como `Record<string, unknown>` y eso obligaba a redeclarar un
 * par de ayudantes `num()`/`str()` en cada archivo que lo leía, solo para sacarle
 * un número o una cadena a un campo que el backend siempre manda con el mismo
 * tipo. Peor: un error de tipeo en el nombre de un campo no lo detectaba nadie y
 * se veía como un `—` en pantalla.
 *
 * Todo es opcional a propósito: mientras la corrida está en curso el resumen
 * viene incompleto, y las métricas que dependen de haber terminado no existen
 * todavía.
 */
export interface RunSummary {
  schema_version?: string
  run_id?: string
  name?: string
  status?: string
  model_name?: string
  device?: string
  prompt_set_id?: string
  source_type?: string
  started_at?: string
  units_processed?: number
  units_dropped?: number
  total_detections?: number
  detections_by_label?: Record<string, number>
  fps_effective?: number
  duration_seconds?: number
  p50_latency_ms?: number
  p95_latency_ms?: number
  gpu_memory_peak_mb?: number
  run_descriptor?: { topology?: string } & Record<string, unknown>
}

export interface RunDetail {
  run_id: string
  name?: string | null
  status: string
  started_at?: string
  model?: string
  summary?: RunSummary
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
  /** Última ejecución consolidada en disco. */
  last_experiment_id?: string | null
  last_run_at?: string | null
  last_status?: string | null
  n_runs?: number
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
/** Un patron de riesgo actualmente confirmed/sustained en el motor del
 *  control-plane (GET /api/runs/current -> bloque `patterns`). */
export interface ActiveRiskPattern {
  pattern_id: string
  condition_id: string
  severity: string
  subject_key?: string
  state: string
  /** Tiempo de FUENTE/frame (puede ser relativo al archivo en video_file).
   *  Sirve para correlacionar con detections.jsonl, no para "hace cuanto". */
  since_timestamp_ms?: number | null
  /** Ms transcurridos reales, medidos por el control-plane con su reloj
   *  monotonico. Usar ESTE campo para mostrar "hace Ns" en la UI. */
  active_ms?: number | null
  subjects_in_evidence?: number
}
/** Snapshot del estado vivo del control-plane (GET /api/control/current,
 *  passthrough de GET /api/runs/current del control-plane). No modelamos el
 *  resto del payload (progress, etc.) porque la consola solo consume
 *  `patterns` por ahora. */
export interface ControlCurrentSnapshot {
  control_run_id: string
  status: string
  patterns: ActiveRiskPattern[]
}

/** Vocabulario de estado de la UI. Vive acá —y no en Badge.tsx— porque lo consumen
 *  runview.ts y experimentview.ts, que son lógica pura y no deben importar de un .tsx. */
export type { BadgeTone } from './palette'

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
/** Un patron confirmed/sustained cuyo episodio sigue abierto en este frame
 *  (reconstruido de pattern_events.jsonl -- ver TraceSection). Persiste desde
 *  el frame de confirmacion hasta el de resolved, aunque frames intermedios
 *  no tengan su propia fila de progreso ni alerta. */
export interface TraceActivePattern {
  pattern_id: string
  condition_id: string
  severity: string
  subject_key: string
}
/** Estado de entrega al motor de reglas, vocabulario cerrado resuelto por el
 *  backend. `unknown` es "sin dato" (el motor de reglas no evaluó la corrida). */
export type ControlState = 'received' | 'dropped' | 'not_received' | 'unknown'

export interface TraceFrame {
  frame_index: number | null
  unit_id: string | null
  timestamp_ms: number | null
  detections: TraceDetection[] | null
  control: string
  progress: TraceProgress[]
  alert: TraceAlert[]
  /** Opcional para no romper fixtures de test viejos; el backend siempre lo
   *  manda (posiblemente []), tratar ausencia igual que []. */
  active_patterns?: TraceActivePattern[]
  /** Vocabulario cerrado + etiqueta ya traducida. Opcionales por compatibilidad
   *  con fixtures viejos; cuando faltan se derivan de `control`. */
  control_state?: ControlState
  control_reason?: string | null
  control_label?: string
}

/** Actividad de la corrida COMPLETA en arrays paralelos: el i-ésimo elemento de
 *  cada uno es el i-ésimo cuadro. Es lo que dibuja la línea de tiempo, en una
 *  sola petición en vez de paginar la traza entera. */
export interface TraceIndex {
  media_run_id: string
  control_run_id: string | null
  topology: string | null
  control_error: string | null
  totals: TraceTotals
  total: number
  unit_id: Array<string | null>
  frame_index: Array<number | null>
  timestamp_ms: Array<number | null>
  detections: number[]
  control_state: ControlState[]
  /** 1 si el cuadro tiene alerta, 0 si no. */
  alert: number[]
}

export interface ArtifactEntry {
  path: string
  name: string
  size_bytes: number
  /** Cantidad de archivos cuando la entrada es un directorio (previews/). */
  n_files: number | null
  description: string | null
}

/** Variación de un indicador contra la corrida anterior comparable. */
export interface RunDelta {
  current: number
  previous: number
  delta: number
  /** Hacia dónde es mejor moverse; null cuando subir no es ni bueno ni malo. */
  better: 'mas' | 'menos' | null
}

export interface RunComparison {
  run_id: string
  /** null cuando no hay ninguna corrida comparable: la interfaz muestra los
   *  indicadores sin variación, que no es lo mismo que variación cero. */
  previous_run_id: string | null
  matched_on: string[]
  deltas: Record<string, RunDelta>
}

/** Condición de riesgo definida en el motor de reglas (CR-01, CR-02, ...). */
export interface ConditionInfo {
  condition_id: string
  pattern_id: string | null
  pattern_set_id: string | null
  name: string | null
  display_name: string | null
  description: string | null
  severity: string | null
  enabled: boolean
}

/** Qué cambió entre un conjunto de prompts y aquel del que deriva. */
export interface PromptSetDiff {
  from: string | null
  classes_added: string[]
  classes_removed: string[]
  phrases_added: Record<string, string[]>
  phrases_removed: Record<string, string[]>
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
  marks: number[]
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
