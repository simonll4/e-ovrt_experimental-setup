import { Link } from 'react-router-dom'
import { useGen2Pruebas } from '../api/queries/gen2'
import { Card, PageHeader } from '../components/ui'
import { GEN1 } from '../nav'
import type { Gen2Prueba } from '../types'
import { EstadoDeLectura } from './evidencia/comun'
import { EstadoPrueba, GRUPOS, REGISTRO_LABEL, Veredicto, noSeRegenera, prefijoDe, valorTexto } from './gen2/comun'
import './gen2/Gen2.css'

/** Cuántas cifras del resumen se muestran en la tarjeta; el resto, en el detalle. */
const CIFRAS_EN_TARJETA = 3

function TarjetaPrueba({ p }: { p: Gen2Prueba }) {
  const cifras = p.resumen.slice(0, CIFRAS_EN_TARJETA)
  const deGen1 = noSeRegenera(p) ? (p.gen1.cifras ?? []).slice(0, CIFRAS_EN_TARJETA) : []
  return (
    <article className="eo-gen2__prueba" aria-labelledby={`prueba-${p.id}`}>
      <h3 id={`prueba-${p.id}`}>
        <Link to={`/resultados/${encodeURIComponent(p.id)}`}>{p.id} — {p.titulo}</Link>
      </h3>
      {p.pregunta && <p className="eo-note">{p.pregunta}</p>}
      <div className="eo-gen2__estado">
        <EstadoPrueba estado={p.estado} registro={p.registro} />
        <Veredicto v={p.veredicto} />
        {p.registro !== 'activa' && !noSeRegenera(p) && (
          <span className="eo-note--meta">({REGISTRO_LABEL[p.registro] ?? p.registro})</span>
        )}
      </div>
      {deGen1.length > 0 && (
        <dl className="eo-gen2__cifras">
          {deGen1.map((c) => (
            <div key={c.clave}>
              <dt>{c.nombre}</dt>
              <dd><b>{valorTexto(c.valor, c.unidad)}</b><span className="eo-note--meta"> · generación 1</span></dd>
            </div>
          ))}
        </dl>
      )}
      {cifras.length > 0 && (
        <dl className="eo-gen2__cifras">
          {cifras.map((c) => (
            <div key={c.clave}>
              <dt>{c.nombre}</dt>
              <dd>
                <b>{valorTexto(c.valor, c.unidad)}</b>
                {c.gen1 != null && <span className="eo-note--meta"> · generación 1: {valorTexto(c.gen1, c.unidad)}</span>}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  )
}

/** «Resultados» (doc 135 §3.3): las pruebas de la generación 2 organizadas como el
 *  informe, no como el archivo. Lee del disco; no consulta servicios ni calcula. */
export default function ResultadosPage() {
  const q = useGen2Pruebas()
  if (q.isPending || q.error) return <EstadoDeLectura titulo="Resultados" q={q} />
  const pruebas = q.data
  const contrastes = pruebas.filter((p) => p.registro === 'no_se_regenera').length
  const aRegenerar = pruebas.length - contrastes
  const completas = pruebas.filter((p) => p.estado === 'completo').length
  return (
    <div className="eo-gen2">
      <PageHeader
        title="Resultados"
        meta={`Generación 2: los resultados finales del informe · ${completas} de ${aRegenerar} pruebas completas`}
      />
      <p className="eo-note">
        Cada prueba se registró por escrito antes de correr (qué mide, con qué insumo y configuración, qué
        se esperaba) y se comparó con la generación 1. El veredicto lo propone el programa que corre las
        pruebas y lo confirma una persona: <i>idéntico</i>, <i>equivalente con la diferencia declarada</i>
        u <i>otra combinación</i>, que se muestra al lado y nunca en reemplazo.
      </p>
      {contrastes > 0 && (
        <p className="eo-note">
          {contrastes === 1 ? 'Una prueba de contraste no se regenera' : `${contrastes} pruebas de contraste no se regeneran`}:
          comparan otra configuración contra el campeón, y el mismo camino lo recorre la prueba del campeón
          en esta PC. Su cifra vigente es la de la generación 1 y se muestra marcada así.
        </p>
      )}
      {GRUPOS.map((g) => {
        const delGrupo = pruebas.filter((p) => g.prefijos.includes(prefijoDe(p.id)))
        if (delGrupo.length === 0) return null
        return (
          <Card key={g.titulo} title={g.titulo} meta={g.informe}>
            <p className="eo-note">{g.explica}</p>
            <div className="eo-gen2__grid">
              {delGrupo.map((p) => <TarjetaPrueba key={p.id} p={p} />)}
            </div>
          </Card>
        )
      })}
      <Card title="Ajuste fino" meta="Tabla 55">
        <p className="eo-note">
          El ajuste fino corrió en el clúster Mendieta durante la generación 1 y no se regenera: el proyecto
          no entrena en una PC local. Sus checkpoints y evaluaciones son evidencia de la
          {' '}<Link to={GEN1.to}>validación inicial (generación 1)</Link>.
        </p>
      </Card>
    </div>
  )
}
