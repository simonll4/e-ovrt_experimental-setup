import { useEffect, useRef, useState } from 'react'

import { ApiError, generateClip, masterMediaUrl } from '../api'
import type { GenerateClipResult, MasterEntry } from '../types'
import { Button, Card, ErrorBanner, Field, IconCheck, IconWarn, NativeSelect } from './ui'

const SCENARIOS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9']

// Labels de cada marca por escenario, en orden cronológico (doc operacion/72
// §4 y §5.3). 2 marcas para los escenarios de 1 episodio, 4 para P6/P8.
const MARK_LABELS: Record<string, string[]> = {
  P1: ['casco_fuera', 'casco_puesto'],
  P2: ['chaleco_fuera', 'chaleco_puesto'],
  P3: ['casco_fuera', 'casco_puesto'],
  P4: ['casco_fuera', 'casco_puesto'],
  P5: ['tramo_inicio', 'tramo_fin'],
  P6: ['casco_fuera', 'chaleco_fuera', 'chaleco_puesto', 'casco_puesto'],
  P7: ['casco_fuera', 'casco_puesto'],
  P8: ['casco_fuera', 'sale_de_cuadro', 'vuelve_a_entrar', 'casco_puesto'],
  P9: ['entra_en_cuadro', 'sale_o_termina'],
}
const DEFAULT_LABELS = ['Marcar evento', 'Marcar fin']

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
  const [scenario, setScenario] = useState(master.scenario ?? '')
  // Deriva de `scenario` (el estado, editable vía el <select> para material
  // sin escenario heredado) y no de `master.scenario` — si no, elegir P6/P8
  // en el dropdown no expandía el diálogo a 4 marcas (quedaba en el
  // DEFAULT_LABELS de 2 marcas).
  const labels = MARK_LABELS[scenario] ?? DEFAULT_LABELS
  const [marks, setMarks] = useState<(number | null)[]>(labels.map(() => null))
  const [regenerate, setRegenerate] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<GenerateClipResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [duracionVideo, setDuracionVideo] = useState<number | null>(null)
  // Un solo pedido de generación a la vez: el doble click no corta dos clips.
  const enviando = useRef(false)

  // Al cambiar de escenario (dropdown), reiniciar las marcas: la cantidad de
  // botones puede cambiar (2 <-> 4) y las marcas viejas ya no corresponden.
  useEffect(() => {
    setMarks(labels.map(() => null))
  }, [scenario])

  const marcar = (i: number) => {
    const t = videoRef.current?.currentTime ?? 0
    setMarks((prev) => prev.map((v, idx) => (idx === i ? t : v)))
  }

  const listo = marks.every((m) => m != null) && scenario !== '' && !busy

  const generar = async () => {
    if (!marks.every((m): m is number => m != null) || enviando.current) return
    enviando.current = true
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const body = {
        master: master.name,
        marks,
        ...(master.scenario == null ? { scenario } : {}),
        ...(regenerate !== '' ? { clip_id: regenerate } : {}),
      }
      const r = await generateClip(body)
      setResult(r)
      onGenerated()
    } catch (e: unknown) {
      setError(mensajeDeError(e))
    } finally {
      enviando.current = false
      setBusy(false)
    }
  }

  // La duración, para dibujar las marcas sobre una barra proporcional: la del
  // material si el backend la informó, o la que lee el reproductor.
  const duracion = master.duration_ms != null ? master.duration_ms / 1000 : duracionVideo
  const pct = (t: number) => (duracion ? Math.min(100, Math.max(0, (t / duracion) * 100)) : 0)
  const marcadas = marks.map((m, i) => ({ m, i })).filter((x): x is { m: number; i: number } => x.m != null)

  return (
    <Card title={`Recortar ${master.name}`}>
      <video
        ref={videoRef}
        controls
        src={masterMediaUrl(master.name)}
        data-testid="trim-video"
        className="eo-trim__video eo-video"
        onLoadedMetadata={(e) => {
          const d = (e.currentTarget as HTMLVideoElement).duration
          if (Number.isFinite(d) && d > 0) setDuracionVideo(d)
        }}
      />

      {/* Las marcas en orden: cada botón toma el instante actual del video.
          El siguiente se habilita recién cuando el anterior está marcado. */}
      <ol className="eo-trim__marks" aria-label="Marcas del recorte">
        {labels.map((label, i) => (
          <li key={label} className="eo-trim__mark">
            <span className="eo-trim__n" aria-hidden="true">{i + 1}</span>
            <Button
              disabled={i > 0 && marks[i - 1] == null}
              onClick={() => marcar(i)}
            >
              {label}
            </Button>
            <span className="eo-mono">{marks[i] != null ? `${marks[i]!.toFixed(1)} s` : 'sin marcar'}</span>
          </li>
        ))}
      </ol>

      {/* La misma información, sobre la duración: una barra proporcional con
          el tramo marcado. No se arrastra: sólo muestra. */}
      {duracion != null && (
        <>
          <div
            className="eo-trim__track"
            role="img"
            aria-label={
              marcadas.length
                ? `Marcas sobre ${duracion.toFixed(1)} s: ${marcadas.map(({ m, i }) => `${labels[i]} ${m.toFixed(1)} s`).join(', ')}`
                : `Ninguna marca todavía sobre ${duracion.toFixed(1)} s`
            }
          >
            {marcadas.length >= 2 && (
              <span
                className="eo-trim__range"
                style={{
                  left: `${pct(marcadas[0].m)}%`,
                  width: `${pct(marcadas[marcadas.length - 1].m) - pct(marcadas[0].m)}%`,
                }}
              />
            )}
            {marcadas.map(({ m, i }) => (
              <span key={i} className="eo-trim__pin" style={{ left: `${pct(m)}%` }}>
                <span aria-hidden="true">{i + 1}</span>
              </span>
            ))}
          </div>
          <p className="eo-trim__trackcap">0 s — {duracion.toFixed(1)} s</p>
        </>
      )}

      <div className="eo-trim__fields">
        {master.scenario == null ? (
          <Field label="Escenario">
            <NativeSelect value={scenario} onChange={(e) => setScenario(e.target.value)}>
              <option value="">elegir…</option>
              {SCENARIOS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </NativeSelect>
          </Field>
        ) : (
          <p className="eo-note">Escenario {master.scenario} (heredado del master)</p>
        )}

        {master.clips.length > 0 && (
          <Field label="Regenerar">
            <NativeSelect value={regenerate} onChange={(e) => setRegenerate(e.target.value)}>
              <option value="">(nuevo)</option>
              {master.clips.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </NativeSelect>
          </Field>
        )}
      </div>
      {regenerate !== '' && (
        <p className="eo-trim__warn eo-feedback"><IconWarn /><span>Regenerar invalida la pre-anotación vieja de ese clip.</span></p>
      )}

      <div className="eo-actions">
        <Button variant="primary" onClick={() => void generar()} disabled={!listo} aria-busy={busy || undefined}>
          {busy ? 'Generando…' : 'Generar clip'}
        </Button>
        <Button onClick={onClose} disabled={busy}>Cerrar</Button>
      </div>
      {/* Pendiente y error junto a la acción, sin tocar las marcas. */}
      {busy && <p className="eo-trim__status" role="status">Generando el clip: las marcas quedan como están.</p>}
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {result && (
        <div className="eo-trim__result" role="status">
          <p className="eo-feedback"><IconCheck /><span>{result.clip_id} generado ({result.info.n_frames} frames)</span></p>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w) => (
                <li key={w} className="eo-feedback"><IconWarn /><span>{w}</span></li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  )
}
