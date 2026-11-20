import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { clipCuadroUrl, clipVideoUrl } from '../api'
import { useClipDePrueba } from '../api/queries/gen2'
import { Badge, Banner, Button, Card, Disclosure, IconPlay, PageHeader, SegmentedControl, Table, TableScroll, Tag } from '../components/ui'
import NombreCodigo from '../components/ui/NombreCodigo'
import type { AlertaDeClip, ClipDePrueba, EpisodioDeClip } from '../types'
import { CAUSA_FALSA_ALARMA, NOMBRE_DE_PRUEBA, TIPO_DE_ALERTA, nombreConCodigo, nombreLectura, nombreLlano } from '../vocabulario'
import { EstadoDeLectura } from './evidencia/comun'
import './gen2/Clip.css'

type Seleccion = { tipo: 'alerta'; alerta: AlertaDeClip } | { tipo: 'episodio'; episodio: EpisodioDeClip }

const PRINCIPAL = '__principal__'
const seg = (ms: number | null | undefined) =>
  ms == null ? '—' : `${(ms / 1000).toLocaleString('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} s`
const TONO_ALERTA = { acierto: 'ok', falsa_alarma: 'error', re_alerta: 'neutral' } as const
const ESTADO_EPISODIO = { acierto: 'Con alerta', perdido: 'Perdido: sin alerta a tiempo', censurado: 'No evaluable: el clip termina antes' }

/** La selección inicial: la alerta que pide la dirección; si no, la primera falsa alarma, la primera alerta o el
 *  primer episodio perdido. Lo que más se pregunta va primero. */
function inicial(d: ClipDePrueba, pedida: string | null): Seleccion | null {
  const alerta = (pedida && d.alertas.find((a) => a.alert_id === pedida))
    || d.alertas.find((a) => a.tipo === 'falsa_alarma') || d.alertas[0]
  if (alerta) return { tipo: 'alerta', alerta }
  const episodio = d.episodios.find((e) => e.estado === 'perdido') || d.episodios[0]
  return episodio ? { tipo: 'episodio', episodio } : null
}

/** El instante que muestra una selección: la alerta, o el comienzo de la ventana en que el episodio debía alertar. */
const instante = (s: Seleccion) => (s.tipo === 'alerta' ? s.alerta.ms : s.episodio.ventana_ms[0])

/** La línea de tiempo del clip: por condición, un carril con los episodios de la referencia, la ventana en que cada
 *  uno debía alertar y las alertas encima. Una línea vertical marca el instante de lo elegido. */
