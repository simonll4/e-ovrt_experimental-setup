import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError, finishDemo, getDemoRespaldo, qk, startDemo } from '../api'
import { useDemoPreflight, useDemoState } from '../api/queries/demo'
import BrokerStrip from '../components/demo/BrokerStrip'
import CameraIndicator from '../components/demo/CameraIndicator'
import ConditionCard from '../components/demo/ConditionCard'
import EvidenceLayer from '../components/demo/EvidenceLayer'
import { cronometro, hora } from '../components/demo/formato'
import { VENTANA_FF_MS, useTeclas } from '../components/demo/teclas'
import type { DemoFase, DemoPreflight, DemoState } from '../types'
import './DemoPage.css'

const PASOS: Record<string, string> = {
  reglas: 'reglas', distribucion: 'distribución', deteccion: 'detección', camara: 'cámara',
}
const CHEQUEOS: Record<string, string> = {
  sesion: 'sesión', deteccion: 'detección', motor: 'motor fresco', reglas: 'reglas',
  distribucion: 'distribución', broker: 'broker', congelado: 'configuración congelada',
  host: 'cámara y host',
}
const SIN_LISTO_S = 30
const SIN_SENAL_RESPALDO_S = 15

function detalleDe(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload as { detail?: unknown } | null
    if (payload && typeof payload.detail === 'string') return payload.detail
    return `error ${error.status}`
  }
  return String(error)
}

