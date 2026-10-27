import { useEffect, useRef } from 'react'
import Termino from '../Glosario'
import { useDemoCifras, useDemoStack } from '../../api/queries/demo'
import type { DemoCongelado, DemoSessionDetail, DemoState } from '../../types'
import { hora, numero } from './formato'

function corto(valor: unknown): string {
  if (typeof valor === 'string' && /^[0-9a-f]{64}$/.test(valor)) return `${valor.slice(0, 12)}…`
  if (valor == null) return '—'
  return typeof valor === 'object' ? JSON.stringify(valor) : String(valor)
}

function Congelado({ congelado }: { congelado: DemoCongelado | undefined }) {
  if (!congelado) return <p>Sin datos del chequeo.</p>
  return (
    <>
      <p>
        {congelado.ok
          ? `Configuración congelada ✓ — igual a la del tag ${congelado.tag}`
          : `La configuración NO coincide con la del tag ${congelado.tag ?? ''}`}
        {congelado.error ? ` (${congelado.error})` : ''}
      </p>
      <ul className="eo-demo-capa__lista">
        {congelado.items.map((i) => (
          <li key={i.id}>
            {i.ok ? '✓' : '✗'} {i.nombre}: <code>{corto(i.actual)}</code>
            {!i.ok && <> (esperado <code>{corto(i.esperado)}</code>)</>}
          </li>
        ))}
      </ul>
    </>
  )
}

/** La capa de evidencia (tecla E, sobre cualquier pantalla de la demo): qué corrió,
 *  en qué equipo, con qué configuración, el mensaje MQTT crudo y el log. Las cifras
 *  de desempeño salen de la generación 2 (o se marcan pendientes): nada a mano. */
export default function EvidenceLayer({
  estado, sesion, congelado, onClose,
}: {
  estado?: DemoState
  sesion?: DemoSessionDetail
  congelado?: DemoCongelado
  onClose: () => void
}) {
  const stack = useDemoStack(true).data
  const cifras = useDemoCifras().data ?? []
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.focus() }, [])

  const rt = cifras.filter((c) => c.prueba === 'RT-03')
  const crudo = sesion
    ? sesion.testigo[sesion.testigo.length - 1]?.crudo
    : estado?.broker?.ultimo?.crudo
  const host = stack?.host?.datos as Record<string, unknown> | undefined
  const ids = sesion?.session?.ids ?? estado?.ids ?? {}

  return (
    <div className="eo-demo-capa" role="dialog" aria-label="Capa de evidencia" tabIndex={-1} ref={ref}>
      <header className="eo-demo-capa__cab">
        <h2>Capa de evidencia</h2>
        <button type="button" className="eo-demo-capa__cerrar" onClick={onClose}>Cerrar (Esc)</button>
      </header>
      <div className="eo-demo-capa__grilla">
        <section aria-label="Cómo corre el stack">
          <h3>Cómo corre el stack</h3>
          {stack?.modo === 'compose' ? (
            <table className="eo-demo-capa__tabla">
              <thead><tr><th>Servicio</th><th>Imagen</th><th>Estado</th><th>Creado</th></tr></thead>
              <tbody>
                {(stack.contenedores ?? []).map((c) => (
                  <tr key={String(c.Name ?? c.Service)}>
                    <td>{c.Service}</td><td><code>{c.Image}</code></td><td>{c.Status ?? c.State}</td>
                    <td>{c.CreatedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>
              {stack ? 'Servicios nativos en el host: ' : 'Consultando…'}
              {stack && Object.entries(stack.servicios).map(([k, v]) => `${k} ${v}`).join(' · ')}
            </p>
          )}
          {stack?.error && <p>No se pudo leer el estado de los contenedores: {stack.error}</p>}
        </section>

        <section aria-label="Equipo">
          <h3>El equipo</h3>
          {host ? (
            <ul className="eo-demo-capa__lista">
              {Object.entries(host).filter(([k]) => k !== 'chequeos').map(([k, v]) => (
                <li key={k}>{k}: <code>{corto(v)}</code></li>
              ))}
            </ul>
          ) : (
            <p>Sin chequeo del host (correr <code>infra/demo/demo.ps1 check</code>).</p>
          )}
        </section>

        <section aria-label="Configuración congelada">
          <h3>Configuración congelada</h3>
          <Congelado congelado={sesion?.session?.congelado ?? congelado} />
        </section>

        <section aria-label="Mensaje MQTT crudo">
          <h3>El mensaje MQTT, tal como lo recibió el <Termino id="testigo_mqtt">testigo</Termino></h3>
          {crudo ? <pre className="eo-demo-capa__pre">{crudo}</pre> : <p>Todavía no llegó ningún mensaje.</p>}
        </section>

        <section aria-label="Latencia y cuadros por segundo">
          <h3>Latencia por cuadro y cuadros por segundo</h3>
          {estado?.metricas && Object.keys(estado.metricas).length > 0 ? (
            <p>
              En esta corrida: ≈{numero(estado.metricas.fps)} cuadros/s efectivos · latencia del último cuadro{' '}
              {numero(estado.metricas.latencia_ms, 0)} ms
            </p>
          ) : (
            <p>Sin telemetría del motor en este momento.</p>
          )}
          <p className="eo-demo-capa__nota">
            La latencia es la del <Termino id="G2A">G2A</Termino>: arranca cuando el cuadro sale de la cola en el
            host. El tramo previo, de la cámara al host (<Termino id="capture_to_host">captura → host</Termino>), se
            mide aparte.
          </p>
          <ul className="eo-demo-capa__lista">
            {rt.map((c) => (
              <li key={c.clave}>
                {c.que_es}: {c.pendiente ? c.texto : `${numero(c.valor, 2)}${c.unidad ? ` ${c.unidad}` : ''}`}
              </li>
            ))}
          </ul>
        </section>

        <section aria-label="Log de la corrida">
          <h3>El log de la corrida</h3>
          <ul className="eo-demo-capa__lista">
            {Object.entries(ids).map(([k, v]) => <li key={k}>{k}: <code>{v}</code></li>)}
          </ul>
          {sesion ? (
            <p>
              Archivos completos en <code>defensa/sesiones/{sesion.session?.session_id}/</code> (configuración enviada,
              testigo, estados mostrados y el resultado).
            </p>
          ) : (
            <ol className="eo-demo-capa__log">
              {(estado?.eventos ?? []).slice(-12).map((e, i) => (
                <li key={`${e.t}-${i}`}>{hora(e.t)} · {e.evento}</li>
              ))}
            </ol>
          )}
        </section>

        <section aria-label="Repositorios">
          <h3>El código</h3>
          <ul className="eo-demo-capa__lista">
            {(stack?.repos ?? []).map((r) => (
              <li key={r.repo}>
                <a href={r.url_tag} target="_blank" rel="noreferrer">{r.repo} @ {r.tag_evaluado}</a>
                {r.commit ? <> · en esta máquina: <code>{r.commit.slice(0, 10)}</code></> : null}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
