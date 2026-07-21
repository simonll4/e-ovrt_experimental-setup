import { useCallback, useEffect, useState } from 'react'

import { ApiError, getRecording, nextTake, startRecording, stopRecording } from '../api'
import type { RecordingStatus } from '../types'

const SCENARIOS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']
const VARIANTS = ['a', 'b', 'c']
// Regla de oro 3 de doc 59: se filma 30-35 s aunque el clip final sea de 20 s,
// porque el re-ventaneo con onset en t~3-4 s se hace despues.
const MIN_TAKE_MS = 30_000
// El backend solo evalua el corte de seguridad por max_duration_s dentro de
// status(): sin este polling nadie vuelve a llamarlo mientras se graba, y la
// salvaguarda no se dispara nunca (queda grabando hasta llenar el disco).
// Ademas es la unica forma de que la UI se entere si el subproceso murio.
const POLL_MS = 1_000

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const mb = bytes / (1024 * 1024)
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

/** El `message` de ApiError es solo "API <status>": el motivo real que manda el
 * backend (ocupado por preview, cámara desconocida, toma ya existente) viaja en
 * `payload.detail`. Sin esto el operador ve "API 409" en pleno rodaje. Mismo
 * patrón que usa el resto de la consola. */
function mensajeDeError(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: unknown }
    if (typeof payload.detail === 'string') return payload.detail
    if (payload.detail != null) return JSON.stringify(payload.detail)
    return e.message
  }
  return e instanceof Error ? e.message : String(e)
}

export default function RecordPanel({ cameraId }: { cameraId: string | null }) {
  const [scenario, setScenario] = useState('P1')
  const [variant, setVariant] = useState('a')
  const [basename, setBasename] = useState<string | null>(null)
  const [status, setStatus] = useState<RecordingStatus>({ state: 'idle' })
  const [error, setError] = useState<string | null>(null)
  const [last, setLast] = useState<RecordingStatus | null>(null)

  useEffect(() => {
    nextTake(scenario, variant)
      .then((r) => setBasename(r.basename))
      .catch((e: unknown) => setError(mensajeDeError(e)))
  }, [scenario, variant])

  useEffect(() => {
    getRecording()
      .then(setStatus)
      .catch(() => undefined)
  }, [])

  // Mientras se graba, se re-consulta el backend en vez de derivar el cronometro
  // de un timer local: eso es lo que dispara la evaluacion de max_duration_s en
  // el backend (F1) y lo que entera al operador si el subproceso murio (F2). El
  // elapsed_ms/size_bytes que muestra el panel viene siempre de esta respuesta,
  // nunca de un reloj propio (que ademas queda en un numero absurdo si se
  // recarga la pagina con una toma en curso).
  useEffect(() => {
    if (status.state !== 'recording') return
    const id = window.setInterval(() => {
      getRecording()
        .then((r) => {
          setStatus(r)
          if (r.state === 'finished') setLast(r)
        })
        .catch(() => undefined)
    }, POLL_MS)
    return () => window.clearInterval(id)
  }, [status.state])

  const onStart = useCallback(async () => {
    if (!cameraId) return
    setError(null)
    setLast(null)
    try {
      setStatus(await startRecording({ camera_id: cameraId, scenario, variant }))
    } catch (e) {
      setError(mensajeDeError(e))
      setStatus({ state: 'idle' })
    }
  }, [cameraId, scenario, variant])

  const onStop = useCallback(async () => {
    setError(null)
    try {
      const final = await stopRecording()
      setLast(final)
      setStatus({ state: 'idle' })
      const r = await nextTake(scenario, variant)
      setBasename(r.basename)
    } catch (e) {
      setError(mensajeDeError(e))
    }
  }, [scenario, variant])

  const recording = status.state === 'recording'
  const elapsed = status.elapsed_ms ?? 0
  const seconds = Math.floor(elapsed / 1000)

  return (
    <section className="record-panel">
      <h3>Grabar toma</h3>

      <label htmlFor="rec-scenario">Escenario</label>
      <select
        id="rec-scenario"
        value={scenario}
        disabled={recording}
        onChange={(e) => setScenario(e.target.value)}
      >
        {SCENARIOS.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <label htmlFor="rec-variant">Variante</label>
      <select
        id="rec-variant"
        value={variant}
        disabled={recording}
        onChange={(e) => setVariant(e.target.value)}
      >
        {VARIANTS.map((v) => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>

      <p className="record-basename">Próxima toma: <strong>{basename ?? '—'}</strong></p>

      {recording ? (
        <>
          <p className={elapsed >= MIN_TAKE_MS ? 'rec-ok' : 'rec-corta'}>
            ● REC {seconds}s, {formatBytes(status.size_bytes ?? 0)}{' '}
            {elapsed >= MIN_TAKE_MS ? '' : '(no cortar antes de 30 s)'}
          </p>
          <button type="button" onClick={onStop}>Detener</button>
        </>
      ) : (
        <button type="button" onClick={onStart} disabled={!cameraId}>
          Grabar
        </button>
      )}

      {status.state === 'error' && (
        <p className="record-error">
          La grabación se interrumpió: {status.error ?? 'motivo desconocido'}
        </p>
      )}

      {error && <p className="record-error">{error}</p>}

      {last && (
        <div className="record-summary">
          <p>
            {last.basename}: {Math.round((last.duration_ms ?? 0) / 1000)}s, {last.resolution ?? '?'},{' '}
            {last.fps ? `${last.fps.toFixed(2)} fps` : 'fps desconocido'}
          </p>
          {(last.duration_ms ?? 0) < MIN_TAKE_MS && (
            <p className="rec-corta">Toma de menos de 30 s: revisá si sirve (regla de oro 3).</p>
          )}
          {last.truncated && <p className="record-error">Toma truncada: {last.error}</p>}
          {last.suspected_substream && (
            <p className="record-error">
              Resolución baja: puede que el preset apunte al substream del DVR.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
