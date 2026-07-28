import { useEffect, useState } from 'react'
import { createPromptSet, getPromptSetDetail, listPromptSets } from '../api'
import type { PromptClassSpec, PromptSetDetail, PromptSetSummary } from '../types'
import { Card, ErrorBanner, Field } from './ui'

interface Props {
  mode: 'raw' | 'detect'
  onModeChange: (m: 'raw' | 'detect') => void
  draft: PromptSetDetail | null
  onDraftChange: (d: PromptSetDetail) => void
  activeClassIds: string[]
  onActiveChange: (ids: string[]) => void
  threshold: number | null
  onThresholdChange: (t: number | null) => void
  onApply: () => void
  disabled: boolean
}

export default function LivePromptPanel({
  mode, onModeChange, draft, onDraftChange, activeClassIds, onActiveChange,
  threshold, onThresholdChange, onApply, disabled,
}: Props) {
  const [sets, setSets] = useState<PromptSetSummary[]>([])
  const [setId, setSetId] = useState('')
  const [newId, setNewId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  useEffect(() => {
    void listPromptSets().then(setSets).catch(() => setSets([]))
  }, [])

  const pickSet = async (id: string) => {
    setSetId(id)
    setError(null)
    if (!id) return
    try {
      const detail = await getPromptSetDetail(id)
      onDraftChange(detail)
      onActiveChange(detail.classes.filter((c) => c.enabled_by_default !== false).map((c) => c.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const setClass = (i: number, patch: Partial<PromptClassSpec>) => {
    if (!draft) return
    onDraftChange({
      ...draft,
      classes: draft.classes.map((c, j) => (j === i ? { ...c, ...patch } : c)),
    })
  }

  const saveAsNew = async () => {
    if (!draft || !newId) return
    setError(null)
    setSaveMsg(null)
    try {
      await createPromptSet({ ...draft, id: newId, status: undefined })
      setSaveMsg(`Guardado como ${newId}`)
      const refreshed = await listPromptSets()
      setSets(refreshed)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <Card title="Detección">
      <label>
        <input
          type="checkbox"
          checked={mode === 'detect'}
          onChange={(e) => onModeChange(e.target.checked ? 'detect' : 'raw')}
        />{' '}
        Detección (desmarcado = solo video)
      </label>
      {mode === 'detect' && (
        <>
          {error && <ErrorBanner>{error}</ErrorBanner>}
          <Field label="Conjunto de prompts">
            <select value={setId} onChange={(e) => void pickSet(e.target.value)}>
              <option value="">— elegir —</option>
              {sets.map((s) => (
                <option key={s.id} value={s.id}>{s.id}</option>
              ))}
            </select>
          </Field>
          {draft && (
            <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
              {draft.classes.map((c, i) => (
                <fieldset key={c.id || i} className="eo-classbox">
                  <label>
                    <input
                      type="checkbox"
                      checked={activeClassIds.includes(c.id)}
                      onChange={(e) =>
                        onActiveChange(
                          e.target.checked
                            ? [...activeClassIds, c.id]
                            : activeClassIds.filter((id) => id !== c.id),
                        )
                      }
                    />{' '}
                    {c.id}
                  </label>
                  {Object.entries(c.phrasings).map(([backend, phrases]) => (
                    <Field key={backend} label={`phrasings.${backend}`}>
                      <textarea
                        rows={3}
                        value={phrases.join('\n')}
                        onChange={(e) =>
                          setClass(i, {
                            phrasings: {
                              ...c.phrasings,
                              [backend]: e.target.value.split('\n').map((p) => p.trim()).filter(Boolean),
                            },
                          })
                        }
                      />
                    </Field>
                  ))}
                </fieldset>
              ))}
            </div>
          )}
          <Field label={`score_threshold (${threshold ?? 0})`}>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={threshold ?? 0}
              onChange={(e) => onThresholdChange(Number(e.target.value))}
            />
          </Field>
          <div className="eo-actions">
            <button type="button" className="eo-btn--primary" disabled={disabled || !draft} onClick={onApply}>
              Aplicar
            </button>
            <input
              placeholder="id del set nuevo"
              value={newId}
              onChange={(e) => setNewId(e.target.value)}
            />
            <button type="button" disabled={!draft || !newId} onClick={() => void saveAsNew()}>
              Guardar como set nuevo
            </button>
          </div>
          {saveMsg && <small className="eo-note">{saveMsg}</small>}
        </>
      )}
      {mode === 'raw' && (
        <div className="eo-actions">
          <button type="button" className="eo-btn--primary" disabled={disabled} onClick={onApply}>
            Aplicar
          </button>
        </div>
      )}
    </Card>
  )
}
