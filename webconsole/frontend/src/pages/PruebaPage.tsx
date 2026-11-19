import { Link, useParams } from 'react-router-dom'
import { gen2ArchivoUrl } from '../api'
import { useGen2Prueba } from '../api/queries/gen2'
import { Banner, Card, Disclosure, MonoCell, PageHeader, Table, TableScroll, Tag } from '../components/ui'
import NombreCodigo, { ConCodigos } from '../components/ui/NombreCodigo'
import { GEN1 } from '../nav'
import { NOMBRE_DE_PRUEBA, nombreConCodigo, nombreLectura } from '../vocabulario'
import type { Gen2Cifra, Gen2Corrida, Gen2Desglose, Gen2Detalle, Gen2Entorno } from '../types'
import { EstadoDeLectura } from './evidencia/comun'
import FalsasAlarmasUnaPorUna from './gen2/FalsasAlarmasUnaPorUna'
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


const nombreCifra = (c: Gen2Cifra) => <ConCodigos texto={c.nombre_consola ?? c.nombre} />

function valorConIntervalo(c: Gen2Cifra | undefined) {
  if (!c) return '—'
  return (
    <>
      {valorTexto(c.valor, c.unidad)}
      {c.ic95 && <span className="eo-note--meta"> (IC 95 %: {valorTexto(c.ic95[0])} a {valorTexto(c.ic95[1])})</span>}
      {c.n != null && <span className="eo-note--meta"> · n = {valorTexto(c.n)}</span>}
    </>
  )
}

/** El resultado (plan de la consola, §2.4): todas las lecturas de la prueba lado a lado —la principal
 *  y las demás (por sujeto, otra regla…)—, con los nombres de la consola. Solo cifras finales. */
function ElResultado({ d }: { d: Gen2Detalle }) {
  const lecturas = d.lecturas ?? []
  if (d.resumen.length === 0 && lecturas.length === 0) return null
  // Las filas son las cifras de la lectura principal, más las que solo tenga alguna otra.
  const filas = [...d.resumen]
  for (const l of lecturas) for (const c of l.resumen) if (!filas.some((f) => f.clave === c.clave)) filas.push(c)
  const de = (resumen: Gen2Cifra[], clave: string) => resumen.find((x) => x.clave === clave)
  return (
    <Card title="El resultado" meta={lecturas.length > 0 ? `${lecturas.length + 1} lecturas` : undefined} flush>
      <TableScroll label="El resultado">
        <Table aria-label="El resultado">
          <thead>
            <tr>
              <th>Qué se mide</th>
              <th className="eo-num">{lecturas.length > 0 ? 'Lectura principal' : 'Resultado'}</th>
              {lecturas.map((l) => <th key={l.nombre} className="eo-num">{nombreLectura(l.nombre)}</th>)}
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.clave}>
                <td>{nombreCifra(f)}</td>
                <td className="eo-num">{valorConIntervalo(de(d.resumen, f.clave))}</td>
                {lecturas.map((l) => <td key={l.nombre} className="eo-num">{valorConIntervalo(de(l.resumen, f.clave))}</td>)}
              </tr>
            ))}
          </tbody>
        </Table>
      </TableScroll>
    </Card>
  )
}

const FUENTE: Record<string, string> = {
  chv: 'CHV', shel5k: 'SHEL5K', obra_test: 'Obra curada, prueba', obra_val: 'Obra curada, validación',
}
const CLASE: Record<string, string> = {
  person: 'Persona', helmet: 'Casco', vest: 'Chaleco', bare_head: 'Cabeza descubierta', machinery: 'Maquinaria',
}
const numero = (v: number | null | undefined, decimales: number) =>
  v == null ? '—' : v.toLocaleString('es-AR', { minimumFractionDigits: decimales, maximumFractionDigits: decimales })

/** El desglose (§2.4): sobre un banco temporal, una fila por clip; sobre imágenes, por fuente y por
 *  clase. Sale de las evaluaciones de la prueba (`evals/`), sin calcular nada. */