function LineaDeTiempo({ d, sel, elegir }: { d: ClipDePrueba; sel: Seleccion | null; elegir: (s: Seleccion) => void }) {
  const fin = Math.max(d.duracion_ms ?? 0, ...d.alertas.map((a) => a.ms ?? 0), ...d.episodios.map((e) => e.hasta_ms ?? 0), 1000)
  const condiciones = Array.from(new Set([...d.episodios.map((e) => e.condicion), ...d.alertas.map((a) => a.condicion)])).sort()
  const ANCHO = 1000, IZQ = 132, DER = 14, FILA = 56, ARRIBA = 24, CARRIL = 24, EJE = 26
  const x = (ms: number) => IZQ + ((ANCHO - IZQ - DER) * ms) / fin
  const paso = fin > 120_000 ? 30_000 : fin > 60_000 ? 10_000 : 5_000
  const marcas = Array.from({ length: Math.floor(fin / paso) + 1 }, (_, i) => i * paso)
  const abajo = ARRIBA + condiciones.length * FILA
  const alto = abajo + EJE
  const ahora = sel ? instante(sel) : null
  return (
    <svg className="eo-clip-linea" viewBox={`0 0 ${ANCHO} ${alto}`} role="group" aria-label="Línea de tiempo del clip">
      {marcas.map((m) => (
        <g key={m}>
          <line x1={x(m)} x2={x(m)} y1={ARRIBA - 4} y2={abajo} className="eo-clip-linea__grilla" />
          <text x={x(m)} y={alto - 6} textAnchor="middle" className="eo-clip-linea__eje">{m / 1000} s</text>
        </g>
      ))}
      {condiciones.map((cond, i) => {
        const y = ARRIBA + i * FILA
        const medio = y + 8 + CARRIL / 2
        return (
          <g key={cond}>
            <text x={0} y={medio - 3} className="eo-clip-linea__cond">{nombreLlano(cond) ?? cond}</text>
            {nombreLlano(cond) && <text x={0} y={medio + 13} className="eo-clip-linea__codigo">{cond}</text>}
            <rect x={IZQ} y={y + 8} width={ANCHO - IZQ - DER} height={CARRIL} rx={5} className="eo-clip-linea__carril" />
            {d.episodios.filter((e) => e.condicion === cond).map((e) => {
              const elegido = sel?.tipo === 'episodio' && sel.episodio.id === e.id
              const [v0, v1] = e.ventana_ms
              return (
                <g key={e.id}>
                  <rect x={x(e.desde_ms)} y={y + 8} width={Math.max(2, x(e.hasta_ms ?? fin) - x(e.desde_ms))} height={CARRIL}
                    rx={5} className={`eo-clip-linea__episodio eo-clip-linea__episodio--${e.estado ?? 'sin-dato'}${elegido ? ' is-sel' : ''}`}
                    role="button" tabIndex={0} aria-label={`Episodio de ${cond} de ${seg(e.desde_ms)} a ${seg(e.hasta_ms)}: ${e.estado ? ESTADO_EPISODIO[e.estado] : 'sin dato'}`}
                    onClick={() => elegir({ tipo: 'episodio', episodio: e })}
                    onKeyDown={(ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); elegir({ tipo: 'episodio', episodio: e }) } }}>
                    <title>Referencia: {cond} de {seg(e.desde_ms)} a {seg(e.hasta_ms)}</title>
                  </rect>
                  <path d={`M${x(v0)} ${y + CARRIL + 11}v5H${x(v1)}v-5`} className="eo-clip-linea__ventana" aria-hidden="true" />
                  {elegido && (
                    <rect x={x(e.desde_ms) - 4} y={y + 4} width={Math.max(2, x(e.hasta_ms ?? fin) - x(e.desde_ms)) + 8}
                      height={CARRIL + 8} rx={8} className="eo-clip-linea__halo" aria-hidden="true" />
                  )}
                </g>
              )
            })}
            {d.alertas.filter((a) => a.condicion === cond && a.ms != null).map((a) => {
              const elegida = sel?.tipo === 'alerta' && sel.alerta.alert_id === a.alert_id
              return (
                <g key={a.alert_id}>
                  {elegida && <circle cx={x(a.ms!)} cy={medio} r={13} className="eo-clip-linea__halo" aria-hidden="true" />}
                  <circle cx={x(a.ms!)} cy={medio} r={elegida ? 8 : 7}
                    className={`eo-clip-linea__alerta eo-clip-linea__alerta--${a.tipo}${elegida ? ' is-sel' : ''}`}
                    role="button" tabIndex={0} aria-label={`${TIPO_DE_ALERTA[a.tipo]} de ${cond} a los ${seg(a.ms)}`}
                    onClick={() => elegir({ tipo: 'alerta', alerta: a })}
                    onKeyDown={(ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); elegir({ tipo: 'alerta', alerta: a }) } }}>
                    <title>{TIPO_DE_ALERTA[a.tipo]} a los {seg(a.ms)}</title>
                  </circle>
                </g>
              )
            })}
          </g>
        )
      })}
      {ahora != null && (
        <g className="eo-clip-linea__ahora" aria-hidden="true">
          <line x1={x(ahora)} x2={x(ahora)} y1={ARRIBA - 6} y2={abajo} />
          <text x={x(ahora)} y={ARRIBA - 10} textAnchor="middle">{seg(ahora)}</text>
        </g>
      )}
    </svg>
  )
}

