import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  ApiError, comprobarDemoCamara, detenerVistaDemo, iniciarVistaDemo, qk, reiniciarMotorDemo,
} from '../../api'
import { usePreviewStream } from '../../preview'
import type { DemoCamara, DemoCamaraChequeo } from '../../types'
import LiveViewer from '../LiveViewer'
import { Badge, Button, Card } from '../ui'

const ESTADO: Record<DemoCamaraChequeo['estado'], { texto: string; tono: 'ok' | 'warn' | 'error' }> = {
  ok: { texto: 'Se ve', tono: 'ok' },
  falla: { texto: 'No se ve', tono: 'error' },
  en_uso: { texto: 'En uso', tono: 'warn' },
}

/** El estado de cada cámara en la lista (sin abrirla): ver `DemoCamara.estado`. */
const ESTADO_LISTA: Record<DemoCamara['estado'], { texto: string; tono: 'ok' | 'warn' | 'error' | 'neutral' }> = {
  activa: { texto: 'Activa', tono: 'ok' },
  inactiva: { texto: 'Sin respuesta', tono: 'error' },
  problema: { texto: 'Con problemas', tono: 'warn' },
  sin_comprobar: { texto: 'Sin comprobar', tono: 'neutral' },
}

function mensajeDe(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload as { detail?: unknown; reason?: string } | null
    if (payload && typeof payload.detail === 'string') return payload.detail
    if (payload?.reason === 'run_active') return 'Hay una corrida activa en el motor: no se puede previsualizar ahora.'
    return `error ${error.status}`
  }
  return String(error)
}

interface Props {
  camaras: DemoCamara[] | undefined
  cargando: boolean
  error: boolean
  elegida: string | null
  onElegir: (id: string) => void
  /** La vista previa vive en la pantalla (no acá): al iniciar la sesión se corta desde afuera. */
  vista: boolean
  onVista: (activa: boolean) => void
}

/** La cámara de la demo (✎ 2026-11-01): elegirla, ver que se ve, ver el encuadre ANTES de iniciar,
 *  y arreglarlo desde la misma pantalla si no se ve.
 *
 *  Durante la corrida la consola NO recibe cuadros —solo el estado, que es lo que hace falta y lo que
 *  deja al motor el rendimiento—; los cuadros se guardan en el motor y el video con las detecciones se
 *  arma al terminar (Resultado). Por eso la vista previa es solo de antes de iniciar. */
