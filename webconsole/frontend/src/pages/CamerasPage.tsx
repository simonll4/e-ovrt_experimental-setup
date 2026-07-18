import { useEffect, useState } from 'react'
import {
  ApiError, deleteCamera, getPreview, listCameras, startPreview, stopPreview,
} from '../api'
import CameraPresetForm from '../components/CameraPresetForm'
import LiveViewer from '../components/LiveViewer'
import LivePromptPanel from '../components/LivePromptPanel'
import { Badge, Card, DetChip, EmptyState, ErrorBanner } from '../components/ui'
import { usePreviewStream } from '../preview'
import { useTargetModelRef } from '../useTarget'
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
  const [mode, setMode] = useState<'raw' | 'detect'>('raw')
  const [threshold, setThreshold] = useState<number | null>(0.3)
  const [promptDraft, setPromptDraft] = useState<PromptSetDetail | null>(null)
  const [activeClassIds, setActiveClassIds] = useState<string[]>([])
  const [streaming, setStreaming] = useState(false)
  const [resumable, setResumable] = useState(false)
  const [busy, setBusy] = useState<{ reason: string; runId?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
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
    })
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

  const currentDetections = live.header?.detections ?? []
  const totalsByLabel = aggregateByLabel(currentDetections)
  const needsPromptSet = mode === 'detect' && !promptDraft

  return (
    <div>
      <h2 className="eo-inline">
        <span>Cámaras</span>
        {modelRef && <Badge tone="neutral">modelo: {modelRef}</Badge>}
      </h2>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {busy && (
        <ErrorBanner>
          {busy.reason === 'run_active' ? (
            <>
              Hay un run en ejecución: {busy.runId}. Detenelo para usar la prueba de cámaras.{' '}
              {busy.runId && <a href={`#/runs/${busy.runId}`}>ver run</a>}
            </>
          ) : (
            <>Ya hay una sesión de preview activa.</>
          )}{' '}
          <button type="button" onClick={recheck}>Reintentar</button>
        </ErrorBanner>
      )}
      {resumable && !streaming && (
        <p className="eo-note eo-note--warn">
          Hay un stream de preview en curso.{' '}
          <button type="button" onClick={resume}>Retomar stream</button>{' '}
          <button type="button" onClick={() => void disconnect()}>Detener</button>
        </p>
      )}
      <Card title="Viewer">
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
          <div style={{ display: 'grid', gap: 'var(--space-3)', marginTop: 'var(--space-3)' }}>
            <div className="eo-stats-row">
              <button type="button" onClick={() => void disconnect()}>Desconectar</button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-1)' }}>
              {totalsByLabel.map(([label, count]) => (
                <DetChip key={label} label={label} count={count} />
              ))}
            </div>
          </div>
        )}
      </Card>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(220px, 1fr) minmax(280px, 1.4fr)',
          gap: 'var(--space-5)',
          alignItems: 'start',
          marginTop: 'var(--space-5)',
        }}
      >
        <Card title="Presets">
          {editing === 'new' && (
            <CameraPresetForm
              initial={null}
              onSaved={() => { setEditing(null); refreshPresets() }}
              onClose={() => setEditing(null)}
            />
          )}
          {editing && editing !== 'new' && (
            <CameraPresetForm
              initial={editing}
              onSaved={() => { setEditing(null); refreshPresets() }}
              onClose={() => setEditing(null)}
            />
          )}
          {!editing && (
            <>
              <button type="button" onClick={() => setEditing('new')}>Nuevo preset</button>
              {needsPromptSet && (
                <p className="eo-note eo-note--warn">
                  Elegí un prompt set en el panel de Detección para poder conectar.
                </p>
              )}
              <ul className="eo-list">
                {presets.map((p) => (
                  <li key={p.id}>
                    <span>{p.name}</span> <small className="eo-note">({p.plugin})</small>
                    <div className="eo-actions">
                      <button
                        type="button"
                        disabled={Boolean(busy) || needsPromptSet}
                        onClick={() => void connect(p)}
                      >
                        Conectar
                      </button>
                      <button type="button" onClick={() => setEditing(p)}>Editar</button>
                      <button
                        type="button"
                        className="eo-btn--danger"
                        onClick={() => {
                          if (!window.confirm(`¿Borrar el preset ${p.id}?`)) return
                          void deleteCamera(p.id).then(refreshPresets)
                        }}
                      >
                        Eliminar
                      </button>
                    </div>
                  </li>
                ))}
                {presets.length === 0 && <EmptyState>Sin presets de cámara todavía.</EmptyState>}
              </ul>
            </>
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
  )
}
