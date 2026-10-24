import { useEffect, useMemo, useRef, useState } from 'react'
import {
  confirmFreeze, createPromptSet, deletePromptSet, derivePromptSet,
  requestFreeze, updatePromptSet,
} from '../api'
import type { PromptClassSpec, PromptSetDetail } from '../types'
import { promptStatusTone } from '../promptview'
import {
  Badge, Button, Card, DiscardPrompt, ErrorBanner, Field, NativeSelect, TextArea, TextInput,
  enfocarCuandoAparezca,
} from './ui'
import { IconChevron } from './ui/icons'

/** La taxonomía de estrategias, con su nombre legible. El valor que viaja es
 *  siempre el código. */
const STRATEGIES: Array<[string, string]> = [
  ['canonical_positive', 'Nombre directo'],
  ['syntactic_negation', 'Negación sintáctica'],
  ['specificity', 'Especificidad'],
  ['observable_state', 'Estado observable'],
  ['presence_template', 'Plantilla de presencia'],
]

const STATUS_LABEL: Record<string, string> = {
  exploratory: 'En exploración',
  frozen_pending_review: 'Pendiente de revisión',
  frozen: 'Congelado',
}

/** Contrato del almacén de conjuntos (`prompt_store._SET_ID_RE`). */
const SET_ID_RE = /^[a-z0-9_]+$/

interface Props {
  initial: PromptSetDetail
  onChanged: () => Promise<void> | void
  onClose: () => void
  /** Avisa si el borrador tiene cambios sin guardar. */
  onDirtyChange?: (dirty: boolean) => void
  isNew?: boolean
}

type Accion = 'guardar' | 'pedir' | 'confirmar' | 'derivar' | 'eliminar'

const VERBO: Record<Accion, string> = {
  guardar: 'Guardando…',
  pedir: 'Pidiendo el congelamiento…',
  confirmar: 'Confirmando el congelado…',
  derivar: 'Creando el derivado…',
  eliminar: 'Eliminando…',
}

/** El texto de un campo de frases: lo que se escribe, con sus «;». Se guarda
 *  aparte del arreglo para que escribir el separador no lo borre al instante;
 *  el arreglo que viaja se arma con la misma regla de siempre. */
const claveTexto = (i: number, backend: string) => `${i}\u0000${backend}`
const partir = (texto: string) => texto.split(';').map((p) => p.trim()).filter(Boolean)

function textosIniciales(set: PromptSetDetail): Record<string, string> {
  const out: Record<string, string> = {}
  set.classes.forEach((c, i) => {
    for (const [backend, frases] of Object.entries(c.phrasings)) out[claveTexto(i, backend)] = frases.join('; ')
  })
  return out
}

/** Índices de clase que menciona un error de validación del servidor
 *  (`loc: ['classes', 0, ...]`), para abrirlas y llevar el foco ahí. */
function clasesConError(detail: unknown): number[] {
  if (!Array.isArray(detail)) return []
  const out = new Set<number>()
  for (const d of detail) {
    const loc = (d as { loc?: unknown[] })?.loc
    if (Array.isArray(loc)) {
      const i = loc.indexOf('classes')
      if (i >= 0 && typeof loc[i + 1] === 'number') out.add(loc[i + 1] as number)
    }
  }
  return [...out]
}

