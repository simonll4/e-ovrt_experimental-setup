import Termino from '../Glosario'
import { demoArchivoUrl } from '../../api'
import { conditionLabel } from '../../labels'
import type { DemoCifra, DemoSessionDetail } from '../../types'
import { fechaCorta, hora, numero, segundos } from './formato'

const TIPO: Record<string, string> = {
  evidencia: 'Primera evidencia',
  confirmacion: 'Confirmación',
  resolucion: 'Resolución',
}
// La ventana de persistencia es CONFIGURACIÓN del pattern set congelado
// (cr01_cr02_v2), no una medición: por eso se escribe acá.
const PERSISTENCIA_MS: Record<string, number> = { 'CR-01': 4000, 'CR-02': 7000 }

function cifra(cifras: DemoCifra[], prueba: string, clave: string): string {
  const c = cifras.find((x) => x.prueba === prueba && x.clave === clave)
  if (!c || c.pendiente) return 'cifra pendiente (generación 2)'
  return `${numero(c.valor, 3)}${c.unidad ? ` ${c.unidad}` : ''}`
}

/** El Resultado de una sesión: video anotado, cuadros clave, línea de tiempo de cada
 *  alerta y la tarjeta «Qué muestra y qué no muestra esta demo». */
export default function ResultView({
  detalle, cifras, rotuloRespaldo,
}: { detalle: DemoSessionDetail; cifras: DemoCifra[]; rotuloRespaldo: boolean }) {
  const sesion = detalle.session
  const resumen = detalle.resumen
  const id = sesion?.session_id ?? ''
  const captura = cifras.find((c) => c.prueba === 'RT-03' && c.clave === 'capture_to_host_p50_ms')
  return (
    <div className="eo-demo-resultado">
      <header className="eo-demo-resultado__cab">
        <h1>Resultado de la demo</h1>
        {rotuloRespaldo && sesion && (
          <p className="eo-demo-resultado__respaldo">Ensayo del {fechaCorta(sesion.iniciada_en)} en esta sala</p>
        )}
        {sesion && (
          <p className="eo-demo-resultado__meta">
            {hora(sesion.iniciada_en)} → {hora(sesion.terminada_en)} ·{' '}
            {sesion.ended_by === 'operator' ? 'cerrada por el operador' : 'terminó sola'} ·{' '}
            {sesion.fase === 'done' ? 'completa' : `con fallas${sesion.error ? `: ${sesion.error}` : ''}`}
          </p>
        )}
      </header>

      <section aria-label="Video anotado" className="eo-demo-resultado__video">
        {resumen?.video ? (
          <>
            <video src={demoArchivoUrl(id, `resultado/${resumen.video}`)} controls preload="metadata" />
            <p className="eo-demo-resultado__rotulo">
              Se ven exactamente los cuadros que procesó el sistema
              {resumen.fps_efectivos ? ` (≈ ${numero(resumen.fps_efectivos)} cuadros/s efectivos)` : ''}.
            </p>
          </>
        ) : (
          <p>Sin video: {[...(resumen?.faltantes ?? []), ...(resumen?.errores ?? [])].join(' · ') || 'no se generó'}.</p>
        )}
      </section>

      {detalle.linea_de_tiempo.map((alerta) => {
        const claves = (resumen?.cuadros_clave ?? []).filter((c) => c.alerta === alerta.n)
        const persistencia = PERSISTENCIA_MS[alerta.condition_id]
        return (
          <section key={alerta.alert_id} aria-label={`Alerta ${alerta.n}`} className="eo-demo-alerta">
            <h2>Alerta {alerta.n}: <Termino id={alerta.condition_id}>{conditionLabel(alerta.condition_id)}</Termino></h2>
            <div className="eo-demo-alerta__cuadros">
              {claves.map((c) => (
                <figure key={c.archivo}>
                  <img src={demoArchivoUrl(id, `resultado/${c.archivo}`)} alt={`${TIPO[c.tipo]}, cuadro ${c.frame_index}`} />
                  <figcaption>{TIPO[c.tipo]}</figcaption>
                </figure>
              ))}
            </div>
            <ol className="eo-demo-alerta__tramos">
              <li>
                <b>Evidencia → confirmación:</b> {segundos(alerta.tramos.evidencia_a_confirmacion_ms)} s. Es la espera a
                propósito de la <Termino id={alerta.condition_id === 'CR-01' ? 'PR-01' : 'PR-02'}>ventana de
                persistencia</Termino>{persistencia ? ` (${persistencia.toLocaleString('es-AR')} ms)` : ''}: no es un
                requisito de latencia.
              </li>
              <li>
                <b>Confirmación → broker:</b>{' '}
                {alerta.tramos.confirmacion_a_broker_ms != null
                  ? `${numero(alerta.tramos.confirmacion_a_broker_ms, 0)} ms (hora del testigo MQTT menos la de emisión)`
                  : alerta.entrega === 'suppressed_cooldown'
                    ? 'notificación suprimida por enfriamiento (30 s)'
                    : 'el testigo no registró el mensaje'}
              </li>
            </ol>
            <p className="eo-demo-alerta__nota">
              El tramo de la cámara al host (<Termino id="capture_to_host">captura → host</Termino>
              {captura && !captura.pendiente ? `, p50 ${numero(captura.valor, 0)} ms en vivo` : ''}) no está incluido:
              el reloj arranca al sacar el cuadro de la cola.
            </p>
          </section>
        )
      })}
      {detalle.linea_de_tiempo.length === 0 && <p>En esta sesión no hubo alertas.</p>}

      <section aria-label="Qué muestra y qué no muestra esta demo" className="eo-demo-tarjeta">
        <h2>Qué muestra y qué no muestra esta demo</h2>
        <p>
          <b>Muestra</b> que la cadena completa funciona en vivo —cámara, detección, reglas temporales, distribución y
          broker— con la configuración congelada que evaluó el informe.
        </p>
        <p>
          <b>No muestra desempeño:</b> es un escenario controlado, con una persona y un fondo liso.
        </p>
        <p>El desempeño medido está en el informe:</p>
        <ul>
          <li>F1 de alertas con granularidad de escena (la de esta demo), rodaje guionado: {cifra(cifras, 'ALR-01', 'f1')}.</li>
          <li>Falsas alarmas en obra real, por escena: {cifra(cifras, 'ALR-07', 'falsas_alarmas')}; por sujeto: {cifra(cifras, 'ALR-08', 'falsas_alarmas')}.</li>
        </ul>
        <p className="eo-demo-tarjeta__nota">
          Las cifras son las de la generación 2, evaluadas contra la referencia temporal corregida en la revisión
          dirigida del 2026-10-26.
        </p>
      </section>
    </div>
  )
}
