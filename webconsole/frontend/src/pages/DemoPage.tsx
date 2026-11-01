import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError, detenerVistaDemo, finishDemo, getDemoRespaldo, qk, startDemo } from '../api'
import { useDemoCamaras, useDemoPreflight, useDemoState } from '../api/queries/demo'
import BrokerStrip from '../components/demo/BrokerStrip'
import CamaraPanel from '../components/demo/CamaraPanel'
import CameraIndicator from '../components/demo/CameraIndicator'
import { guardarCamaraElegida, leerCamaraElegida, resolverCamara } from '../components/demo/camaraElegida'
import ConditionCard from '../components/demo/ConditionCard'
import EvidenceLayer from '../components/demo/EvidenceLayer'
import { cronometro, hora } from '../components/demo/formato'
import { Banner, Button, Card, PageHeader } from '../components/ui'
import { IconPlay, IconStop } from '../components/ui/icons'
import { rutaDemo, useProyeccion } from '../components/demo/proyeccion'
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

function Corriendo({ estado, consola }: { estado: DemoState; consola?: boolean }) {
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
      {consola && (
        <p className="eo-demo-consola__nota">
          La consola no recibe video durante la corrida: solo el estado, para no restarle rendimiento al motor. Los
          cuadros se guardan y el video con las detecciones se arma al terminar (Resultado).
        </p>
      )}
      {estado.camara?.sin_senal && (estado.camara.ultimo_cuadro_hace_s ?? 0) > SIN_SENAL_RESPALDO_S && (
        <p className="eo-demo-aviso" role="alert">Respaldo: <kbd>R</kbd></p>
      )}
    </section>
  )
}

/** `/demo`: la pantalla de la demo en vivo. Dentro de la consola por defecto, con
 *  botones; con `P` pasa a la proyección (oscura, letra grande, sin el armazón y solo
 *  por teclado: I · F F · E/Esc · R · P), porque el proyector duplica lo que ve el
 *  operador (spec 2026-10-23 §5; modos en components/demo/proyeccion.ts). */
