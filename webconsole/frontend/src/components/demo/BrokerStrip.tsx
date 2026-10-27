import Termino from '../Glosario'
import type { DemoState } from '../../types'
import { hora, numero } from './formato'

/** Lo último que recibió el broker, según el testigo MQTT (independiente del
 *  distribuidor: es la prueba de que el mensaje pasó por el broker). */
export default function BrokerStrip({ broker }: { broker: DemoState['broker'] }) {
  const ultimo = broker?.ultimo
  return (
    <section className="eo-demo-strip" aria-label="Broker">
      <span className="eo-demo-strip__rotulo">
        <Termino id="testigo_mqtt">Broker</Termino>
      </span>
      {ultimo ? (
        <span>
          <code>{ultimo.topic}</code> · {hora(ultimo.recibido_en)} · hace {numero(ultimo.hace_s, 0)} s
          {broker && broker.mensajes > 1 ? ` · ${broker.mensajes} mensajes en esta corrida` : ''}
        </span>
      ) : (
        <span>sin mensajes todavía</span>
      )}
    </section>
  )
}
