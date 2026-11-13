import { useEffect, useRef } from 'react'
import Termino from '../Glosario'
import { demoArchivoUrl } from '../../api'
import { useDemoCifras, useDemoStack } from '../../api/queries/demo'
import type { DemoCongelado, DemoSessionDetail, DemoState } from '../../types'
import { hora, numero } from './formato'
import { avisoModo } from './modoPrompts'

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
  // Una sesión guardada muestra lo que ella registró (su equipo, su stack, su log), no el equipo ni
  // el estado de quien la abre: se puede abrir días después, en otra máquina y con todo apagado.
  const host = (sesion ? sesion.equipo ?? undefined : stack?.host?.datos) as Record<string, unknown> | undefined
  const ids = sesion?.session?.ids ?? estado?.ids ?? {}
  const sid = sesion?.session?.session_id
  const log = sesion?.log
  // El modo de prompts de la sesión que se mira: la guardada, o la que está corriendo. El estado de
  // una sesión ya cerrada no cuenta: lo que sigue en Listo vuelve al campeón.
  const enCurso = estado && ['preparing', 'live', 'finishing', 'rendering'].includes(estado.fase)
  const modo = sesion ? sesion.session?.modo_prompts : enCurso ? estado?.modo_prompts : null

  return (
    <div className="eo-demo-capa" role="dialog" aria-label="Capa de evidencia" tabIndex={-1} ref={ref}>
      <header className="eo-demo-capa__cab">
        <h2>Capa de evidencia</h2>
        <button type="button" className="eo-demo-capa__cerrar" onClick={onClose}>Cerrar (Esc)</button>
      </header>
      <div className="eo-demo-capa__grilla">
        <section aria-label="Cómo corre el stack">
          <h3>Cómo corre el stack</h3>
          {sesion ? (
            <p>
              {sesion.session?.stack === 'compose'
                ? 'Esta sesión corrió con la plataforma en contenedores (Docker Compose).'
                : 'Esta sesión corrió con los servicios ejecutados en forma nativa.'}
            </p>
          ) : stack?.modo === 'compose' ? (
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
          {!sesion && stack?.error && <p>No se pudo leer el estado de los contenedores: {stack.error}</p>}
        </section>

        <section aria-label="Equipo">
          <h3>El equipo</h3>
          {host ? (
            <ul className="eo-demo-capa__lista">
              {Object.entries(host).filter(([k]) => k !== 'chequeos').map(([k, v]) => (
                <li key={k}>{k}: <code>{corto(v)}</code></li>
              ))}
            </ul>
          ) : sesion ? (
            <p>La sesión no guardó el chequeo del equipo.</p>
          ) : (
            <p>Sin chequeo del host (correr <code>infra/demo/demo.ps1 check</code>).</p>
          )}
        </section>

        <section aria-label="Configuración congelada">
          <h3>Configuración congelada</h3>
          {modo && <p className="eo-demo-capa__modo" role="note">{avisoModo(modo.nombre)}.</p>}
          <Congelado congelado={sesion?.session?.congelado ?? congelado} />
        </section>

        <section aria-label="Mensaje MQTT crudo">
          <h3>El mensaje MQTT, tal como lo recibió el <Termino id="testigo_mqtt">testigo</Termino></h3>
          {sesion && sesion.testigo.length > 1 && (
            <p className="eo-demo-capa__nota">Llegaron {sesion.testigo.length} mensajes; este es el último.</p>
          )}
          {crudo
            ? <pre className="eo-demo-capa__pre">{crudo}</pre>
            : <p>{sesion ? 'La sesión cerró sin mensajes en el broker: no se confirmó ninguna alerta.' : 'Todavía no llegó ningún mensaje.'}</p>}
        </section>

        <section aria-label="Latencia y cuadros por segundo">
          <h3>Latencia por cuadro y cuadros por segundo</h3>
          {estado?.metricas && Object.keys(estado.metricas).length > 0 ? (
            <p>
              En esta corrida: ≈{numero(estado.metricas.fps)} cuadros/s efectivos · latencia del último cuadro{' '}
              {numero(estado.metricas.latencia_ms, 0)} ms
            </p>
          ) : sesion?.resumen?.cuadros_procesados != null ? (
            <p>
              En esta sesión: {numero(sesion.resumen.cuadros_procesados, 0)} cuadros procesados
              {sesion.resumen.fps_efectivos != null && <> · {numero(sesion.resumen.fps_efectivos, 2)} cuadros por segundo</>}
            </p>
          ) : sesion ? null : (
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
            <>
              {log?.informe && (
                <>
                  <h4>El informe del experimento</h4>
                  <pre className="eo-demo-capa__pre">{log.informe}</pre>
                </>
              )}
              <h4>Las alertas confirmadas por el motor de reglas</h4>
              {log?.alertas?.trim()
                ? <pre className="eo-demo-capa__pre">{log.alertas}</pre>
                : <p>Ninguna en esta sesión.</p>}
              {log?.distribucion && (
                <>
                  <h4>La distribución</h4>
                  <pre className="eo-demo-capa__pre">{log.distribucion}</pre>
                </>
              )}
              {sid && (log?.archivos.length ?? 0) > 0 && (
                <>
                  <h4>Todos los archivos del log</h4>
                  <ul className="eo-demo-capa__lista">
                    {log?.archivos.map((rel) => (
                      <li key={rel}>
                        <a href={demoArchivoUrl(sid, rel)} target="_blank" rel="noreferrer">
                          <code>{rel.replace(/^resultado\/log\//, '')}</code>
                        </a>
                      </li>
                    ))}
                  </ul>
                </>
              )}
              <p className="eo-demo-capa__nota">
                La carpeta de la sesión guarda además la configuración enviada, el testigo del broker y los estados
                que mostró la pantalla.
              </p>
            </>
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
                {/* El commit es el del equipo que tiene abierta la consola: no dice nada de una sesión guardada. */}
                {!sesion && r.commit ? <> · en esta máquina: <code>{r.commit.slice(0, 10)}</code></> : null}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
