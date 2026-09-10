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
  Badge, Button, Card, DetChip, ErrorBanner, IconNavCameras, InlineDeleteConfirm, PageHeader,
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
  const [presets, setPresets] = useState<CameraPreset[]>([])
  const [editing, setEditing] = useState<CameraPreset | null | 'new'>(null)
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
  // Qué cámara tiene abierta la confirmación de borrado. Reemplaza al
  // `window.confirm()`, que corta el hilo de la pantalla con un diálogo del
  // sistema operativo y no se puede leer con el mismo lenguaje visual.
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const live = usePreviewStream(streaming)
  const modelRef = useTargetModelRef()

  const refreshPresets = () => {
    void listCameras().then(setPresets).catch(() => setPresets([]))
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
    setConfirmId(null)
    void deleteCamera(p.id).then(() => {
      // Sin esto queda una cámara fantasma en el panel de grabación: el botón
      // sigue habilitado sobre una cámara que ya no existe y falla recién al
      // grabar.
      setLastChosen((prev) => (prev?.id === p.id ? null : prev))
      return refreshPresets()
    })
  }

  const currentDetections = live.header?.detections ?? []
  const totalsByLabel = aggregateByLabel(currentDetections)
  const needsPromptSet = mode === 'detect' && !promptDraft
  const formularioAbierto = editing !== null
  const sinCamaras = presets.length === 0

  const formulario = formularioAbierto && (
    <Card title={editing === 'new' ? 'Agregar cámara' : 'Editar cámara'}>
      <CameraPresetForm
        initial={editing === 'new' ? null : editing}
        onSaved={() => { setEditing(null); refreshPresets() }}
        onClose={() => setEditing(null)}
      />
    </Card>
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
                <Badge tone="neutral">modelo: {modelRef}</Badge>
              </>
            )}
          </>
        }
        actions={
          !sinCamaras && !formularioAbierto ? (
            <Button variant="primary" onClick={() => setEditing('new')}>Agregar cámara</Button>
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
        <p className="eo-note eo-note--warn">
          Hay una prueba de cámara en curso.{' '}
          <Button onClick={resume}>Retomar</Button>{' '}
          <Button onClick={() => void disconnect()}>Detener</Button>
        </p>
      )}

      {sinCamaras && !formularioAbierto ? (
        <Card>
          <div className="eo-bigempty">
            <IconNavCameras />
            <h4>Todavía no guardaste ninguna cámara</h4>
            <p>
              Una cámara guardada te deja verificar el encuadre antes de lanzar una corrida, y
              después elegirla desde Nueva corrida sin volver a escribir la dirección.
            </p>
            <Button variant="primary" onClick={() => setEditing('new')}>
              Agregar la primera cámara
            </Button>
          </div>
        </Card>
      ) : (
        <div className="eo-cams">
          <div className="eo-cams__col">
            {formulario}

            {!sinCamaras && (
              <Card title="Cámaras guardadas" meta={String(presets.length)} flush>
                {needsPromptSet && (
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
                              disabled={Boolean(busy) || needsPromptSet}
                              onClick={() => void connect(p)}
                            >
                              Probar
                            </Button>
                          )}
                          <Button variant="ghost" onClick={() => setEditing(p)}>Editar</Button>
                          <Button
                            variant="ghost"
                            aria-label={`Eliminar ${p.name}`}
                            onClick={() => setConfirmId(p.id)}
                          >
                            Eliminar
                          </Button>
                        </>
                      )}
                    </span>
                  </div>
                ))}
              </Card>
            )}

            <RecordPanel cameras={presets} connectedId={lastChosen?.id ?? null} />
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
