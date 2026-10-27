import { Link, useParams } from 'react-router-dom'
import { gen2ArchivoUrl } from '../api'
import { useGen2Prueba } from '../api/queries/gen2'
import { Banner, Card, Disclosure, MonoCell, PageHeader, Table, TableScroll, Tag } from '../components/ui'
import { GEN1 } from '../nav'
import type { Gen2Corrida, Gen2Detalle, Gen2Entorno } from '../types'
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

/** Cómo corrió: el equipo, las imágenes y los commits, tal como los registró la
 *  prueba (`entorno.json`). */
export function ComoCorrio({ entorno, titulo = 'Cómo corrió' }: { entorno: Gen2Entorno; titulo?: string }) {
  const imagenes = Object.entries(entorno.docker?.imagenes ?? {})
  const repos = Object.entries(entorno.repos ?? {})
  return (
    <Card title={titulo}>
      <dl className="eo-deflist">
        <div><dt>Equipo</dt><dd>{entorno.host?.nombre ?? '—'}</dd></div>
        <div><dt>Procesador</dt><dd>{entorno.host?.cpu ?? '—'}{entorno.host?.nucleos ? ` (${entorno.host.nucleos} núcleos)` : ''}</dd></div>
        <div><dt>Memoria</dt><dd>{entorno.host?.memoria_gb != null ? `${valorTexto(entorno.host.memoria_gb)} GB` : '—'}</dd></div>
        <div><dt>GPU</dt><dd>{entorno.gpu ?? '—'}</dd></div>
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
      {d.entorno && <ComoCorrio entorno={d.entorno} />}
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