function Listo({ preflight, cargando }: { preflight: DemoPreflight | undefined; cargando: boolean }) {
  const host = preflight?.items.find((i) => i.id === 'host')
  const problemas = preflight?.items.filter((i) => i.estado !== 'ok') ?? []
  return (
    <section className="eo-demo-listo" aria-label="Listo">
      <ul className="eo-demo-chequeos" aria-label="Chequeo previo">
        {(preflight?.items ?? []).map((i) => (
          <li key={i.id} className={`eo-demo-chequeo eo-demo-chequeo--${i.estado}`}>
            {CHEQUEOS[i.id] ?? i.nombre}
          </li>
        ))}
      </ul>
      {cargando && !preflight && <p>Comprobando la plataforma…</p>}
      {preflight && (
        <p className="eo-demo-listo__meta">
          Chequeo de la consola: {hora(preflight.comprobado_en)} · host: {host?.detalle ?? '—'} · stack{' '}
          {preflight.stack}
        </p>
      )}
      {preflight?.listo ? (
        <p className="eo-demo-listo__accion">
          Iniciar <kbd>I</kbd>
        </p>
      ) : (
        preflight && (
          <p className="eo-demo-listo__bloqueo">La tecla <kbd>I</kbd> funciona con todo en verde.</p>
        )
      )}
      {problemas.length > 0 && (
        <ul className="eo-demo-listo__problemas">
          {problemas.map((i) => (
            <li key={i.id}>
              <b>{CHEQUEOS[i.id] ?? i.nombre}:</b> {i.detalle}
              {i.accion ? <> — {i.accion}</> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Corriendo({ estado }: { estado: DemoState }) {
  const preparando = estado.fase === 'preparing'
  const espera = estado.iniciada_en ? (Date.now() - new Date(estado.iniciada_en).getTime()) / 1000 : 0
  return (
    <section className="eo-demo-corriendo" aria-label="Corriendo">
      {preparando ? (
        <>
          <p className="eo-demo-preparando">
            Preparando:{' '}
            {(estado.pasos ?? []).map((p, i) => (
              <span key={p.id} className={`eo-demo-paso eo-demo-paso--${p.estado}`}>
                {i > 0 ? ' → ' : ''}{PASOS[p.id] ?? p.id}
              </span>
            ))}
          </p>
          {espera > SIN_LISTO_S && (
            <p className="eo-demo-aviso" role="alert">
              No llegó «Listo» en {SIN_LISTO_S} s. Respaldo: <kbd>R</kbd>
            </p>
          )}
        </>
      ) : (
        <p className="eo-demo-listo-ya">Listo: entrá a cuadro</p>
      )}
      <p className="eo-demo-crono" aria-label="Cronómetro">{cronometro(estado.transcurrido_s)}</p>
      <div className="eo-demo-cards">
        {(estado.condiciones ?? []).map((c) => <ConditionCard key={c.condicion} condicion={c} />)}
      </div>
      <BrokerStrip broker={estado.broker} />
      <CameraIndicator camara={estado.camara} />
      {estado.camara?.sin_senal && (estado.camara.ultimo_cuadro_hace_s ?? 0) > SIN_SENAL_RESPALDO_S && (
        <p className="eo-demo-aviso" role="alert">Respaldo: <kbd>R</kbd></p>
      )}
    </section>
  )
}

/** `/demo`: la pantalla de la demo en vivo. Oscura, letra grande, sin el armazón de
 *  la consola y solo por teclado (I · F F · E/Esc · R), porque el proyector duplica
 *  lo que ve el operador (spec 2026-10-23 §5). */
export default function DemoPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  const variante = params.get('variante') === 'ensayo' ? 'ensayo' : 'oakd'
  const estadoQ = useDemoState()
  const estado = estadoQ.data
  const fase: DemoFase = estado?.fase ?? 'idle'
  const corriendo = fase === 'preparing' || fase === 'live'
  const cerrando = fase === 'finishing' || fase === 'rendering'
  const preflightQ = useDemoPreflight(!corriendo && !cerrando)
  const preflight = preflightQ.data
  const [capa, setCapa] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const primeraF = useRef<number | null>(null)
  const faseVista = useRef<DemoFase | null>(null)

  // Al terminar una corrida que esta pantalla vio correr, pasa sola al Resultado.
  useEffect(() => {
    const anterior = faseVista.current
    faseVista.current = fase
    if (
      anterior && anterior !== fase && (fase === 'done' || fase === 'failed')
      && ['preparing', 'live', 'finishing', 'rendering'].includes(anterior) && estado?.session_id
    ) {
      navigate(`/demo/resultado/${estado.session_id}`)
    }
  }, [fase, estado?.session_id, navigate])

  const refrescar = () => queryClient.invalidateQueries({ queryKey: qk.demo.all })

  const iniciar = async () => {
    if (corriendo || cerrando || enviando) return
    if (!preflight?.listo) {
      setAviso('Todavía no: la tecla I funciona con todo en verde.')
      return
    }
    setEnviando(true)
    setAviso(null)
    try {
      await startDemo(variante)
    } catch (error) {
      setAviso(`No se pudo iniciar: ${detalleDe(error)}`)
    } finally {
      setEnviando(false)
      void refrescar()
    }
  }

  const finalizar = async () => {
    if (!corriendo) return
    const ahora = Date.now()
    if (primeraF.current == null || ahora - primeraF.current > VENTANA_FF_MS) {
      primeraF.current = ahora
      setAviso('Apretá F otra vez para finalizar')
      return
    }
    primeraF.current = null
    setAviso(null)
    try {
      await finishDemo()
    } catch (error) {
      setAviso(`No se pudo finalizar: ${detalleDe(error)}`)
    } finally {
      void refrescar()
    }
  }

  const irAlRespaldo = async () => {
    try {
      const { session_id } = await getDemoRespaldo()
      navigate(`/demo/resultado/${session_id}?respaldo=1`)
    } catch {
      setAviso('No hay ninguna sesión marcada como respaldo.')
    }
  }

  useTeclas((tecla) => {
    if (tecla === 'e') setCapa((c) => !c)
    else if (tecla === 'Escape') setCapa(false)
    else if (tecla === 'r') void irAlRespaldo()
    else if (tecla === 'i') void iniciar()
    else if (tecla === 'f') void finalizar()
  })

  return (
    <main className="eo-demo" aria-label="Demo en vivo">
      <header className="eo-demo__cab">
        <h1>Demo en vivo · E-OVRT</h1>
        {variante === 'ensayo' && (
          <p className="eo-demo__variante">Variante de ensayo: la entrada es una grabación; todo lo demás corre en vivo.</p>
        )}
      </header>
      {estadoQ.isError && <p className="eo-demo-aviso" role="alert">La consola no responde.</p>}
      {(fase === 'idle' || fase === 'done' || fase === 'failed') && (
        <Listo preflight={preflight} cargando={preflightQ.isLoading} />
      )}
      {corriendo && estado && <Corriendo estado={estado} />}
      {cerrando && (
        <p className="eo-demo-cerrando" role="status">Cerrando la corrida · armando la evidencia</p>
      )}
      {aviso && <p className="eo-demo-aviso" role="status">{aviso}</p>}
      <footer className="eo-demo__teclas" aria-label="Teclas">
        <kbd>I</kbd> iniciar · <kbd>F</kbd> <kbd>F</kbd> finalizar · <kbd>E</kbd> evidencia · <kbd>R</kbd> respaldo
      </footer>
      {capa && (
        <EvidenceLayer estado={estado} congelado={preflight?.congelado} onClose={() => setCapa(false)} />
      )}
    </main>
  )
}