export default function PromptSetEditor({ initial, onChanged, onClose, onDirtyChange, isNew }: Props) {
  const [draft, setDraft] = useState<PromptSetDetail>(initial)
  const [textos, setTextos] = useState<Record<string, string>>(() => textosIniciales(initial))
  const [abiertas, setAbiertas] = useState<Set<number>>(() => new Set(initial.classes.length ? [0] : []))
  const [conError, setConError] = useState<Set<number>>(new Set())
  const [deriveOpen, setDeriveOpen] = useState(false)
  const [newId, setNewId] = useState('')
  const [changes, setChanges] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [idError, setIdError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Accion | null>(null)
  const ocupado = useRef(false)
  const [preguntarCierre, setPreguntarCierre] = useState(false)

  const status = initial.status ?? 'exploratory'
  const editable = isNew || status === 'exploratory'

  // Cambios sin guardar: el borrador difiere del conjunto que se abrió.
  const dirty = useMemo(() => JSON.stringify(draft) !== JSON.stringify(initial), [draft, initial])
  const avisar = useRef(onDirtyChange)
  avisar.current = onDirtyChange
  useEffect(() => {
    avisar.current?.(dirty)
  }, [dirty])

  // Al abrir, el foco va al título del editor: el botón que lo abrió ya no
  // está y sin esto el lector queda en el documento.
  useEffect(() => {
    enfocarCuandoAparezca('.eo-editor__head h2')
  }, [])

  // Una clase marcada con error se abre y recibe el foco.
  useEffect(() => {
    const primera = [...conError].sort((a, b) => a - b)[0]
    if (primera == null) return
    document.getElementById(`eo-clase-${primera}`)?.querySelector<HTMLElement>('summary')?.focus()
  }, [conError])

  const run = async (accion: Accion, action: () => Promise<unknown>) => {
    // Una operación a la vez: el doble click no manda dos escrituras.
    if (ocupado.current) return
    ocupado.current = true
    setBusy(accion)
    setError(null)
    let escrito = false
    try {
      await action()
      escrito = true
    } catch (e) {
      const detail = (e as { payload?: { detail?: unknown } }).payload?.detail
      setError(typeof detail === 'string' ? detail : detail !== undefined ? JSON.stringify(detail) : String(e))
      const indices = clasesConError(detail)
      if (indices.length) {
        setConError(new Set(indices))
        setAbiertas((prev) => new Set([...prev, ...indices]))
      }
    } finally {
      ocupado.current = false
      setBusy(null)
    }
    // La escritura ya ocurrió: refrescar el listado es otra cosa, y si falla no
    // convierte el guardado en un fallo.
    if (escrito) await onChanged()
  }

  const setClass = (i: number, patch: Partial<PromptClassSpec>) =>
    setDraft((d) => ({
      ...d,
      classes: d.classes.map((c, j) => (j === i ? { ...c, ...patch } : c)),
    }))

  const setFrases = (i: number, c: PromptClassSpec, backend: string, texto: string) => {
    setTextos((t) => ({ ...t, [claveTexto(i, backend)]: texto }))
    setClass(i, { phrasings: { ...c.phrasings, [backend]: partir(texto) } })
  }

  const guardar = () => {
    if (isNew && !SET_ID_RE.test(draft.id)) {
      setIdError('Sólo minúsculas, números y guion bajo (a-z, 0-9, _).')
      document.getElementById('eo-set-id')?.focus()
      return
    }
    setIdError(null)
    void run('guardar', () => (isNew ? createPromptSet(draft) : updatePromptSet(draft.id, draft)))
  }

  const handleDelete = () => {
    if (!window.confirm(`¿Eliminar el set ${draft.id}? No se puede deshacer.`)) return
    void run('eliminar', () => deletePromptSet(draft.id))
  }

  const cerrar = () => {
    if (dirty) setPreguntarCierre(true)
    else onClose()
  }

  const alternar = (i: number, abierta: boolean) =>
    setAbiertas((prev) => {
      const next = new Set(prev)
      if (abierta) next.add(i)
      else next.delete(i)
      return next
    })

  const variantes = (c: PromptClassSpec) => Object.values(c.phrasings).reduce((n, f) => n + f.length, 0)

  return (
    <Card>
      <div className="eo-editor">
        <div className="eo-editor__head">
          <h2>{isNew ? 'Nuevo conjunto de prompts' : <span className="eo-mono">{draft.id}</span>}</h2>
          {!isNew && <Badge tone={promptStatusTone(status)}>{STATUS_LABEL[status] ?? status}</Badge>}
          {dirty && <span className="eo-editor__dirty" role="status">Cambios sin guardar</span>}
        </div>
        {error && <ErrorBanner>{error}</ErrorBanner>}
        {status === 'exploratory' && (
          <p className="eo-editor__note">
            Editable. Al pedir congelamiento pasa a revisión; una vez congelado es inmutable
            y citable por experimentos.
          </p>
        )}
        {status === 'frozen_pending_review' && (
          <p className="eo-editor__note eo-note--warn">
            Pendiente de revisión — confirmá el congelado cuando la revisión esté hecha.
          </p>
        )}
        {status === 'frozen' && (
          <p className="eo-editor__note">
            Inmutable (huella <span className="eo-mono">{initial.frozen_sha256}</span>). Para
            cambiarlo, derivá un conjunto nuevo.
          </p>
        )}

        {/* metadatos editables solo en exploratory / nuevo */}
        {editable && (
          <>
            {isNew && (
              <Field
                label="Identificador del conjunto"
                labelKey="id"
                id="eo-set-id"
                hint="Minúsculas, números y guion bajo. No se puede cambiar después."
                error={idError ?? undefined}
              >
                <TextInput value={draft.id} onChange={(e) => setDraft({ ...draft, id: e.target.value })} />
              </Field>
            )}
            <Field label="Descripción" labelKey="description">
              <TextArea
                rows={2}
                value={draft.description ?? ''}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              />
            </Field>
          </>
        )}

        <h3 className="eo-editor__section">Clases ({draft.classes.length})</h3>
        {draft.classes.length === 0 && (
          <p className="eo-note">Un conjunto necesita al menos una clase.</p>
        )}
        <div className="eo-editor__classes">
          {draft.classes.map((c, i) => (
            <details
              key={i}
              id={`eo-clase-${i}`}
              className={conError.has(i) ? 'eo-adv eo-classbox eo-classbox--invalid' : 'eo-adv eo-classbox'}
              open={abiertas.has(i)}
              onToggle={(e) => alternar(i, (e.currentTarget as HTMLDetailsElement).open)}
            >
              <summary>
                <span className="eo-adv__chev" aria-hidden="true"><IconChevron /></span>
                <span className="eo-classbox__sum">
                  <b>{c.id || 'clase sin identificador'}</b>
                  <span>{variantes(c)} variante{variantes(c) === 1 ? '' : 's'}</span>
                  {c.strategy && <span>{STRATEGIES.find(([v]) => v === c.strategy)?.[1] ?? c.strategy}</span>}
                  {conError.has(i) && <span className="eo-field__error">revisar: el servidor marcó un error</span>}
                </span>
              </summary>
              {/* El contenido sigue montado con la clase plegada: plegar no
                  pierde lo escrito. */}
              <div className="eo-adv__body">
                <fieldset disabled={!editable}>
                  <Field
                    label="Identificador de la clase"
                    labelKey="id"
                    hint={i === 0 ? 'Identificador canónico (ej: person, helmet).' : undefined}
                  >
                    <TextInput value={c.id} onChange={(e) => setClass(i, { id: e.target.value })} />
                  </Field>
                  <Field
                    label="Estrategia"
                    labelKey="strategy"
                    hint={i === 0 ? 'Cómo se formula la clase al modelo: nombre directo, o un estado visible (ej: bare_head).' : undefined}
                  >
                    <NativeSelect
                      value={c.strategy ?? ''}
                      onChange={(e) => setClass(i, { strategy: e.target.value || null })}
                    >
                      <option value="">(sin estrategia)</option>
                      {/* Un valor que esta consola no conoce se conserva tal cual. */}
                      {c.strategy && !STRATEGIES.some(([v]) => v === c.strategy) && (
                        <option value={c.strategy}>{c.strategy}</option>
                      )}
                      {STRATEGIES.map(([v, nombre]) => (
                        <option key={v} value={v}>{nombre} ({v})</option>
                      ))}
                    </NativeSelect>
                  </Field>
                  {Object.entries(c.phrasings).map(([backend, phrases]) => (
                    <Field
                      key={backend}
                      label={`Frases — ${backend}`}
                      labelKey={`phrasings.${backend}`}
                      hint={i === 0 && backend === 'default'
                        ? 'Variantes separadas por «;». El detector prueba cada una.'
                        : undefined}
                    >
                      <TextInput
                        value={textos[claveTexto(i, backend)] ?? phrases.join('; ')}
                        placeholder="person; worker; obrero"
                        onChange={(e) => setFrases(i, c, backend, e.target.value)}
                      />
                    </Field>
                  ))}
                </fieldset>
              </div>
            </details>
          ))}
        </div>
        {editable && (
          <div className="eo-actions">
            <Button
              disabled={busy !== null}
              onClick={() => {
                const i = draft.classes.length
                setDraft({
                  ...draft,
                  classes: [...draft.classes, { id: '', phrasings: { default: [] } }],
                })
                setAbiertas((prev) => new Set([...prev, i]))
              }}
            >
              Agregar clase
            </Button>
          </div>
        )}

        {/* acciones por estado — status NUNCA es un campo editable */}
        {deriveOpen && (
          <fieldset className="eo-fieldset eo-editor__derive">
            <legend>Derivar un conjunto nuevo</legend>
            <Field label="Nuevo id" labelKey="new_id" hint="Minúsculas, números y guion bajo.">
              <TextInput value={newId} onChange={(e) => setNewId(e.target.value)} />
            </Field>
            <Field label="Cambios respecto del congelado" labelKey="changes">
              <TextInput value={changes} onChange={(e) => setChanges(e.target.value)} />
            </Field>
            <Button
              variant="primary"
              disabled={busy !== null || !newId}
              onClick={() => void run('derivar', () => derivePromptSet(draft.id, newId, changes))}
            >
              {busy === 'derivar' ? VERBO.derivar : 'Crear derivado'}
            </Button>
          </fieldset>
        )}

        {preguntarCierre && (
          <DiscardPrompt
            what="el conjunto"
            onKeep={() => setPreguntarCierre(false)}
            onDiscard={onClose}
          />
        )}

        {/* Pie visible al fondo del panel: las acciones no quedan dos mil
            píxeles más abajo. El cuerpo reserva su alto, así que no tapa el
            último campo. */}
        <div className="eo-editor__foot">
          {status === 'exploratory' && !isNew && dirty && (
            <p className="eo-editor__note">
              Para pedir el congelamiento, primero guardá o descartá los cambios: congelar no
              guarda nada por su cuenta.
            </p>
          )}
          <div className="eo-actions">
            {editable && (
              <Button variant="primary" disabled={busy !== null} aria-busy={busy === 'guardar' || undefined} onClick={guardar}>
                {busy === 'guardar' ? VERBO.guardar : 'Guardar'}
              </Button>
            )}
            {status === 'exploratory' && !isNew && (
              <Button
                disabled={busy !== null || dirty}
                title="Pasa a frozen_pending_review: queda esperando tu revisión"
                onClick={() => void run('pedir', () => requestFreeze(draft.id))}
              >
                {busy === 'pedir' ? VERBO.pedir : 'Pedir congelamiento'}
              </Button>
            )}
            {status === 'frozen_pending_review' && (
              <Button
                disabled={busy !== null}
                title="Pasa a frozen: queda inmutable y citable por experimentos"
                onClick={() => void run('confirmar', () => confirmFreeze(draft.id))}
              >
                {busy === 'confirmar' ? VERBO.confirmar : 'Confirmar freeze'}
              </Button>
            )}
            {status === 'frozen' && !deriveOpen && (
              <Button
                disabled={busy !== null}
                title="Crea un set nuevo, editable, con linaje a este frozen"
                onClick={() => setDeriveOpen(true)}
              >
                Derivar set nuevo
              </Button>
            )}
            <Button onClick={cerrar} disabled={busy !== null}>Cerrar</Button>
            {status === 'exploratory' && !isNew && (
              <Button variant="danger" disabled={busy !== null} onClick={handleDelete}>
                {busy === 'eliminar' ? VERBO.eliminar : 'Eliminar'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}