/** La clave de la línea de tiempo, con los conteos del evaluador al lado de cada marca. */
function Clave({ k, conEpisodios }: { k: ClipDePrueba['conteos']; conEpisodios: boolean }) {
  const n = (valor: number | null | undefined, uno: string, varios: string) =>
    valor == null ? varios : <><b>{valor}</b> {valor === 1 ? uno : varios}</>
  return (
    <div className="eo-clip-clave">
      <div className="eo-clip-clave__grupo">
        <span className="eo-clip-clave__titulo">Referencia{k ? <> · {n(k.episodios, 'episodio', 'episodios')}</> : null}</span>
        {conEpisodios && <>
          {k ? <>
            <span className="eo-clip-clave__item eo-clip-clave__item--acierto">{n(k.aciertos, 'con alerta', 'con alerta')}</span>
            <span className="eo-clip-clave__item eo-clip-clave__item--perdido">{n(k.perdidos, 'perdido', 'perdidos')}</span>
          </> : <span className="eo-clip-clave__item eo-clip-clave__item--censurado">episodio</span>}
          {k && (k.censurados ?? 0) > 0 && (
            <span className="eo-clip-clave__item eo-clip-clave__item--censurado">{n(k.censurados, 'no evaluable', 'no evaluables')}</span>
          )}
          <span className="eo-clip-clave__item eo-clip-clave__item--ventana">ventana en que debía alertar</span>
        </>}
      </div>
      <div className="eo-clip-clave__grupo">
        <span className="eo-clip-clave__titulo">Alertas</span>
        <span className="eo-clip-clave__item eo-clip-clave__item--punto-acierto">acierto</span>
        <span className="eo-clip-clave__item eo-clip-clave__item--punto-falsa">{n(k?.falsas_alarmas, 'falsa alarma', 'falsas alarmas')}</span>
        <span className="eo-clip-clave__item eo-clip-clave__item--punto-re">{n(k?.re_alertas, 're-alerta', 're-alertas')}</span>
      </div>
    </div>
  )
}

/** Una imagen que tarda en salir (la primera vez el cuadro se saca del video): mientras tanto, lo dice. */
function Cuadro({ src, alt }: { src: string; alt: string }) {
  const [estado, setEstado] = useState<'cargando' | 'listo' | 'falla'>('cargando')
  useEffect(() => { setEstado('cargando') }, [src])
  return (
    <>
      {estado === 'cargando' && <p className="eo-note eo-clip-sel__cargando">Sacando el cuadro del video…</p>}
      {estado === 'falla' && <p className="eo-note eo-clip-sel__cargando">Este cuadro no se pudo sacar en este equipo.</p>}
      <img src={src} alt={alt} onLoad={() => setEstado('listo')} onError={() => setEstado('falla')}
        style={estado === 'listo' ? undefined : { display: 'none' }} />
    </>
  )
}

/** Lo elegido: el cuadro con lo que vio el sistema, la persona de la alerta acercada y, en una línea, qué fue. */
function LoQueSeVe({ d, sel, lectura, alVideo }: { d: ClipDePrueba; sel: Seleccion; lectura: string | null; alVideo?: () => void }) {
  const ms = instante(sel)
  const cuadro = ms == null ? null : sel.tipo === 'alerta' && sel.alerta.cuadro != null ? sel.alerta.cuadro : Math.round((ms / 1000) * d.fps)
  const alerta = sel.tipo === 'alerta' ? sel.alerta : null
  const src = d.cuadros && cuadro != null ? clipCuadroUrl(d.prueba, d.clip, cuadro, lectura, alerta?.alert_id) : null
  const acercado = src && alerta?.caja ? clipCuadroUrl(d.prueba, d.clip, cuadro!, lectura, alerta.alert_id, true) : null
  return (
    <div className="eo-clip-sel">
      <figure className="eo-clip-sel__cuadro">
        {src
          ? <Cuadro src={src} alt={`Cuadro ${cuadro} del clip ${d.clip}, con las cajas del sistema`} />
          : <p className="eo-note">El video de este clip no está en este equipo.</p>}
        {src && (
          <figcaption>
            Cuadro {cuadro}.{' '}
            {!d.cajas ? 'Sin cajas: las detecciones de la corrida no están en este equipo.'
              : alerta?.caja ? 'Las cajas son las que vio el sistema en ese cuadro; en amarillo, la persona de la alerta.'
                : 'Las cajas son las que vio el sistema en ese cuadro.'}
          </figcaption>
        )}
      </figure>
      <div className="eo-clip-sel__texto">
        {sel.tipo === 'alerta' ? (
          <>
            <p className="eo-clip-sel__tipo"><Badge tone={TONO_ALERTA[sel.alerta.tipo]}>{TIPO_DE_ALERTA[sel.alerta.tipo]}</Badge></p>
            <p className="eo-clip-sel__titular">
              <NombreCodigo codigo={sel.alerta.condicion} /> a los <b>{seg(sel.alerta.ms)}</b>
            </p>
            {sel.alerta.causa && CAUSA_FALSA_ALARMA[sel.alerta.causa] && (
              <p><b>Causa: {CAUSA_FALSA_ALARMA[sel.alerta.causa].nombre}.</b> {CAUSA_FALSA_ALARMA[sel.alerta.causa].que}.</p>
            )}
            {sel.alerta.tipo === 'falsa_alarma' && !sel.alerta.causa && (
              <p>No cae en la ventana de ningún episodio de la referencia.</p>
            )}
            {sel.alerta.primera_evidencia_ms != null && (
              <p className="eo-note">Primera evidencia a los {seg(sel.alerta.primera_evidencia_ms)}; la regla la confirmó a los {seg(sel.alerta.ms)}.</p>
            )}
            {sel.alerta.sujeto && <p className="eo-note">Persona seguida: <span className="eo-mono">{sel.alerta.sujeto}</span>.</p>}
            {acercado && (
              <figure className="eo-clip-sel__acercado">
                <Cuadro src={acercado} alt={`La persona de la alerta, acercada, en el cuadro ${cuadro}`} />
                <figcaption>La persona de la alerta, acercada.</figcaption>
              </figure>
            )}
          </>
        ) : (
          <>
            <p className="eo-clip-sel__tipo">
              <Badge tone={sel.episodio.estado === 'perdido' ? 'error' : sel.episodio.estado === 'acierto' ? 'ok' : 'neutral'}>
                {sel.episodio.estado ? ESTADO_EPISODIO[sel.episodio.estado] : 'Sin dato en este equipo'}
              </Badge>
            </p>
            <p className="eo-clip-sel__titular">
              <NombreCodigo codigo={sel.episodio.condicion} /> en la referencia, de <b>{seg(sel.episodio.desde_ms)}</b> a <b>{seg(sel.episodio.hasta_ms)}</b>
            </p>
            <p>La regla tenía que alertar entre los {seg(sel.episodio.ventana_ms[0])} y los {seg(sel.episodio.ventana_ms[1])}: el cuadro es el del comienzo de esa ventana.</p>
          </>
        )}
        {d.video && alVideo && <Button className="eo-clip-sel__video" onClick={alVideo}><IconPlay /> Ver en el video</Button>}
      </div>
    </div>
  )
}

