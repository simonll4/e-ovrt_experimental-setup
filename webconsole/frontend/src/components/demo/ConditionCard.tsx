import Termino from '../Glosario'
import { conditionLabel } from '../../labels'
import type { DemoCondicion } from '../../types'
import { FALTA, SEVERIDAD, segundos } from './formato'

const BROKER: Record<string, string> = {
  recibido: 'Mensaje recibido en el broker',
  esperando: 'Esperando el broker…',
  suprimido_enfriamiento: 'Notificación suprimida por enfriamiento (30 s)',
  no_llego: 'El mensaje no llegó al broker en 5 s',
}

function Barra({ valor, umbral, etiqueta }: { valor: number | null; umbral: number | null; etiqueta: string }) {
  const pct = valor != null && umbral ? Math.max(0, Math.min(100, (valor / umbral) * 100)) : 0
  return (
    <div
      className="eo-demo-barra"
      role="progressbar"
      aria-label={etiqueta}
      aria-valuemin={0}
      aria-valuemax={umbral ? Math.round(umbral) : 100}
      aria-valuenow={valor != null ? Math.round(valor) : 0}
    >
      <div className="eo-demo-barra__relleno" style={{ width: `${pct}%` }} />
    </div>
  )
}

/** Una tarjeta grande por condición (Casco, Chaleco), en una de cinco caras:
 *  OK · Confirmando (con barra) · ALERTA · Resolviendo (con barra) · Resuelta. */
export default function ConditionCard({ condicion }: { condicion: DemoCondicion }) {
  const { condicion: codigo, nombre, estado, transcurrido_ms, umbral_ms, severidad } = condicion
  const patron = codigo === 'CR-01' ? 'PR-01' : 'PR-02'
  return (
    <section
      className={`eo-demo-card eo-demo-card--${estado}`}
      aria-label={`${nombre}: ${estado}`}
      aria-live="polite"
    >
      <h2 className="eo-demo-card__titulo">{nombre}</h2>
      {estado === 'ok' && <p className="eo-demo-card__cara">{nombre} ✓</p>}
      {estado === 'confirmando' && (
        <>
          <p className="eo-demo-card__cara">
            {FALTA[codigo] ?? codigo} · confirmando {segundos(transcurrido_ms)} / {segundos(umbral_ms, 0)} s
          </p>
          <Barra valor={transcurrido_ms} umbral={umbral_ms} etiqueta={`Confirmando ${codigo}`} />
          <p className="eo-demo-card__nota">
            Es la <Termino id={patron}>ventana de persistencia</Termino> de {codigo}: una espera a propósito, no
            una demora.
          </p>
        </>
      )}
      {estado === 'alerta' && (
        <>
          <p className="eo-demo-card__cara eo-demo-card__cara--alerta">
            ALERTA <Termino id={codigo}>{conditionLabel(codigo)}</Termino>
            {severidad ? ` (${SEVERIDAD[severidad] ?? severidad})` : ''}
          </p>
          {condicion.broker && <p className="eo-demo-card__broker">{BROKER[condicion.broker]}</p>}
        </>
      )}
      {estado === 'resolviendo' && (
        <>
          <p className="eo-demo-card__cara">
            Resolviendo {segundos(transcurrido_ms)} / {segundos(umbral_ms, 0)} s
          </p>
          <Barra valor={transcurrido_ms} umbral={umbral_ms} etiqueta={`Resolviendo ${codigo}`} />
          {condicion.broker && <p className="eo-demo-card__broker">{BROKER[condicion.broker]}</p>}
        </>
      )}
      {estado === 'resuelta' && <p className="eo-demo-card__cara">Resuelta</p>}
      {condicion.alertas > 0 && (
        <p className="eo-demo-card__nota">Alertas en esta corrida: {condicion.alertas}</p>
      )}
    </section>
  )
}
