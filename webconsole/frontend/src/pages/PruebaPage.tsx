import { Link, useParams } from 'react-router-dom'
import { gen2ArchivoUrl } from '../api'
import { useGen2Prueba } from '../api/queries/gen2'
import { Banner, Card, Disclosure, MonoCell, PageHeader, Table, TableScroll, Tag } from '../components/ui'
import { GEN1 } from '../nav'
import type { Gen2Cifra, Gen2Corrida, Gen2Detalle, Gen2Entorno } from '../types'
import { EstadoDeLectura } from './evidencia/comun'
import { CifraFila, EstadoPrueba, VEREDICTO_LABEL, Veredicto, noSeRegenera, valorTexto } from './gen2/comun'
import './gen2/Gen2.css'

const corto = (s: string | null | undefined, n = 12) => (s ? s.replace(/^sha256:/, '').slice(0, n) : '—')

function filasCorridas(corridas: Record<string, Gen2Corrida>) {
  const filas: Array<[string, Gen2Corrida]> = []
  for (const [clave, c] of Object.entries(corridas)) {
    filas.push([clave, c])
    for (const [nombre, v] of Object.entries(c.variantes ?? {})) filas.push([`${clave} · ${nombre}`, v])
  }
  return filas
}

const nombreLectura = (nombre: string) => nombre.replace(/_/g, ' ')

/** Todas las lecturas de la prueba, una columna por lectura: la principal (el
 *  `resumen`) y las demás (por sujeto, otra regla…). Sin esto, la cifra de una
 *  lectura secundaria solo aparecía dentro del texto del veredicto. */
function Lecturas({ d }: { d: Gen2Detalle }) {
  const lecturas = d.lecturas ?? []
  if (lecturas.length === 0) return null
  const valor = (resumen: Gen2Cifra[], clave: string) => {
    const c = resumen.find((x) => x.clave === clave)
    return c ? valorTexto(c.valor, c.unidad) : '—'
  }
  // Las filas son las cifras de la lectura principal, más las que solo tenga alguna otra.
  const filas = [...d.resumen]
  for (const l of lecturas) for (const c of l.resumen) if (!filas.some((f) => f.clave === c.clave)) filas.push(c)
  return (
    <Card title="Las lecturas de la prueba" meta={`${lecturas.length + 1} lecturas`} flush>
      <TableScroll label="Lecturas de la prueba">
        <Table aria-label="Lecturas de la prueba">
          <thead>
            <tr>
              <th>Qué se mide</th>
              <th>Lectura principal</th>
              {lecturas.map((l) => <th key={l.nombre}>{nombreLectura(l.nombre)}</th>)}
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.clave}>
                <td>{f.nombre}</td>
                <td className="eo-num">{valor(d.resumen, f.clave)}</td>
                {lecturas.map((l) => <td key={l.nombre} className="eo-num">{valor(l.resumen, f.clave)}</td>)}
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
    </Card>
  )
}

const segundos = (ms: number | null | undefined) =>
  ms == null ? null : `${(ms / 1000).toLocaleString('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} s`

function CondicionDeToma({ c }: { c?: { esperado?: string; alertas?: number; ok?: boolean } }) {
  if (!c) return <>—</>
  const espera = c.esperado === 'alerta' ? 'alerta' : 'silencio'
  const paso = (c.alertas ?? 0) > 0 ? `${c.alertas} ${c.alertas === 1 ? 'alerta' : 'alertas'}` : 'silencio'
  return (
    <>
      <span className={c.ok ? undefined : 'eo-note--error'}>{paso}</span>
      <span className="eo-note--meta"> · se esperaba {espera}</span>
    </>
  )
}

/** Las tomas de una prueba en vivo, una por fila: qué se esperaba, qué pasó y
 *  cuánto tardó cada alerta desde la acción del actor. */