export default function DemoPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [params] = useSearchParams()
  const { search } = useLocation()
  const { proyectando, alternar } = useProyeccion()
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
  // La cámara de la demo: se elige en la consola y se recuerda en este navegador; la proyección usa la
  // misma sin pedir la lista. `vista` = la vista previa de antes de iniciar (nunca durante la corrida).
  const [guardada, setGuardada] = useState<string | null>(leerCamaraElegida)
  const [vista, setVista] = useState(false)
  const vistaRef = useRef(false)
  vistaRef.current = vista
  const camarasQ = useDemoCamaras(!proyectando && !corriendo && !cerrando)
  const camaraElegida = camarasQ.data ? resolverCamara(camarasQ.data, guardada) : guardada
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
      navigate(rutaDemo(`/demo/resultado/${estado.session_id}`, search))
    }
  }, [fase, estado?.session_id, navigate, search])

  const refrescar = () => queryClient.invalidateQueries({ queryKey: qk.demo.all })

  // Al salir de la pantalla no puede quedar la cámara abierta en el motor.
  useEffect(() => () => {
    if (vistaRef.current) void detenerVistaDemo().catch(() => undefined)
  }, [])

  const elegirCamara = (id: string) => {
    setGuardada(id)
    guardarCamaraElegida(id)
  }

  const iniciar = async () => {
    if (corriendo || cerrando || enviando) return
    if (!preflight?.listo) {
      setAviso('Todavía no: la tecla I funciona con todo en verde.')
      return
    }
    setEnviando(true)
    setAviso(null)
    // El motor corta la vista por su cuenta antes de lanzar; acá se cierra el visor.
    setVista(false)
    try {
      await startDemo(variante, camaraElegida)
    } catch (error) {
      setAviso(`No se pudo iniciar: ${detalleDe(error)}`)
    } finally {
      setEnviando(false)
      void refrescar()
    }
  }

  const finalizar = async (origen: 'tecla' | 'boton' = 'tecla') => {
    if (!corriendo) return
    const ahora = Date.now()
    if (primeraF.current == null || ahora - primeraF.current > VENTANA_FF_MS) {
      primeraF.current = ahora
      setAviso(origen === 'tecla' ? 'Apretá F otra vez para finalizar' : 'Tocá Finalizar otra vez para cortar')
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
      navigate(rutaDemo(`/demo/resultado/${session_id}`, search, { respaldo: '1' }))
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
    else if (tecla === 'p') alternar()
  })

  const avisoVariante = variante === 'ensayo'
    ? 'Variante de ensayo: la entrada es una grabación; todo lo demás corre en vivo.'
    : null
  const cuerpo = (
    <>
      {estadoQ.isError && <p className="eo-demo-aviso" role="alert">La consola no responde.</p>}
      {(fase === 'idle' || fase === 'done' || fase === 'failed') && (
        <Listo preflight={preflight} cargando={preflightQ.isLoading} />
      )}
      {corriendo && estado && <Corriendo estado={estado} consola={!proyectando} />}
      {cerrando && (
        <p className="eo-demo-cerrando" role="status">Cerrando la corrida · armando la evidencia</p>
      )}
      {aviso && <p className="eo-demo-aviso" role="status">{aviso}</p>}
    </>
  )
  const teclas = (
    <>
      <kbd>I</kbd> iniciar · <kbd>F</kbd> <kbd>F</kbd> finalizar · <kbd>E</kbd> evidencia · <kbd>R</kbd> respaldo ·{' '}
      <kbd>P</kbd> {proyectando ? 'volver a la consola' : 'proyectar'}
    </>
  )
  const capaEvidencia = capa && (
    <EvidenceLayer estado={estado} congelado={preflight?.congelado} onClose={() => setCapa(false)} />
  )

  if (proyectando) {
    return (
      <main className="eo-demo eo-demo--proyeccion" aria-label="Demo en vivo">
        <header className="eo-demo__cab">
          <h1>Demo en vivo · E-OVRT</h1>
          {avisoVariante && <p className="eo-demo__variante">{avisoVariante}</p>}
        </header>
        {cuerpo}
        <footer className="eo-demo__teclas" aria-label="Teclas">{teclas}</footer>
        {capaEvidencia}
      </main>
    )
  }

  // Dentro de la consola: una pantalla más, con su cabecera, su aviso y sus tarjetas.
  return (
    <div className="eo-demo-consola" aria-label="Demo en vivo">
      <PageHeader
        title="Demo en vivo"
        meta={corriendo ? 'En vivo' : cerrando ? 'Cerrando' : fase === 'done' || fase === 'failed' ? 'Última corrida cerrada' : 'Lista para iniciar'}
        bajada="La cadena completa —cámara, detección, reglas temporales, distribución y broker— corriendo en vivo con la configuración congelada del informe. Proyectar la deja a pantalla completa, para el tribunal."
        actions={(
          <div className="eo-demo-consola__acciones" role="toolbar" aria-label="Acciones de la demo">
            {!corriendo && !cerrando && (
              <Button variant="primary" disabled={enviando} onClick={() => void iniciar()}>
                <IconPlay /> Iniciar <kbd>I</kbd>
              </Button>
            )}
            {corriendo && (
              <Button variant="danger" onClick={() => void finalizar('boton')}>
                <IconStop /> Finalizar <kbd>F</kbd> <kbd>F</kbd>
              </Button>
            )}
            <Button aria-pressed={capa} onClick={() => setCapa((c) => !c)}>Evidencia <kbd>E</kbd></Button>
            <Button onClick={alternar}>Proyectar <kbd>P</kbd></Button>
          </div>
        )}
      />
      {avisoVariante && <Banner tone="warn">{avisoVariante}</Banner>}
      {!corriendo && !cerrando && (
        <CamaraPanel
          camaras={camarasQ.data}
          cargando={camarasQ.isLoading}
          error={camarasQ.isError}
          elegida={camaraElegida}
          onElegir={elegirCamara}
          vista={vista}
          onVista={setVista}
        />
      )}
      <Card title={corriendo || cerrando ? 'Corrida en curso' : 'Chequeo previo'}>{cuerpo}</Card>
      <p className="eo-demo-consola__teclas" aria-label="Teclas">{teclas}</p>
      {capaEvidencia}
    </div>
  )
}
