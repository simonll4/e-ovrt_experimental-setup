import { useEffect, useRef, useState } from 'react'
import { deriveExperimentManifest, getDeriveDefaults, getPromptSets, listCameras } from '../api'
import type { CameraPreset, PromptSet } from '../types'
import { Button, Card, ErrorBanner, Field, NativeSelect, TextInput } from './ui'

// Claves de `overrides` del endpoint de derive, 1:1 con las que devuelve
// GET .../derive-defaults. Todo se maneja como string (lo que ve el input) y se
// convierte recién al armar el body.
const FIELDS = [
  'warmup_frames',
  'fps',
  'camera_id',
  'prompt_set_id',
  'stride',
  'max_units',
  'pattern_set_file',
  'pattern_active_ids',
] as const
type FieldKey = (typeof FIELDS)[number]

const NUMERIC: FieldKey[] = ['warmup_frames', 'fps', 'stride', 'max_units']

const EMPTY = Object.fromEntries(FIELDS.map((k) => [k, ''])) as Record<FieldKey, string>

/** Rótulo humano de cada override; la clave técnica viaja al lado. */
const ROTULO: Record<FieldKey, string> = {
  warmup_frames: 'Cuadros a descartar al inicio',
  fps: 'Cuadros por segundo',
  camera_id: 'Cámara',
  prompt_set_id: 'Conjunto de prompts',
  stride: 'Procesar uno de cada N cuadros',
  max_units: 'Máximo de unidades a procesar',
  pattern_set_file: 'Archivo de patrones',
  pattern_active_ids: 'Clases del archivo de patrones',
}

/** Valor del manifiesto fuente -> texto del input. `null` (campo ausente) => vacío. */
function toText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

type Lista<T> = { estado: 'cargando' | 'lista' | 'error'; items: T[]; error?: string }

