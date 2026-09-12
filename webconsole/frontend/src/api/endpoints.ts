import type {
  CameraPreset, ClipEntry, Clase, CompareResult, ControlCurrentSnapshot, Composition, DatasetEntry,
  DeriveDefaults, DetectionsPage, EvalResult,
  Experiment, ExperimentAlert, ExperimentManifestSummary, ExperimentReport, ExperimentRunState,
  FieldError, GenerateClipBody, GenerateClipResult, IngestPlugin, MasterEntry, PlatformInstance,
  PreflightStatus, PreviewStartBody, PreviewStatus, PromptSet, PromptSetDetail, PromptSetSummary,
  RecordingStatus, RunDetail, RunGroup, RunRow, StartRecordingBody, TargetStatus, TracePage,
  ArtifactEntry, ConditionInfo, RunComparison, TraceIndex, EvidenceListingMeta, EvidenceView,
  EvidenceRecorrido, EvidenceStepPage, EvidenceResultPage, ArchivedRunDetail, PlatformTestSlug,
  Documentacion,
} from '../types'

export class ApiError extends Error {
  constructor(
    public status: number,
    public payload: unknown,
  ) {
    super(`API ${status}`)
  }
}

/** La documentación de la consola. Como la evidencia, sale del disco local: no
 *  toca ningún servicio y contesta con los tres planos apagados. */
export const getDocumentacion = () => request<Documentacion>('/api/documentacion')

export const getEvidenceRecorrido = () => request<EvidenceRecorrido>('/api/evidencia')
export const getEvidenceStep = (n: number) =>
  request<EvidenceStepPage>(`/api/evidencia/paso?${new URLSearchParams({ n: String(n) })}`)
export const getEvidenceResult = (id: string, page: number, pageSize = 25) =>
  request<EvidenceResultPage>(`/api/evidencia/resultado?${new URLSearchParams({ id, page: String(page), page_size: String(pageSize) })}`)
export const getArchivedRun = (plane: string, runId: string) =>
  request<ArchivedRunDetail>(`/api/evidencia/run?${new URLSearchParams({ plane, run_id: runId })}`)

