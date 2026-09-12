import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDocumentacion, qk } from '../api'
import { Card, EmptyState, ErrorBanner, PageHeader, Table } from '../components/ui'
import Termino from '../components/Glosario'
import './DocumentacionPage.css'

/** La primera pantalla que conviene leer: qué se hizo, por qué, y qué significa
 *  cada nombre que aparece en el resto de la consola.
 *
 *  Se lee del disco (`results/evidence-vista/documentacion.yaml`, servido por
 *  `/api/documentacion`) y **no consulta ningún servicio**: funciona con los
 *  tres planos apagados, igual que `/evidencia`.
 *
 *  Tres bloques, con el método como espina: cómo se trabajó (los cinco pasos, y
 *  cada uno dice POR QUÉ — es lo que hace que los nombres se entiendan en vez de
 *  memorizarse), qué aporta cada cosa (corrida, experimento, campaña, evidencia,
 *  resultado — los cinco términos que hoy se usan casi como sinónimos), y el
 *  vocabulario agrupado por familia. */
export default function DocumentacionPage() {
  const q = useQuery({ queryKey: qk.documentacion, queryFn: getDocumentacion, staleTime: Infinity })
  if (q.isPending) return <EmptyState>Leyendo la documentación…</EmptyState>
  if (q.error) return <ErrorBanner>No se pudo leer la documentación.</ErrorBanner>
  if (!q.data.available) return <>
    <PageHeader title="Documentación" />
    <EmptyState hint={q.data.message ?? undefined}>Documentación no disponible</EmptyState>
  </>
  const doc = q.data
  return <div className="eo-doc">
    <PageHeader
      title={doc.titulo ?? 'Documentación'}
      meta={`${doc.metodo.length} pasos · ${Object.keys(doc.terminos).length} términos definidos · lectura del disco`}
    />
    {doc.bajada && <p className="eo-note">{doc.bajada}</p>}

    <h2 className="eo-doc__h2" id="metodo">Cómo se trabajó</h2>
    <p className="eo-doc__intro">Cinco pasos, en el orden en que se dieron. Cada uno dice
      qué se hizo, <b>por qué</b>, y qué quedó.</p>
    <ol className="eo-doc__pasos">
      {doc.metodo.map((paso) => (
        <li key={paso.n} className="eo-doc__paso" id={`paso-${paso.n}`}>
          <div className="eo-doc__n" aria-hidden="true">{paso.n}</div>
          <div className="eo-doc__cuerpo">
            <h3 className="eo-doc__t">{paso.titulo}</h3>
            <dl className="eo-doc__qpq">
              <dt>Qué se hizo</dt><dd>{paso.hizo}</dd>
              <dt>Por qué</dt><dd>{paso.porque}</dd>
              <dt>Qué quedó</dt><dd>{paso.quedo}</dd>
            </dl>
            {paso.terminos.length > 0 && <p className="eo-doc__chips">
              {paso.terminos.map((id) => <Termino key={id} id={id} />)}
            </p>}
            {/* El enlace a la evidencia sólo se dibuja si el YAML lo declara:
                un paso sin evidencia asociada no inventa un link a ninguna
                parte. */}
            {paso.evidencia_href && (
              <p className="eo-doc__ev">
                <Link to={paso.evidencia_href}>{paso.evidencia_label ?? 'Ver la evidencia'}</Link>
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>

    <h2 className="eo-doc__h2" id="aportes">Qué aporta cada cosa</h2>
    <p className="eo-doc__intro">Corrida, experimento, campaña, evidencia y resultado se usan
      casi como sinónimos y no lo son. Cada uno suma algo que los otros no.</p>
    <Card flush>
      <Table aria-label="Qué aporta cada cosa">
        <thead><tr>
          <th>Qué es</th><th>De qué habla</th><th>Qué suma</th><th>Dónde se ve</th>
        </tr></thead>
        <tbody>
          {doc.aportes.map((fila) => (
            <tr key={fila.id} id={`aporte-${fila.id}`}>
              <td>
                <div className="eo-rowname">
                  <b>{fila.termino}</b>
                  {/* El identificador sólo si la fila lo tiene: «campaña» y
                      «evidencia» no son un campo de ningún contrato, y
                      ponerles uno inventado sería la peor clase de error acá. */}
                  {fila.identificador
                    ? <span className="eo-mono">{fila.identificador}</span>
                    : <span className="eo-na">sin identificador propio</span>}
                </div>
              </td>
              <td>{fila.que_es}</td>
              <td>{fila.que_suma}</td>
              <td>
                {fila.href
                  ? <Link to={fila.href}>{fila.donde}</Link>
                  : <span className="eo-na">—</span>}
                {/* El conteo lo calcula el servidor contra el registro. Si el
                    registro no está, no se muestra número: un total escrito a
                    mano envejece en silencio. */}
                {fila.conteo != null && <span className="eo-doc__n2">{fila.conteo} hoy</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>

    {/* El conteo sale de los datos: el título decía «Tres símbolos» con el
        número escrito a mano, y declarar una colisión más lo dejaba mintiendo
        — en la sección cuyo trabajo es justamente que nada se lea mal. */}
    <h2 className="eo-doc__h2" id="colisiones">Símbolos que significan más de una cosa</h2>
    <p className="eo-doc__intro">Son {doc.colisiones.length}. Es lo que más confusión ahorra:
      un lector que no estuvo los pisa sí o sí si no se los avisan.</p>
    <div className="eo-doc__cols">
      {doc.colisiones.map((c) => (
        <Card key={c.simbolo} title={<span className="eo-mono">{c.simbolo}</span>}>
          <ul className="eo-doc__sentidos">
            {c.sentidos.map((s) => (
              <li key={s.de}><span className="eo-mono">{s.de}</span> {s.es}</li>
            ))}
          </ul>
          <p className="eo-doc__aqui">{c.en_la_consola}</p>
        </Card>
      ))}
    </div>

    <h2 className="eo-doc__h2" id="vocabulario">Vocabulario</h2>
    <p className="eo-doc__intro">Agrupado por familia. Los términos marcados en el resto de
      la consola apuntan acá.</p>
    {doc.vocabulario.map((familia) => (
      <Card key={familia.id} title={familia.titulo} meta={`${familia.terminos.length} términos`}>
        {familia.nota && <p className="eo-doc__nota">{familia.nota}</p>}
        <dl className="eo-doc__voc">
          {familia.terminos.map((t) => (
            <div key={t.id} className="eo-doc__voci" id={t.id}>
              <dt className={t.mono ? 'eo-mono' : undefined}>
                {t.termino}
                {t.nivel && <span className="eo-doc__nivel">Nivel {t.nivel}</span>}
              </dt>
              <dd>
                {t.definicion}
                {/* Los result_id que sostienen el término, enlazados a su
                    evidencia. Un término sin result_id no dibuja nada: no
                    todos los términos son una campaña. */}
                {t.result_ids.length > 0 && <span className="eo-doc__rids">
                  {t.result_ids.map((rid) => (
                    <Link key={rid} className="eo-mono"
                      to={`/evidencia/resultado?${new URLSearchParams({ id: rid })}`}>{rid}</Link>
                  ))}
                </span>}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    ))}

    <p className="eo-cap">Este texto vive en <b>results/evidence-vista/documentacion.yaml</b> y
      se edita sin tocar código. Nada de esta pantalla consulta a los servicios.</p>
  </div>
}