/** «Mostrame un run donde pasó esto» (consola de evidencia): un clip de una prueba de la campaña final, con la
 *  referencia, las alertas, el cuadro de cada una con sus cajas y el video original. Las cifras son las del
 *  evaluador; lo que no está en este equipo se dice. */
export default function ClipPage() {
  const { id = '', clip = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const lectura = params.get('lectura')
  const q = useClipDePrueba(id, clip, lectura)
  const [sel, setSel] = useState<Seleccion | null>(null)
  const video = useRef<HTMLVideoElement>(null)
  const d = q.data
  const pedida = params.get('alerta')
  useEffect(() => { if (d) setSel(inicial(d, pedida)) }, [d, pedida])
  const alVideo = useMemo(() => () => {
    const ms = sel ? instante(sel) : null
    if (video.current && ms != null) {
      video.current.currentTime = Math.max(0, ms / 1000 - 1)
      video.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [sel])
  if (q.isPending || q.error || !d) {
    return <EstadoDeLectura titulo={`Clip ${clip}`} q={q} noExiste="Ese clip no está en esa prueba." />
  }
  const elegirLectura = (valor: string) => {
    const siguiente = new URLSearchParams(params)
    siguiente.delete('alerta')
    if (valor === PRINCIPAL) siguiente.delete('lectura')
    else siguiente.set('lectura', valor)
    setParams(siguiente, { replace: true })
  }
  const k = d.conteos
  const hayMarcas = d.alertas.length > 0 || d.episodios.length > 0
  return (
    <div className="eo-gen2 eo-clip">
      <PageHeader
        title={<>Clip <span className="eo-mono">{d.clip}</span></>}
        meta={<>
          <Tag>{d.tipo_clip === 'rodaje' ? 'Rodaje guionado' : 'Obra real'}</Tag>
          <span>de <Link to={`/resultados/${encodeURIComponent(d.prueba)}`} title={nombreConCodigo(d.prueba)}>
            {NOMBRE_DE_PRUEBA[d.prueba] ?? d.prueba} <span className="eo-mono">{d.prueba}</span></Link></span>
        </>}
      />
      {d.lecturas.length > 1 && (
        <SegmentedControl label="Lectura" value={lectura ?? PRINCIPAL} onChange={elegirLectura}
          options={d.lecturas.map((l) => ({ value: l ?? PRINCIPAL, label: l ? nombreLectura(l) : 'Lectura principal' }))} />
      )}
      {d.faltan.length > 0 && (
        <Banner tone="warn">En este equipo falta {d.faltan.join('; ')}.</Banner>
      )}
      <Card title="Lo que pasó" meta={hayMarcas ? 'cada marca se puede elegir' : undefined}>
        <Clave k={k} conEpisodios={d.episodios.length > 0} />
        {hayMarcas ? <>
          <LineaDeTiempo d={d} sel={sel} elegir={setSel} />
          {sel && <LoQueSeVe d={d} sel={sel} lectura={lectura} alVideo={d.video ? alVideo : undefined} />}
        </> : <p className="eo-note eo-clip__vacio">Sin alertas ni episodios en este clip.</p>}
      </Card>
      {d.video && (
        <Card title="El video">
          <video ref={video} className="eo-clip__video" controls preload="metadata" src={clipVideoUrl(d.prueba, d.clip)} />
        </Card>
      )}
      <div className="eo-clip__tablas">
        {d.alertas.length > 0 && (
          <Card title="Las alertas" meta={d.alertas_completas ? `${d.alertas.length}` : 'solo las falsas alarmas: la corrida no está en este equipo'} flush>
            <TableScroll label="Las alertas">
              <Table aria-label="Las alertas">
                <thead><tr><th className="eo-num">Segundo</th><th>Condición</th><th>Qué fue</th><th>Causa</th><th><span className="eo-sr">Ver</span></th></tr></thead>
                <tbody>
                  {d.alertas.map((a) => (
                    <tr key={a.alert_id} className={sel?.tipo === 'alerta' && sel.alerta.alert_id === a.alert_id ? 'is-sel' : undefined}>
                      <td className="eo-num">{seg(a.ms)}</td>
                      <td><NombreCodigo codigo={a.condicion} /></td>
                      <td><Badge tone={TONO_ALERTA[a.tipo]}>{TIPO_DE_ALERTA[a.tipo]}</Badge></td>
                      <td>{a.causa ? (CAUSA_FALSA_ALARMA[a.causa]?.nombre ?? a.causa) : '—'}</td>
                      <td className="eo-clip__ver"><Button variant="ghost" onClick={() => setSel({ tipo: 'alerta', alerta: a })}>Ver</Button></td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableScroll>
          </Card>
        )}
        {d.episodios.length > 0 && (
          <Card title="Los episodios de la referencia" meta={`${d.episodios.length}`} flush>
            <TableScroll label="Los episodios de la referencia">
              <Table aria-label="Los episodios de la referencia">
                <thead><tr><th className="eo-num">Desde</th><th className="eo-num">Hasta</th><th>Condición</th><th>Resultado</th><th><span className="eo-sr">Ver</span></th></tr></thead>
                <tbody>
                  {d.episodios.map((e) => (
                    <tr key={e.id} className={sel?.tipo === 'episodio' && sel.episodio.id === e.id ? 'is-sel' : undefined}>
                      <td className="eo-num">{seg(e.desde_ms)}</td>
                      <td className="eo-num">{seg(e.hasta_ms)}</td>
                      <td><NombreCodigo codigo={e.condicion} /></td>
                      <td>{e.estado ? ESTADO_EPISODIO[e.estado] : '—'}</td>
                      <td className="eo-clip__ver"><Button variant="ghost" onClick={() => setSel({ tipo: 'episodio', episodio: e })}>Ver</Button></td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableScroll>
          </Card>
        )}
      </div>
      <Card>
        <Disclosure summary={<h2 className="eo-gen2__plegado">De dónde sale</h2>}>
          <ul className="eo-clip__origen">
            <li>Cifras: las del evaluador, en <span className="eo-mono">{d.origen.evaluacion ?? '—'}</span>.</li>
            <li>Experimento: {d.origen.experiment_id
              ? <Link className="eo-mono" to={`/experiments/${encodeURIComponent(d.origen.experiment_id)}`}>{d.origen.experiment_id}</Link>
              : '—'}</li>
            <li>Corrida de detección: <span className="eo-mono">{d.origen.media_run_id ?? '—'}</span></li>
            <li>Corrida del plano de control: <span className="eo-mono">{d.origen.control_run_id ?? '—'}</span></li>
          </ul>
        </Disclosure>
      </Card>
    </div>
  )
}
