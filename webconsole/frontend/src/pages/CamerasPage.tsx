import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ApiError, deleteCamera, getPreview, listCameras, startPreview, stopPreview,
} from '../api'
import CameraPresetForm from '../components/CameraPresetForm'
import LiveViewer from '../components/LiveViewer'
import LivePromptPanel from '../components/LivePromptPanel'
import RecordPanel from '../components/RecordPanel'
import {
  Button, Card, DetChip, DiscardPrompt, ErrorBanner, IconNavCameras, InlineDeleteConfirm,
  LoadingState, PageHeader, enfocarCuandoAparezca,
} from '../components/ui'
import { usePreviewStream } from '../preview'
import { useTargetModelRef } from '../api/queries/platform'
import { sourceLabel } from '../runview'
import type {
  CameraPreset, PreviewDetection, PreviewStartBody, PromptSetDetail,
} from '../types'

function draftToSetInline(draft: PromptSetDetail): Record<string, unknown> {
  return {
    id: draft.id,
    description: draft.description ?? null,
    language: draft.language ?? null,
    classes: draft.classes.map((c) => ({
      id: c.id,
      canonical: c.canonical ?? null,
      role: c.role ?? null,
      strategy: c.strategy ?? null,
      condition_id: c.condition_id ?? null,
      enabled_by_default: c.enabled_by_default ?? true,
      phrasings: c.phrasings,
    })),
  }
}

/** De dónde sale la imagen de esta cámara, para el subtítulo de su fila.
 *
 *  La clave depende del plugin: `url` en RTSP y OAK-D, `path` en las cámaras de
 *  archivo que usa el entorno de prueba. Mirando solo `url`, esas últimas
 *  aparecían como «sin dirección» teniendo una perfectamente visible. */
function direccionDe(config: Record<string, unknown>): string {
  const valor = config.url ?? config.path
  return typeof valor === 'string' && valor ? valor : 'sin dirección'
}

function aggregateByLabel(detections: PreviewDetection[] | undefined): Array<[string, number]> {
  if (!detections) return []
  const counts = new Map<string, number>()
  for (const d of detections) counts.set(d.label, (counts.get(d.label) ?? 0) + 1)
  return [...counts.entries()]
}

