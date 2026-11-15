import { Link } from 'react-router-dom'
import { useFiguras } from '../../api/queries/gen2'
import BarrasHorizontales from '../../components/charts/BarrasHorizontales'
import LineasPorPunto from '../../components/charts/LineasPorPunto'
import { Card, Disclosure, Table, TableScroll } from '../../components/ui'
import type { CifraPregunta, FiguraInforme, GraficoLineas } from '../../types'
import { textoCifra } from './comun'

const numero = (c: CifraPregunta) => (c.ok && typeof c.valor === 'number' ? c.valor : null)

function DatosDeLineas({ g, titulo }: { g: GraficoLineas; titulo: string }) {
  return (
    <Disclosure summary="Las cifras del gráfico">
      <TableScroll label={titulo}>
        <Table aria-label={`Cifras: ${titulo}`}>
          <thead>
            <tr>
              <th><span className="eo-sr">Punto</span></th>
              {g.series.map((s) => <th key={s} className="eo-num">{s}</th>)}
            </tr>
          </thead>
          <tbody>
            {g.puntos.map((p) => (
              <tr key={p.etiqueta}>
                <th scope="row" className="eo-pregunta__fila">{p.etiqueta}</th>
                {p.valores.map((c, i) => <td key={i} className="eo-num">{textoCifra(c)}</td>)}
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
    </Disclosure>
  )
}

/** Lo que se ve de una figura: el gráfico, dibujado con las cifras resueltas; la imagen, si ya se sacó;
 *  o por qué no está. El elemento con `data-figura` es lo que captura `tools/sacar_figuras.mjs`. */
function Contenido({ f }: { f: FiguraInforme }) {
  const g = f.grafico
  if (g?.tipo === 'barras') {
    return (
      <div className="eo-figura__lienzo" data-figura={f.id}>
        <BarrasHorizontales
          nombre={f.titulo}
          unidad={g.unidad}
          barras={g.barras.map((b) => ({ etiqueta: b.etiqueta, valor: numero(b.cifra), texto: textoCifra(b.cifra), aparte: b.aparte }))}
        />
      </div>
    )
  }
  if (g?.tipo === 'lineas') {
    return (
      <>
        <div className="eo-figura__lienzo" data-figura={f.id}>
          <LineasPorPunto
            nombre={f.titulo}
            eje="F1"
            categorias={g.puntos.map((p) => p.etiqueta)}
            series={g.series.map((nombre, si) => ({
              nombre,
              valores: g.puntos.map((p) => (p.valores[si] ? numero(p.valores[si]) : null)),
              textos: g.puntos.map((p) => textoCifra(p.valores[si])),
            }))}
          />
        </div>
        <DatosDeLineas g={g} titulo={f.titulo} />
      </>
    )
  }
  const pantalla = f.fuente.pantalla
  return (
    <>
      {f.disponible && f.url
        ? <img className="eo-figura__imagen" src={f.url} alt={f.titulo} loading="lazy" />
        : (
          <p className="eo-note eo-figura__falta">
            {f.privada
              ? 'No está en este equipo: tiene personas o cuadros de terceros y no se publica.'
              : 'Todavía no se sacó.'}
          </p>
        )}
      {pantalla && <p className="eo-note--meta eo-figura__fuente">Sale de <Link to={pantalla}>esta pantalla</Link>.</p>}
    </>
  )
}

/** «Cómo se ve» (plan de la consola, §8): las figuras del informe que muestran algo de esta pregunta.
 *  Las que todavía no tienen fuente no aparecen. */
export default function ComoSeVe({ preguntaId }: { preguntaId: string }) {
  const q = useFiguras()
  if (q.isPending) return null
  if (q.error) {
    return (
      <Card title="Cómo se ve">
        <p className="eo-note">No se pudieron leer las figuras: {q.error.message}</p>
      </Card>
    )
  }
  const figuras = q.data.figuras.filter((f) => !f.pendiente && f.preguntas.includes(preguntaId))
  if (figuras.length === 0) return null
  return (
    <Card title="Cómo se ve">
      <div className="eo-figuras">
        {figuras.map((f) => (
          <figure key={f.id} className="eo-figura" aria-labelledby={`figura-${f.id}`}>
            <figcaption className="eo-figura__cab">
              <span id={`figura-${f.id}`} className="eo-figura__titulo">
                <span className="eo-figura__num">Figura {f.numero}</span> {f.titulo}
              </span>
              {f.pie && <span className="eo-figura__pie">{f.pie}</span>}
            </figcaption>
            <Contenido f={f} />
          </figure>
        ))}
      </div>
    </Card>
  )
}
