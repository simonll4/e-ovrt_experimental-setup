import { useEffect, useRef, useState } from 'react'
import { deriveExperimentManifest, getDeriveDefaults, getPromptSets, listCameras } from '../api'
import type { CameraPreset, PromptSet } from '../types'
import { Card, ErrorBanner, Field } from './ui'

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

/** Valor del manifiesto fuente -> texto del input. `null` (campo ausente) => vacío. */
function toText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

export function DeriveExperimentForm({
  source,
  onDone,
  onCancel,
  mode = 'derive',
}: {
  source: string
  onDone: (newSlug: string) => void
  onCancel: () => void
  /** Sólo copy (título de la card + texto del botón de submit). No afecta
   *  overrides ni el fetch de defaults, que son iguales en los dos modos:
   *  - 'derive' (default, atajo desde la fila de la tabla): "Derivar de
   *    <source>" / botón "Derivar" — el usuario ya eligió de qué partir.
   *  - 'create' (entrada desde /experiments/new, con el selector "basado en"
   *    arriba): "Nuevo experimento" / botón "Crear" — no repite la fuente,
   *    ya la comunica el selector. */
  mode?: 'derive' | 'create'
}) {
  const [cameras, setCameras] = useState<CameraPreset[]>([])
  const [promptSets, setPromptSets] = useState<PromptSet[]>([])
  const [newSlug, setNewSlug] = useState('')
  const [changes, setChanges] = useState('')
  const [values, setValues] = useState<Record<FieldKey, string>>(EMPTY)
  // Valores del manifiesto fuente ya precargados. Se compara contra esto para
  // decidir qué va en `overrides`: precargar NO convierte un campo en override.
  const [initial, setInitial] = useState<Record<FieldKey, string>>(EMPTY)
  // Campos que el usuario tocó antes de que llegue la precarga: la respuesta
  // asincrónica no debe pisar lo que ya escribió.
  const touched = useRef<Set<FieldKey>>(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setField = (key: FieldKey, value: string) => {
    touched.current.add(key)
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  useEffect(() => {
    let alive = true
    listCameras().then((v) => alive && setCameras(v)).catch(() => alive && setCameras([]))
    getPromptSets().then((v) => alive && setPromptSets(v)).catch(() => alive && setPromptSets([]))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    let alive = true
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
      })
      .catch(() => {
        // Sin precarga el formulario sigue siendo usable: arranca vacío y cada
        // campo ausente conserva el valor del fuente por la semántica del endpoint.
      })
    return () => {
      alive = false
    }
  }, [source])

  const submit = async () => {
    if (!newSlug || submitting) return
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
    for (const key of FIELDS) {
      const raw = values[key]
      if (raw === initial[key]) continue // no lo tocó (o lo dejó como el fuente)
      if (!raw) continue // vaciar un campo no es "borrar": ver spec, fuera de alcance
      if (NUMERIC.includes(key)) {
        const n = Number(raw)
        if (!Number.isFinite(n)) {
          setError(`${key}: "${raw}" no es un número válido`)
          return
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
    setSubmitting(true)
    try {
      const { slug } = await deriveExperimentManifest(source, {
        new_slug: newSlug,
        ...(changes ? { changes } : {}),
        overrides,
      })
      onDone(slug)
    } catch (e) {
      // Mismo patrón que PromptSetEditor.tsx: ApiError pone en `.message` el
      // string genérico `API ${status}` — el mensaje útil (p.ej. "Ya existe" o
      // "override desconocido: [...]") viaja en `payload.detail`.
      const detail = (e as { payload?: { detail?: unknown } }).payload?.detail
      setError(
        typeof detail === 'string' ? detail : detail !== undefined ? JSON.stringify(detail) : String(e),
      )
    } finally {
      setSubmitting(false)
    }
  }

  const cardTitle = mode === 'create' ? 'Nuevo experimento' : `Derivar de ${source}`
  const submitLabel = mode === 'create' ? 'Crear' : 'Derivar'
  const submittingLabel = mode === 'create' ? 'Creando…' : 'Derivando…'

  return (
    <Card title={cardTitle}>
      <Field label="nombre nuevo">
        <input value={newSlug} onChange={(e) => setNewSlug(e.target.value)} />
      </Field>
      <Field label="changes">
        <input value={changes} onChange={(e) => setChanges(e.target.value)} />
      </Field>
      <Field label="warmup_frames">
        <input
          value={values.warmup_frames}
          onChange={(e) => setField('warmup_frames', e.target.value)}
        />
      </Field>
      <Field label="fps">
        <input value={values.fps} onChange={(e) => setField('fps', e.target.value)} />
      </Field>
      <Field label="cámara">
        <select value={values.camera_id} onChange={(e) => setField('camera_id', e.target.value)}>
          <option value="">— sin cambiar —</option>
          {cameras.map((c) => (
            <option key={c.id} value={c.id}>{c.name || c.id}</option>
          ))}
        </select>
      </Field>
      <Field label="prompt set">
        <select
          value={values.prompt_set_id}
          onChange={(e) => setField('prompt_set_id', e.target.value)}
        >
          <option value="">— sin cambiar —</option>
          {promptSets.map((s) => (
            <option key={s.id} value={s.id}>{s.id}</option>
          ))}
        </select>
      </Field>
      <Field label="stride">
        <input value={values.stride} onChange={(e) => setField('stride', e.target.value)} />
      </Field>
      <Field label="max_units">
        <input value={values.max_units} onChange={(e) => setField('max_units', e.target.value)} />
      </Field>
      <Field label="pattern set" hint="ruta absoluta al pattern set file">
        <input
          value={values.pattern_set_file}
          onChange={(e) => setField('pattern_set_file', e.target.value)}
        />
      </Field>
      <Field label="pattern set clases" hint="ids separados por coma">
        <input
          value={values.pattern_active_ids}
          onChange={(e) => setField('pattern_active_ids', e.target.value)}
        />
      </Field>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
        <button onClick={submit} disabled={!newSlug || submitting}>
          {submitting ? submittingLabel : submitLabel}
        </button>
        <button onClick={onCancel}>Cancelar</button>
      </div>
    </Card>
  )
}
