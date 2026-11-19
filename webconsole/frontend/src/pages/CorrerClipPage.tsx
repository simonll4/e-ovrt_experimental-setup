import { useState } from 'react'
import { ApiError } from '../api'
import { useClipsDemostracion, useCorrerClip, useDejarLista, usePreparacionClip } from '../api/queries/plataforma'
import { segundos } from '../components/demo/formato'
import {
  Badge, Button, Card, Disclosure, ErrorBanner, LoadingState, NombreCodigo, PageHeader, Table, TableScroll, Tag,
} from '../components/ui'
import type { BadgeTone, ClipDemostracion, CorridaClip, PasoClip } from '../types'
import './CorrerClipPage.css'

const PASOS: Array<[keyof CorridaClip['pasos'], string]> = [
  ['deteccion', 'Detección'], ['reglas', 'Reglas'], ['distribucion', 'Distribución'], ['broker', 'Broker'],
]
const ESTADO_PASO: Record<PasoClip['estado'], [BadgeTone, string]> = {
  espera: ['neutral', 'en espera'], en_curso: ['live', 'en curso'], ok: ['ok', 'listo'], error: ['error', 'falló'],
}

function Referencia({ clip }: { clip: ClipDemostracion }) {
  if (clip.referencia.length === 0) return <span>Nadie se saca nada: no tiene que haber alerta.</span>
  return (
    <span>
      {clip.referencia.map((e, i) => (
        <span key={i}>{i > 0 && '; '}<NombreCodigo codigo={e.condicion} /> desde el segundo {segundos(e.desde_ms)}</span>
      ))}
    </span>
  )
}

function detallePaso(clave: keyof CorridaClip['pasos'], p: PasoClip, esperados: number | null): string | null {
  if (clave === 'broker') return p.mensajes != null ? `${p.mensajes} ${p.mensajes === 1 ? 'mensaje' : 'mensajes'}` : null
  if (p.cuadros == null) return null
  return esperados && clave === 'deteccion' ? `${p.cuadros} de ${esperados} cuadros` : `${p.cuadros} cuadros`
}

function Avance({ c }: { c: CorridaClip }) {
  return (
    <ol className="eo-clip__cadena" aria-label="El clip por la cadena">
      {PASOS.map(([clave, nombre]) => {
        const p = c.pasos[clave]
        const [tono, texto] = ESTADO_PASO[p.estado]
        const detalle = detallePaso(clave, p, c.cuadros_esperados)
        return (
          <li key={clave} className={`eo-clip__paso eo-clip__paso--${p.estado}`}>
            <span className="eo-clip__paso-nombre">{nombre}</span>
            <Badge tone={tono} pulse={p.estado === 'en_curso'}>{texto}</Badge>
            {detalle && <span className="eo-note--meta">{detalle}</span>}
          </li>
        )
      })}
    </ol>
  )
}

