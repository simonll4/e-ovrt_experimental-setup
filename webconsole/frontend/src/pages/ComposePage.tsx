import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, saveManifest } from '../api'
import { useLaunchRun } from '../api/queries/runs'
import type { Composition, FieldError } from '../types'
import { usePreflight, useTarget } from '../api/queries/platform'
import {
  useCatalogExperiments, useCatalogPromptSets, useDatasets, useIngestPlugins,
} from '../api/queries/catalog'
import { useCameras } from '../api/queries/cameras'
import PlatformStatus from '../components/PlatformStatus'
import {
  Badge, Button, Card, ErrorBanner, Field, IconCheck, IconCircle, IconInfo, IconPlay,
  PageHeader, Select,
} from '../components/ui'
import { sourceLabel } from '../runview'

/** Un requisito del panel *Antes de lanzar*: si está cumplido, y por qué. */
interface Paso {
  ok: boolean
  label: string
  sub: string
}

/** Círculo numerado del encabezado del paso; violeta cuando el paso se completó. */
function NumeroDePaso({ n, ok }: { n: number; ok?: boolean }) {
  return <span className={ok ? 'eo-step__num eo-step__num--on' : 'eo-step__num'}>{n}</span>
}

export default function ComposePage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [plugin, setPlugin] = useState('image_folder')
  const [dataset, setDataset] = useState('')
  const [path, setPath] = useState('')
  const [cameraId, setCameraId] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  // Cuadros a descartar al arrancar una fuente en vivo (asentamiento de
  // exposición/enfoque): solo válido en rtsp/oak_d, el motor de detección lo
  // rechaza (422) en fuentes acotadas. Vacío = no enviar el campo (default 0 del
  // lado del servicio, comportamiento previo).
  const [warmupFrames, setWarmupFrames] = useState('')
  // `source.type` original del manifiesto prefilleado (video/video_frame/…): se
  // conserva para que guardar no lo colapse a video_file. null cuando la fuente
  // se arma desde cero o por dataset ref.
  const [sourceType, setSourceType] = useState<string | null>(null)
  const [setId, setSetId] = useState('')
  const [activeIds, setActiveIds] = useState<string[]>([])
  // Nombre opcional de la corrida: si queda vacío, el servicio usa el
  // identificador autogenerado como siempre — esto es solo para reconocerla.
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

  // La instancia activa gatea el botón de lanzar: sin motor de detección listo
  // no se lanza.
  //
  // Los catálogos ya no se piden con un efecto keyado en `modelRef`: las queries
  // llevan la referencia del modelo en su clave, así que si el servicio reinicia
  // con otro modelo se recargan solas. Ver `api/queries/catalog.ts`.
  const target = useTarget()
  const preflight = usePreflight()
  const lanzamiento = useLaunchRun()
  const plugins = useIngestPlugins().data ?? []
  const datasets = useDatasets().data ?? []
  const sets = useCatalogPromptSets().data ?? []
  const experiments = useCatalogExperiments().data ?? []
  const cameras = useCameras().data ?? []

  const selectedSet = useMemo(() => sets.find((s) => s.id === setId), [sets, setId])
  // Fuente en vivo (cámara) vs acotada (conjunto/archivo): decide qué campos mostrar.
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
      // Cámara guardada primero; URL manual solo como fallback de rtsp. La cámara
      // guardada no trae warmup_frames (es un ajuste por corrida, no de la
      // cámara) — se agrega acá como override si el operador lo completó.
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
    if (missingReason !== null || lanzamiento.isPending) return
    setErrors([])
    setBusyRunId(null)
    setPreviewBusy(false)
    try {
      const { run_id } = await lanzamiento.mutateAsync(composition())
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
          ? 'elegí una cámara guardada o escribí la dirección RTSP (paso 1)'
          : 'elegí una cámara guardada (paso 1) — se crean en Cámaras'
      }
      // Los manifiestos guardados censuran la credencial RTSP como "***": esa
      // URL pasa la validación de shape pero muere adentro de la corrida.
      if (!selectedCamera && plugin === 'rtsp' && rtspUrl.includes('***')) {
        return 'recompletá las credenciales de la dirección RTSP (paso 1)'
      }
    } else if (!dataset && !path) {
      return 'elegí un conjunto del catálogo o escribí una ruta (paso 1)'
    }
    if (!setId) return 'elegí un conjunto de prompts (paso 2)'
    if (activeIds.length === 0) return 'activá al menos una clase del conjunto (paso 2)'
    return null
  })()

  // Los cuatro requisitos del panel lateral. Es la misma verdad que
  // `missingReason` pero desplegada: aquél dice qué arreglar primero, éste
  // muestra los cuatro a la vez para saber cuánto falta.
  const origen: Paso = isLive
    ? {
        ok: Boolean(selectedCamera || (plugin === 'rtsp' && rtspUrl && !rtspUrl.includes('***'))),
        label: 'Elegiste una cámara',
        sub: selectedCamera
          ? `Cámara guardada ${selectedCamera.name || selectedCamera.id}`
          : rtspUrl.includes('***')
            ? 'Recompletá el usuario y la clave de la dirección'
            : rtspUrl
              ? 'Dirección cargada a mano'
              : pluginCameras.length === 0
                ? 'No hay cámaras guardadas para esta fuente'
                : 'Sin elegir',
      }
    : {
        ok: Boolean(dataset || path),
        label: 'Elegiste un origen',
        sub: dataset
          ? `Conjunto ${dataset}`
          : path
            ? 'Ruta manual'
            : 'Ni conjunto del catálogo ni ruta',
      }

  const pasos: Paso[] = [
    {
      ok: Boolean(target?.healthy && target?.ready),
      label: 'El motor de detección está listo',
      sub: !target
        ? 'Verificando…'
        : !target.healthy
          ? 'No responde'
          : !target.ready
            ? 'Todavía está cargando el modelo'
            : `${target.model?.ref ?? 'modelo'} · modelo cargado`,
    },
    origen,
    {
      ok: Boolean(setId),
      label: 'Elegiste un conjunto de prompts',
      sub: selectedSet
        ? selectedSet.frozen
          ? 'Congelado, no se puede editar'
          : 'Editable'
        : 'Sin elegir',
    },
    {
      ok: activeIds.length > 0,
      label: 'Activaste al menos una clase',
      sub: activeIds.length
        ? `${activeIds.length} de ${selectedSet?.classes.length ?? 0} activas`
        : 'Ninguna activa',
    },
  ]

  const toggleClase = (id: string) =>
    setActiveIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]))

  return (
    <>
      <PageHeader
        title="Nueva corrida"
        meta="Elegí de dónde salen las imágenes y qué se busca en ellas"
      />

      <div className="eo-compose">
        <div className="eo-steps">
          <Card title={<><NumeroDePaso n={1} ok={origen.ok} />Fuente</>}>
            {/* Botones-tarjeta y no un desplegable: son cuatro opciones fijas y
                el motivo de una deshabilitada tiene que verse sin abrir nada. */}
            <div className="eo-srcgrid">
              {plugins.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className="eo-src"
                  aria-pressed={plugin === p.id}
                  disabled={!p.enabled}
                  onClick={() => {
                    setPlugin(p.id)
                    setCameraId('')
                  }}
                >
                  <b>{sourceLabel(p.id)}</b>
                  <span>
                    {p.enabled
                      ? p.description
                      : p.disabled_reason ?? 'No disponible en esta instancia'}
                  </span>
                </button>
              ))}
            </div>
            {fieldError('ingest.plugin') && (
              <p className="eo-field__error">{fieldError('ingest.plugin')}</p>
            )}

            {isLive ? (
              <>
                <Field label="Cámara" error={fieldError('ingest.config.url')}>
                  <Select
                    ariaLabel="Cámara"
                    value={cameraId}
                    placeholder={plugin === 'rtsp' ? 'Escribir la dirección a mano' : 'Elegir una cámara'}
                    options={[
                      {
                        value: '',
                        label: plugin === 'rtsp' ? 'Escribir la dirección a mano' : 'Elegir una cámara',
                      },
                      ...pluginCameras.map((c) => ({ value: c.id, label: c.name || c.id })),
                    ]}
                    onChange={setCameraId}
                  />
                </Field>
                {pluginCameras.length === 0 && (
                  <p className="eo-note">
                    No hay cámaras guardadas para esta fuente — se crean (y se prueban) en{' '}
                    <Link to="/cameras">Cámaras</Link>.
                  </p>
                )}
                {plugin === 'rtsp' && !selectedCamera && (
                  <>
                    <Field label="Dirección de la cámara">
                      <input

                        placeholder="rtsp://usuario:clave@192.168.1.50:554/stream1"
                        value={rtspUrl}
                        onChange={(e) => setRtspUrl(e.target.value)}
                      />
                    </Field>
                    {rtspUrl.includes('***') && (
                      <p className="eo-note eo-note--warn">
                        Los manifiestos guardados ocultan la contraseña. Recompletala antes de lanzar.
                      </p>
                    )}
                  </>
                )}
                <Field
                  label="Descartar los primeros cuadros (opcional)"
                  hint="La cámara tarda en asentar exposición y enfoque. A 10 cuadros por segundo, 20 son unos 2 s."
                >
                  <input

                    placeholder="20"
                    value={warmupFrames}
                    onChange={(e) => setWarmupFrames(e.target.value)}
                  />
                </Field>
              </>
            ) : (
              <>
                <Field label="Conjunto del catálogo" error={fieldError('ingest.config.dataset')}>
                  <Select
                    ariaLabel="Conjunto del catálogo"
                    value={dataset}
                    placeholder="Indicar una ruta a mano"
                    options={[
                      { value: '', label: 'Indicar una ruta a mano' },
                      ...datasets.map((d) => ({
                        value: d.id,
                        label: d.id,
                        disabled: !d.available,
                        disabledReason: d.available ? undefined : 'No montado',
                      })),
                    ]}
                    onChange={setDataset}
                  />
                </Field>
                {!dataset && (
                  <Field
                    label="Ruta en el disco"
                    hint="Una carpeta de imágenes o un archivo de video accesible desde el motor de detección."
                    error={fieldError('ingest.config.path')}
                  >
                    <input

                      placeholder="/ruta/a/las/imagenes"
                      value={path}
                      onChange={(e) => setPath(e.target.value)}
                    />
                  </Field>
                )}
              </>
            )}
          </Card>

          <Card
            title={<><NumeroDePaso n={2} ok={Boolean(setId) && activeIds.length > 0} />Qué buscar</>}
            meta={
              selectedSet ? (
                <Badge tone="neutral">{selectedSet.frozen ? 'Congelado' : 'Editable'}</Badge>
              ) : undefined
            }
          >
            <Field label="Conjunto de prompts" error={fieldError('prompts.set_id')}>
              <Select
                ariaLabel="Conjunto de prompts"
                value={setId}
                placeholder="Elegir un conjunto"
                options={sets.map((s) => ({
                  value: s.id,
                  label: s.frozen ? `${s.id} — congelado` : s.id,
                }))}
                onChange={(nextId) => {
                  setSetId(nextId)
                  const found = sets.find((s) => s.id === nextId)
                  setActiveIds(
                    found
                      ? found.classes.filter((c) => c.enabled_by_default !== false).map((c) => c.id)
                      : [],
                  )
                }}
              />
            </Field>
            {selectedSet ? (
              <>
                <div className="eo-clsw">
                  {selectedSet.classes.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className="eo-cls"
                      aria-pressed={activeIds.includes(c.id)}
                      onClick={() => toggleClase(c.id)}
                    >
                      {c.id}
                    </button>
                  ))}
                </div>
                <p className="eo-cap">
                  Las clases desactivadas no se buscan en las imágenes. Los nombres vienen del
                  archivo del conjunto.
                </p>
              </>
            ) : (
              <p className="eo-empty">Elegí un conjunto para ver sus clases.</p>
            )}
            {fieldError('prompts.active_ids') && (
              <p className="eo-field__error">{fieldError('prompts.active_ids')}</p>
            )}
          </Card>

          <Card title={<><NumeroDePaso n={3} />Identificación</>}>
            <Field
              label="Nombre de la corrida (opcional)"
              hint="Si lo dejás vacío se usa el identificador generado automáticamente."
            >
              <input

                placeholder="prueba OAK-D laboratorio"
                value={runName}
                onChange={(e) => setRunName(e.target.value)}
              />
            </Field>

            {manifestModelRef && (
              <>
                <p className="eo-note">
                  El manifiesto declara el modelo <b className="eo-mono">{manifestModelRef}</b>.
                </p>
                {modelError && (
                  <label className="eo-note eo-note--error">
                    <input
                      type="checkbox"
                      checked={confirmModel}
                      onChange={(e) => setConfirmModel(e.target.checked)}
                    />{' '}
                    Usar el modelo de la instancia activa de todas formas
                  </label>
                )}
                {fieldError('model') && (
                  <p className="eo-field__error">{fieldError('model')}</p>
                )}
              </>
            )}

            <details className="eo-adv">
              <summary>Opciones avanzadas</summary>
              <div className="eo-adv__body">
                <p className="eo-note">
                  Los umbrales son fijos por instancia: se ven en Catálogos.
                </p>
                <Field label="Partir de un manifiesto">
                  <Select
                    ariaLabel="Partir de un manifiesto"
                    value={params.get('from') ?? ''}
                    placeholder="Desde cero"
                    options={[
                      { value: '', label: 'Desde cero' },
                      ...experiments.map((x) => ({
                        value: x.id,
                        label: x.group ? `[${x.group}] ${x.id}` : x.id,
                      })),
                    ]}
                    onChange={(v) =>
                      navigate(v ? `/compose?from=${encodeURIComponent(v)}` : '/compose')
                    }
                  />
                </Field>
                <Field label="Procesar uno de cada N cuadros" error={fieldError('run.stride')}>
                  <input

                    placeholder="1"
                    value={stride}
                    onChange={(e) => setStride(e.target.value)}
                  />
                </Field>
                <Field label="Máximo de unidades a procesar" error={fieldError('run.max_units')}>
                  <input

                    placeholder="Sin límite"
                    value={maxUnits}
                    onChange={(e) => setMaxUnits(e.target.value)}
                  />
                </Field>
                <label>
                  <input
                    type="checkbox"
                    checked={annotated}
                    onChange={(e) => setAnnotated(e.target.checked)}
                  />{' '}
                  Guardar el video con las detecciones dibujadas
                </label>
                <Field label="Guardar esta configuración como manifiesto">
                  <span className="eo-inputrow">
                    <input

                      placeholder="perimetro_nocturno"
                      value={saveName}
                      onChange={(e) => setSaveName(e.target.value)}
                    />
                    <Button onClick={save} disabled={!saveName}>
                      Guardar
                    </Button>
                  </span>
                </Field>
                {saveMsg && <p className="eo-note">{saveMsg}</p>}
              </div>
            </details>
          </Card>
        </div>

        <aside className="eo-rail">
          <Card title="Antes de lanzar" flush>
            {pasos.map((p) => (
              <div key={p.label} className={p.ok ? 'eo-chk' : 'eo-chk eo-chk--no'}>
                <span className="eo-chk__mark">{p.ok ? <IconCheck /> : <IconCircle />}</span>
                <span className="eo-chk__text">
                  <b>{p.label}</b>
                  <span>{p.sub}</span>
                </span>
              </div>
            ))}
            <div className="eo-launch">
              <Button variant="primary" onClick={submit} disabled={missingReason !== null || lanzamiento.isPending}>
                <IconPlay />
                Lanzar corrida
              </Button>
              <span className="eo-launch__why">
                {missingReason
                  ? `Falta: ${missingReason}`
                  : 'Todo listo. La corrida arranca en cuanto confirmes.'}
              </span>
            </div>
          </Card>

          {generalError && <ErrorBanner>{generalError}</ErrorBanner>}

          {busyRunId && (
            <p className="eo-note eo-note--warn">
              Ya hay una corrida activa: <Link to={`/runs/${busyRunId}`}>{busyRunId}</Link>
            </p>
          )}
          {previewBusy && (
            <p className="eo-note eo-note--warn">
              Hay una prueba de cámara activa. Cerrala en <Link to="/cameras">Cámaras</Link> para
              lanzar la corrida.
            </p>
          )}

          <PlatformStatus status={preflight} />

          <p className="eo-note eo-note--icon">
            <IconInfo />
            <span>
              Las fuentes en vivo generan corridas que no terminan solas: se detienen a mano desde
              el detalle.
            </span>
          </p>
        </aside>
      </div>
    </>
  )
}
