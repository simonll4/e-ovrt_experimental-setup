import type {
  CompareResult, Composition, DatasetEntry, DetectionsPage, EvalResult, Experiment, FieldError,
  IngestPlugin, PromptSet, RunDetail, RunRow, TargetStatus,
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
  return (await response.json()) as T
}

export const getTarget = () => request<TargetStatus>('/api/target')
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
