import { useEffect, useRef, useState } from 'react'
import { createPromptSet, getPromptSetDetail, listPromptSets } from '../api'
import type { PromptClassSpec, PromptSetDetail, PromptSetSummary } from '../types'
import { Button, Card, ErrorBanner, Field, NativeSelect, SegmentedControl, TextArea, TextInput } from './ui'

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

/** Contrato del almacén de conjuntos (`prompt_store._SET_ID_RE`). */
const SET_ID_RE = /^[a-z0-9_]+$/

export default function LivePromptPanel({
  mode, onModeChange, draft, onDraftChange, activeClassIds, onActiveChange,
  threshold, onThresholdChange, onApply, disabled,
}: Props) {
  const [sets, setSets] = useState<{ estado: 'cargando' | 'lista' | 'error'; items: PromptSetSummary[] }>({
    estado: 'cargando',
    items: [],
  })
  const [setId, setSetId] = useState('')
  const [newId, setNewId] = useState('')
  const [newIdError, setNewIdError] = useState<string | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const [cargandoSet, setCargandoSet] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const guardandoRef = useRef(false)
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    let alive = true
    setSets((s) => ({ ...s, estado: 'cargando' }))
    listPromptSets()
      .then((items) => alive && setSets({ estado: 'lista', items }))
      .catch(() => alive && setSets({ estado: 'error', items: [] }))
    return () => {
      alive = false
    }
  }, [intento])

  const pickSet = async (id: string) => {
    setSetId(id)
    setError(null)
    if (!id) return
    setCargandoSet(true)
    try {
      const detail = await getPromptSetDetail(id)
      onDraftChange(detail)
      onActiveChange(detail.classes.filter((c) => c.enabled_by_default !== false).map((c) => c.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setCargandoSet(false)
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
    if (!draft || !newId || guardandoRef.current) return
    if (!SET_ID_RE.test(newId)) {
      setNewIdError('Sólo minúsculas, números y guion bajo (a-z, 0-9, _).')
      return
    }
    setNewIdError(undefined)
    setError(null)
    setSaveMsg(null)
    guardandoRef.current = true
    setGuardando(true)
    try {
      await createPromptSet({ ...draft, id: newId, status: undefined })
      setSaveMsg(`Guardado como ${newId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return
    } finally {
      guardandoRef.current = false
      setGuardando(false)
    }
    // Ya está guardado: si la lista no se puede recargar, se dice aparte.
    try {
      setSets({ estado: 'lista', items: await listPromptSets() })
    } catch {
      setSaveMsg(`Guardado como ${newId}. La lista de conjuntos no se pudo recargar.`)
    }
  }

  return (
    <Card title="Qué mostrar">
      {/* Segmento y no un checkbox: son dos modos con nombre propio, no una
          opción que se prende. */}
      <SegmentedControl
        value={mode}
        label="Modo de la prueba"
        options={[
          { value: 'raw', label: 'Imagen directa' },
          { value: 'detect', label: 'Con detecciones' },
        ]}
        onChange={onModeChange}
      />
      {mode === 'raw' && (
        <p className="eo-cap">
          La imagen directa no pasa por el modelo: sirve para verificar encuadre, foco y luz.
        </p>
      )}
      {mode === 'detect' && (
        <>
          {error && <ErrorBanner>{error}</ErrorBanner>}
          <Field
            label="Conjunto de prompts"
            hint={
              sets.estado === 'cargando'
                ? 'Cargando los conjuntos…'
                : cargandoSet
                  ? 'Leyendo el conjunto elegido…'
                  : undefined
            }
          >
            <NativeSelect value={setId} onChange={(e) => void pickSet(e.target.value)}>
              <option value="">— elegir —</option>
              {sets.items.map((s) => (
                <option key={s.id} value={s.id}>{s.id}</option>
              ))}
            </NativeSelect>
          </Field>
          {sets.estado === 'error' && (
            <p className="eo-note eo-note--warn">
              No se pudo leer la lista de conjuntos.{' '}
              <Button variant="ghost" onClick={() => setIntento((n) => n + 1)}>Reintentar</Button>
            </p>
          )}
          {draft && (
            <div className="eo-editor__classes">
              {draft.classes.map((c, i) => (
                <fieldset key={c.id || i} className="eo-classbox eo-classbox--plain">
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
                    />
                    {c.id}
                  </label>
                  {/* `backend` es la clave del modelo en el YAML (gdino, owlv2):
                      es un dato, no se traduce. */}
                  {Object.entries(c.phrasings).map(([backend, phrases]) => (
                    <Field key={backend} label={`Frases — ${backend}`} hint="Una frase por línea.">
                      <TextArea
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
          {/* "Confianza mínima" con el valor al lado, en decimales con coma.
              `score_threshold` es la clave de la API, no texto de interfaz. */}
          <Field label={`Confianza mínima — ${(threshold ?? 0).toFixed(2).replace('.', ',')}`}>
            <TextInput
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={threshold ?? 0}
              onChange={(e) => onThresholdChange(Number(e.target.value))}
            />
          </Field>
          <div className="eo-actions">
            <Button variant="primary" disabled={disabled || !draft} onClick={onApply}>
              Aplicar a la prueba
            </Button>
          </div>
          <Field
            label="Guardar estas frases como conjunto nuevo"
            labelKey="id"
            hint="Crea un conjunto en exploración con las clases y frases de arriba."
            error={newIdError}
          >
            <span className="eo-inputrow">
              <TextInput
                placeholder="identificador del conjunto nuevo"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
              />
              <Button disabled={!draft || !newId || guardando} onClick={() => void saveAsNew()}>
                {guardando ? 'Guardando…' : 'Guardar como conjunto nuevo'}
              </Button>
            </span>
          </Field>
          {saveMsg && <p className="eo-note" role="status">{saveMsg}</p>}
        </>
      )}
      {mode === 'raw' && (
        <div className="eo-actions">
          <Button variant="primary" disabled={disabled} onClick={onApply}>
            Aplicar a la prueba
          </Button>
        </div>
      )}
    </Card>
  )
}