export function DeriveExperimentForm({
  source,
  onDone,
  onCancel,
  onDirtyChange,
  mode = 'derive',
  showTitle = true,
}: {
  source: string
  onDone: (newSlug: string) => void | Promise<void>
  onCancel: () => void
  /** Avisa si hay cambios sin guardar, para que quien lo contiene pueda
   *  ofrecer seguir editando antes de cerrarlo o cambiar de origen. */
  onDirtyChange?: (dirty: boolean) => void
  /** Sólo copy (título y texto del botón de submit). No afecta overrides ni el
   *  fetch de defaults, que son iguales en los dos modos. */
  mode?: 'derive' | 'create'
  /** La pantalla que ya titula con «Nuevo experimento» / «Derivar de …» lo
   *  apaga para no repetirlo. */
  showTitle?: boolean
}) {
  const [cameras, setCameras] = useState<Lista<CameraPreset>>({ estado: 'cargando', items: [] })
  const [promptSets, setPromptSets] = useState<Lista<PromptSet>>({ estado: 'cargando', items: [] })
  const [listas, setListas] = useState(0)
  const [newSlug, setNewSlug] = useState('')
  const [changes, setChanges] = useState('')
  const [values, setValues] = useState<Record<FieldKey, string>>(EMPTY)
  // Valores del manifiesto fuente ya precargados. Se compara contra esto para
  // decidir qué va en `overrides`: precargar NO convierte un campo en override.
  const [initial, setInitial] = useState<Record<FieldKey, string>>(EMPTY)
  const [precarga, setPrecarga] = useState<{ estado: 'cargando' | 'lista' | 'error'; error?: string }>({
    estado: 'cargando',
  })
  const [intento, setIntento] = useState(0)
  // Campos que el usuario tocó antes de que llegue la precarga: la respuesta
  // asincrónica no debe pisar lo que ya escribió.
  const touched = useRef<Set<FieldKey>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const enviando = useRef(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, string>>>({})

  const setField = (key: FieldKey, value: string) => {
    touched.current.add(key)
    setValues((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => (prev[key] ? { ...prev, [key]: undefined } : prev))
  }

  const dirty =
    newSlug !== '' || changes !== '' || FIELDS.some((k) => touched.current.has(k) && values[k] !== initial[k])
  const avisarDirty = useRef(onDirtyChange)
  avisarDirty.current = onDirtyChange
  useEffect(() => {
    avisarDirty.current?.(dirty)
  }, [dirty])

  // Listas para los desplegables. Un fallo no se convierte en "no hay
  // cámaras": se dice, y el campo sigue pudiendo quedar sin cambiar.
  useEffect(() => {
    let alive = true
    setCameras((c) => ({ ...c, estado: 'cargando' }))
    setPromptSets((c) => ({ ...c, estado: 'cargando' }))
    listCameras()
      .then((v) => alive && setCameras({ estado: 'lista', items: v }))
      .catch((e) => alive && setCameras({ estado: 'error', items: [], error: String(e) }))
    getPromptSets()
      .then((v) => alive && setPromptSets({ estado: 'lista', items: v }))
      .catch((e) => alive && setPromptSets({ estado: 'error', items: [], error: String(e) }))
    return () => {
      alive = false
    }
  }, [listas])

  useEffect(() => {
    let alive = true
    setPrecarga({ estado: 'cargando' })
    getDeriveDefaults(source)
      .then((d) => {
        if (!alive) return
        const texts = Object.fromEntries(
          FIELDS.map((k) => [k, toText(d[k])]),
        ) as Record<FieldKey, string>
        setInitial(texts)
        setValues((prev) =>
          Object.fromEntries(
            FIELDS.map((k) => [k, touched.current.has(k) ? prev[k] : texts[k]]),
          ) as Record<FieldKey, string>,
        )
        setPrecarga({ estado: 'lista' })
      })
      .catch((e) => {
        // Sin precarga el formulario sigue siendo usable: cada campo que no se
        // complete conserva el valor del fuente por la semántica del endpoint.
        if (alive) setPrecarga({ estado: 'error', error: String(e) })
      })
    return () => {
      alive = false
    }
  }, [source, intento])

  const submit = async () => {
    if (!newSlug || enviando.current) return
    setError(null)
    // Solo se mandan las claves que el usuario cambió respecto del manifiesto
    // fuente — clave ausente conserva el valor del fuente (semántica del
    // endpoint). Un override numérico que no parsea NO se manda como `null`: del
    // lado del servidor `null` explícito significa "borrar el campo y volver al
    // default", así que un typo silencioso (p.ej. "3o" en vez de "30") borraría
    // warmup_frames en vez de fallar. Por eso se valida acá con Number.isFinite y
    // se corta el submit con un error visible en vez de mandar algo que se
    // serializa a null.
    const overrides: Record<string, unknown> = {}
    const errores: Partial<Record<FieldKey, string>> = {}
    for (const key of FIELDS) {
      const raw = values[key]
      if (raw === initial[key]) continue // no lo tocó (o lo dejó como el fuente)
      if (!raw) continue // vaciar un campo no es "borrar": ver spec, fuera de alcance
      if (NUMERIC.includes(key)) {
        const n = Number(raw)
        if (!Number.isFinite(n)) {
          errores[key] = `"${raw}" no es un número válido`
          continue
        }
        overrides[key] = n
      } else if (key === 'pattern_active_ids') {
        overrides[key] = raw
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length > 0)
      } else {
        overrides[key] = raw
      }
    }
    const conError = Object.keys(errores) as FieldKey[]
    if (conError.length) {
      setFieldErrors(errores)
      setError(
        `${conError.length === 1 ? 'Un campo tiene' : `${conError.length} campos tienen`} un valor que no se puede enviar: ${conError.join(', ')}. No se mandó nada.`,
      )
      document.getElementById(`derive-${conError[0]}`)?.focus()
      return
    }
    enviando.current = true
    setSubmitting(true)
    try {
      const { slug } = await deriveExperimentManifest(source, {
        new_slug: newSlug,
        ...(changes ? { changes } : {}),
        overrides,
      })
      // La escritura ya ocurrió: lo que pase después (recargar el listado) no
      // la convierte en un fallo de este formulario.
      await onDone(slug)
    } catch (e) {
      // Mismo patrón que PromptSetEditor.tsx: ApiError pone en `.message` el
      // string genérico `API ${status}` — el mensaje útil (p.ej. "Ya existe" o
      // "override desconocido: [...]") viaja en `payload.detail`.
      const detail = (e as { payload?: { detail?: unknown } }).payload?.detail
      setError(
        typeof detail === 'string' ? detail : detail !== undefined ? JSON.stringify(detail) : String(e),
      )
    } finally {
      enviando.current = false
      setSubmitting(false)
    }
  }

  /** De dónde sale el valor que se ve: del origen, o cambiado acá. Omitir un
   *  campo conserva lo que defina el origen. */
  const herencia = (key: FieldKey): string => {
    if (precarga.estado !== 'lista') return 'Si lo dejás vacío se conserva el valor del origen.'
    const base = initial[key]
    if (values[key] === base) return base ? `Heredado del origen: ${base}` : 'El origen no lo define; vacío lo deja así.'
    if (!values[key]) return `Vacío conserva el valor del origen (${base}).`
    return base ? `Cambia el valor del origen (${base}).` : 'El origen no lo define: se agrega.'
  }

  const campo = (key: FieldKey, extraHint?: string, numeric = NUMERIC.includes(key)) => (
    <Field
      label={ROTULO[key]}
      labelKey={key}
      id={`derive-${key}`}
      hint={[extraHint, herencia(key)].filter(Boolean).join(' ')}
      error={fieldErrors[key]}
    >
      <TextInput
        inputMode={numeric ? (key === 'fps' ? 'decimal' : 'numeric') : undefined}
        value={values[key]}
        onChange={(e) => setField(key, e.target.value)}
      />
    </Field>
  )

  const cardTitle = mode === 'create' ? 'Nuevo experimento' : `Derivar de ${source}`
  const submitLabel = mode === 'create' ? 'Crear' : 'Derivar'
  const submittingLabel = mode === 'create' ? 'Creando…' : 'Derivando…'

  return (
    <Card title={showTitle ? cardTitle : undefined}>
      {precarga.estado === 'cargando' && (
        <p className="eo-status-line" role="status">Leyendo los valores de {source}…</p>
      )}
      {precarga.estado === 'error' && (
        <div className="eo-stale" role="alert">
          <span>
            No se pudieron leer los valores de <span className="eo-mono">{source}</span>. Podés
            crear igual: lo que no completes conserva lo que define el origen.
          </span>
          <Button variant="ghost" onClick={() => setIntento((n) => n + 1)}>Reintentar</Button>
        </div>
      )}
      <p className="eo-note">
        Se parte de <span className="eo-mono">{source}</span>. Sólo se envía lo que cambies: un
        campo que dejes como está, o vacío, conserva el valor del origen.
      </p>

      <fieldset className="eo-fieldset">
        <legend>Identificación</legend>
        <div className="eo-fieldgrid">
          <Field label="Nombre nuevo del manifiesto" labelKey="new_slug" hint="Obligatorio. Es el nombre del manifiesto que se crea.">
            <TextInput value={newSlug} onChange={(e) => setNewSlug(e.target.value)} required />
          </Field>
          <Field label="Qué cambia respecto del origen" labelKey="changes" hint="Opcional. Queda escrito en el manifiesto.">
            <TextInput value={changes} onChange={(e) => setChanges(e.target.value)} />
          </Field>
        </div>
      </fieldset>

      <fieldset className="eo-fieldset">
        <legend>Fuente y prompts</legend>
        <div className="eo-fieldgrid">
          <Field label={ROTULO.camera_id} labelKey="camera_id" id="derive-camera_id" hint={herencia('camera_id')}>
            <NativeSelect value={values.camera_id} onChange={(e) => setField('camera_id', e.target.value)}>
              <option value="">— sin cambiar —</option>
              {/* Un valor del origen que no está en la lista se muestra tal cual,
                  en vez de desaparecer del desplegable. */}
              {values.camera_id && !cameras.items.some((c) => c.id === values.camera_id) && (
                <option value={values.camera_id}>{values.camera_id}</option>
              )}
              {cameras.items.map((c) => (
                <option key={c.id} value={c.id}>{c.name || c.id}</option>
              ))}
            </NativeSelect>
          </Field>
          <Field label={ROTULO.prompt_set_id} labelKey="prompt_set_id" id="derive-prompt_set_id" hint={herencia('prompt_set_id')}>
            <NativeSelect
              value={values.prompt_set_id}
              onChange={(e) => setField('prompt_set_id', e.target.value)}
            >
              <option value="">— sin cambiar —</option>
              {values.prompt_set_id && !promptSets.items.some((s) => s.id === values.prompt_set_id) && (
                <option value={values.prompt_set_id}>{values.prompt_set_id}</option>
              )}
              {promptSets.items.map((s) => (
                <option key={s.id} value={s.id}>{s.id}</option>
              ))}
            </NativeSelect>
          </Field>
          {campo('fps')}
          {campo('warmup_frames', 'Sólo para cámaras en vivo.')}
        </div>
        {(cameras.estado === 'error' || promptSets.estado === 'error') && (
          <p className="eo-note eo-note--warn">
            No se pudo leer la lista de {cameras.estado === 'error' ? 'cámaras' : 'conjuntos de prompts'}:
            el campo puede quedar sin cambiar.{' '}
            <Button variant="ghost" onClick={() => setListas((n) => n + 1)}>Reintentar</Button>
          </p>
        )}
      </fieldset>

      <fieldset className="eo-fieldset">
        <legend>Procesamiento</legend>
        <div className="eo-fieldgrid">
          {campo('stride')}
          {campo('max_units')}
        </div>
      </fieldset>

      <fieldset className="eo-fieldset">
        <legend>Detalles de reglas</legend>
        <div className="eo-fieldgrid">
          {campo('pattern_set_file', 'Ruta en el servidor del motor de reglas; no se verifica desde acá.', false)}
          {campo('pattern_active_ids', 'Identificadores separados por coma.', false)}
        </div>
      </fieldset>

      {error && <ErrorBanner>{error}</ErrorBanner>}
      <div className="eo-actions">
        <Button
          variant="primary"
          onClick={() => void submit()}
          disabled={!newSlug || submitting}
          aria-busy={submitting || undefined}
        >
          {submitting ? submittingLabel : submitLabel}
        </Button>
        <Button onClick={onCancel} disabled={submitting}>Cancelar</Button>
        {dirty && !submitting && <span className="eo-editor__dirty">Cambios sin guardar</span>}
      </div>
    </Card>
  )
}
