import { useState } from 'react'
import {
  confirmFreeze, createPromptSet, deletePromptSet, derivePromptSet,
  requestFreeze, updatePromptSet,
} from '../api'
import type { PromptClassSpec, PromptSetDetail } from '../types'

const STRATEGIES = [
  'canonical_positive', 'syntactic_negation', 'specificity',
  'observable_state', 'presence_template',
]

interface Props {
  initial: PromptSetDetail
  onChanged: () => Promise<void> | void
  onClose: () => void
  isNew?: boolean
}

export default function PromptSetEditor({ initial, onChanged, onClose, isNew }: Props) {
  const [draft, setDraft] = useState<PromptSetDetail>(initial)
  const [deriveOpen, setDeriveOpen] = useState(false)
  const [newId, setNewId] = useState('')
  const [changes, setChanges] = useState('')
  const [error, setError] = useState<string | null>(null)

  const status = initial.status ?? 'exploratory'
  const editable = isNew || status === 'exploratory'

  const run = async (action: () => Promise<unknown>) => {
    try {
      setError(null)
      await action()
      await onChanged()
    } catch (e) {
      const detail = (e as { payload?: { detail?: unknown } }).payload?.detail
      setError(typeof detail === 'string' ? detail : detail !== undefined ? JSON.stringify(detail) : String(e))
    }
  }

  const setClass = (i: number, patch: Partial<PromptClassSpec>) =>
    setDraft((d) => ({
      ...d,
      classes: d.classes.map((c, j) => (j === i ? { ...c, ...patch } : c)),
    }))

  return (
    <section className="prompt-set-editor">
      <h3>{isNew ? 'Nuevo prompt set' : draft.id}</h3>
      {error && <p role="alert">{error}</p>}
      {status === 'frozen' && (
        <p>Set congelado — inmutable (sha256: {initial.frozen_sha256}).</p>
      )}
      {status === 'frozen_pending_review' && (
        <p>Pendiente de revisión del usuario — confirmar freeze cuando la revisión esté hecha.</p>
      )}

      {/* metadata editable solo en exploratory / nuevo */}
      {editable && (
        <>
          {isNew && (
            <label>id
              <input value={draft.id}
                onChange={(e) => setDraft({ ...draft, id: e.target.value })} />
            </label>
          )}
          <label>descripción
            <textarea value={draft.description ?? ''}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
          </label>
        </>
      )}

      <h4>Clases</h4>
      {draft.classes.map((c, i) => (
        <fieldset key={i} disabled={!editable}>
          <label>clase id
            <input value={c.id} onChange={(e) => setClass(i, { id: e.target.value })} />
          </label>
          <label>strategy
            <select value={c.strategy ?? ''}
              onChange={(e) => setClass(i, { strategy: e.target.value || null })}>
              <option value="">(sin strategy)</option>
              {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          {Object.entries(c.phrasings).map(([backend, phrases]) => (
            <label key={backend}>{`phrasings.${backend}`}
              <input value={phrases.join('; ')}
                onChange={(e) => setClass(i, {
                  phrasings: {
                    ...c.phrasings,
                    [backend]: e.target.value.split(';').map((p) => p.trim()).filter(Boolean),
                  },
                })} />
            </label>
          ))}
        </fieldset>
      ))}
      {editable && (
        <button type="button"
          onClick={() => setDraft({
            ...draft,
            classes: [...draft.classes, { id: '', phrasings: { default: [] } }],
          })}>
          Agregar clase
        </button>
      )}

      {/* acciones por estado — status NUNCA es un campo editable */}
      {editable && (
        <button type="button"
          onClick={() => void run(() =>
            isNew ? createPromptSet(draft) : updatePromptSet(draft.id, draft))}>
          Guardar
        </button>
      )}
      {status === 'exploratory' && !isNew && (
        <>
          <button type="button" onClick={() => void run(() => requestFreeze(draft.id))}>
            Pedir congelamiento
          </button>
          <button type="button" onClick={() => void run(() => deletePromptSet(draft.id))}>
            Eliminar
          </button>
        </>
      )}
      {status === 'frozen_pending_review' && (
        <button type="button" onClick={() => void run(() => confirmFreeze(draft.id))}>
          Confirmar freeze
        </button>
      )}
      {status === 'frozen' && !deriveOpen && (
        <button type="button" onClick={() => setDeriveOpen(true)}>Derivar set nuevo</button>
      )}
      {deriveOpen && (
        <div>
          <label>nuevo id
            <input value={newId} onChange={(e) => setNewId(e.target.value)} />
          </label>
          <label>cambios
            <input value={changes} onChange={(e) => setChanges(e.target.value)} />
          </label>
          <button type="button"
            onClick={() => void run(() => derivePromptSet(draft.id, newId, changes))}>
            Crear derivado
          </button>
        </div>
      )}
      <button type="button" onClick={onClose}>Cerrar</button>
    </section>
  )
}
