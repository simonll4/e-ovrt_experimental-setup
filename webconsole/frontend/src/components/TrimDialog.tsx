import { useRef, useState } from 'react'

import { ApiError, generateClip, masterMediaUrl } from '../api'
import type { GenerateClipResult, MasterEntry } from '../types'
import Card from './ui/Card'
import ErrorBanner from './ui/ErrorBanner'
import Field from './ui/Field'

const SCENARIOS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']

/** Mismo patrón que RecordPanel: el motivo real del backend viaja en
 * payload.detail (p. ej. la salida completa de prepare_clip.sh). */
function mensajeDeError(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: unknown }
    if (typeof payload.detail === 'string') return payload.detail
    if (payload.detail != null) return JSON.stringify(payload.detail)
    return e.message
  }
  return e instanceof Error ? e.message : String(e)
}

export default function TrimDialog({
  master,
  onClose,
  onGenerated,
}: {
  master: MasterEntry
  onClose: () => void
  onGenerated: () => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [tEvent, setTEvent] = useState<number | null>(null)
  const [tEnd, setTEnd] = useState<number | null>(null)
  const [scenario, setScenario] = useState(master.scenario ?? '')
  const [regenerate, setRegenerate] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<GenerateClipResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const listo = tEvent != null && tEnd != null && scenario !== '' && !busy

  const generar = async () => {
    if (tEvent == null || tEnd == null) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const body = {
        master: master.name,
        t_event_s: tEvent,
        t_end_s: tEnd,
        ...(master.scenario == null ? { scenario } : {}),
        ...(regenerate !== '' ? { clip_id: regenerate } : {}),
      }
      const r = await generateClip(body)
      setResult(r)
      onGenerated()
    } catch (e: unknown) {
      setError(mensajeDeError(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title={`Recortar ${master.name}`}>
      <video
        ref={videoRef}
        controls
        src={masterMediaUrl(master.name)}
        data-testid="trim-video"
        className="eo-trim__video eo-video"
      />

      <div className="eo-trim__marks">
        <button type="button" onClick={() => setTEvent(videoRef.current?.currentTime ?? 0)}>
          Marcar evento
        </button>
        <span>{tEvent != null ? `${tEvent.toFixed(1)} s` : 'sin marcar'}</span>
        <button type="button" onClick={() => setTEnd(videoRef.current?.currentTime ?? 0)}>
          Marcar fin
        </button>
        <span>{tEnd != null ? `${tEnd.toFixed(1)} s` : 'sin marcar'}</span>
      </div>

      <div className="eo-trim__fields">
        {master.scenario == null ? (
          <Field label="Escenario">
            <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
              <option value="">elegir…</option>
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
        ) : (
          <p className="eo-note">Escenario {master.scenario} (heredado del master)</p>
        )}

        {master.clips.length > 0 && (
          <Field label="Regenerar">
            <select value={regenerate} onChange={(e) => setRegenerate(e.target.value)}>
              <option value="">(nuevo)</option>
              {master.clips.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </Field>
        )}
      </div>
      {regenerate !== '' && (
        <p className="eo-trim__warn">Regenerar invalida la pre-anotación vieja de ese clip.</p>
      )}

      <div className="eo-actions">
        <button type="button" className="eo-btn--primary" onClick={generar} disabled={!listo}>
          {busy ? 'Generando…' : 'Generar clip'}
        </button>
        <button type="button" onClick={onClose}>Cerrar</button>
      </div>

      {result && (
        <div className="eo-trim__result">
          <p>✓ {result.clip_id} generado ({result.info.n_frames} frames)</p>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <ErrorBanner>{error}</ErrorBanner>}
    </Card>
  )
}
