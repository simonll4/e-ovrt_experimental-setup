import type { ReactNode } from 'react'
import { demoArchivoUrl } from '../../api'
import type { DemoLineaAlerta, DemoSessionDetail } from '../../types'
import NombreCodigo from '../ui/NombreCodigo'
import { ESTADO_DEL_INFORME, segundos } from './formato'

/** El mensaje con sangría, pero con las listas de números en una sola línea (una caja, por ejemplo). */
export function jsonLegible(valor: unknown): string {
  return JSON.stringify(valor, null, 2).replace(/\[\s*(-?[\d.eE+-]+(?:,\s*-?[\d.eE+-]+)*)\s*\]/g,
    (_, adentro: string) => `[${adentro.split(/,\s*/).join(', ')}]`)
}

const ESTADO: Record<string, string> = {
  ok: 'en regla', confirmando: 'confirmando', alerta: 'en alerta', resolviendo: 'resolviendo', resuelta: 'resuelta',
}

interface EntradaEstado {
  t: string
  condiciones?: Array<{ condicion: string; estado: string; transcurrido_ms: number | null; umbral_ms: number | null }>
}

/** El primer registro de estados desde la confirmación (en hora de reloj, la de `confirmed_wall_ms`): el
 *  registro se toma cada medio segundo y el anterior todavía muestra la condición confirmando, aunque el
 *  cuadro ya diga alerta. Si no hay ninguno después, el último antes. Devuelve también cuánto después. */
export function estadoAlConfirmar(stateLog: unknown[], instanteMs: number | null): { entrada: EntradaEstado; desfaseMs: number } | null {
  if (instanteMs == null) return null
  let despues: { entrada: EntradaEstado; desfaseMs: number } | null = null
  let antes: { entrada: EntradaEstado; desfaseMs: number } | null = null
  for (const crudo of stateLog) {
    const e = crudo as EntradaEstado
    const t = Date.parse(e?.t)
    if (!Number.isFinite(t) || !Array.isArray(e.condiciones)) continue
    const d = t - instanteMs
    if (d >= 0 && (!despues || d < despues.desfaseMs)) despues = { entrada: e, desfaseMs: d }
    if (d < 0 && (!antes || d > antes.desfaseMs)) antes = { entrada: e, desfaseMs: d }
  }
  const elegido = despues ?? antes
  // Un registro lejos de la confirmación no dice el estado de ese instante: mejor no mostrarlo. El registro se
  // toma cada medio segundo, así que el que corresponde está a menos de un segundo (revisión del 2026-11-19).
  if (!elegido || Math.abs(elegido.desfaseMs) > MAX_DESFASE_MS) return null
  return elegido
}

/** Hasta cuánto puede estar el registro de la confirmación para mostrarlo como su estado. */
export const MAX_DESFASE_MS = 2000

/** «El momento de la alerta» (plan de la consola, §6): el cuadro de la confirmación con el estado de cada
 *  condición, y el mensaje que llegó al broker con los tramos de esa alerta (`children`). De acá salen las
 *  figuras 2 (la toma) y 3 (el mensaje). Todo sale de lo que registró la sesión. */
export default function MomentoDeLaAlerta({ detalle, alerta, children }: {
  detalle: DemoSessionDetail
  alerta: DemoLineaAlerta
  children?: ReactNode
}) {
  const id = detalle.session?.session_id ?? ''
  const cuadro = (detalle.resumen?.cuadros_clave ?? []).find((c) => c.alerta === alerta.n && c.tipo === 'confirmacion')
  const estado = estadoAlConfirmar(detalle.state_log ?? [], alerta.confirmed_wall_ms)
  const mensaje = detalle.testigo.find((m) => (m.payload as { alert_id?: string } | null)?.alert_id === alerta.alert_id)
  return (
    <section className="eo-momento" aria-label={`El momento de la alerta ${alerta.n}`}>
      <h3>El momento de la alerta</h3>
      <div className="eo-momento__cuerpo">
        <figure className="eo-momento__toma" data-figura="momento-toma">
          {cuadro
            ? <img src={demoArchivoUrl(id, `resultado/${cuadro.archivo}`)} alt={`Cuadro de la confirmación, ${cuadro.frame_index}`} />
            : <p className="eo-note">La sesión no guardó el cuadro de la confirmación.</p>}
          <figcaption>
            <span className="eo-momento__titulo">Estado de cada condición al confirmarse</span>
            {estado?.entrada.condiciones?.length ? (
              <>
                <ul className="eo-momento__estados">
                  {estado.entrada.condiciones.map((c) => (
                    <li key={c.condicion} className={`eo-momento__estado eo-momento__estado--${c.estado}`}>
                      <span className="eo-momento__cara">
                        <NombreCodigo codigo={c.condicion} />: <b>{ESTADO[c.estado] ?? c.estado}</b>
                        {(c.estado === 'confirmando' || c.estado === 'resolviendo') && c.transcurrido_ms != null && c.umbral_ms != null && (
                          <span className="eo-note--meta"> · {segundos(c.transcurrido_ms)} de {segundos(c.umbral_ms)} s</span>
                        )}
                      </span>
                      {ESTADO_DEL_INFORME[c.estado] && <>
                        <span className="eo-sr">; </span><span className="eo-momento__informe">en el informe: <b>{ESTADO_DEL_INFORME[c.estado]}</b></span>
                      </>}
                    </li>
                  ))}
                </ul>
                <span className="eo-note--meta">
                  Registro de {segundos(Math.abs(estado.desfaseMs), 1)} s {estado.desfaseMs >= 0 ? 'después' : 'antes'} de la confirmación.
                </span>
              </>
            ) : (
              <span className="eo-note--meta">
                {alerta.confirmed_wall_ms == null
                  ? 'Esta alerta no tiene hora de confirmación registrada.'
                  : 'La sesión no registró el estado en ese instante.'}
              </span>
            )}
          </figcaption>
        </figure>
        <div className="eo-momento__mensaje" data-figura="momento-mensaje">
          <p className="eo-momento__titulo">El mensaje que llegó al broker</p>
          {mensaje ? (
            <>
              <p className="eo-note--meta">
                Tópico <code className="eo-mono">{mensaje.topic}</code> · recibido a las {new Date(mensaje.recibido_en).toLocaleTimeString('es-AR')}
              </p>
              <pre className="eo-pre eo-momento__json">{jsonLegible(mensaje.payload)}</pre>
            </>
          ) : (
            <p className="eo-note">
              {alerta.entrega === 'suppressed_cooldown'
                ? 'No hubo mensaje: la notificación se suprimió por el cooldown (la pausa entre avisos).'
                : 'El testigo del broker no registró un mensaje para esta alerta.'}
            </p>
          )}
          {children}
        </div>
      </div>
    </section>
  )
}
