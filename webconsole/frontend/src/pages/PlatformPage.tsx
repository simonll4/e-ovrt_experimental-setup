import { useEffect, useState } from 'react'
import { ApiError, activateInstance, getInstances, stopPlatform } from '../api'
import type { PlatformInstance } from '../types'
import { Badge, Button, ErrorBanner, Table } from '../components/ui'

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const payload = (e.payload ?? {}) as { detail?: string; step?: string; run_id?: string }
    if (e.status === 409) return `Hay un run activo (${payload.run_id ?? '?'}): esperá a que termine o detenelo.`
    if (e.status === 504) return `La instancia no llegó a ready: ${payload.detail ?? 'timeout'}`
    if (e.status === 502) return `Docker falló${payload.step ? ` (${payload.step})` : ''}: ${payload.detail ?? ''}`
  }
  return String(e)
}

export default function PlatformPage() {
  const [rows, setRows] = useState<PlatformInstance[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null) // instancia activándose/deteniéndose
  const [notEnabled, setNotEnabled] = useState(false)

  const refresh = () =>
    getInstances()
      .then((r) => {
        setRows(r)
        setNotEnabled(false)
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 501) setNotEnabled(true)
        else setError(errorMessage(e))
      })

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [])

  const activate = async (name: string) => {
    setBusy(name)
    setError(null)
    try {
      await activateInstance(name)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
      refresh()
    }
  }

  const stop = async () => {
    setBusy('__stop__')
    setError(null)
    try {
      await stopPlatform()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
      refresh()
    }
  }

  if (notEnabled)
    return (
      <p>
        Orquestación no habilitada: la consola corre en modo target fijo. Desplegá la
        plataforma con <code>infra/platform/</code> (define <code>EOVRT_CONSOLE_COMPOSE_DIR</code>).
      </p>
    )
  if (error && !rows) return <ErrorBanner>Error: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
      <h2>Plataforma — instancias del servicio</h2>
      <p>
        <small>
          Una instancia activa a la vez: activar otra apaga la actual y espera a que el
          modelo cargue (puede tardar minutos).
        </small>
      </p>
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <Table style={{ maxWidth: 760 }}>
        <thead>
          <tr>
            {['instancia', 'modelo', 'estado', 'operativa', '', ''].map((h, i) => (
              <th key={i}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name}>
              <td>{r.name}</td>
              <td>{r.model_ref}</td>
              <td>
                <span className="eo-inline">
                  {busy === r.name ? 'activando…' : r.state}
                  {r.is_target && <Badge tone="ok">TARGET</Badge>}
                </span>
              </td>
              <td>{r.ready ? '✓' : '—'}</td>
              <td>
                {!r.is_target && (
                  <Button variant="primary" onClick={() => activate(r.name)} disabled={busy !== null}>
                    {busy === r.name ? 'Activando…' : 'Activar'}
                  </Button>
                )}
              </td>
              <td>
                {r.is_target && (
                  <Button variant="danger" onClick={stop} disabled={busy !== null}>Apagar</Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
