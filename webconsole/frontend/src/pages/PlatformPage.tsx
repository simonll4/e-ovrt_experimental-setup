import { useState } from 'react'
import { ApiError } from '../api'
import {
  useActivateInstance, useInstances, usePreflight, useStopPlatform,
} from '../api/queries/platform'
import type { PlaneStatus } from '../types'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  IconStop,
  MonoCell,
  PageHeader,
  Table,
} from '../components/ui'

/** Un motor con su estado y su puerto. Repite lo que dice el pie de la barra
 *  lateral, a propósito: acá es donde se viene a mirar el estado del sistema. */
function Plano({ nombre, estado }: { nombre: string; estado: PlaneStatus | null }) {
  return (
    <section className="eo-plane">
      {!estado ? (
        <Badge tone="neutral">verificando…</Badge>
      ) : !estado.healthy ? (
        <Badge tone="error">Sin respuesta</Badge>
      ) : estado.ready ? (
        <Badge tone="ok">Operativo</Badge>
      ) : (
        <Badge tone="warn">No listo</Badge>
      )}
      <span className="eo-plane__text">
        <b>{nombre}</b>
        <span>{estado ? hostDe(estado.service_url) : '—'}</span>
      </span>
    </section>
  )
}

/** `http://127.0.0.1:8080` → `127.0.0.1:8080`. El esquema es ruido acá. */
function hostDe(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return url
  }
}

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
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null) // instancia activándose/deteniéndose

  const { data: rows, error: loadError } = useInstances()
  const preflight = usePreflight()
  const activateMutation = useActivateInstance()
  const stopMutation = useStopPlatform()

  // El 501 no es un fallo: es "esta consola apunta a una instancia fija y la
  // orquestación no está habilitada". Se distingue del resto para poder mostrar
  // un estado de interfaz en vez de un error.
  const notEnabled = loadError instanceof ApiError && loadError.status === 501

  const activate = async (name: string) => {
    setBusy(name)
    setError(null)
    try {
      await activateMutation.mutateAsync(name)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const stop = async () => {
    setBusy('__stop__')
    setError(null)
    try {
      await stopMutation.mutateAsync()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
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
  // `error` es de las acciones (activar/apagar); `loadError` es del listado. Si
  // el listado nunca cargó no hay tabla que mostrar, así que ese gana.
  if (loadError && !rows) return <ErrorBanner>Error: {errorMessage(loadError)}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const activa = rows.find((r) => r.is_target) ?? null

  return (
    <>
      <PageHeader title="Plataforma" meta={`${rows.length} instancias del servicio`} />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="eo-hero">
        {activa ? (
          <section className="eo-target">
            <div className="eo-target__label">Instancia activa</div>
            <div className="eo-target__name">{activa.name}</div>
            <div className="eo-target__chips">
              {activa.ready ? (
                <Badge tone="ok">Operativa</Badge>
              ) : (
                <Badge tone="warn">Cargando el modelo</Badge>
              )}
              <span className="eo-mono eo-note">{activa.model_ref}</span>
            </div>
            {/* El prototipo muestra acá encendida-hace, memoria de GPU y
                corridas-hoy. El backend no expone ninguno de los tres, y tres
                casilleros en «sin dato» ocupan lugar sin informar: se muestra el
                pie solo con la acción hasta que existan. */}
            <div className="eo-target__foot">
              <Button variant="danger" onClick={stop} disabled={busy !== null}>
                <IconStop />
                Apagar
              </Button>
            </div>
          </section>
        ) : (
          <section className="eo-target">
            <div className="eo-target__label">Instancia activa</div>
            <div className="eo-target__name">—</div>
            <p className="eo-note">
              Ninguna instancia está activa. Activá una desde la tabla para poder lanzar corridas.
            </p>
          </section>
        )}

        <div className="eo-planes">
          <Plano nombre="Motor de detección" estado={preflight?.media ?? null} />
          <Plano nombre="Motor de reglas" estado={preflight?.control ?? null} />
        </div>
      </div>

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
