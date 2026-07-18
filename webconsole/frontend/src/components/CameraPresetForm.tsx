import { useState } from 'react'
import { createCamera, deleteCamera, updateCamera } from '../api'
import type { CameraPreset } from '../types'
import { Card, ErrorBanner, Field } from './ui'

const PLUGINS = ['rtsp', 'oak_d', 'video_file', 'image_folder']

interface Props {
  initial: CameraPreset | null
  onSaved: () => void
  onClose: () => void
}

export default function CameraPresetForm({ initial, onSaved, onClose }: Props) {
  const [id, setId] = useState(initial?.id ?? '')
  const [name, setName] = useState(initial?.name ?? '')
  const [plugin, setPlugin] = useState(initial?.plugin ?? 'rtsp')
  const [configText, setConfigText] = useState(
    initial ? JSON.stringify(initial.config, null, 2) : '{}',
  )
  const [configError, setConfigError] = useState<string | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)

  const save = async () => {
    setError(null)
    let config: Record<string, unknown>
    try {
      config = JSON.parse(configText) as Record<string, unknown>
      setConfigError(undefined)
    } catch (e) {
      setConfigError(`JSON inválido: ${e instanceof Error ? e.message : String(e)}`)
      return
    }
    const preset: CameraPreset = { id, name, plugin, config }
    try {
      if (initial) {
        await updateCamera(initial.id, preset)
      } else {
        await createCamera(preset)
      }
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const remove = async () => {
    if (!initial) return
    if (!window.confirm(`¿Borrar el preset ${initial.id}?`)) return
    setError(null)
    try {
      await deleteCamera(initial.id)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <Card title={initial ? `Editar ${initial.id}` : 'Nuevo preset'}>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <Field label="id">
        <input value={id} disabled={Boolean(initial)} onChange={(e) => setId(e.target.value)} />
      </Field>
      <Field label="name">
        <input value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="plugin">
        <select value={plugin} onChange={(e) => setPlugin(e.target.value)}>
          {PLUGINS.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </Field>
      <Field label="config (JSON)" error={configError}>
        <textarea rows={6} value={configText} onChange={(e) => setConfigText(e.target.value)} />
      </Field>
      <div className="eo-actions">
        <button type="button" className="eo-btn--primary" onClick={() => void save()}>
          Guardar
        </button>
        {initial && (
          <button type="button" className="eo-btn--danger" onClick={() => void remove()}>
            Eliminar
          </button>
        )}
        <button type="button" onClick={onClose}>Cerrar</button>
      </div>
    </Card>
  )
}
