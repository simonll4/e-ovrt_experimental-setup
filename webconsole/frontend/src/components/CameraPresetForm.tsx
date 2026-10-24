import { useEffect, useMemo, useRef, useState } from 'react'
import { createCamera, deleteCamera, updateCamera } from '../api'
import type { CameraPreset } from '../types'
import { sourceLabel } from '../runview'
import { Button, Card, DiscardPrompt, ErrorBanner, Field, NativeSelect, TextArea, TextInput, enfocarCuandoAparezca } from './ui'

const PLUGINS = ['rtsp', 'oak_d', 'video_file', 'image_folder']

/** Contrato del almacén de cámaras (`camera_store._ID_RE`). */
const ID_RE = /^[a-z0-9_-]+$/

/** Forma mínima de la configuración de cada fuente, para mostrar al lado del
 *  editor. Es un ejemplo: no se inserta ni se exige — la configuración sigue
 *  siendo el objeto completo que la persona escriba, con las claves que sean. */
const EJEMPLO: Record<string, string> = {
  rtsp: '{ "url": "rtsp://usuario:clave@192.168.1.50:554/stream1" }',
  oak_d: '{ "url": "192.168.1.50" }',
  video_file: '{ "path": "/ruta/al/video.mp4" }',
  image_folder: '{ "path": "/ruta/a/las/imagenes" }',
}

interface Props {
  initial: CameraPreset | null
  onSaved: () => void
  onClose: () => void
  /** Avisa si hay cambios sin guardar, para preguntar antes de pasar a otra
   *  cámara o cerrar desde afuera. */
  onDirtyChange?: (dirty: boolean) => void
}

/**
 * Alta y edición de una cámara: `{id, name, plugin, config}`.
 *
 * La configuración es JSON completo, no un constructor que sólo conoce
 * algunas propiedades: una clave anidada que esta consola no conoce sobrevive
 * a la edición tal cual. Se valida que sea JSON y que sea un objeto (no `null`
 * ni un arreglo); `{}` sigue siendo válido.
 *
 * La identidad del formulario es la cámara: quien lo monta le pone `key` por
 * id, y el borrador se compara contra su propia línea de base. Así los campos
 * de una cámara nunca viajan en el PUT de otra.
 */
