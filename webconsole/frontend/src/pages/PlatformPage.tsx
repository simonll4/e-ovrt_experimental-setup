import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api'
import { useGen2Prueba } from '../api/queries/gen2'
import { usePreflight } from '../api/queries/platform'
import { useAccionPlataforma, useDejarLista, usePlataforma } from '../api/queries/plataforma'
import { ComoCorrio } from './PruebaPage'
import type { AccionPlataforma, BadgeTone, GpuPlataforma, PlaneStatus, ServicioPlataforma } from '../types'
import {
  Badge, Banner, Button, Card, ErrorBanner, LoadingState, MonoCell, PageHeader, StaleNotice, Table, TableScroll, Tag,
} from '../components/ui'
import './PlatformPage.css'

const VERBO: Record<string, string> = { levantar: 'Levantar', detener: 'Detener', reiniciar: 'Reiniciar', activar: 'Activar' }
const HECHO: Record<string, string> = {
  levantar: 'levantó', detener: 'detuvo', reiniciar: 'reinició', activar: 'activó', 'dejar lista': 'dejó lista la plataforma',
}

/** El estado de un contenedor en llano, con su salud cuando la tiene. */
export function estadoServicio(s: Pick<ServicioPlataforma, 'estado' | 'salud'>): { tono: BadgeTone; texto: string } {
  if (s.estado === 'running') {
    if (s.salud === 'unhealthy') return { tono: 'error', texto: 'Corre con problemas' }
    if (s.salud === 'starting') return { tono: 'warn', texto: 'Arrancando' }
    return { tono: 'ok', texto: 'Corriendo' }
  }
  if (s.estado === 'restarting') return { tono: 'warn', texto: 'Reiniciando' }
  if (s.estado === 'ausente') return { tono: 'neutral', texto: 'Sin crear' }
  if (s.estado === 'created') return { tono: 'neutral', texto: 'Creado' }
  return { tono: 'neutral', texto: 'Detenido' }
}

/** «desde las 14:05 · hace 2 h 10 min». */
export function desdeCuando(iso: string | null, ahora = Date.now()): string {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (!Number.isFinite(t)) return '—'
  const min = Math.max(0, Math.round((ahora - t) / 60_000))
  const hace = min < 1 ? 'recién' : min < 60 ? `hace ${min} min`
    : min < 24 * 60 ? `hace ${Math.floor(min / 60)} h${min % 60 ? ` ${min % 60} min` : ''}`
      : `hace ${Math.floor(min / (24 * 60))} d`
  const hora = new Date(t).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
  return `${hora} · ${hace}`
}

