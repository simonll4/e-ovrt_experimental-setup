import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  ApiError, getDatasets, getExperiments, getIngestPlugins, getPromptSets,
  launchRun, saveManifest,
} from '../api'
import type {
  Composition, DatasetEntry, Experiment, FieldError, IngestPlugin, PromptSet,
} from '../types'
import { useTargetModelRef } from '../useTarget'
import { Card, ErrorBanner, Field } from '../components/ui'

export default function ComposePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [plugins, setPlugins] = useState<IngestPlugin[]>([])
  const [datasets, setDatasets] = useState<DatasetEntry[]>([])
  const [sets, setSets] = useState<PromptSet[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [plugin, setPlugin] = useState('image_folder')
  const [dataset, setDataset] = useState('')
  const [path, setPath] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  // `source.type` original del manifiesto prefilleado (video/video_frame/…): se
  // conserva para que guardar no lo colapse a video_file. null cuando la fuente
  // se arma desde cero o por dataset ref.
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [setId, setSetId] = useState('')
  const [activeIds, setActiveIds] = useState<string[]>([])
  const [stride, setStride] = useState('')
  const [maxUnits, setMaxUnits] = useState('')
  const [annotated, setAnnotated] = useState(false)
  const [manifestModelRef, setManifestModelRef] = useState<string | null>(null)
  const [confirmModel, setConfirmModel] = useState(false)
  const [errors, setErrors] = useState<FieldError[]>([])
  const [busyRunId, setBusyRunId] = useState<string | null>(null)
  const [saveName, setSaveName] = useState('')
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  const fieldError = (field: string): string | undefined => {
    const msg = errors.filter((e) => e.field === field).map((e) => e.message).join('; ')
    return msg || undefined
  }

  // Si el servicio se reinicia con otro EOVRT_MODEL_REF, `modelRef` cambia (poll de
  // useTargetModelRef) y re-fetcheamos los catálogos para no quedar con datos stale.
  const modelRef = useTargetModelRef()
  useEffect(() => {
    let alive = true
    getIngestPlugins().then((v) => alive && setPlugins(v)).catch(() => alive && setPlugins([]))
    getDatasets().then((v) => alive && setDatasets(v)).catch(() => alive && setDatasets([]))
    getPromptSets().then((v) => alive && setSets(v)).catch(() => alive && setSets([]))
    getExperiments().then((v) => alive && setExperiments(v)).catch(() => alive && setExperiments([]))
    return () => {
      alive = false
    }
  }, [modelRef])

  const selectedSet = useMemo(() => sets.find((s) => s.id === setId), [sets, setId])

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
    if (m.prompts?.ref) setSetId(m.prompts.ref)
    if (m.prompts?.active_ids) setActiveIds(m.prompts.active_ids)
    if (m.rate_control?.stride != null) setStride(String(m.rate_control.stride))
    if (m.run?.max_units != null) setMaxUnits(String(m.run.max_units))
    if (m.outputs?.save_annotated_video) setAnnotated(true)
    if (m.model?.ref) setManifestModelRef(m.model.ref)
  }, [params, experiments])

  const composition = (): Composition => ({
    ingest: {
      plugin,
      config:
        plugin === 'rtsp'
          ? (rtspUrl ? { url: rtspUrl } : {})
          : dataset ? { dataset } : path ? { path } : {},
      // Solo relevante para fuentes por `path` (video); rtsp deriva el type en el BFF.
      source_type: plugin === 'rtsp' ? null : dataset ? null : sourceType,
    },
    prompts: { set_id: setId, active_ids: activeIds },
    run: {
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
        const payload = (e.payload ?? {}) as { active_run_id?: string }
        setBusyRunId(payload.active_run_id ?? null)
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
  return (
    <div>
      <h2>Nueva corrida</h2>
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
      <Card title="Ingesta">
        <div>
          <Field label="Plugin de ingesta" error={fieldError('ingest.plugin')}>
            <select value={plugin} onChange={(e) => setPlugin(e.target.value)}>
              {plugins.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.enabled}>
                  {p.id}{!p.enabled ? ' (no soportado)' : ''}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {plugin === 'rtsp' ? (
          <div>
            <Field label="URL RTSP de la cámara" error={fieldError('ingest.config.url')}>
              <input placeholder="rtsp://usuario:clave@192.168.1.50:554/stream1" value={rtspUrl}
                     onChange={(e) => setRtspUrl(e.target.value)} />
            </Field>
            {rtspUrl.includes('***') && (
              <small className="eo-note eo-note--warn">Recompletá las credenciales antes de lanzar.</small>
            )}
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
      <Card title="Prompts">
        <div>
          <Field label="Prompt set" error={fieldError('prompts.set_id')}>
            <select
              value={setId}
              onChange={(e) => {
                const nextId = e.target.value
                setSetId(nextId)
                const found = sets.find((s) => s.id === nextId)
                setActiveIds(found ? found.classes.filter((c) => c.enabled_by_default).map((c) => c.id) : [])
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
      <Card title="Parámetros">
        <p className="eo-note">Overrides (thresholds: read-only del modelo, ver Catálogos)</p>
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
      </Card>
      {manifestModelRef && (
        <div>
          <small className="eo-note">El manifiesto declara modelo <b>{manifestModelRef}</b>.</small>
          {modelError && (
            <label className="eo-note eo-note--error">
              <input type="checkbox" checked={confirmModel}
                     onChange={(e) => setConfirmModel(e.target.checked)} />{' '}
              Usar el modelo del target de todas formas
            </label>
          )}
          {fieldError('model') && <small className="eo-field__error">{fieldError('model')}</small>}
        </div>
      )}
      {generalError && <ErrorBanner>{generalError}</ErrorBanner>}
      {busyRunId && (
        <p className="eo-note eo-note--warn">
          Ya hay un run activo: <a href={`#/runs/${busyRunId}`}>{busyRunId}</a>
        </p>
      )}
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
        <button onClick={submit}>Lanzar</button>
        <input placeholder="nombre_manifiesto" value={saveName}
               onChange={(e) => setSaveName(e.target.value)} />
        <button onClick={save} disabled={!saveName}>Guardar como manifiesto</button>
      </div>
      {saveMsg && <p><small>{saveMsg}</small></p>}
    </div>
  )
}
