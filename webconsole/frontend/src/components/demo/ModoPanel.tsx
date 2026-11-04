import type { DemoModos } from '../../types'
import { Card, Tag } from '../ui'
import { EVIDENCIA_MODO, valorCifra } from './modoPrompts'

interface Props {
  modos: DemoModos
  /** El id del modo que se muestra elegido: el de la pantalla antes de iniciar, el de la sesión
   *  mientras corre. */
  elegido: string
  onElegir: (id: string) => void
  /** Durante la corrida la tarjeta solo muestra el modo de la sesión: no se cambia. */
  soloLectura: boolean
}

/** Los modos de prompts de la demo (✎ 2026-11-01): la lista cerrada de `modos.yaml`, cada uno un par
 *  prompt set + pattern set ya medido en la generación 2, con sus frases y sus cifras.
 *
 *  La elección vive solo en la pantalla (sin almacenamiento): arranca siempre en el campeón y vuelve
 *  a él al terminar cada sesión, para que la defensa nunca arranque en un modo que quedó de un ensayo. */
export default function ModoPanel({ modos, elegido, onElegir, soloLectura }: Props) {
  const actual = modos.modos.find((m) => m.id === elegido)
    ?? modos.modos.find((m) => m.id === modos.default)
    ?? null
  return (
    <Card title="Prompts">
      <fieldset className="eo-demo-modos" role="radiogroup" aria-label="Modo de prompts">
        <legend>Modo de prompts</legend>
        {modos.modos.map((m) => {
          const deshabilitado = soloLectura || Boolean(m.error)
          const clases = ['eo-demo-modos__fila']
          if (m.id === actual?.id) clases.push('eo-demo-modos__fila--elegida')
          if (deshabilitado) clases.push('eo-demo-modos__fila--deshabilitada')
          return (
            <label key={m.id} className={clases.join(' ')}>
              <input
                type="radio" name="demo-modo" value={m.id}
                checked={m.id === actual?.id} disabled={deshabilitado} onChange={() => onElegir(m.id)}
              />
              <span className="eo-demo-modos__nombre">{m.nombre}</span>
              <Tag>{EVIDENCIA_MODO[m.evidencia] ?? m.evidencia}</Tag>
              {m.error && <span className="eo-demo-modos__error">No se puede usar: {m.error}</span>}
            </label>
          )
        })}
      </fieldset>

      {actual && (
        <section className="eo-demo-modo" aria-label={`Modo ${actual.nombre}`}>
          {soloLectura && (
            <p className="eo-demo-modo__nota">Es el modo de la sesión en curso: no se cambia hasta que termine.</p>
          )}
          {actual.resumen && <p>{actual.resumen}</p>}
          {actual.nota && <p className="eo-demo-modo__nota">{actual.nota}</p>}
          {actual.id !== modos.default && (
            <p className="eo-demo-modo__aviso">
              No es la configuración congelada: la sesión queda marcada y no cuenta como ensayo.
            </p>
          )}

          <p className="eo-demo-modo__sub">Lo que recibe el modelo</p>
          <ul className="eo-demo-modo__lista" aria-label="Frases por clase">
            {actual.clases.map((c) => (
              <li key={c.id}>
                <code>{c.id}</code>: {c.frases.map((f) => `«${f}»`).join(', ')}
              </li>
            ))}
          </ul>
          {(actual.prompt_set || actual.pattern_set) && (
            <p className="eo-demo-modo__nota">
              Prompt set <code>{actual.prompt_set ?? '—'}</code> · pattern set <code>{actual.pattern_set ?? '—'}</code>
            </p>
          )}

          {actual.evidencia === 'exploratoria' && (
            <p className="eo-demo-modo__aviso">
              Sin medir en la generación 2: es una exploración, no evidencia. No hay cifra que mostrar.
            </p>
          )}

          {actual.cifras.length > 0 && (
            <>
              <p className="eo-demo-modo__sub">Lo que midió la generación 2</p>
              <ul className="eo-demo-modo__lista" aria-label="Cifras del modo">
                {actual.cifras.map((c) => (
                  <li key={`${c.prueba}-${c.clave}`}>
                    {c.que_es}: <b>{valorCifra(c)}</b> <Tag mono title={c.fuente}>{c.prueba}</Tag>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </Card>
  )
}