async function request<T>(path: string, init?: RequestInit, onResponse?: (r: Response) => void): Promise<T> {
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
  onResponse?.(response)
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
/** Tope de página del servidor (`page_size` acepta hasta 200). */
const RUNS_PAGE_MAX = 200

/** Todas las corridas, agotando la paginación del servidor.
 *
 *  `GET /api/runs` pelado ya no devuelve el historial completo: desde que el
 *  listado pagina del lado del servidor, sin parámetros contesta la primera
 *  página de 25. Quien creía tener todas las corridas —Comparar, que filtra las
 *  evaluadas— estaba mirando las 25 más nuevas y no tenía forma de notarlo.
 *
 *  Se pide de a 200 y se sigue mientras `X-Total-Count` diga que falta. Para el
 *  listado de la pantalla de Corridas esto NO se usa: ahí se pide una página por
 *  vez, que es de lo que se trata paginar en el servidor.
 */
export async function listRuns(): Promise<RunRow[]> {
  const primera = await listRunsPaged({ pageSize: RUNS_PAGE_MAX })
  const items = [...primera.items]
  const paginas = Math.ceil(primera.total / RUNS_PAGE_MAX)
  for (let pagina = 2; pagina <= paginas; pagina++) {
    items.push(...(await listRunsPaged({ pagina, pageSize: RUNS_PAGE_MAX })).items)
  }
  return items
}
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

export const getExperimentManifests = (
  vista?: EvidenceView, onMetadata?: (meta: EvidenceListingMeta) => void,
) => request<ExperimentManifestSummary[]>(
  `/api/experiments/manifests${vista ? `?vista=${vista}` : ''}`, undefined,
  response => onMetadata?.(evidenceMetadata(response)),
)
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

/** Actividad de la corrida completa en una sola petición.
 *  Reemplaza al bucle que paginaba `/trace` hasta 40 veces para dibujar la
 *  línea de tiempo. */
export const getTraceIndex = (id: string, controlRunId?: string) => {
  const params = controlRunId ? `?control_run_id=${encodeURIComponent(controlRunId)}` : ''
  return request<TraceIndex>(`/api/runs/${encodeURIComponent(id)}/trace/index${params}`)
}

/** Inventario de archivos generados por la corrida. */
export const getArtifacts = (id: string) =>
  request<{ run_id: string; items: ArtifactEntry[]; complete?: boolean; notice?: string }>(
    `/api/runs/${encodeURIComponent(id)}/artifacts`,
  )

/** Corrida anterior comparable y variación de cada indicador. */
export const getRunComparison = (id: string) =>
  request<RunComparison>(`/api/runs/${encodeURIComponent(id)}/comparison`)

/** Nombres legibles de las condiciones de riesgo, desde el motor de reglas. */
export const getConditions = () => request<ConditionInfo[]>('/api/catalog/conditions')

/** Listado de corridas con filtro, orden y paginación del lado del servidor.
 *  El total viaja en la cabecera `X-Total-Count`, así que hace falta leer la
 *  respuesta cruda en vez de pasar por `request()`. */
export interface RunsQuery {
  vista?: EvidenceView
  estado?: string
  q?: string
  orden?: string
  direccion?: 'asc' | 'desc'
  pagina?: number
  pageSize?: number
  /** Sólo las corridas de esta clase (Task 7). */
  clase?: Clase
  /** Sólo las corridas que citan este resultado — así se piden las de un
   *  grupo al expandirlo (Task 7). */
  resultId?: string
}

export async function listRunsPaged(
  filtros: RunsQuery = {},
): Promise<{ items: RunRow[]; total: number; visibility?: EvidenceListingMeta }> {
  const params = new URLSearchParams()
  if (filtros.vista) params.set('vista', filtros.vista)
  if (filtros.estado) params.set('estado', filtros.estado)
  if (filtros.q) params.set('q', filtros.q)
  if (filtros.orden) params.set('orden', filtros.orden)
  if (filtros.direccion) params.set('direccion', filtros.direccion)
  if (filtros.pagina) params.set('pagina', String(filtros.pagina))
  if (filtros.pageSize) params.set('page_size', String(filtros.pageSize))
  if (filtros.clase) params.set('clase', filtros.clase)
  if (filtros.resultId) params.set('result_id', filtros.resultId)

  const response = await fetch(`/api/runs?${params.toString()}`, {
    headers: { 'Content-Type': 'application/json' },
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
  const items = (await response.json()) as RunRow[]
  // Sin la cabecera (proxy que la filtra, fixture vieja) se cae a la cantidad
  // de la página: es un total incorrecto pero acotado, mejor que romper.
  const total = Number(response.headers.get('X-Total-Count') ?? items.length)
  return { items, total: Number.isFinite(total) ? total : items.length,
    ...(response.headers.has('X-Evidence-Available') ? { visibility: evidenceMetadata(response) } : {}) }
}

/** Las corridas colapsadas por resultado (Task 7): la granularidad que hace
 *  legible la pantalla de Corridas, no el filtro de clase.
 *
 *  Los conteos por clase vienen en `X-Class-Counts` y NO se derivan sumando
 *  `n_runs` sobre los grupos: eso cuenta CITACIONES (una corrida citada por dos
 *  resultados está en los dos grupos), y daba 693 donde el filtro devuelve 412
 *  — un número mayor que el total de corridas. El servidor los calcula sobre
 *  corridas distintas, en el mismo handler.
 *
 *  Sin la cabecera (proxy que la filtra, fixture vieja) `conteos` queda
 *  `undefined`: la pantalla no dibuja chips, en vez de dibujar un número
 *  inventado. */
export async function listRunGroups(
  clase?: Clase,
): Promise<{ items: RunGroup[]; conteos?: Partial<Record<Clase, number>>; visibility?: EvidenceListingMeta }> {
  const response = await fetch(`/api/runs/grupos${clase ? `?${new URLSearchParams({ clase })}` : ''}`, {
    headers: { 'Content-Type': 'application/json' },
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
  const items = (await response.json()) as RunGroup[]
  return {
    items,
    conteos: parseClassCounts(response.headers.get('X-Class-Counts')),
    ...(response.headers.has('X-Evidence-Available') ? { visibility: evidenceMetadata(response) } : {}),
  }
}

/** `clave=n,clave=n,…` -> pares, descartando cualquiera que no matchee el
 *  formato (cabecera ausente, vacía, o corrupta en tránsito). Lo comparten
 *  `X-Platform-Test-Slugs` y `X-Class-Counts`. */
function parsePares(raw: string | null): Array<{ clave: string; n: number }> {
  if (!raw) return []
  return raw.split(',').map((par) => {
    const [clave, n] = par.split('=')
    return { clave, n: Number(n) }
  }).filter((p) => Boolean(p.clave) && Number.isFinite(p.n))
}

function parsePlatformTestSlugs(raw: string | null): PlatformTestSlug[] | undefined {
  const pares = parsePares(raw).map(({ clave, n }): PlatformTestSlug => ({ slug: clave, n }))
  return pares.length ? pares : undefined
}

const CLASES: readonly Clase[] = ['resultado', 'instrumento', 'ensayo', 'plataforma', 'sin_clasificar']

/** `X-Class-Counts` -> conteos por clase. Una clave que no es una clase del
 *  vocabulario se descarta: la pantalla no inventa una sexta clase porque la
 *  cabecera llegó con algo raro. */
function parseClassCounts(raw: string | null): Partial<Record<Clase, number>> | undefined {
  const pares = parsePares(raw).filter((p): p is { clave: Clase; n: number } =>
    (CLASES as readonly string[]).includes(p.clave))
  if (!pares.length) return undefined
  return Object.fromEntries(pares.map(({ clave, n }) => [clave, n]))
}

function evidenceMetadata(response: Response): EvidenceListingMeta {
  const available = response.headers.get('X-Evidence-Available')
  // Ausente se queda en `undefined` y no afirma nada: sólo un 'false' explícito
  // dispara la advertencia. La fixture del contrato congelado no manda ninguna
  // de las dos cabeceras.
  const clasificacion = response.headers.get('X-Clasificacion-Available')
  const count = (name: string) => {
    const value = response.headers.get(name)
    return value != null && Number.isFinite(Number(value)) ? Number(value) : undefined
  }
  // "N/M" y nada más: cualquier otra forma —ausente, vacía, un solo número,
  // texto— deja las DOS cifras en `undefined` y la pantalla no dice nada sobre
  // la cobertura de la clasificación. Nunca un 0 fabricado.
  const roles = (response.headers.get('X-Clasificacion-Roles') ?? '').split('/')
  const [sinClase, totalRoles] = roles.length === 2
    ? roles.map((v) => (v.trim() !== '' && Number.isFinite(Number(v)) ? Number(v) : undefined))
    : [undefined, undefined]
  return {
    available: available == null ? undefined : available === 'true',
    clasificacionAvailable: clasificacion == null ? undefined : clasificacion === 'true',
    rolesSinClasificar: totalRoles == null ? undefined : sinClase,
    rolesDelRegistro: sinClase == null ? undefined : totalRoles,
    archived: count('X-Archived-Count'),
    archivedExecutions: count('X-Archived-Executions-Count'),
    platformTestCount: count('X-Platform-Test-Count'),
    platformTestSlugs: parsePlatformTestSlugs(response.headers.get('X-Platform-Test-Slugs')),
    totalExecutions: count('X-Total-Executions-Count'),
  }
}

export const getTrace = (
  id: string,
  page = 1,
  pageSize = 50,
  controlRunId?: string,
  /** Filtra los cuadros ANTES de paginar: 'actividad' | 'alertas'. */
  solo?: string,
) => {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (controlRunId) params.set('control_run_id', controlRunId)
  if (solo) params.set('solo', solo)
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