export default function CamerasPage() {
  // La lista de cámaras con su estado: una lista vacía mientras carga, o
  // porque falló, no es «todavía no guardaste ninguna cámara».
  const [lista, setLista] = useState<{ estado: 'cargando' | 'lista' | 'error'; error?: string }>({ estado: 'cargando' })
  const [presets, setPresets] = useState<CameraPreset[]>([])
  const [editing, setEditing] = useState<CameraPreset | null | 'new'>(null)
  const [formDirty, setFormDirty] = useState(false)
  // Pedido de abrir otro formulario (o cerrar) mientras el abierto tiene
  // cambios sin guardar.
  const [pedido, setPedido] = useState<{ destino: CameraPreset | null | 'new' } | null>(null)
  const [connected, setConnected] = useState<CameraPreset | null>(null)
  // Última cámara elegida por el operador (conectada o simplemente seleccionada
  // para grabar). A diferencia de `connected`, NO se limpia al desconectar el
  // preview: el guion de rodaje es conectar → verificar encuadre → cortar
  // preview → recién ahí grabar (grabar y previsualizar son excluyentes, el
  // backend devuelve 409 si hay un preview activo), así que el panel de
  // grabación necesita seguir sabiendo qué cámara usar después de desconectar.
  const [lastChosen, setLastChosen] = useState<CameraPreset | null>(null)
  const [mode, setMode] = useState<'raw' | 'detect'>('raw')
  const [threshold, setThreshold] = useState<number | null>(0.3)
  const [promptDraft, setPromptDraft] = useState<PromptSetDetail | null>(null)
  const [activeClassIds, setActiveClassIds] = useState<string[]>([])
  const [streaming, setStreaming] = useState(false)
  const [resumable, setResumable] = useState(false)
  const [busy, setBusy] = useState<{ reason: string; runId?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conectando, setConectando] = useState<string | null>(null)
  // Qué cámara tiene abierta la confirmación de borrado. Reemplaza al
  // `window.confirm()`, que corta el hilo de la pantalla con un diálogo del
  // sistema operativo y no se puede leer con el mismo lenguaje visual.
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [borrando, setBorrando] = useState<string | null>(null)
  const [errorBorrado, setErrorBorrado] = useState<string | null>(null)
  const live = usePreviewStream(streaming)
  const modelRef = useTargetModelRef()

  const refreshPresets = () => {
    setLista((l) => ({ ...l, estado: l.estado === 'lista' ? 'lista' : 'cargando' }))
    void listCameras()
      .then((items) => {
        setPresets(items)
        setLista({ estado: 'lista' })
      })
      .catch((e) => setLista({ estado: 'error', error: String(e) }))
  }

  useEffect(() => { refreshPresets() }, [])

  // Al montar: si ya hay una sesión de preview `streaming` (dejada por otra pestaña o
  // por un remount), ofrecemos retomarla en vez de pisarla con un POST nuevo.
  useEffect(() => {
    void getPreview().then((s) => {
      if (s.status === 'streaming') setResumable(true)
    }).catch(() => setError('No se pudo consultar la previsualización. Verificá el motor de detección antes de conectar.'))
    return () => {
      void stopPreview().catch(() => undefined)
    }
  }, [])

  const recheck = () => {
    setBusy(null)
    void getPreview()
      .then((s) => {
        if (s.status === 'streaming') setResumable(true)
      })
      .catch(() => undefined)
  }

  const connect = async (preset: CameraPreset) => {
    if (conectando) return
    setError(null)
    setBusy(null)
    const body: PreviewStartBody = {
      mode,
      ingest: { plugin: preset.plugin, config: preset.config },
    }
    if (mode === 'detect' && promptDraft) {
      body.prompts = { set_inline: draftToSetInline(promptDraft), active_ids: activeClassIds }
      body.params = { score_threshold: threshold }
    }
    setConectando(preset.id)
    try {
      await stopPreview().catch(() => undefined)
      setStreaming(false)
      await startPreview(body)
      setConnected(preset)
      setLastChosen(preset)
      setResumable(false)
      setStreaming(true)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        const payload = (e.payload ?? {}) as { reason?: string; active_run_id?: string }
        setBusy({ reason: payload.reason ?? 'run_active', runId: payload.active_run_id })
      } else {
        setError(e instanceof Error ? e.message : String(e))
      }
    } finally {
      setConectando(null)
    }
  }

  const disconnect = async () => {
    setStreaming(false)
    setResumable(false)
    setConnected(null)
    await stopPreview().catch(() => undefined)
  }

  const resume = () => {
    setResumable(false)
    setStreaming(true)
  }

  const apply = () => {
    if (connected) void connect(connected)
  }

  const borrar = (p: CameraPreset) => {
    if (borrando) return
    setConfirmId(null)
    setErrorBorrado(null)
    setBorrando(p.id)
    void deleteCamera(p.id)
      .then(() => {
        // Sin esto queda una cámara fantasma en el panel de grabación: el botón
        // sigue habilitado sobre una cámara que ya no existe y falla recién al
        // grabar.
        setLastChosen((prev) => (prev?.id === p.id ? null : prev))
        if (editing !== 'new' && editing?.id === p.id) {
          setEditing(null)
          setFormDirty(false)
        }
        refreshPresets()
      })
      .catch((e) => setErrorBorrado(`No se pudo eliminar ${p.name || p.id}: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => setBorrando(null))
  }

  /** Abrir otra cámara en el formulario, una nueva, o cerrarlo. Con cambios sin
   *  guardar se pregunta antes: los campos de una cámara nunca pasan a otra. */
  const abrirFormulario = (destino: CameraPreset | null | 'new') => {
    const mismo = destino === editing || (destino !== 'new' && editing !== 'new' && destino?.id === editing?.id)
    if (mismo) return
    if (editing !== null && formDirty) {
      setPedido({ destino })
      return
    }
    setPedido(null)
    setFormDirty(false)
    setEditing(destino)
  }

  // El formulario se va con su botón Cerrar: el foco vuelve a la lista de
  // cámaras, o al vacío si no hay ninguna.
  const cerrarFormulario = () => {
    setFormDirty(false)
    setEditing(null)
    enfocarCuandoAparezca('#eo-camaras-guardadas .eo-card__title, .eo-bigempty h2')
  }

  const currentDetections = live.header?.detections ?? []
  const totalsByLabel = aggregateByLabel(currentDetections)
  const needsPromptSet = mode === 'detect' && !promptDraft
  const formularioAbierto = editing !== null
  const sinCamaras = lista.estado === 'lista' && presets.length === 0

  const formulario = formularioAbierto && (
    <>
      {pedido && (
        <DiscardPrompt
          what="la cámara que estás editando"
          onKeep={() => setPedido(null)}
          onDiscard={() => {
            setFormDirty(false)
            setEditing(pedido.destino)
            setPedido(null)
          }}
        />
      )}
      {/* Identidad estable: el formulario de una cámara es otro componente que
          el de la siguiente, con su propia línea de base. */}
      <CameraPresetForm
        key={editing === 'new' ? 'camera:new' : `camera:${editing.id}`}
        initial={editing === 'new' ? null : editing}
        onDirtyChange={setFormDirty}
        onSaved={() => { cerrarFormulario(); refreshPresets() }}
        onClose={cerrarFormulario}
      />
    </>
  )

  return (
    <>
      <PageHeader
        title="Cámaras"
        meta={
          <>
            <span>Guardá una cámara para poder probarla y usarla en las corridas</span>
            {modelRef && (
              <>
                <span className="eo-sep">·</span>
                <span>modelo activo <span className="eo-mono">{modelRef}</span></span>
              </>
            )}
          </>
        }
        actions={
          !sinCamaras && lista.estado === 'lista' && !formularioAbierto ? (
            <Button variant="primary" onClick={() => abrirFormulario('new')}>Agregar cámara</Button>
          ) : undefined
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {busy && (
        <ErrorBanner>
          {busy.reason === 'run_active' ? (
            <>
              Hay una corrida en curso: {busy.runId}. Detenela para poder probar la cámara.{' '}
              {busy.runId && <Link to={`/runs/${busy.runId}`}>ver corrida</Link>}
            </>
          ) : (
            <>Ya hay una prueba de cámara activa.</>
          )}{' '}
          <Button onClick={recheck}>Reintentar</Button>
        </ErrorBanner>
      )}
      {resumable && !streaming && (
        <div className="eo-stale" role="status">
          <span>Hay una prueba de cámara en curso.</span>
          <Button onClick={resume}>Retomar</Button>
          <Button onClick={() => void disconnect()}>Detener</Button>
        </div>
      )}

      {sinCamaras && !formularioAbierto ? (
        <Card>
          <div className="eo-bigempty">
            <IconNavCameras />
            <h2>Todavía no guardaste ninguna cámara</h2>
            <p>
              Una cámara guardada te deja verificar el encuadre antes de lanzar una corrida, y
              después elegirla desde Nueva corrida sin volver a escribir la dirección.
            </p>
            <Button variant="primary" onClick={() => abrirFormulario('new')}>
              Agregar la primera cámara
            </Button>
          </div>
        </Card>
      ) : (
        <div className="eo-cams">
          <div className="eo-cams__col">
            {formulario}

            <Card
              id="eo-camaras-guardadas"
              title="Cámaras guardadas"
              meta={lista.estado === 'lista' ? String(presets.length) : undefined}
              flush
            >
              {lista.estado === 'cargando' && presets.length === 0 && (
                <LoadingState lines={2}>Cargando las cámaras guardadas…</LoadingState>
              )}
              {lista.estado === 'error' && (
                <ErrorBanner detail={lista.error} onRetry={refreshPresets}>
                  No se pudo leer la lista de cámaras. No se sabe si hay alguna guardada.
                </ErrorBanner>
              )}
              {errorBorrado && <ErrorBanner>{errorBorrado}</ErrorBanner>}
              {needsPromptSet && presets.length > 0 && (
                <p className="eo-note eo-note--warn eo-cams__note">
                  Elegí un conjunto de prompts en <b>Qué mostrar</b> para poder probar.
                </p>
              )}
              {presets.map((p) => (
                <div key={p.id} className="eo-lrow" aria-current={connected?.id === p.id}>
                  <span className="eo-lrow__main">
                    <b>{p.name}</b>
                    <span>
                      {sourceLabel(p.plugin)} · {direccionDe(p.config)}
                    </span>
                  </span>
                  <span className="eo-lrow__actions">
                    {confirmId === p.id ? (
                      <InlineDeleteConfirm
                        onConfirm={() => borrar(p)}
                        onCancel={() => setConfirmId(null)}
                      />
                    ) : (
                      <>
                        {connected?.id === p.id ? (
                          <Button variant="ghost" onClick={() => void disconnect()}>
                            Desconectar
                          </Button>
                        ) : (
                          <Button
                            disabled={Boolean(busy) || needsPromptSet || conectando != null}
                            aria-busy={conectando === p.id || undefined}
                            onClick={() => void connect(p)}
                          >
                            {conectando === p.id ? 'Conectando…' : 'Probar'}
                          </Button>
                        )}
                        <Button variant="ghost" onClick={() => abrirFormulario(p)}>Editar</Button>
                        <Button
                          variant="ghost"
                          aria-label={`Eliminar ${p.name}`}
                          disabled={borrando === p.id}
                          onClick={() => setConfirmId(p.id)}
                        >
                          {borrando === p.id ? 'Eliminando…' : 'Eliminar'}
                        </Button>
                      </>
                    )}
                  </span>
                </div>
              ))}
            </Card>

            {/* Con la lista resuelta, como antes: el panel consulta grabaciones
                al montarse y no tiene nada que grabar sin cámaras conocidas. */}
            {lista.estado === 'lista' && (
              <RecordPanel cameras={presets} connectedId={lastChosen?.id ?? null} />
            )}
          </div>

          <div className="eo-cams__col">
            <Card title="Vista de la cámara">
              {live.finalState?.status === 'error' && (
                <ErrorBanner>{live.finalState.error}</ErrorBanner>
              )}
              <LiveViewer
                frameUrl={live.frameUrl}
                header={live.header}
                connected={live.connected}
                fps={live.fps}
                mode={mode}
              />
              {live.frameUrl && (
                <div className="eo-cams__under">
                  <Button onClick={() => void disconnect()}>Desconectar</Button>
                  <span className="eo-cams__dets">
                    {totalsByLabel.map(([label, count]) => (
                      <DetChip key={label} label={label} count={count} />
                    ))}
                  </span>
                </div>
              )}
            </Card>

            <LivePromptPanel
              mode={mode}
              onModeChange={setMode}
              draft={promptDraft}
              onDraftChange={setPromptDraft}
              activeClassIds={activeClassIds}
              onActiveChange={setActiveClassIds}
              threshold={threshold}
              onThresholdChange={setThreshold}
              onApply={apply}
              disabled={!connected || Boolean(busy)}
            />
          </div>
        </div>
      )}
    </>
  )
}
