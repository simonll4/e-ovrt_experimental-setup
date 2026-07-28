import { useEffect, useState } from 'react'
import { ApiError, activateInstance, getInstances, stopPlatform } from '../api'
import type { PlatformInstance } from '../types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  MonoCell,
  PageHeader,
  Table,
} from '../components/ui'

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
      <>
        <PageHeader title="Plataforma" />
        <EmptyState
          hint={
            <>
              Desplegá la plataforma con <span className="eo-mono">infra/platform/</span> y
              definí <span className="eo-mono">EOVRT_CONSOLE_COMPOSE_DIR</span>.
            </>
          }
        >
          La orquestación no está habilitada: la consola apunta a una instancia fija
        </EmptyState>
      </>
    )
  if (error && !rows) return <ErrorBanner>Error: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  return (
    <>
      <PageHeader title="Plataforma" meta={`${rows.length} instancias del servicio`} />
      {error && <ErrorBanner>{error}</ErrorBanner>}
      <Card title="Instancias del servicio" meta="Solo una puede estar activa" flush>
        <Table>
          <thead>
            <tr>
              <th>Instancia</th>
              <th>Modelo</th>
              <th>Estado</th>
              <th aria-label="Acciones" />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name}>
                <MonoCell>{r.name}</MonoCell>
                <MonoCell>{r.model_ref}</MonoCell>
                <td>
                  <span className="eo-inline">
                    {busy === r.name ? (
                      <Badge tone="warn">Activando…</Badge>
                    ) : r.is_target && r.ready ? (
                      <Badge tone="ok">Operativa</Badge>
                    ) : r.is_target ? (
                      <Badge tone="warn">Cargando el modelo</Badge>
                    ) : (
                      <Badge tone="neutral">Detenida</Badge>
                    )}
                  </span>
                </td>
                <td className="eo-cell--actions">
                  {r.is_target ? (
                    <Button onClick={stop} disabled={busy !== null}>
                      Apagar
                    </Button>
                  ) : (
                    <Button onClick={() => activate(r.name)} disabled={busy !== null}>
                      Activar
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <p className="eo-cap">
        Activar otra instancia apaga la actual y espera a que el modelo cargue, lo que puede
        tardar varios minutos. No se puede cambiar de instancia mientras haya una corrida en
        curso.
      </p>
    </>
  )
}