export default function CameraPresetForm({ initial, onSaved, onClose, onDirtyChange }: Props) {
  const base = useMemo(
    () => ({
      id: initial?.id ?? '',
      name: initial?.name ?? '',
      plugin: initial?.plugin ?? 'rtsp',
      configText: initial ? JSON.stringify(initial.config, null, 2) : '{}',
    }),
    [initial],
  )
  const [id, setId] = useState(base.id)
  const [name, setName] = useState(base.name)
  const [plugin, setPlugin] = useState(base.plugin)
  const [configText, setConfigText] = useState(base.configText)
  const [idError, setIdError] = useState<string | undefined>(undefined)
  const [configError, setConfigError] = useState<string | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<'guardar' | 'eliminar' | null>(null)
  const ocupado = useRef(false)
  const [preguntarCierre, setPreguntarCierre] = useState(false)

  const dirty =
    id !== base.id || name !== base.name || plugin !== base.plugin || configText !== base.configText
  const avisar = useRef(onDirtyChange)
  avisar.current = onDirtyChange
  useEffect(() => {
    avisar.current?.(dirty)
  }, [dirty])

  // Al abrir, el foco va al título del formulario: el botón que lo abrió
  // (Agregar, Editar) puede no seguir en pantalla.
  useEffect(() => {
    enfocarCuandoAparezca('.eo-camform .eo-card__title')
  }, [])

  const save = async () => {
    if (ocupado.current) return
    setError(null)
    if (!initial && !ID_RE.test(id)) {
      setIdError('Sólo minúsculas, números, guion y guion bajo (a-z, 0-9, -, _).')
      document.getElementById('eo-camara-id')?.focus()
      return
    }
    setIdError(undefined)
    let config: Record<string, unknown>
    try {
      const parsed: unknown = JSON.parse(configText)
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setConfigError('La configuración tiene que ser un objeto JSON, por ejemplo {}.')
        document.getElementById('eo-camara-config')?.focus()
        return
      }
      config = parsed as Record<string, unknown>
      setConfigError(undefined)
    } catch (e) {
      setConfigError(`JSON inválido: ${e instanceof Error ? e.message : String(e)}`)
      document.getElementById('eo-camara-config')?.focus()
      return
    }
    const preset: CameraPreset = { id, name, plugin, config }
    ocupado.current = true
    setBusy('guardar')
    try {
      if (initial) {
        await updateCamera(initial.id, preset)
      } else {
        await createCamera(preset)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      ocupado.current = false
      setBusy(null)
      return
    }
    ocupado.current = false
    setBusy(null)
    // Guardado: refrescar la lista es responsabilidad de quien lo monta, y un
    // fallo ahí no convierte esta escritura en fallida.
    onSaved()
  }

  const remove = async () => {
    if (!initial || ocupado.current) return
    if (!window.confirm(`¿Borrar el preset ${initial.id}?`)) return
    setError(null)
    ocupado.current = true
    setBusy('eliminar')
    try {
      await deleteCamera(initial.id)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      ocupado.current = false
      setBusy(null)
    }
  }

  const cerrar = () => {
    if (dirty) setPreguntarCierre(true)
    else onClose()
  }

  const pluginConocido = PLUGINS.includes(plugin)

  return (
    <Card
      className="eo-camform"
      title={initial ? <>Editar <span className="eo-mono">{initial.id}</span></> : 'Agregar cámara'}
      meta={dirty ? <span className="eo-editor__dirty" role="status">Cambios sin guardar</span> : undefined}
    >
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <div className="eo-fieldgrid">
        <Field
          label="Identificador"
          labelKey="id"
          id="eo-camara-id"
          hint={initial ? 'El identificador no se cambia: es la clave de la cámara.' : 'Minúsculas, números, guion y guion bajo.'}
          error={idError}
        >
          <TextInput value={id} disabled={Boolean(initial)} onChange={(e) => setId(e.target.value)} />
        </Field>
        <Field label="Nombre" labelKey="name" hint="Cómo aparece en las listas.">
          <TextInput value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
      </div>
      <Field label="Tipo de fuente" labelKey="plugin">
        <NativeSelect value={plugin} onChange={(e) => setPlugin(e.target.value)}>
          {/* Un tipo que trae la cámara y esta consola no conoce se muestra tal
              cual, sin reemplazarlo por otro. */}
          {!pluginConocido && <option value={plugin}>{plugin}</option>}
          {PLUGINS.map((p) => (
            <option key={p} value={p}>{sourceLabel(p)} ({p})</option>
          ))}
        </NativeSelect>
      </Field>
      <Field
        label="Configuración"
        labelKey="config (JSON)"
        id="eo-camara-config"
        hint={
          <>
            Objeto JSON con las claves de la fuente; se guarda completo, también las que esta
            pantalla no conoce.{' '}
            {EJEMPLO[plugin] && (
              <>Forma habitual para {sourceLabel(plugin)}: <code className="eo-mono">{EJEMPLO[plugin]}</code></>
            )}
          </>
        }
        error={configError}
      >
        <TextArea
          className="eo-input--mono"
          rows={8}
          spellCheck={false}
          value={configText}
          onChange={(e) => setConfigText(e.target.value)}
        />
      </Field>
      {preguntarCierre && (
        <DiscardPrompt what="la cámara" onKeep={() => setPreguntarCierre(false)} onDiscard={onClose} />
      )}
      <div className="eo-actions">
        <Button
          variant="primary"
          onClick={() => void save()}
          disabled={busy !== null}
          aria-busy={busy === 'guardar' || undefined}
        >
          {busy === 'guardar' ? 'Guardando…' : 'Guardar'}
        </Button>
        <Button onClick={cerrar} disabled={busy !== null}>Cerrar</Button>
        {initial && (
          <Button variant="danger" onClick={() => void remove()} disabled={busy !== null}>
            {busy === 'eliminar' ? 'Eliminando…' : 'Eliminar'}
          </Button>
        )}
      </div>
    </Card>
  )
}