function Desglose({ desglose, prueba, conRun }: { desglose: Gen2Desglose; prueba: string; conRun: boolean }) {
  if (desglose.tipo === 'clips') {
    return (
      <Card title="Clip por clip" meta={`${desglose.clips.length} clips${conRun ? ' · cada clip abre su run' : ''}`} flush>
        <TableScroll label="Clip por clip">
          <Table aria-label="Clip por clip">
            <thead>
              <tr>
                <th>Clip</th><th className="eo-num">Episodios</th><th className="eo-num">Aciertos</th>
                <th className="eo-num">Perdidos</th><th className="eo-num">Falsas alarmas</th>
                <th className="eo-num">Re-alertas</th><th className="eo-num">Latencia de alerta</th>
                <th className="eo-num" title="Qué fracción del episodio anotado quedó cubierta por detecciones">SDR (cobertura del episodio)</th>
              </tr>
            </thead>
            <tbody>
              {desglose.clips.map((c) => (
                <tr key={c.clip}>
                  <MonoCell>
                    {conRun
                      ? <Link to={`/resultados/${encodeURIComponent(prueba)}/clips/${encodeURIComponent(c.clip)}`}
                          aria-label={`Ver el run del clip ${c.clip}`}>{c.clip}</Link>
                      : c.clip}
                  </MonoCell>
                  <td className="eo-num">{numero(c.episodios, 0)}</td>
                  <td className="eo-num">{numero(c.aciertos, 0)}</td>
                  <td className="eo-num">{numero(c.perdidos, 0)}</td>
                  <td className="eo-num">{numero(c.falsas_alarmas, 0)}</td>
                  <td className="eo-num">{numero(c.re_alertas, 0)}</td>
                  <td className="eo-num">{c.t_alert_ms == null ? '—' : `${numero(c.t_alert_ms / 1000, 2)} s`}</td>
                  <td className="eo-num">{numero(c.sdr, 3)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </TableScroll>
      </Card>
    )
  }
  const clases = Array.from(new Set(desglose.fuentes.flatMap((f) => f.clases.map((c) => c.clase))))
  return (
    <Card title="Por fuente y por clase" meta={`${desglose.fuentes.length} fuentes`} flush>
      <TableScroll label="Por fuente y por clase">
        <Table aria-label="Por fuente y por clase">
          <thead>
            <tr>
              <th>Fuente</th><th className="eo-num">mAP50</th>
              {clases.map((c) => <th key={c} className="eo-num">AP50 {CLASE[c]?.toLowerCase() ?? c}</th>)}
              <th className="eo-num"><ConCodigos texto="Recall de CR-01 por evidencia directa" /></th>
            </tr>
          </thead>
          <tbody>
            {desglose.fuentes.map((f) => (
              <tr key={f.fuente}>
                <td>{FUENTE[f.fuente] ?? f.fuente}</td>
                <td className="eo-num">{numero(f.map50, 3)}</td>
                {clases.map((c) => {
                  const x = f.clases.find((y) => y.clase === c)
                  return (
                    <td key={c} className="eo-num">
                      {x ? numero(x.ap50, 3) : '—'}
                      {x?.n_gt != null && <span className="eo-note--meta"> · n = {x.n_gt}</span>}
                    </td>
                  )
                })}
                <td className="eo-num">{numero(f.recall_cr01, 3)}</td>
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

/** Cómo se validó (plegado; plan de la consola, §2.4 y ajuste del 2026-11-15): lo que se escribió antes de
 *  correr, tal cual; el veredicto con su motivo; y la comparación con la etapa de desarrollo. Es el único
 *  lugar del detalle donde aparecen esos textos y esa jerga. */
function ComoSeValido({ d }: { d: Gen2Detalle }) {
  const v = d.veredicto
  const difs = Object.entries(v?.diferencias ?? {})
  const contraste = noSeRegenera(d)
  const sinCorrer = d.estado === 'sin_correr' && !contraste
  const cifrasGen1 = contraste ? (d.gen1.cifras ?? []) : []
  return (
    <Card>
      <Disclosure summary={<h2 className="eo-gen2__plegado">Cómo se validó</h2>} open={sinCorrer}>
        <h3 className="eo-editor__section">Lo que se escribió antes de correr (pre-registro, tal cual)</h3>
        <blockquote className="eo-gen2__cita">
          <p>{d.pregunta ?? '—'}</p>
          {d.esperado && <p><b>Qué se esperaba:</b> {d.esperado}</p>}
        </blockquote>

        <h3 className="eo-editor__section">La concordancia</h3>
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
              ? 'No se regenera, así que no tiene concordancia: su cifra vigente es la de la etapa de desarrollo.'
              : sinCorrer ? 'La concordancia aparece cuando la prueba corre.' : 'Esta prueba no registró concordancia.'}
          </p>
        )}

        <h3 className="eo-editor__section">Contra la etapa de desarrollo</h3>
        {contraste && <p>{d.no_se_regenera ?? 'Prueba de contraste: su cifra vigente es la de la etapa de desarrollo.'}</p>}
        {cifrasGen1.length > 0 && (
          <TableScroll label="Cifras de la etapa de desarrollo">
            <Table aria-label="Cifras de la etapa de desarrollo">
              <thead><tr><th>Qué se mide</th><th>Etapa de desarrollo</th></tr></thead>
              <tbody>
                {cifrasGen1.map((c) => (
                  <tr key={c.clave}><td>{c.nombre}</td><td className="eo-num">{valorTexto(c.valor, c.unidad)}</td></tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        )}
        {d.resumen.length > 0 && (
          <TableScroll label="Cifras de la prueba">
            <Table aria-label="Cifras de la prueba">
              <thead><tr><th>Qué se mide</th><th>Resultado</th><th>Etapa de desarrollo</th></tr></thead>
              <tbody>{d.resumen.map((c) => <CifraFila key={c.clave} c={c} />)}</tbody>
            </Table>
          </TableScroll>
        )}
        {difs.length > 0 && (
          <TableScroll label="Diferencias con la etapa de desarrollo">
            <Table aria-label="Diferencias con la etapa de desarrollo">
              <thead><tr><th>Campo</th><th>Resultado</th><th>Etapa de desarrollo</th></tr></thead>
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
          <div><dt>Resultado de la etapa de desarrollo</dt><dd className="eo-mono">{d.gen1.result_id ?? '—'}</dd></div>
          <div><dt>Documento</dt><dd className="eo-mono">{d.gen1.doc ?? '—'}</dd></div>
          {d.gen1.relacion && <div><dt>Relación</dt><dd>{VEREDICTO_LABEL[d.gen1.relacion] ?? d.gen1.relacion}</dd></div>}
          {d.gen1.motivo && <div><dt>Por qué</dt><dd>{d.gen1.motivo}</dd></div>}
          {d.gen1.nota && <div><dt>Nota</dt><dd>{d.gen1.nota}</dd></div>}
        </dl>
        <p className="eo-note--meta">
          Las cifras de la etapa de desarrollo están en el <Link to={GEN1.to}>Archivo</Link>.
        </p>

        <h3 className="eo-editor__section">El pre-registro completo</h3>
        <p className="eo-note">
          {d.pre_registro.origen === 'copia_al_correr'
            ? 'Tal como estaba escrito cuando la prueba corrió.'
            : 'Tal como está en el catálogo (experiments/evidencia).'}
          {d.pre_registro.coincide_con_catalogo === false && (
            <b> El catálogo actual difiere de esta copia: se cambió después de correr.</b>
          )}
        </p>
        {d.pre_registro.texto && <pre className="eo-pre">{d.pre_registro.texto}</pre>}
      </Disclosure>
    </Card>
  )
}

/** Archivos y comandos (plegado, §2.4): las corridas con sus identificadores, lo que se ejecutó y los
 *  archivos que dejó la prueba. */
function ArchivosYComandos({ d }: { d: Gen2Detalle }) {
  const corridas = d.corridas ? filasCorridas(d.corridas) : []
  if (corridas.length === 0 && !d.comandos && d.archivos.logs.length + d.archivos.evals.length + d.archivos.capturas.length === 0) {
    return null
  }
  return (
    <Card>
      <Disclosure summary={<h2 className="eo-gen2__plegado">Archivos y comandos</h2>}>
        {corridas.length > 0 && (
          <>
            <h3 className="eo-editor__section">Las corridas <span className="eo-note--meta">· {corridas.length} registradas</span></h3>
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
          </>
        )}
        {d.comandos && (
          <>
            <h3 className="eo-editor__section">Lo que se ejecutó, en orden y con su hora</h3>
            <pre className="eo-pre">{d.comandos}</pre>
          </>
        )}
        <Archivos d={d} />
      </Disclosure>
    </Card>
  )
}

/** El detalle de una prueba (plan de la consola, §2.4). A la vista: qué midió, el resultado con todas sus
 *  lecturas, el desglose y cómo corrió. Plegado: cómo se validó y los archivos. */
export default function PruebaPage() {
  const { id = '' } = useParams()
  const q = useGen2Prueba(id)
  if (q.isPending || q.error) {
    return <EstadoDeLectura titulo={nombreConCodigo(id)} q={q} noExiste="Esa prueba no está en el catálogo." />
  }
  const d = q.data
  const contraste = noSeRegenera(d)
  const sinCorrer = d.estado === 'sin_correr' && !contraste
  return (
    <div className="eo-gen2">
      <PageHeader
        title={<NombreCodigo codigo={d.id} nombre={NOMBRE_DE_PRUEBA[d.id] ?? d.titulo ?? undefined} />}
        meta={<>
          {d.estado !== 'completo' && <EstadoPrueba estado={d.estado} registro={d.registro} />}
          {d.informe.map((s) => <Tag key={s}>{s}</Tag>)}
          {/* «generado» es cuándo se escribió el resultado, no cuándo se tomaron los datos: las pruebas en vivo se
              re-agregaron el 2026-11-12 sobre tomas del 11-01 y del 11-07 (doc 134 §13.22). */}
          {d.generado && <span>Resultado generado el {d.generado.slice(0, 10)}</span>}
        </>}
      />
      {d.que_midio && <p className="eo-gen2__que">{d.que_midio}</p>}
      {sinCorrer && (
        <Banner tone="warn">
          Todavía no se corrió. En «Cómo se validó» está lo que se escribió antes de correr.
        </Banner>
      )}
      {d.estado === 'parcial' && (
        <Banner tone="warn">
          Quedó parcial: no tiene todo lo que pedía su pre-registro. Lo que falta y por qué está en «Cómo se
          validó»; las corridas, en «Archivos y comandos».
        </Banner>
      )}
      <ElResultado d={d} />
      {d.desglose && (
        <Desglose desglose={d.desglose} prueba={d.id} conRun={Boolean(d.corridas && Object.keys(d.corridas).length > 0)} />
      )}
      {d.id === 'ERR-01' && <FalsasAlarmasUnaPorUna />}
      <Tomas d={d} />
      {d.entorno && <ComoCorrio entorno={d.entorno} gpuDeLaPlataforma={d.gpu_de_la_plataforma} />}
      <ComoSeValido d={d} />
      <ArchivosYComandos d={d} />
    </div>
  )
}
