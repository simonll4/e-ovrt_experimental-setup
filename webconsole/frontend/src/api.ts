import type {
  CameraPreset, ClipEntry, CompareResult, ControlCurrentSnapshot, Composition, DatasetEntry,
  DeriveDefaults, DetectionsPage, EvalResult,
  Experiment, ExperimentAlert, ExperimentManifestSummary, ExperimentReport, ExperimentRunState,
  FieldError, GenerateClipBody, GenerateClipResult, IngestPlugin, MasterEntry, PlatformInstance,
  PreflightStatus, PreviewStartBody, PreviewStatus, PromptSet, PromptSetDetail, PromptSetSummary,
  RecordingStatus, RunDetail, RunRow, StartRecordingBody, TargetStatus, TracePage,
} from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: unknown,
  ) {
    super(`API ${status}`)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      /* cuerpo no-JSON */
    }
    throw new ApiError(response.status, payload)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const getTarget = () => request<TargetStatus>('/api/target')
export const getPreflight = () => request<PreflightStatus>('/api/preflight')
export const getPromptSets = () => request<PromptSet[]>('/api/catalog/prompt-sets')
export const getExperiments = () => request<Experiment[]>('/api/catalog/experiments')
export const getIngestPlugins = () => request<IngestPlugin[]>('/api/catalog/ingest-plugins')
export const getDatasets = () => request<DatasetEntry[]>('/api/catalog/datasets')
export const validateComposition = (comp: Composition) =>
  request<{ valid: boolean; errors: FieldError[] }>('/api/compose/validate', {
    method: 'POST',
    body: JSON.stringify(comp),
  })
export const launchRun = (comp: Composition) =>
  request<{ run_id: string }>('/api/runs', { method: 'POST', body: JSON.stringify(comp) })
export const listRuns = () => request<RunRow[]>('/api/runs')
export const getRun = (id: string) => request<RunDetail>(`/api/runs/${encodeURIComponent(id)}`)
export const stopRun = (id: string) =>
  request<{ run_id: string; stopping: boolean }>(
    `/api/runs/${encodeURIComponent(id)}/stop`,
    { method: 'POST' },
  )
export const deleteRun = (id: string) =>
  request<{ detail: string; errors: Record<string, string> } | undefined>(
    `/api/runs/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
  )
export const evaluateRun = (id: string) =>
  request<EvalResult>(`/api/runs/${encodeURIComponent(id)}/evaluate`, { method: 'POST' })
export const getEvaluation = (id: string) =>
  request<EvalResult>(`/api/runs/${encodeURIComponent(id)}/evaluate`)
export const getCompare = (ids: string[]) =>
  request<CompareResult>(`/api/compare?runs=${ids.map(encodeURIComponent).join(',')}`)
export const getDetections = (id: string, page = 1, pageSize = 50) =>
  request<DetectionsPage>(
    `/api/runs/${encodeURIComponent(id)}/detections?page=${page}&page_size=${pageSize}`,
  )
export const saveManifest = (body: {
  name: string
  group?: string | null
  overwrite?: boolean
  composition: Composition
}) => request<{ path: string }>('/api/manifests', { method: 'POST', body: JSON.stringify(body) })

// `path` puede traer '/' legítimos (p.ej. `previews/u0.preview.jpg`); encodeamos cada
// segmento por separado para no convertirlos en `%2F` y romper el ruteo del servidor.
const encodePathSegments = (path: string) => path.split('/').map(encodeURIComponent).join('/')

export const artifactUrl = (id: string, path: string) =>
  `/api/runs/${encodeURIComponent(id)}/artifacts/${encodePathSegments(path)}`
export const streamUrl = (id: string) => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/runs/${encodeURIComponent(id)}/stream`
}

export const getInstances = () => request<PlatformInstance[]>('/api/platform/instances')
export const activateInstance = (name: string) =>
  request<{ target: string; model_ref: string }>(
    `/api/platform/instances/${encodeURIComponent(name)}/activate`,
    { method: 'POST' },
  )
export const stopPlatform = () =>
  request<{ target: null }>('/api/platform/stop', { method: 'POST' })

export const getExperimentManifests = () =>
  request<ExperimentManifestSummary[]>('/api/experiments/manifests')
export const runExperiment = (body: { slug: string }) =>
  request<{ experiment_id: string }>('/api/experiments/run', {
    method: 'POST',
    body: JSON.stringify(body),
  })
