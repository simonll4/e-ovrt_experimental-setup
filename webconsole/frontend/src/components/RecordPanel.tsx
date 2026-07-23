import { useCallback, useEffect, useState } from 'react'

import { ApiError, getRecording, nextTake, startRecording, stopRecording } from '../api'
import type { CameraPreset, RecordingStatus } from '../types'

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

/** `connectedId` es la cámara conectada en el preview: solo PRE-SELECCIONA el
 * selector (el guion es conectar → verificar encuadre → desconectar → grabar).
 * Quien manda al grabar es siempre lo elegido acá — antes la única forma de
 * elegir fuente era conectar su preview, y el operador se encontraba con el
 * botón Grabar en gris sin ninguna pista (F-DR5, dry-run 2026-07-22). */
export default function RecordPanel({
  cameras,
  connectedId,
}: {
  cameras: CameraPreset[]
  connectedId: string | null
}) {
  const [scenario, setScenario] = useState('P1')
  const [variant, setVariant] = useState('a')
  const [cameraId, setCameraId] = useState<string>(connectedId ?? '')
  const [basename, setBasename] = useState<string | null>(null)
  const [status, setStatus] = useState<RecordingStatus>({ state: 'idle' })
  const [error, setError] = useState<string | null>(null)
  const [last, setLast] = useState<RecordingStatus | null>(null)

  // Conectar el preview de una cámara la propone como fuente, pero sin pisar
  // una elección explícita distinta que el operador ya haya hecho acá.
  useEffect(() => {
    if (connectedId) setCameraId((prev) => (prev === '' ? connectedId : prev))
  }, [connectedId])

  // Si la cámara elegida desaparece (preset borrado), se limpia la elección:
  // dejarla apuntando a un id inexistente falla recién al grabar.
  useEffect(() => {
    if (cameraId && !cameras.some((c) => c.id === cameraId)) setCameraId('')
  }, [cameras, cameraId])

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
    // También se pollea en 'starting': es lo único que detecta la transición a
    // 'recording' cuando el device termina de conectar (F-DR6).
    if (status.state !== 'recording' && status.state !== 'starting') return
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
      // No asumir 'idle': si el backend rechazó porque YA hay una toma activa
      // (409), forzarlo deja la UI mintiendo Y sin polling, así que no se
      // recupera sola -- hay que recargar la página para enterarse de que la
      // cámara está grabando (F-DR8). Se re-sincroniza con el backend.
      try {
        setStatus(await getRecording())
      } catch {
        setStatus({ state: 'idle' })
      }
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
  const starting = status.state === 'starting'
  // La toma está en curso (no se puede cambiar cámara/escenario, y se puede
  // cortar) tanto mientras el device inicializa como mientras graba.
  const enCurso = recording || starting
  const elapsed = status.elapsed_ms ?? 0
  const seconds = Math.floor(elapsed / 1000)

  return (
    <section className="record-panel">
      <h3>Grabar toma</h3>

      <label htmlFor="rec-camera">Cámara</label>
      <select
        id="rec-camera"
        value={cameraId}
        disabled={enCurso}
        onChange={(e) => setCameraId(e.target.value)}
      >
        <option value="">— elegir cámara —</option>
        {cameras.map((c) => (
          <option key={c.id} value={c.id}>{c.name} ({c.plugin})</option>
        ))}
      </select>

      <label htmlFor="rec-scenario">Escenario</label>
      <select
        id="rec-scenario"
        value={scenario}
        disabled={enCurso}
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
        disabled={enCurso}
        onChange={(e) => setVariant(e.target.value)}
      >
        {VARIANTS.map((v) => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>

      <p className="record-basename">Próxima toma: <strong>{basename ?? '—'}</strong></p>

      {enCurso ? (
        <>
          {starting ? (
            <p className="rec-corta">
              ⏳ Conectando la cámara… <strong>no actúes todavía</strong>: la
              OAK-D tarda unos segundos en empezar a capturar.
            </p>
          ) : (
            <p className={elapsed >= MIN_TAKE_MS ? 'rec-ok' : 'rec-corta'}>
              ● REC {seconds}s, {formatBytes(status.size_bytes ?? 0)}{' '}
              {elapsed >= MIN_TAKE_MS ? '' : '(no cortar antes de 30 s)'}
            </p>
          )}
          <button type="button" onClick={onStop}>Detener</button>
        </>
      ) : (
        <>
          <button type="button" onClick={onStart} disabled={!cameraId}>
            Grabar
          </button>
          {!cameraId && (
            <p className="eo-note">Elegí una cámara para poder grabar.</p>
          )}
        </>
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