export default function CamaraPanel({ camaras, cargando, error, elegida, onElegir, vista, onVista }: Props) {
  const queryClient = useQueryClient()
  const [comprobando, setComprobando] = useState(false)
  const [chequeo, setChequeo] = useState<DemoCamaraChequeo | null>(null)
  const [conectandoVista, setConectandoVista] = useState(false)
  const [errorVista, setErrorVista] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)
  const live = usePreviewStream(vista)

  const lista = camaras ?? []
  const actual = lista.find((c) => c.id === elegida) ?? null
  const refrescar = () => queryClient.invalidateQueries({ queryKey: qk.demo.all })

  const cortarVista = async () => {
    onVista(false)
    await detenerVistaDemo().catch(() => undefined)
  }

  const elegir = (id: string) => {
    // Cambiar de cámara descarta lo que se sabía de la anterior, y corta su vista.
    setChequeo(null)
    setErrorVista(null)
    setAviso(null)
    if (vista) void cortarVista()
    onElegir(id)
  }

  const comprobar = async () => {
    if (!elegida || comprobando) return
    setComprobando(true)
    setAviso(null)
    try {
      // La OAK-D admite una sola conexión: si la vista la tiene abierta, se corta antes de probar.
      if (vista) await cortarVista()
      setChequeo(await comprobarDemoCamara(elegida))
      // La comprobación explícita es lo que alimenta el estado de la OAK-D en la lista.
      void queryClient.invalidateQueries({ queryKey: qk.demo.camaras })
    } catch (e) {
      setChequeo(null)
      setAviso(`No se pudo comprobar la cámara: ${mensajeDe(e)}`)
    } finally {
      setComprobando(false)
    }
  }

  const alternarVista = async () => {
    setErrorVista(null)
    setAviso(null)
    if (vista) {
      await cortarVista()
      if (actual?.plugin === 'oak_d') {
        // La OAK-D abierta en el motor cuenta como un uso (F-101.5): se lo reinicia para que quede
        // «fresco» y la sesión pueda iniciar. Es lo mismo que hace la consola al terminar una sesión.
        try {
          await reiniciarMotorDemo()
          setAviso('Vista cortada. Reiniciando el motor (~30 s): cuando quede fresco se puede iniciar.')
        } catch (e) {
          setAviso(`Vista cortada, pero no se pudo reiniciar el motor: ${mensajeDe(e)}`)
        }
        void refrescar()
      }
      return
    }
    if (!elegida) return
    setConectandoVista(true)
    try {
      await iniciarVistaDemo(elegida)
      onVista(true)
      void refrescar()
    } catch (e) {
      setErrorVista(mensajeDe(e))
    } finally {
      setConectandoVista(false)
    }
  }

  const reiniciarMotor = async () => {
    setAviso(null)
    try {
      await reiniciarMotorDemo()
      setAviso('Reiniciando el motor (~30 s). Cuando termine, volvé a comprobar la cámara.')
      void refrescar()
    } catch (e) {
      setAviso(`No se pudo reiniciar el motor: ${mensajeDe(e)}`)
    }
  }

  const estado = chequeo ? ESTADO[chequeo.estado] : null
  return (
    <Card title="Cámara">
      {cargando && <p>Cargando las cámaras…</p>}
      {error && (
        <p className="eo-demo-aviso" role="alert">
          No se pudieron leer las cámaras. Se sigue usando la OAK-D de la plantilla.
        </p>
      )}
      {!cargando && !error && lista.length === 0 && (
        <p>
          No hay cámaras OAK-D ni RTSP guardadas. Agregá una en <Link to="/cameras">Cámaras</Link>.
        </p>
      )}
      {lista.length > 0 && (
        <>
          <fieldset className="eo-demo-camaras" role="radiogroup" aria-label="Cámara de la demo">
            <legend>Cámara de la demo</legend>
            {lista.map((c) => {
              const e = ESTADO_LISTA[c.estado] ?? ESTADO_LISTA.sin_comprobar
              return (
                <label key={c.id} className={c.id === elegida ? 'eo-demo-camaras__fila eo-demo-camaras__fila--elegida' : 'eo-demo-camaras__fila'}>
                  <input
                    type="radio" name="demo-camara" value={c.id}
                    checked={c.id === elegida} onChange={() => elegir(c.id)}
                  />
                  <span className="eo-demo-camaras__nombre">{c.nombre}</span>
                  <code className="eo-demo-camaras__destino">{c.destino}</code>
                  <Badge tone={e.tono}>{e.texto}</Badge>
                  <span className="eo-demo-camaras__detalle">{c.detalle}</span>
                </label>
              )
            })}
          </fieldset>
          <div className="eo-demo-camara-fila">
            <Button onClick={() => void comprobar()} disabled={comprobando || !elegida}>
              {comprobando ? 'Comprobando…' : 'Comprobar'}
            </Button>
            <Button
              aria-pressed={vista}
              onClick={() => void alternarVista()}
              disabled={conectandoVista || comprobando || !elegida}
            >
              {conectandoVista ? 'Conectando…' : vista ? 'Cortar la vista' : 'Ver la cámara'}
            </Button>
          </div>

          {chequeo && (
            <div className="eo-demo-camara-chequeo" role="status" aria-label="Resultado de la comprobación">
              <p className="eo-demo-camara-chequeo__titulo">
                {estado && <Badge tone={estado.tono}>{estado.texto}</Badge>}{' '}
                {chequeo.causa ?? `${chequeo.nombre} se ve.`}
              </p>
              <ul className="eo-demo-camara-pasos">
                {chequeo.pasos.map((p) => (
                  <li key={p.id} className={p.ok ? 'eo-demo-camara-paso--ok' : 'eo-demo-camara-paso--mal'}>
                    <span aria-hidden="true">{p.ok ? '✓' : '✗'}</span> <b>{p.nombre}:</b> {p.detalle}
                  </li>
                ))}
              </ul>
              {chequeo.ayuda.length > 0 && (
                <>
                  <p className="eo-demo-camara-chequeo__sub">Cómo arreglarlo</p>
                  <ol className="eo-demo-camara-ayuda">
                    {chequeo.ayuda.map((linea) => <li key={linea}>{linea}</li>)}
                  </ol>
                </>
              )}
              {chequeo.acciones.length > 0 && (
                <div className="eo-demo-camara-acciones">
                  {chequeo.acciones.map((a) => (
                    <Button
                      key={a.id}
                      variant={a.id === 'reintentar' ? 'secondary' : 'primary'}
                      disabled={comprobando}
                      onClick={() => void (a.id === 'reiniciar_motor' ? reiniciarMotor() : comprobar())}
                    >
                      {a.etiqueta}
                    </Button>
                  ))}
                </div>
              )}
            </div>
          )}

          {errorVista && <p className="eo-demo-aviso" role="alert">No se pudo ver la cámara: {errorVista}</p>}
          {vista && (
            <div className="eo-demo-camara-vista">
              {live.finalState?.status === 'error' && (
                <p className="eo-demo-aviso" role="alert">{live.finalState.error}</p>
              )}
              <LiveViewer
                frameUrl={live.frameUrl} header={live.header} connected={live.connected} fps={live.fps} mode="raw"
              />
              {!live.frameUrl && <p className="eo-demo-camara-nota">Conectando con la cámara… la OAK-D tarda unos 10 s.</p>}
              {actual?.plugin === 'oak_d' && (
                <p className="eo-demo-camara-nota">
                  Para iniciar, cortá la vista: la OAK-D abierta obliga a reiniciar el motor (lo hace solo al cortar).
                </p>
              )}
            </div>
          )}
          {aviso && <p className="eo-demo-camara-nota" role="status">{aviso}</p>}
          <p className="eo-demo-camara-nota">
            La vista es solo para encuadrar, antes de iniciar. Durante la corrida la consola no recibe video: solo el
            estado. El video con las detecciones se arma al terminar y queda en el Resultado.
          </p>
        </>
      )}
    </Card>
  )
}