function Tomas({ d }: { d: Gen2Detalle }) {
  const tomas = d.tomas ?? []
  if (tomas.length === 0) return null
  const condiciones = Array.from(new Set(tomas.flatMap((t) => Object.keys(t.por_condicion ?? {})))).sort()
  const con = (campo: 'stream' | 'motor' | 'camara' | 'remera') => tomas.some((t) => t[campo])
  const comoElGuion = tomas.filter((t) => t.como_se_esperaba).length
  return (
    <Card title="Las tomas" meta={`${comoElGuion} de ${tomas.length} como el guion`} flush>
      <TableScroll label="Tomas de la prueba">
        <Table aria-label="Tomas de la prueba">
          <thead>
            <tr>
              <th>Escena</th>
              {con('stream') && <th>Stream</th>}
              {con('motor') && <th>Motor</th>}
              {con('camara') && <th>Cámara</th>}
              {con('remera') && <th>Remera</th>}
              {condiciones.map((c) => <th key={c}>{c}</th>)}
              <th>Como el guion</th>
              <th>De la acción a la alerta</th>
              <th>Sesión</th>
            </tr>
          </thead>
          <tbody>
            {tomas.map((t, i) => (
              <tr key={t.session_id ?? i}>
                <td>{t.escena ?? '—'}</td>
                {con('stream') && <td>{t.stream ?? '—'}</td>}
                {con('motor') && <MonoCell>{t.motor ?? '—'}</MonoCell>}
                {con('camara') && <MonoCell>{t.camara ?? '—'}</MonoCell>}
                {con('remera') && <td>{t.remera ?? '—'}</td>}
                {condiciones.map((c) => <td key={c}><CondicionDeToma c={t.por_condicion?.[c]} /></td>)}
                <td>
                  {t.como_se_esperaba ? 'sí' : <span className="eo-note--error">no</span>}
                  {t.sujeto_como_se_esperaba != null && t.sujeto_como_se_esperaba !== t.como_se_esperaba && (
                    <span className="eo-note--meta"> · por sujeto: {t.sujeto_como_se_esperaba ? 'sí' : 'no'}</span>
                  )}
                  {(t.alertas_antes_de_la_accion ?? 0) > 0 && (
                    <span className="eo-note--meta"> · {t.alertas_antes_de_la_accion} antes de la acción</span>
                  )}
                </td>
                <td>
                  {t.alertas.filter((a) => a.accion_a_confirmacion_ms != null).map((a) => `${a.condicion} ${segundos(a.accion_a_confirmacion_ms)}`).join(' · ') || '—'}
                </td>
                <td>
                  {t.session_id
                    ? <Link className="eo-mono" to={`/demo/resultado/${encodeURIComponent(t.session_id)}`}>{t.session_id}</Link>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
      <p className="eo-note--meta eo-gen2__nota-tabla">
        La sesión se abre si su carpeta está en este equipo: tiene video con personas y no se publica.
      </p>
    </Card>
  )
}

/** Cómo corrió: el equipo, las imágenes y los commits, tal como los registró la
 *  prueba (`entorno.json`). Si la prueba no registró la GPU, se muestra la de la
 *  prueba de plataforma y se dice de dónde sale. */
export function ComoCorrio({ entorno, titulo = 'Cómo corrió', gpuDeLaPlataforma }: {
  entorno: Gen2Entorno
  titulo?: string
  gpuDeLaPlataforma?: string | null
}) {
  const imagenes = Object.entries(entorno.docker?.imagenes ?? {})
  const repos = Object.entries(entorno.repos ?? {})
  return (
    <Card title={titulo}>
      <dl className="eo-deflist">
        <div><dt>Equipo</dt><dd>{entorno.host?.nombre ?? '—'}</dd></div>
        <div><dt>Procesador</dt><dd>{entorno.host?.cpu ?? '—'}{entorno.host?.nucleos ? ` (${entorno.host.nucleos} núcleos)` : ''}</dd></div>
        <div><dt>Memoria</dt><dd>{entorno.host?.memoria_gb != null ? `${valorTexto(entorno.host.memoria_gb)} GB` : '—'}</dd></div>
        <div>
          <dt>GPU</dt>
          <dd>
            {entorno.gpu ?? gpuDeLaPlataforma ?? '—'}
            {!entorno.gpu && gpuDeLaPlataforma && (
              <span className="eo-note--meta"> · la registró <Link to="/resultados/PLAT-01">PLAT-01</Link></span>
            )}
          </dd>
        </div>
        <div><dt>Despliegue</dt><dd>{entorno.modo === 'docker' ? 'Contenedores (Docker)' : entorno.modo === 'nativo' ? 'Servicios nativos' : '—'}</dd></div>
        <div><dt>Modelo cargado</dt><dd className="eo-mono">{entorno.modelo_cargado?.model?.ref ?? '—'}</dd></div>
        <div><dt>Sistema</dt><dd>{entorno.host?.plataforma ?? '—'}</dd></div>
        <div><dt>Registrado</dt><dd>{entorno.fecha_utc ?? '—'}</dd></div>
      </dl>
      {imagenes.length > 0 && (
        <TableScroll label="Imágenes de contenedor">
          <Table aria-label="Imágenes de contenedor">
            <thead><tr><th>Imagen</th><th>Id</th><th>Creada</th><th>Digest</th></tr></thead>
            <tbody>
              {imagenes.map(([nombre, img]) => (
                <tr key={nombre}>
                  <MonoCell>{nombre}</MonoCell>
                  <MonoCell title={img?.id}>{corto(img?.id)}</MonoCell>
                  <td>{img?.creada ?? '—'}</td>
                  <MonoCell title={(img?.digests ?? []).join('\n')}>{img?.digests?.[0] ? corto(img.digests[0].split('@')[1] ?? img.digests[0], 16) : '— (imagen local)'}</MonoCell>
                </tr>
              ))}
            </tbody>
          </Table>
        </TableScroll>
      )}
      {repos.length > 0 && (
        <TableScroll label="Commits de los repositorios">
          <Table aria-label="Commits de los repositorios">
            <thead><tr><th>Repositorio</th><th>Rama</th><th>Commit</th><th>Archivos sin commitear</th></tr></thead>
            <tbody>
              {repos.map(([nombre, r]) => (
                <tr key={nombre}>
                  <MonoCell>{nombre}</MonoCell>
                  <td>{r.rama ?? '—'}</td>
                  <MonoCell title={r.commit ?? undefined}>{corto(r.commit, 10)}</MonoCell>
                  <td className="eo-num">{r.archivos_sin_commitear ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </TableScroll>
      )}
    </Card>
  )
}

function Archivos({ d }: { d: Gen2Detalle }) {
  const textos = [...d.archivos.logs, ...d.archivos.evals]
  if (textos.length === 0 && d.archivos.capturas.length === 0) return null
  return (
    <Card title="Archivos">
      {d.archivos.capturas.length > 0 && (
        <div className="eo-gen2__capturas">
          {d.archivos.capturas.map((ruta) => (
            <figure key={ruta}>
              <a href={gen2ArchivoUrl(d.id, ruta)} target="_blank" rel="noreferrer">
                <img src={gen2ArchivoUrl(d.id, ruta)} alt={`Captura ${ruta.replace(/^capturas\//, '')}`} loading="lazy" />
              </a>
              <figcaption className="eo-mono">{ruta.replace(/^capturas\//, '')}</figcaption>
            </figure>
          ))}
        </div>
      )}
      {textos.length > 0 && (
        <ul className="eo-gen2__archivos">
          {textos.map((ruta) => (
            <li key={ruta}>
              <a href={gen2ArchivoUrl(d.id, ruta)} target="_blank" rel="noreferrer" className="eo-mono">{ruta}</a>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

/** El detalle de una prueba (doc 135 §3.3): la pregunta, la cifra contra la
 *  generación 1, el veredicto, cómo corrió, el pre-registro y las corridas que la
 *  produjeron. Se ve bien también antes de correr: muestra el pre-registro. */
export default function PruebaPage() {
  const { id = '' } = useParams()
  const q = useGen2Prueba(id)
  if (q.isPending || q.error) {
    return <EstadoDeLectura titulo={id} q={q} noExiste="Esa prueba no está en el catálogo de la generación 2." />
  }
  const d = q.data
  const v = d.veredicto
  const difs = Object.entries(v?.diferencias ?? {})
  const corridas = d.corridas ? filasCorridas(d.corridas) : []
  const contraste = noSeRegenera(d)
  const sinCorrer = d.estado === 'sin_correr' && !contraste
  const cifrasGen1 = contraste ? (d.gen1.cifras ?? []) : []
  return (
    <div className="eo-gen2">
      <PageHeader
        title={`${d.id} — ${d.titulo ?? ''}`}
        meta={<>
          <EstadoPrueba estado={d.estado} registro={d.registro} />
          {d.informe.map((s) => <Tag key={s}>{s}</Tag>)}
          {d.generado && <span>Generado {d.generado}</span>}
        </>}
      />
      {contraste && (
        <Card title="Por qué no se regenera">
          <p>{d.no_se_regenera ?? 'Prueba de contraste: su cifra vigente es la de la generación 1.'}</p>
        </Card>
      )}
      {sinCorrer && (
        <Banner tone="warn">
          Todavía no se corrió. Abajo está su pre-registro: lo que va a medir y lo que se esperaba,
          escrito antes de correr.
        </Banner>
      )}
      {d.estado === 'parcial' && (
        <Banner tone="warn">
          Quedó a mitad de camino: algunas corridas faltan o fallaron (ver «Las corridas»). La cifra final
          aparece cuando la prueba se completa.
        </Banner>
      )}
      <Card title="La pregunta">
        <p>{d.pregunta ?? '—'}</p>
        {d.esperado && (
          <>
            <h3 className="eo-editor__section">Qué se esperaba (escrito antes de correr)</h3>
            <p className="eo-note">{d.esperado}</p>
          </>
        )}
      </Card>
      {cifrasGen1.length > 0 && (
        <Card title="Las cifras" meta="Generación 1: la cifra vigente" flush>
          <TableScroll label="Cifras de la generación 1">
            <Table aria-label="Cifras de la generación 1">
              <thead><tr><th>Qué se mide</th><th>Generación 1</th></tr></thead>
              <tbody>
                {cifrasGen1.map((c) => (
                  <tr key={c.clave}>
                    <td>{c.nombre}</td>
                    <td className="eo-num">{valorTexto(c.valor, c.unidad)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>
      )}
      {d.resumen.length > 0 && (
        <Card title="Las cifras" flush>
          <TableScroll label="Cifras de la prueba">
            <Table aria-label="Cifras de la prueba">
              <thead><tr><th>Qué se mide</th><th>Generación 2</th><th>Generación 1</th></tr></thead>
              <tbody>{d.resumen.map((c) => <CifraFila key={c.clave} c={c} />)}</tbody>
            </Table>
          </TableScroll>
        </Card>
      )}
      <Lecturas d={d} />
      <Tomas d={d} />
      <Card title="Contra la generación 1">
        {v ? (
          <>
            <p><Veredicto v={v} /></p>
            {v.confirmado?.motivo && <p className="eo-note">Motivo de quien confirmó: {v.confirmado.motivo}</p>}
            {v.motivo && <p className="eo-note">{v.confirmado ? 'Propuesta del programa: ' : ''}{v.motivo}</p>}
            {v.referencia && <p className="eo-note--meta">Referencia: <span className="eo-mono">{v.referencia}</span></p>}
          </>
        ) : (
          <p className="eo-note">
            {contraste
              ? 'No se regenera, así que no tiene veredicto: la cifra de arriba es la de la generación 1.'
              : sinCorrer ? 'El veredicto aparece cuando la prueba corre.' : 'Esta prueba no registró veredicto.'}
          </p>
        )}
        {difs.length > 0 && (
          <TableScroll label="Diferencias con la generación 1">
            <Table aria-label="Diferencias con la generación 1">
              <thead><tr><th>Campo</th><th>Generación 2</th><th>Generación 1</th></tr></thead>
              <tbody>
                {difs.map(([campo, par]) => (
                  <tr key={campo}>
                    <MonoCell>{campo}</MonoCell>
                    <td className="eo-num">{valorTexto(par.gen2)}</td>
                    <td className="eo-num">{valorTexto(par.gen1)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        )}
        <dl className="eo-deflist eo-gen2__gen1">
          <div><dt>Resultado de la generación 1</dt><dd className="eo-mono">{d.gen1.result_id ?? '—'}</dd></div>
          <div><dt>Documento</dt><dd className="eo-mono">{d.gen1.doc ?? '—'}</dd></div>
          {d.gen1.relacion && <div><dt>Relación</dt><dd>{VEREDICTO_LABEL[d.gen1.relacion] ?? d.gen1.relacion}</dd></div>}
          {d.gen1.motivo && <div><dt>Por qué</dt><dd>{d.gen1.motivo}</dd></div>}
          {d.gen1.nota && <div><dt>Nota</dt><dd>{d.gen1.nota}</dd></div>}
        </dl>
        <p className="eo-note--meta">
          Las cifras de la generación 1 están en la <Link to={GEN1.to}>validación inicial</Link>.
        </p>
      </Card>
      {d.entorno && <ComoCorrio entorno={d.entorno} gpuDeLaPlataforma={d.gpu_de_la_plataforma} />}
      {corridas.length > 0 && (
        <Card title="Las corridas" meta={`${corridas.length} registradas`} flush>
          <TableScroll label="Corridas de la prueba">
            <Table aria-label="Corridas de la prueba">
              <thead>
                <tr><th>Clave</th><th>Estado</th><th>Experimento</th><th>Corrida de detección</th><th>Corrida de reglas</th><th>Segundos</th></tr>
              </thead>
              <tbody>
                {corridas.map(([clave, c]) => (
                  <tr key={clave}>
                    <MonoCell>{clave}</MonoCell>
                    <td>{c.estado === 'ok' ? 'ok' : <span className="eo-note--error" title={c.error}>{c.estado}{c.error ? `: ${c.error}` : ''}</span>}</td>
                    <td>
                      {c.experiment_id
                        ? <Link className="eo-mono" to={`/experiments/${encodeURIComponent(c.experiment_id)}`}>{c.experiment_id}</Link>
                        : '—'}
                    </td>
                    <MonoCell>{c.media_run_id ?? '—'}</MonoCell>
                    <MonoCell>{c.control_run_id ?? '—'}</MonoCell>
                    <td className="eo-num">{c.segundos != null ? valorTexto(c.segundos) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>
      )}
      <Card title="El pre-registro">
        <p className="eo-note">
          {d.pre_registro.origen === 'copia_al_correr'
            ? 'Tal como estaba escrito cuando la prueba corrió.'
            : 'Tal como está en el catálogo (experiments/evidencia).'}
          {d.pre_registro.coincide_con_catalogo === false && (
            <b> El catálogo actual difiere de esta copia: se cambió después de correr.</b>
          )}
        </p>
        {d.pre_registro.texto && (
          <Disclosure summary="Ver el pre-registro completo (prueba.yaml)" open={sinCorrer}>
            <pre className="eo-pre">{d.pre_registro.texto}</pre>
          </Disclosure>
        )}
      </Card>
      {d.comandos && (
        <Card title="Lo que se ejecutó">
          <Disclosure summary="Ver los comandos, en orden y con su hora (comandos.txt)">
            <pre className="eo-pre">{d.comandos}</pre>
          </Disclosure>
        </Card>
      )}
      <Archivos d={d} />
    </div>
  )
}