function Resultado({ c }: { c: CorridaClip }) {
  const r = c.resultado
  if (!r) return null
  const ev = r.evaluacion
  return (
    <Card title="El resultado" meta={c.clip.titulo}>
      {ev && ev.expected === 0 && ev.observed === 0 && (
        <p className="eo-clip__conteo">La referencia no espera alertas y la corrida no dio ninguna.</p>
      )}
      {ev && (ev.expected > 0 || ev.observed > 0) && (
        <p className="eo-clip__conteo">
          La referencia esperaba <b>{ev.expected}</b> {ev.expected === 1 ? 'alerta' : 'alertas'}; la corrida dio{' '}
          <b>{ev.observed}</b>: <b>{ev.matched}</b> {ev.matched === 1 ? 'acertada' : 'acertadas'}
          {ev.unexpected > 0 && <>, <b>{ev.unexpected}</b> de más</>}
          {ev.missed > 0 && <>, <b>{ev.missed}</b> sin alerta</>}.
        </p>
      )}
      {!ev && r.alertas.length === 0 && r.sin_alerta.length === 0 && <p>Sin alertas, como la referencia.</p>}
      {r.alertas.length > 0 && (
        <TableScroll label="Las alertas de la corrida">
          <Table aria-label="Las alertas de la corrida">
            <thead>
              <tr>
                <th>Alerta</th><th className="eo-num">Confirmada en el clip</th><th>En la referencia</th>
                <th className="eo-num">Desde que empieza el episodio</th><th className="eo-num">Hasta el broker</th>
              </tr>
            </thead>
            <tbody>
              {r.alertas.map((a) => (
                <tr key={a.alert_id}>
                  <th scope="row"><NombreCodigo codigo={a.condicion} /></th>
                  <td className="eo-num">{a.confirmada_ms != null ? `${segundos(a.confirmada_ms)} s` : '—'}</td>
                  <td>{a.episodio
                    ? <>desde el segundo {segundos(a.episodio.desde_ms)}</>
                    : a.tipo === 'no_penalizada'
                      ? <Badge tone="neutral">re-alerta, no es falsa alarma</Badge>
                      : <Badge tone="warn">de más</Badge>}</td>
                  <td className="eo-num">{a.demora_ms != null ? `${segundos(a.demora_ms)} s` : '—'}</td>
                  <td className="eo-num">{a.broker?.demora_ms != null ? `${Math.round(a.broker.demora_ms)} ms` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </TableScroll>
      )}
      {r.sin_alerta.map((e, i) => (
        <p key={i} className="eo-note">
          La referencia tiene <NombreCodigo codigo={e.condicion} /> desde el segundo {segundos(e.desde_ms)} y la corrida
          no alertó.
        </p>
      ))}
      {r.alertas.filter((a) => a.broker).map((a) => (
        <Disclosure key={a.alert_id} summary={<>El mensaje que llegó al broker: <NombreCodigo codigo={a.condicion} /></>}>
          <p className="eo-note--meta">Tópico <code className="eo-mono">{a.broker!.topic}</code></p>
          <pre className="eo-pre">{JSON.stringify(a.broker!.payload, null, 2)}</pre>
        </Disclosure>
      ))}
    </Card>
  )
}

/** «Correr un clip» (plan de la consola, §7.2): elegir uno de tres clips del rodaje, correrlo por la cadena
 *  completa con la configuración del informe y ver sus alertas al lado de la referencia. No es evidencia. */
export default function CorrerClipPage() {
  const q = useClipsDemostracion()
  const corriendo = q.data?.actual?.fase === 'corriendo'
  const prep = usePreparacionClip(!corriendo)
  const correr = useCorrerClip()
  const lista = useDejarLista()
  const [elegido, setElegido] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (q.isPending) {
    return (<><PageHeader title="Correr un clip" /><LoadingState lines={3}>Leyendo los clips…</LoadingState></>)
  }
  if (q.error) {
    return (
      <>
        <PageHeader title="Correr un clip" />
        <ErrorBanner onRetry={() => void q.refetch()} retrying={q.isFetching}>No se pudieron leer los clips.</ErrorBanner>
      </>
    )
  }
  const { clips, actual, cadencia } = q.data
  const clip = elegido ?? actual?.clip.id ?? null
  const listo = prep.data?.listo ?? false
  const faltan = (prep.data?.items ?? []).filter((i) => !i.ok)

  const lanzar = async () => {
    if (!clip) return
    setError(null)
    try {
      await correr.mutateAsync(clip)
    } catch (e) {
      setError(e instanceof ApiError ? ((e.payload as { detail?: string } | null)?.detail ?? String(e.status)) : String(e))
    }
  }

  return (
    <div className="eo-clip">
      <PageHeader title="Correr un clip" meta={<Tag>demostración: no es evidencia</Tag>} />

      <Card title="1. El clip">
        <div className="eo-clip__opciones" role="radiogroup" aria-label="El clip">
          {clips.map((c) => (
            <button key={c.id} type="button" role="radio" aria-checked={clip === c.id} disabled={!c.disponible || corriendo}
              className={clip === c.id ? 'eo-clip__opcion eo-clip__opcion--elegida' : 'eo-clip__opcion'}
              onClick={() => setElegido(c.id)}>
              <span className="eo-clip__titulo">{c.titulo}</span>
              <span className="eo-note--meta">
                {c.disponible ? <>{c.duracion_ms != null ? `${segundos(c.duracion_ms, 0)} s · ` : ''}<span className="eo-mono">{c.id}</span></>
                  : 'no está en este equipo'}
              </span>
              <span className="eo-clip__ref"><Referencia clip={c} /></span>
            </button>
          ))}
        </div>
      </Card>

      <Card title="2. Correr" meta={`Perfil operativo y configuración de la demo${cadencia?.cuadros_por_segundo
        ? `, a ${cadencia.cuadros_por_segundo.toLocaleString('es-AR')} cuadros por segundo` : ''}`}>
        {!corriendo && faltan.length > 0 && (
          <div className="eo-clip__faltan">
            <ul>
              {faltan.map((i) => <li key={i.id}><b>{i.nombre}:</b> {i.detalle || 'no responde'}</li>)}
            </ul>
            {faltan.some((i) => i.id !== 'libre' && i.id !== 'orquestacion') && (
              <Button onClick={() => void lista.mutateAsync(false).catch((e: unknown) => setError(
                e instanceof ApiError ? ((e.payload as { detail?: string } | null)?.detail ?? String(e.status)) : String(e)))}
                disabled={lista.isPending}>
                {lista.isPending ? 'Dejándola lista…' : 'Dejar la plataforma lista'}
              </Button>
            )}
          </div>
        )}
        {error && <ErrorBanner>{error}</ErrorBanner>}
        <div className="eo-clip__accion">
          <Button variant="primary" onClick={() => void lanzar()} disabled={!clip || corriendo || !listo || correr.isPending}>
            {corriendo ? 'Corriendo…' : 'Correr'}
          </Button>
        </div>
        {actual && <Avance c={actual} />}
        {actual?.fase === 'fallida' && <ErrorBanner>La corrida no terminó bien: {actual.error}</ErrorBanner>}
      </Card>

      {actual && <Resultado c={actual} />}
    </div>
  )
}
