import { useState } from 'react'
import {
  confirmFreeze, createPromptSet, deletePromptSet, derivePromptSet,
  requestFreeze, updatePromptSet,
} from '../api'
import type { PromptClassSpec, PromptSetDetail } from '../types'
import { promptStatusTone } from '../promptview'
import { Badge, Card, ErrorBanner, Field } from './ui'

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

  const handleDelete = () => {
    if (!window.confirm(`¿Eliminar el set ${draft.id}? No se puede deshacer.`)) return
    void run(() => deletePromptSet(draft.id))
  }

  return (
    <Card>
      <h3>
        {isNew ? 'Nuevo prompt set' : draft.id}
        {!isNew && <> <Badge tone={promptStatusTone(status)}>{status}</Badge></>}
      </h3>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {status === 'exploratory' && (
        <small className="eo-note">
          Editable. Al pedir congelamiento pasa a revisión; una vez congelado es inmutable
          y citable por experimentos.
        </small>
      )}
      {status === 'frozen_pending_review' && (
        <small className="eo-note eo-note--warn">
          Pendiente de revisión del usuario — confirmar freeze cuando la revisión esté hecha.
        </small>
      )}
      {status === 'frozen' && (
        <small className="eo-note">
          Inmutable (sha256: {initial.frozen_sha256}). Para cambiarlo, derivá un set nuevo.
        </small>
      )}

      {/* metadata editable solo en exploratory / nuevo */}
      {editable && (
        <>
          {isNew && (
            <Field label="id">
              <input value={draft.id}
                onChange={(e) => setDraft({ ...draft, id: e.target.value })} />
            </Field>
          )}
          <Field label="descripción">
            <textarea value={draft.description ?? ''}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
          </Field>
        </>
      )}

      <h4>Clases</h4>
      {draft.classes.length === 0 && (
        <small className="eo-note">Un set necesita al menos una clase.</small>
      )}
      {/* Los hints didácticos van solo en la PRIMERA clase: enseñan una vez,
          las demás quedan limpias (9 repeticiones eran ruido, visto en screenshot). */}
      {draft.classes.map((c, i) => (
        <fieldset key={i} disabled={!editable} className="eo-classbox">
          <Field label="clase id"
            hint={i === 0 ? 'identificador canónico (ej: person, helmet)' : undefined}>
            <input value={c.id} onChange={(e) => setClass(i, { id: e.target.value })} />
          </Field>
          <Field label="strategy"
            hint={i === 0 ? 'cómo se formula la clase al modelo (canonical_positive = nombre directo; observable_state = estado visible, ej: bare_head)' : undefined}>
            <select value={c.strategy ?? ''}
              onChange={(e) => setClass(i, { strategy: e.target.value || null })}>
              <option value="">(sin strategy)</option>
              {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          {Object.entries(c.phrasings).map(([backend, phrases]) => (
            <Field key={backend} label={`phrasings.${backend}`}
              hint={i === 0 && backend === 'default'
                ? 'variantes de fraseo separadas por ; — el detector prueba cada una'
                : undefined}>
              <input value={phrases.join('; ')}
                placeholder="person; worker; obrero"
                onChange={(e) => setClass(i, {
                  phrasings: {
                    ...c.phrasings,
                    [backend]: e.target.value.split(';').map((p) => p.trim()).filter(Boolean),
                  },
                })} />
            </Field>
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
      {deriveOpen && (
        <div>
          <Field label="nuevo id">
            <input value={newId} onChange={(e) => setNewId(e.target.value)} />
          </Field>
          <Field label="cambios">
            <input value={changes} onChange={(e) => setChanges(e.target.value)} />
          </Field>
          <button type="button"
            onClick={() => void run(() => derivePromptSet(draft.id, newId, changes))}>
            Crear derivado
          </button>
        </div>
      )}

      <div className="eo-actions">
        {editable && (
          <button type="button" className="eo-btn--primary"
            onClick={() => void run(() =>
              isNew ? createPromptSet(draft) : updatePromptSet(draft.id, draft))}>
            Guardar
          </button>
        )}
        {status === 'exploratory' && !isNew && (
          <button type="button"
            title="Pasa a frozen_pending_review: queda esperando tu revisión"
            onClick={() => void run(() => requestFreeze(draft.id))}>
            Pedir congelamiento
          </button>
        )}
        {status === 'frozen_pending_review' && (
          <button type="button"
            title="Pasa a frozen: queda inmutable y citable por experimentos"
            onClick={() => void run(() => confirmFreeze(draft.id))}>
            Confirmar freeze
          </button>
        )}
        {status === 'frozen' && !deriveOpen && (
          <button type="button"
            title="Crea un set nuevo, editable, con linaje a este frozen"
            onClick={() => setDeriveOpen(true)}>
            Derivar set nuevo
          </button>
        )}
        {status === 'exploratory' && !isNew && (
          <button type="button" className="eo-btn--danger" onClick={handleDelete}>
            Eliminar
          </button>
        )}
        <button type="button" onClick={onClose}>Cerrar</button>
      </div>
    </Card>
  )
}
