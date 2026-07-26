import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ApiError, getDatasets, getExperiments, getIngestPlugins, getPromptSets,
  launchRun, listCameras, saveManifest,
} from '../api'
import type {
  CameraPreset, Composition, DatasetEntry, Experiment, FieldError, IngestPlugin, PromptSet,
} from '../types'
import { useTarget } from '../useTarget'
import { usePreflight } from '../usePreflight'
import PlatformStatus from '../components/PlatformStatus'
import { Button, Card, ErrorBanner, Field } from '../components/ui'

export default function ComposePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [plugins, setPlugins] = useState<IngestPlugin[]>([])
  const [datasets, setDatasets] = useState<DatasetEntry[]>([])
  const [cameras, setCameras] = useState<CameraPreset[]>([])
  const [sets, setSets] = useState<PromptSet[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [plugin, setPlugin] = useState('image_folder')
  const [dataset, setDataset] = useState('')
  const [path, setPath] = useState('')
  const [cameraId, setCameraId] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  // Frames a descartar al arrancar una fuente en vivo (asentamiento de
  // exposición/enfoque): solo válido en rtsp/oak_d, el media-plane lo rechaza
  // (422) en fuentes acotadas. Vacío = no enviar el campo (default 0 del lado
  // del servicio, comportamiento previo).
  const [warmupFrames, setWarmupFrames] = useState('')
  // `source.type` original del manifiesto prefilleado (video/video_frame/…): se
  // conserva para que guardar no lo colapse a video_file. null cuando la fuente
  // se arma desde cero o por dataset ref.
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [setId, setSetId] = useState('')
  const [activeIds, setActiveIds] = useState<string[]>([])
  // Nombre opcional del run: si queda vacío, el servicio usa el run_id
  // autogenerado como siempre — esto es puramente para identificarlo mejor.
  const [runName, setRunName] = useState('')
  const [stride, setStride] = useState('')
  const [maxUnits, setMaxUnits] = useState('')
  const [annotated, setAnnotated] = useState(false)
  const [manifestModelRef, setManifestModelRef] = useState<string | null>(null)
  const [confirmModel, setConfirmModel] = useState(false)
  const [errors, setErrors] = useState<FieldError[]>([])
  const [busyRunId, setBusyRunId] = useState<string | null>(null)
  const [previewBusy, setPreviewBusy] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  const fieldError = (field: string): string | undefined => {
    const msg = errors.filter((e) => e.field === field).map((e) => e.message).join('; ')
    return msg || undefined
  }

  // Si el servicio se reinicia con otro EOVRT_MODEL_REF, `modelRef` cambia (poll de
  // useTarget) y re-fetcheamos los catálogos para no quedar con datos stale. El
  // target completo además gatea el botón Lanzar: sin media-plane listo no se lanza.
  const target = useTarget()
  const modelRef = target?.model?.ref
  const preflight = usePreflight()
  useEffect(() => {
    let alive = true
    getIngestPlugins().then((v) => alive && setPlugins(v)).catch(() => alive && setPlugins([]))
    getDatasets().then((v) => alive && setDatasets(v)).catch(() => alive && setDatasets([]))
    getPromptSets().then((v) => alive && setSets(v)).catch(() => alive && setSets([]))
    getExperiments().then((v) => alive && setExperiments(v)).catch(() => alive && setExperiments([]))
    listCameras().then((v) => alive && setCameras(v)).catch(() => alive && setCameras([]))
    return () => {
      alive = false
    }
  }, [modelRef])

  const selectedSet = useMemo(() => sets.find((s) => s.id === setId), [sets, setId])
  // Fuente en vivo (cámara) vs acotada (dataset/archivo): decide qué campos mostrar.
  const isLive = plugins.find((p) => p.id === plugin)?.kind === 'live'
  const pluginCameras = useMemo(
    () => cameras.filter((c) => c.plugin === plugin),
    [cameras, plugin],
  )
  const selectedCamera = useMemo(
    () => pluginCameras.find((c) => c.id === cameraId),
    [pluginCameras, cameraId],
  )

  // Prefill desde manifiesto (?from=<experiment_id>) — la traducción canónica vive en el
  // BFF; acá solo mapeamos el manifiesto crudo a los campos del form (mismo mapeo §5.4).
  //
  // Idempotente por valor de `from`: el re-fetch de catálogos keyado en `modelRef` (más
  // arriba) llama a getExperiments() y produce un array `experiments` con referencia
  // nueva aunque el contenido no cambie. Sin este guard, ese cambio de referencia
  // re-dispara este efecto y reaplica los valores del manifiesto, pisando cualquier
  // edición manual que el usuario haya hecho en el form. `lastPrefilledFrom` recuerda
  // qué `from` ya fue prefilleado para no repetir el trabajo.
  const lastPrefilledFrom = useRef<string | null>(null)
  useEffect(() => {
    const from = params.get('from')
    if (!from) {
      lastPrefilledFrom.current = null
      return
    }
    if (from === lastPrefilledFrom.current) return
    const exp = experiments.find((e) => e.id === from)
    if (!exp) return // experiments aún no cargó; reintentar cuando llegue (dep abajo)
    lastPrefilledFrom.current = from
    const m = exp.manifest as Record<string, any>
    const source = m.source ?? {}
    if (source.ref) {
      setPlugin('image_folder')
      setDataset(source.ref)
      setSourceType(null)
    } else if (source.type) {
      setPlugin(source.type.includes('video') ? 'video_file' : source.type)
      setPath(source.path ?? '')
      setRtspUrl(source.type === 'rtsp' ? (source.url ?? '') : '')
      setSourceType(source.type) // preserva el string exacto para el round-trip
    }
    if (source.warmup_frames != null) setWarmupFrames(String(source.warmup_frames))
    if (m.prompts?.ref) setSetId(m.prompts.ref)
    if (m.prompts?.active_ids) setActiveIds(m.prompts.active_ids)
    if (m.run?.name) setRunName(m.run.name)
    if (m.rate_control?.stride != null) setStride(String(m.rate_control.stride))
    if (m.run?.max_units != null) setMaxUnits(String(m.run.max_units))
    if (m.outputs?.save_annotated_video) setAnnotated(true)
    if (m.model?.ref) setManifestModelRef(m.model.ref)
  }, [params, experiments])

  const ingestConfig = (): Record<string, unknown> => {
    if (isLive) {
      // Cámara guardada primero; URL manual solo como fallback de rtsp. El preset
      // no trae warmup_frames (es un ajuste por-run, no de la cámara) — se agrega
      // acá como override si el operador lo completó.
      const base: Record<string, unknown> = selectedCamera
        ? { ...selectedCamera.config }
        : (plugin === 'rtsp' && rtspUrl ? { url: rtspUrl } : {})
      if (warmupFrames) base.warmup_frames = Number(warmupFrames)
      return base
    }
    return dataset ? { dataset } : path ? { path } : {}
  }

  const composition = (): Composition => ({
    ingest: {
      plugin,
      config: ingestConfig(),
      // Solo relevante para fuentes por `path` (video); rtsp deriva el type en el BFF.
      source_type: isLive ? null : dataset ? null : sourceType,
    },
    prompts: { set_id: setId, active_ids: activeIds },
    run: {
      name: runName || null,
      stride: stride ? Number(stride) : null,
      max_units: maxUnits ? Number(maxUnits) : null,
      save_annotated_video: annotated,
    },
    manifest_model_ref: manifestModelRef,
    confirm_target_model: confirmModel,
  })

  const submit = async () => {
    setErrors([])
    setBusyRunId(null)
    setPreviewBusy(false)
    try {
      const { run_id } = await launchRun(composition())
      navigate(`/runs/${run_id}`)
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const payload = (e.payload ?? {}) as { errors?: FieldError[]; detail?: string }
        setErrors(
          payload.errors ?? [{ field: '_service', message: String(payload.detail ?? 'Error del servicio') }],
        )
      } else if (e instanceof ApiError && e.status === 409) {
        const payload = (e.payload ?? {}) as { active_run_id?: string; reason?: string }
        if (payload.reason === 'preview_active') {
          setPreviewBusy(true)
          setBusyRunId(null)
        } else {
          setBusyRunId(payload.active_run_id ?? null)
          setPreviewBusy(false)
        }
      } else {
        setErrors([{ field: '_target', message: String(e) }])
      }
    }
  }

  const save = async () => {
    setSaveMsg(null)
    try {
      const { path: saved } = await saveManifest({ name: saveName, composition: composition() })
      setSaveMsg(`Guardado en experiments/${saved}`)
    } catch (e) {
      setSaveMsg(`Error: ${e instanceof ApiError ? JSON.stringify(e.payload) : String(e)}`)
    }
  }

  const modelError = errors.some((e) => e.field === 'model')
  const generalError = fieldError('_target') ?? fieldError('_service')

  // Checklist de lanzamiento: una sola razón a la vez, en orden de arreglo.
  // El botón queda deshabilitado hasta que no falte nada — así el 422 del
  // servicio queda solo para casos que el form no puede anticipar.
  const missingReason = ((): string | null => {
    if (!target) return 'verificando el motor de detección…'
    if (!target.healthy) return 'el motor de detección no responde'
    if (!target.ready) return 'el motor de detección no terminó de cargar el modelo'
    if (isLive) {
      if (!selectedCamera && !(plugin === 'rtsp' && rtspUrl)) {
        return plugin === 'rtsp'
          ? 'elegí una cámara guardada o ingresá la URL RTSP (paso 1)'
          : 'elegí una cámara guardada (paso 1) — se crean en Cámaras'
      }
      // Los manifiestos guardados censuran la credencial RTSP como "***": esa
      // URL pasa la validación de shape pero muere adentro del run. Bloquear acá.
      if (!selectedCamera && plugin === 'rtsp' && rtspUrl.includes('***')) {
        return 'recompletá las credenciales de la URL RTSP (paso 1)'
      }
    } else if (!dataset && !path) {
      return 'elegí un dataset o ingresá una ruta (paso 1)'
    }
    if (!setId) return 'elegí un conjunto de prompts (paso 2)'
    if (activeIds.length === 0) return 'activá al menos una clase del conjunto de prompts (paso 2)'
    return null
  })()

  return (
    <div>
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
        <h2>Nueva corrida</h2>
        <PlatformStatus status={preflight} />
      </div>
      <Card title="1 · Fuente">
        <div>
          <Field label="Tipo de fuente" error={fieldError('ingest.plugin')}>
            <select
              value={plugin}
              onChange={(e) => {
                setPlugin(e.target.value)
                setCameraId('')
              }}
            >
              {plugins.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.enabled}>
                  {p.id}{!p.enabled ? ' (no soportado)' : ''}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {isLive ? (
          <div>
            <Field label="Cámara guardada" error={fieldError('ingest.config.url')}>
              <select value={cameraId} onChange={(e) => setCameraId(e.target.value)}>
                <option value="">
                  {plugin === 'rtsp' ? '— URL manual —' : '— elegir cámara —'}
                </option>
                {pluginCameras.map((c) => (
                  <option key={c.id} value={c.id}>{c.name || c.id}</option>
                ))}
              </select>
            </Field>
            {pluginCameras.length === 0 && (
              <small className="eo-note">
                No hay cámaras de tipo {plugin} guardadas — se crean (y se prueban) en{' '}
                <a href="#/cameras">Cámaras</a>.
              </small>
            )}
            {plugin === 'rtsp' && !selectedCamera && (
              <>
                <Field label="URL RTSP de la cámara">
                  <input placeholder="rtsp://usuario:clave@192.168.1.50:554/stream1" value={rtspUrl}
                         onChange={(e) => setRtspUrl(e.target.value)} />
                </Field>
                {rtspUrl.includes('***') && (
                  <small className="eo-note eo-note--warn">Recompletá las credenciales antes de lanzar.</small>
                )}
              </>
            )}
            <Field
              label="Descartar cuadros iniciales (opcional)"
              hint="La cámara tarda en asentar exposición/enfoque al arrancar — los primeros cuadros salen mal. ~20 a 10 cuadros por segundo ≈ 2 s."
            >
              <input placeholder="ej. 20" value={warmupFrames}
                     onChange={(e) => setWarmupFrames(e.target.value)} />
            </Field>
          </div>
        ) : (
          <div>
            <Field label="Dataset del catálogo (o dejar vacío y dar un path)" error={fieldError('ingest.config.dataset')}>
              <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
                <option value="">— path manual —</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id} disabled={!d.available}>
                    {d.id}{!d.available ? ' (no montado)' : ''}
                  </option>
                ))}
              </select>
            </Field>
            {!dataset && (
              <Field label="Ruta manual" hint="/ruta/a/imagenes o /ruta/video.mp4" error={fieldError('ingest.config.path')}>
                <input placeholder="/ruta/a/imagenes o /ruta/video.mp4" value={path}
                       onChange={(e) => setPath(e.target.value)} />
              </Field>
            )}
          </div>
        )}
      </Card>
      <Card title="2 · Prompts">
        <div>
          <Field label="Conjunto de prompts" error={fieldError('prompts.set_id')}>
            <select
              value={setId}
              onChange={(e) => {
                const nextId = e.target.value
                setSetId(nextId)
                const found = sets.find((s) => s.id === nextId)
                setActiveIds(found ? found.classes.filter((c) => c.enabled_by_default !== false).map((c) => c.id) : [])
              }}
            >
              <option value="">— elegir —</option>
              {sets.map((s) => (
                <option key={s.id} value={s.id}>{s.id}{s.frozen ? ' ❄' : ''}</option>
              ))}
            </select>
          </Field>
          {selectedSet && (
            <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
              {selectedSet.classes.map((c) => (
                <label key={c.id}>
                  <input
                    type="checkbox"
                    checked={activeIds.includes(c.id)}
                    onChange={(e) =>
                      setActiveIds((prev) =>
                        e.target.checked ? [...prev, c.id] : prev.filter((i) => i !== c.id),
                      )
                    }
                  />{' '}
                  {c.id}
                </label>
              ))}
            </div>
          )}
          {fieldError('prompts.active_ids') && (
            <small className="eo-field__error">{fieldError('prompts.active_ids')}</small>
          )}
        </div>
      </Card>
      <Card title="3 · Lanzar">
        <Field label="Nombre de la corrida (opcional)" hint="Si lo dejás vacío se usa el id autogenerado.">
          <input placeholder="ej. prueba OAK-D laboratorio" value={runName}
                 onChange={(e) => setRunName(e.target.value)} />
        </Field>
        {manifestModelRef && (
          <div>
            <small className="eo-note">El manifiesto declara modelo <b>{manifestModelRef}</b>.</small>
            {modelError && (
              <label className="eo-note eo-note--error">
                <input type="checkbox" checked={confirmModel}
                       onChange={(e) => setConfirmModel(e.target.checked)} />{' '}
                Usar el modelo de la instancia activa de todas formas
              </label>
            )}
            {fieldError('model') && <small className="eo-field__error">{fieldError('model')}</small>}
          </div>
        )}
        {generalError && <ErrorBanner>{generalError}</ErrorBanner>}
        {busyRunId && (
          <p className="eo-note eo-note--warn">
            Ya hay una corrida activa: <a href={`#/runs/${busyRunId}`}>{busyRunId}</a>
          </p>
        )}
        {previewBusy && (
          <p className="eo-note eo-note--warn">
            Hay una prueba de cámara activa. Cerrala en <a href="#/cameras">Cámaras</a> para lanzar la corrida.
          </p>
        )}
        {missingReason && (
          <p className="eo-note eo-note--warn">Para lanzar: {missingReason}.</p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
          <Button variant="primary" onClick={submit} disabled={missingReason !== null}>Lanzar</Button>
        </div>
        <details>
          <summary>Opciones avanzadas</summary>
          <p className="eo-note">Ajustes. Los umbrales del modelo son de solo lectura: se ven en Catálogos.</p>
          <div>
            <Field label="Partir de un manifiesto">
              <select
                value={params.get('from') ?? ''}
                onChange={(e) => navigate(`/compose?from=${encodeURIComponent(e.target.value)}`)}
              >
                <option value="">— desde cero —</option>
                {experiments.map((x) => (
                  <option key={x.id} value={x.id}>{x.group ? `[${x.group}] ` : ''}{x.id}</option>
                ))}
              </select>
            </Field>
          </div>
          <div>
            <Field label="stride (opcional)" error={fieldError('run.stride')}>
              <input value={stride} onChange={(e) => setStride(e.target.value)} />
            </Field>
          </div>
          <div>
            <Field label="max_units (opcional)" error={fieldError('run.max_units')}>
              <input value={maxUnits} onChange={(e) => setMaxUnits(e.target.value)} />
            </Field>
          </div>
          <label>
            <input type="checkbox" checked={annotated} onChange={(e) => setAnnotated(e.target.checked)} />{' '}
            save_annotated_video
          </label>
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            <input placeholder="nombre_manifiesto" value={saveName}
                   onChange={(e) => setSaveName(e.target.value)} />
            <Button variant="secondary" onClick={save} disabled={!saveName}>Guardar como manifiesto</Button>
          </div>
          {saveMsg && <p><small>{saveMsg}</small></p>}
        </details>
      </Card>
    </div>
  )
}