export const deriveExperimentManifest = (
  slug: string,
  body: { new_slug: string; changes?: string; overrides: Record<string, unknown> },
) =>
  request<{ slug: string }>(`/api/experiments/manifests/${encodeURIComponent(slug)}/derive`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
/** Valores del manifiesto fuente para precargar el formulario de derivación.
 *  Nunca trae la url de la cámara (los presets RTSP llevan credenciales): el
 *  BFF resuelve `camera_id` contra el catálogo, o manda `null`. */
export const getDeriveDefaults = (slug: string) =>
  request<DeriveDefaults>(
    `/api/experiments/manifests/${encodeURIComponent(slug)}/derive-defaults`,
  )
export const getCurrentExperiment = async (): Promise<ExperimentRunState | null> => {
  try {
    return await request<ExperimentRunState>('/api/experiments/current')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}
export const getExperiment = (id: string) =>
  request<ExperimentRunState>(`/api/experiments/${encodeURIComponent(id)}`)
export const getExperimentAlerts = (id: string) =>
  request<ExperimentAlert[]>(`/api/experiments/${encodeURIComponent(id)}/alerts`)
export const getExperimentReport = (id: string) =>
  request<ExperimentReport>(`/api/experiments/${encodeURIComponent(id)}/report`)
export const getControlCurrent = async (): Promise<ControlCurrentSnapshot | null> => {
  try {
    return await request<ControlCurrentSnapshot>('/api/control/current')
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

export const listPromptSets = () => request<PromptSetSummary[]>('/api/prompt-sets')
export const getPromptSetDetail = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${encodeURIComponent(id)}`)
export const createPromptSet = (set: PromptSetDetail) =>
  request<PromptSetDetail>('/api/prompt-sets', { method: 'POST', body: JSON.stringify(set) })
export const updatePromptSet = (id: string, set: PromptSetDetail) =>
  request<PromptSetDetail>(`/api/prompt-sets/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(set),
  })
export const deletePromptSet = (id: string) =>
  request<void>(`/api/prompt-sets/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const requestFreeze = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${encodeURIComponent(id)}/freeze-request`, {
    method: 'POST',
  })
export const confirmFreeze = (id: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${encodeURIComponent(id)}/freeze`, {
    method: 'POST',
  })
export const derivePromptSet = (id: string, newId: string, changes: string) =>
  request<PromptSetDetail>(`/api/prompt-sets/${encodeURIComponent(id)}/derive`, {
    method: 'POST',
    body: JSON.stringify({ new_id: newId, changes }),
  })

export const getTrace = (id: string, page = 1, pageSize = 50, controlRunId?: string) => {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (controlRunId) params.set('control_run_id', controlRunId)
  return request<TracePage>(`/api/runs/${encodeURIComponent(id)}/trace?${params.toString()}`)
}

export const listCameras = () => request<CameraPreset[]>('/api/cameras')
export const createCamera = (p: CameraPreset) =>
  request<CameraPreset>('/api/cameras', { method: 'POST', body: JSON.stringify(p) })
export const updateCamera = (id: string, p: CameraPreset) =>
  request<CameraPreset>(`/api/cameras/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(p),
  })
export const deleteCamera = (id: string) =>
  request<undefined>(`/api/cameras/${encodeURIComponent(id)}`, { method: 'DELETE' })
export const startPreview = (body: PreviewStartBody) =>
  request<{ preview_id: string }>('/api/preview', { method: 'POST', body: JSON.stringify(body) })
export const getPreview = () => request<PreviewStatus>('/api/preview')
export const stopPreview = () => request<undefined>('/api/preview', { method: 'DELETE' })
export function previewStreamUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/api/preview/stream`
}

export const nextTake = (scenario: string, variant: string) =>
  request<{ basename: string }>(
    `/api/recordings/next?scenario=${encodeURIComponent(scenario)}&variant=${encodeURIComponent(variant)}`,
  )
export const getRecording = () => request<RecordingStatus>('/api/recordings')
export const startRecording = (body: StartRecordingBody) =>
  request<RecordingStatus>('/api/recordings', { method: 'POST', body: JSON.stringify(body) })
export const stopRecording = () =>
  request<RecordingStatus>('/api/recordings', { method: 'DELETE' })

export const getMasters = () => request<{ masters: MasterEntry[] }>('/api/clips/masters')
export const getClips = () => request<{ clips: ClipEntry[] }>('/api/clips')
export const generateClip = (body: GenerateClipBody) =>
  request<GenerateClipResult>('/api/clips', { method: 'POST', body: JSON.stringify(body) })
export const masterMediaUrl = (name: string) =>
  `/api/clips/media/master/${encodeURIComponent(name)}`
export const clipMediaUrl = (clipId: string) =>
  `/api/clips/media/clip/${encodeURIComponent(clipId)}`
