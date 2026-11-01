import { useState } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { getDemoRespaldo } from '../api'
import { useDemoCifras, useDemoSession, useDemoState } from '../api/queries/demo'
import EvidenceLayer from '../components/demo/EvidenceLayer'
import { rutaDemo, useProyeccion } from '../components/demo/proyeccion'
import ResultView from '../components/demo/ResultView'
import { Button, PageHeader } from '../components/ui'
import { useTeclas } from '../components/demo/teclas'
import './DemoPage.css'

/** `/demo/resultado/:session_id`: el Resultado de una sesión (o el del ensayo general,
 *  con `?respaldo=1`). Dentro de la consola por defecto, con botones; en proyección
 *  (`?proyectar=1`), solo teclado. Teclas: E/Esc · L (volver a Listo con el motor
 *  fresco) · R · P. Al moverse se conservan la variante y el modo. */
export default function DemoResultPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [params] = useSearchParams()
  const { search } = useLocation()
  const navigate = useNavigate()
  const { proyectando, alternar } = useProyeccion()
  const detalleQ = useDemoSession(sessionId)
  const cifras = useDemoCifras().data ?? []
  const estado = useDemoState().data
  const [capa, setCapa] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const detalle = detalleQ.data
  const respaldo = params.get('respaldo') === '1' || Boolean(detalle?.respaldo)
  const motorFresco = estado?.motor?.estado === 'fresco'

  const volverAListo = () => {
    if (motorFresco) navigate(rutaDemo('/demo', search))
    else if (estado?.stack === 'nativo') {
      setAviso('Despliegue nativo: reiniciá el media-plane a mano y volvé con L.')
      navigate(rutaDemo('/demo', search))
    } else {
      setAviso('El motor todavía se está reiniciando: L funciona cuando quede fresco.')
    }
  }

  const irAlRespaldo = () => {
    getDemoRespaldo()
      .then(({ session_id }) => navigate(rutaDemo(`/demo/resultado/${session_id}`, search, { respaldo: '1' })))
      .catch(() => setAviso('No hay ninguna sesión marcada como respaldo.'))
  }

  useTeclas((tecla) => {
    if (tecla === 'e') setCapa((c) => !c)
    else if (tecla === 'Escape') setCapa(false)
    else if (tecla === 'l') volverAListo()
    else if (tecla === 'r') irAlRespaldo()
    else if (tecla === 'p') alternar()
  })

  const teclas = (
    <>
      <kbd>E</kbd> evidencia · <kbd>L</kbd> volver a Listo · <kbd>R</kbd> respaldo ·{' '}
      <kbd>P</kbd> {proyectando ? 'volver a la consola' : 'proyectar'}
      {estado?.motor?.estado === 'reiniciando' ? ' · reiniciando el motor…' : ''}
    </>
  )
  const cuerpo = (
    <>
      {detalleQ.isLoading && <p>Cargando el resultado…</p>}
      {detalleQ.isError && <p className="eo-demo-aviso" role="alert">Sesión desconocida: {sessionId}</p>}
      {aviso && <p className="eo-demo-aviso" role="status">{aviso}</p>}
    </>
  )
  const capaEvidencia = capa && <EvidenceLayer sesion={detalle} onClose={() => setCapa(false)} />

  if (proyectando) {
    return (
      <main className="eo-demo eo-demo--proyeccion" aria-label="Resultado de la demo">
        {detalle && <ResultView detalle={detalle} cifras={cifras} rotuloRespaldo={respaldo} />}
        {cuerpo}
        <footer className="eo-demo__teclas" aria-label="Teclas">{teclas}</footer>
        {capaEvidencia}
      </main>
    )
  }

  // Dentro de la consola: cabecera de la consola con las acciones, y el mismo Resultado.
  // Las acciones están siempre, también mientras carga o si la sesión no existe.
  const acciones = (
    <div className="eo-demo-consola__acciones" role="toolbar" aria-label="Acciones del resultado">
      <Button
        variant="primary"
        onClick={volverAListo}
        disabled={!motorFresco && estado?.stack !== 'nativo'}
        title={motorFresco ? undefined : 'El motor se está reiniciando: se habilita cuando queda fresco'}
      >
        Volver a Listo <kbd>L</kbd>
      </Button>
      <Button aria-pressed={capa} onClick={() => setCapa((c) => !c)}>Evidencia <kbd>E</kbd></Button>
      <Button onClick={alternar}>Proyectar <kbd>P</kbd></Button>
    </div>
  )
  return (
    <div className="eo-demo-consola" aria-label="Resultado de la demo">
      {detalle ? (
        <ResultView detalle={detalle} cifras={cifras} rotuloRespaldo={respaldo} acciones={acciones} />
      ) : (
        <PageHeader title="Resultado de la demo" meta={sessionId} actions={acciones} />
      )}
      {cuerpo}
      <p className="eo-demo-consola__teclas" aria-label="Teclas">{teclas}</p>
      {capaEvidencia}
    </div>
  )
}