function textoGpu(g: GpuPlataforma | null): string | null {
  if (!g) return null
  if (!g.disponible || g.usada_mb == null || g.total_mb == null) return g.motivo ? `GPU: ${g.motivo}` : null
  const gb = (mb: number) => (mb / 1024).toLocaleString('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  return `GPU: ${gb(g.usada_mb)} de ${gb(g.total_mb)} GB en uso${g.nombre ? ` (${g.nombre})` : ''}`
}

function motivo(e: unknown): string {
  if (e instanceof ApiError) {
    const p = (e.payload ?? {}) as { detail?: string }
    return p.detail ?? `${e.status}`
  }
  return String(e)
}

/** Lo que se le pidió y quedó esperando: la confirmación, si algo en curso se cortaría. */
interface Pedido { servicio: string; verbo: string; detalle?: string }

function Acciones({ s, ocupado, pedir }: { s: ServicioPlataforma; ocupado: boolean; pedir: (p: Pedido) => void }) {
  const corre = s.estado === 'running'
  const verbos = s.grupo === 'deteccion'
    ? (s.activa ? ['detener'] : ['activar'])
    : s.servicio === 'console' ? ['reiniciar'] : corre ? ['reiniciar', 'detener'] : ['levantar']
  return (
    <span className="eo-inline">
      {verbos.map((v) => (
        <Button key={v} variant={v === 'detener' ? 'danger' : 'secondary'} disabled={ocupado}
          onClick={() => pedir({ servicio: s.servicio, verbo: v })}
          aria-label={`${VERBO[v]} ${s.nombre ?? s.servicio}`}>
          {VERBO[v]}
        </Button>
      ))}
    </span>
  )
}

function TablaServicios({ titulo, filas, meta, ocupado, enCurso, pedir }: {
  titulo: string
  filas: ServicioPlataforma[]
  meta?: string | null
  ocupado: string | null
  enCurso: boolean
  pedir: (p: Pedido) => void
}) {
  return (
    <Card title={titulo} meta={meta ?? undefined} flush>
      <TableScroll label={titulo}>
        <Table aria-label={titulo}>
          <thead>
            <tr><th>Servicio</th><th>Estado</th><th>Imagen</th><th>Desde</th><th>Puerto</th><th aria-label="Acciones" /></tr>
          </thead>
          <tbody>
            {filas.map((s) => {
              const e = estadoServicio(s)
              return (
                <tr key={s.servicio} className={s.activa ? 'eo-plataforma__activa' : undefined}>
                  <th scope="row" className="eo-plataforma__servicio">
                    <span>{s.nombre ?? s.servicio}</span>
                    {s.activa && <Tag>activa</Tag>}
                    <span className="eo-mono eo-note--meta">{s.nombre ? s.servicio : s.modelo}</span>
                  </th>
                  <td>{ocupado === s.servicio ? <Badge tone="warn" pulse>Trabajando…</Badge> : <Badge tone={e.tono}>{e.texto}</Badge>}</td>
                  <td className="eo-mono">
                    {s.imagen ?? '—'}
                    {s.etiqueta_movida && (
                      <span className="eo-note--meta" title="El contenedor corre la imagen con la que se creó; después la etiqueta pasó a otra construcción">
                        {' '}· la etiqueta apunta ahora a otra imagen
                      </span>
                    )}
                  </td>
                  <td className="eo-plataforma__desde">{desdeCuando(s.desde)}</td>
                  <MonoCell>{s.puerto ?? '—'}</MonoCell>
                  <td className="eo-cell--actions">
                    {s.orquestable || s.servicio === 'console'
                      ? <Acciones s={s} ocupado={ocupado !== null} pedir={pedir} />
                      : null}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </Table>
      </TableScroll>
      {enCurso && <p className="eo-note eo-plataforma__nota">Detener algo ahora corta lo que está en curso: se pide confirmación.</p>}
    </Card>
  )
}

function Registro({ acciones }: { acciones: AccionPlataforma[] }) {
  return (
    <Card title="Registro de acciones" meta={acciones.length ? undefined : 'Todavía no se pidió nada desde esta consola'}>
      {acciones.length > 0 && (
        <ol className="eo-plataforma__registro">
          {acciones.map((a) => (
            <li key={`${a.t}-${a.accion}-${a.servicio}`}>
              <span className="eo-mono eo-note--meta">{new Date(a.t).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'medium' })}</span>
              <span>
                {a.resultado === 'ok' ? <Badge tone="ok">listo</Badge> : <Badge tone="error">falló</Badge>}{' '}
                {a.servicio ? <>{VERBO[a.accion] ?? a.accion} <code className="eo-mono">{a.servicio}</code></> : HECHO[a.accion] ?? a.accion}
                <span className="eo-note--meta"> · {a.duracion_s.toLocaleString('es-AR')} s</span>
              </span>
              {a.detalle && <span className="eo-note--meta">{a.detalle}</span>}
            </li>
          ))}
        </ol>
      )}
    </Card>
  )
}

/** Un motor con su estado y su puerto, para la consola nativa: sin contenedores no hay más que esto. */
function Plano({ nombre, estado }: { nombre: string; estado: PlaneStatus | null }) {
  return (
    <section className="eo-plane">
      {!estado ? <Badge tone="neutral">verificando…</Badge>
        : !estado.healthy ? <Badge tone="error">Sin respuesta</Badge>
          : estado.ready ? <Badge tone="ok">Operativo</Badge> : <Badge tone="warn">No listo</Badge>}
      <span className="eo-plane__text"><b>{nombre}</b><span>{estado?.service_url ?? '—'}</span></span>
    </section>
  )
}

/** La plataforma (plan de la consola, §7.1): los trece servicios en dos grupos, con su orquestación, la
 *  memoria de GPU de la instancia activa y el registro de lo que se pidió. En nativo, el estado de los motores
 *  y el aviso de que la orquestación necesita los contenedores. */
export default function PlatformPage() {
  const q = usePlataforma()
  const preflight = usePreflight()
  const accion = useAccionPlataforma()
  const lista = useDejarLista()
  const [ocupado, setOcupado] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [comando, setComando] = useState<string | null>(null)
  const [aConfirmar, setAConfirmar] = useState<Pedido | null>(null)

  const pedir = async (p: Pedido, confirmar = false) => {
    setOcupado(p.servicio)
    setError(null)
    setComando(null)
    setAConfirmar(null)
    try {
      await accion.mutateAsync({ servicio: p.servicio, verbo: p.verbo, confirmar })
    } catch (e) {
      const cuerpo = (e instanceof ApiError ? e.payload : null) as { detail?: string; confirmar?: boolean; comando?: string } | null
      if (cuerpo?.comando) setComando(cuerpo.comando)
      else if (cuerpo?.confirmar) setAConfirmar({ ...p, detalle: cuerpo.detail })
      else setError(motivo(e))
    } finally {
      setOcupado(null)
    }
  }

  const dejarLista = async () => {
    setOcupado('__lista__')
    setError(null)
    try {
      await lista.mutateAsync()
    } catch (e) {
      setError(motivo(e))
    } finally {
      setOcupado(null)
    }
  }

  if (q.isPending) {
    return (
      <>
        <PageHeader title="Plataforma" />
        <LoadingState lines={4}>Leyendo el estado de los servicios…</LoadingState>
      </>
    )
  }
  if (q.error && !q.data) {
    return (
      <>
        <PageHeader title="Plataforma" />
        <ErrorBanner onRetry={() => void q.refetch()} retrying={q.isFetching}>
          No se pudo leer el estado de los servicios: {motivo(q.error)}
        </ErrorBanner>
      </>
    )
  }
  const d = q.data!
  const total = d.nucleo.length + d.deteccion.length
  const corriendo = [...d.nucleo, ...d.deteccion].filter((s) => s.estado === 'running').length
  return (
    <div className="eo-plataforma">
      <PageHeader
        title="Plataforma"
        meta={d.orquestada ? `${corriendo} de ${total} servicios corriendo` : undefined}
        actions={d.orquestada ? (
          <Button variant="primary" onClick={() => void dejarLista()} disabled={ocupado !== null}
            aria-busy={ocupado === '__lista__' || undefined}>
            {ocupado === '__lista__' ? 'Dejándola lista…' : 'Dejar la plataforma lista'}
          </Button>
        ) : undefined}
      />
      {q.error && <StaleNotice what="el estado de los servicios" onRetry={() => void q.refetch()} retrying={q.isFetching} />}
      {error && <ErrorBanner>{error}</ErrorBanner>}
      {comando && (
        <Banner tone="warn" onClose={() => setComando(null)}>
          La consola no se detiene a sí misma. Desde una terminal, en <code className="eo-mono">infra/platform</code>:{' '}
          <code className="eo-mono">{comando}</code>
        </Banner>
      )}
      {aConfirmar && (
        <Banner tone="warn" onClose={() => setAConfirmar(null)} action={(
          <span className="eo-inline">
            <Button variant="danger" onClick={() => void pedir(aConfirmar, true)}>{VERBO[aConfirmar.verbo]} igual</Button>
            <Button onClick={() => setAConfirmar(null)}>Cancelar</Button>
          </span>
        )}>
          {aConfirmar.detalle ?? 'Hay algo en curso.'}
        </Banner>
      )}

      {!d.orquestada ? (
        <>
          <Banner tone="live">
            Esta consola corre fuera de los contenedores: muestra el estado de los motores, pero levantar, detener o
            cambiar de modelo necesita la consola en contenedor (<code className="eo-mono">infra/platform</code>).
          </Banner>
          <div className="eo-planes">
            <Plano nombre="Motor de detección" estado={preflight?.media ?? null} />
            <Plano nombre="Motor de reglas" estado={preflight?.control ?? null} />
          </div>
        </>
      ) : (
        <div className="eo-plataforma__servicios" data-figura="plataforma-servicios">
          <TablaServicios titulo="Núcleo" filas={d.nucleo} ocupado={ocupado} enCurso={Boolean(d.en_curso)} pedir={(p) => void pedir(p)} />
          <TablaServicios titulo="Detección" filas={d.deteccion} meta={textoGpu(d.gpu)} ocupado={ocupado}
            enCurso={Boolean(d.en_curso)} pedir={(p) => void pedir(p)} />
        </div>
      )}
      {d.orquestada && (
        <p className="eo-cap">
          Una sola instancia de detección está activa a la vez: activar otra detiene la actual y espera a que cargue
          el modelo, que puede tardar unos minutos. «Dejar la plataforma lista» levanta lo que falte del núcleo y
          activa {d.perfil_operativo ? <code className="eo-mono">{d.perfil_operativo}</code> : 'el perfil operativo'},
          sin recrear lo que ya corre.
        </p>
      )}
      {d.orquestada && <Registro acciones={d.acciones} />}
      <ComoSeDesplego />
    </div>
  )
}

/** Cómo se desplegó en la campaña: la foto que registró la prueba de plataforma —equipo, imágenes, servicios
 *  arriba—. Sale del disco; si la prueba todavía no corrió, no se muestra nada. */
function ComoSeDesplego() {
  const q = useGen2Prueba('PLAT-01')
  const foto = q.data?.plataforma ?? q.data?.entorno
  if (!foto) return null
  const servicios = Array.isArray(foto.docker?.compose_ps)
    ? (foto.docker.compose_ps as Array<Record<string, unknown>>)
    : []
  return (
    <section className="eo-plataforma__campana" aria-label="Cómo se desplegó en la campaña">
      <h2>Cómo se desplegó en la campaña</h2>
      <ComoCorrio entorno={foto} titulo="El equipo y las imágenes" />
      {servicios.length > 0 && (
        <Card title="Los servicios, al registrar la prueba" flush>
          <TableScroll label="Los servicios, al registrar la prueba">
            <Table aria-label="Los servicios, al registrar la prueba">
              <thead><tr><th>Servicio</th><th>Estado</th><th>Imagen</th></tr></thead>
              <tbody>
                {servicios.map((s, i) => (
                  <tr key={String(s.Name ?? s.Service ?? i)}>
                    <MonoCell>{String(s.Service ?? s.Name ?? '—')}</MonoCell>
                    <td>{String(s.Status ?? s.State ?? '—')}</td>
                    <MonoCell>{String(s.Image ?? '—')}</MonoCell>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>
      )}
      <p className="eo-cap">
        La prueba completa, con sus comandos, está en <Link to="/resultados/PLAT-01">su detalle</Link>.
      </p>
    </section>
  )
}
