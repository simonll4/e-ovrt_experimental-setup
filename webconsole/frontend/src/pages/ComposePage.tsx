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
import type { PlaneStatus } from '../types'
import {
  Button, Card, Disclosure, ErrorBanner, Field, IconCheck, IconCircle, IconInfo, IconPlay,
  IconWarn, LoadingState, PageHeader, Select, Tag, TextInput,
} from '../components/ui'
import { sourceLabel } from '../runview'

/** Un requisito del panel *Antes de lanzar*: si está cumplido, y por qué.
 *  `corto` es cómo se nombra en el resumen de pendientes de una columna. */
interface Paso {
  ok: boolean
  label: string
  sub: string
  corto: string
}

/** El motor de reglas no bloquea una corrida de medios: se muestra como una
 *  verificación informativa, con el mismo rótulo que usa el resto de la
 *  consola para ese estado. */
function estadoDelPlano(p: PlaneStatus): string {
  if (!p.healthy) return 'sin respuesta'
  return p.ready ? 'operativo' : 'no listo'
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
  const [saving, setSaving] = useState(false)

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
  // Cada catálogo conserva su consulta: una lista vacía mientras carga, o
  // porque falló, no es lo mismo que una lista vacía de verdad.
  const pluginsQ = useIngestPlugins()
  const datasetsQ = useDatasets()
  const setsQ = useCatalogPromptSets()
  const experimentsQ = useCatalogExperiments()
  const camerasQ = useCameras()
  const plugins = pluginsQ.data ?? []
  const datasets = datasetsQ.data ?? []
  const sets = setsQ.data ?? []
  const experiments = experimentsQ.data ?? []
  const cameras = camerasQ.data ?? []

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
    // Un solo guardado a la vez: el doble click no escribe dos veces.
    if (saving || !saveName) return
    setSaveMsg(null)
    setSaving(true)
    try {
      const { path: saved } = await saveManifest({ name: saveName, composition: composition() })
      setSaveMsg(`Guardado en experiments/${saved}`)
    } catch (e) {
      setSaveMsg(`Error: ${e instanceof ApiError ? JSON.stringify(e.payload) : String(e)}`)
    } finally {
      setSaving(false)
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
        corto: 'cámara',
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
        corto: 'origen de las imágenes',
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
      corto: 'motor de detección',
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
      corto: 'conjunto de prompts',
      sub: selectedSet
        ? selectedSet.frozen
          ? 'Congelado, no se puede editar'
          : 'Editable'
        : 'Sin elegir',
    },
    {
      ok: activeIds.length > 0,
      label: 'Activaste al menos una clase',
      corto: 'clases activas',
      sub: activeIds.length
        ? `${activeIds.length} de ${selectedSet?.classes.length ?? 0} activas`
        : 'Ninguna activa',
    },
  ]

  const toggleClase = (id: string) =>
    setActiveIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]))

  const pendientes = pasos.filter((p) => !p.ok)

  /** Estado de una consulta de catálogo dentro de su paso: espera y fallo se
   *  dicen, en vez de mostrar una lista vacía. */
  const estadoCatalogo = (
    q: { isPending: boolean; error: unknown; data: unknown; isFetching: boolean; refetch: () => unknown },
    que: string,
  ) => {
    if (q.isPending && !q.data) return <LoadingState lines={1} inline>Cargando {que}…</LoadingState>
    if (q.error && !q.data) {
      return (
        <ErrorBanner detail={String(q.error)} onRetry={() => void q.refetch()} retrying={q.isFetching}>
          No se pudo leer {que}.
        </ErrorBanner>
      )
    }
    return null
  }

  return (
    <>
      <PageHeader
        title="Nueva corrida"
        meta="Elegí de dónde salen las imágenes y qué se busca en ellas"
      />

      {/* En una columna el panel de verificación queda después del formulario:
          esto adelanta qué falta y lleva al panel completo. Con dos columnas el
          panel está a la vista y el CSS esconde este resumen. */}
      {pendientes.length > 0 && (
        <div className="eo-compose__pending">
          <IconWarn />
          <span>
            <b>Pendiente para lanzar ({pendientes.length} de {pasos.length}):</b>{' '}
            {pendientes.map((p) => p.corto).join(', ')}.
          </span>
          <a href="#antes-de-lanzar" onClick={(e) => {
            // HashRouter usa el fragmento para rutas: se desplaza a mano.
            e.preventDefault()
            const destino = document.getElementById('antes-de-lanzar')
            destino?.scrollIntoView?.({ block: 'start' })
            destino?.focus()
          }}>Ver la verificación completa</a>
        </div>
      )}

      <div className="eo-compose">
        <div className="eo-compose__form">
          <Card title={<><NumeroDePaso n={1} ok={origen.ok} />Fuente</>}>
            {/* Botones-tarjeta y no un desplegable: son cuatro opciones fijas y
                el motivo de una deshabilitada tiene que verse sin abrir nada. */}
            {estadoCatalogo(pluginsQ, 'las fuentes de esta instancia')}
            {plugins.length > 0 && (
              <div className="eo-srcgrid" role="group" aria-label="Fuente de las imágenes">
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
            )}
            {fieldError('ingest.plugin') && (
              <p className="eo-field__error">{fieldError('ingest.plugin')}</p>
            )}

            {isLive ? (
              <>
                {estadoCatalogo(camerasQ, 'las cámaras guardadas')}
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
                {camerasQ.data && pluginCameras.length === 0 && (
                  <p className="eo-note">
                    No hay cámaras guardadas para esta fuente — se crean (y se prueban) en{' '}
                    <Link to="/cameras">Cámaras</Link>.
                  </p>
                )}
                {plugin === 'rtsp' && !selectedCamera && (
                  <>
                    <Field label="Dirección de la cámara">
                      <TextInput
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
                  <TextInput
                    inputMode="numeric"
                    placeholder="20"
                    value={warmupFrames}
                    onChange={(e) => setWarmupFrames(e.target.value)}
                  />
                </Field>
              </>
            ) : (
              <>
                {estadoCatalogo(datasetsQ, 'los conjuntos del catálogo')}
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
                    <TextInput
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
                <Tag>{selectedSet.frozen ? 'Congelado' : 'Editable'}</Tag>
              ) : undefined
            }
          >
            {estadoCatalogo(setsQ, 'los conjuntos de prompts')}
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
                <div className="eo-clsw" role="group" aria-label="Clases a buscar">
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
              <p className="eo-note">Elegí un conjunto para ver sus clases.</p>
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
              <TextInput
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
                  <label className="eo-check eo-note--error">
                    <input
                      type="checkbox"
                      checked={confirmModel}
                      onChange={(e) => setConfirmModel(e.target.checked)}
                    />
                    Usar el modelo de la instancia activa de todas formas
                  </label>
                )}
                {fieldError('model') && (
                  <p className="eo-field__error">{fieldError('model')}</p>
                )}
              </>
            )}

            <Disclosure summary="Opciones avanzadas">
              <p className="eo-note">
                Los umbrales son fijos por instancia: se ven en <Link to="/catalog">Catálogos</Link>.
              </p>
              {estadoCatalogo(experimentsQ, 'los manifiestos')}
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
              <div className="eo-fieldgrid">
                <Field label="Procesar uno de cada N cuadros" error={fieldError('run.stride')}>
                  <TextInput
                    inputMode="numeric"
                    placeholder="1"
                    value={stride}
                    onChange={(e) => setStride(e.target.value)}
                  />
                </Field>
                <Field label="Máximo de unidades a procesar" error={fieldError('run.max_units')}>
                  <TextInput
                    inputMode="numeric"
                    placeholder="Sin límite"
                    value={maxUnits}
                    onChange={(e) => setMaxUnits(e.target.value)}
                  />
                </Field>
              </div>
              <label className="eo-check">
                <input
                  type="checkbox"
                  checked={annotated}
                  onChange={(e) => setAnnotated(e.target.checked)}
                />
                Guardar el video con las detecciones dibujadas
              </label>
              <Field label="Guardar esta configuración como manifiesto">
                <span className="eo-inputrow">
                  <TextInput
                    placeholder="perimetro_nocturno"
                    value={saveName}
                    onChange={(e) => setSaveName(e.target.value)}
                  />
                  <Button onClick={() => void save()} disabled={!saveName || saving} aria-busy={saving || undefined}>
                    {saving ? 'Guardando…' : 'Guardar'}
                  </Button>
                </span>
              </Field>
              {saveMsg && <p className="eo-note" role="status">{saveMsg}</p>}
            </Disclosure>
          </Card>
        </div>

        <aside className="eo-rail" aria-label="Verificación antes de lanzar">
          <section className="eo-card" id="antes-de-lanzar" tabIndex={-1}>
            <header className="eo-card__head">
              <h2 className="eo-card__title">Antes de lanzar</h2>
              <div className="eo-card__meta">
                {pendientes.length ? `${pendientes.length} pendiente${pendientes.length > 1 ? 's' : ''}` : 'Todo cumplido'}
              </div>
            </header>
            {pasos.map((p) => (
              <div key={p.label} className={p.ok ? 'eo-chk' : 'eo-chk eo-chk--no'}>
                <span className="eo-chk__mark" aria-hidden="true">{p.ok ? <IconCheck /> : <IconCircle />}</span>
                <span className="eo-chk__text">
                  <b>
                    <span className="eo-sr">{p.ok ? 'Cumplido: ' : 'Pendiente: '}</span>
                    {p.label}
                  </b>
                  <span>{p.sub}</span>
                </span>
              </div>
            ))}
            {/* El motor de reglas se verifica pero no bloquea: una corrida de
                medios no lo necesita. Lo que sí lo necesita es un experimento,
                y ese bloqueo vive en Experimentos. */}
            <p className="eo-chk__group">Servicios (informativo)</p>
            {preflight ? (
              <div className={preflight.control.healthy && preflight.control.ready ? 'eo-chk' : 'eo-chk eo-chk--info'}>
                <span className="eo-chk__mark" aria-hidden="true">
                  {preflight.control.healthy && preflight.control.ready ? <IconCheck /> : <IconWarn />}
                </span>
                <span className="eo-chk__text">
                  <b>Motor de reglas {estadoDelPlano(preflight.control)}</b>
                  <span>No bloquea esta corrida: la evaluación de reglas sólo hace falta en un experimento.</span>
                </span>
              </div>
            ) : (
              <div className="eo-chk eo-chk--no">
                <span className="eo-chk__mark" aria-hidden="true"><IconCircle /></span>
                <span className="eo-chk__text"><b>Verificando servicios…</b></span>
              </div>
            )}
            <div className="eo-launch">
              <Button
                variant="primary"
                onClick={submit}
                disabled={missingReason !== null || lanzamiento.isPending}
                aria-busy={lanzamiento.isPending || undefined}
              >
                <IconPlay />
                {lanzamiento.isPending ? 'Lanzando corrida…' : 'Lanzar corrida'}
              </Button>
              <span className="eo-launch__why" role="status">
                {missingReason
                  ? `Falta: ${missingReason}`
                  : lanzamiento.isPending
                    ? 'Pidiendo la corrida al motor de detección…'
                    : 'Todo listo. La corrida arranca en cuanto confirmes.'}
              </span>
            </div>
          </section>

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
