import { useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { getDemoRespaldo } from '../api'
import { useDemoCifras, useDemoSession, useDemoState } from '../api/queries/demo'
import EvidenceLayer from '../components/demo/EvidenceLayer'
import ResultView from '../components/demo/ResultView'
import { useTeclas } from '../components/demo/teclas'
import './DemoPage.css'

/** `/demo/resultado/:session_id`: el Resultado de una sesión (o el del ensayo general,
 *  con `?respaldo=1`). Teclas: E/Esc · L (volver a Listo con el motor fresco) · R. */
export default function DemoResultPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const detalleQ = useDemoSession(sessionId)
  const cifras = useDemoCifras().data ?? []
  const estado = useDemoState().data
  const [capa, setCapa] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const detalle = detalleQ.data
  const respaldo = params.get('respaldo') === '1' || Boolean(detalle?.respaldo)

  useTeclas((tecla) => {
    if (tecla === 'e') setCapa((c) => !c)
    else if (tecla === 'Escape') setCapa(false)
    else if (tecla === 'l') {
      const motor = estado?.motor?.estado
      if (motor === 'fresco') navigate('/demo')
      else if (estado?.stack === 'nativo') {
        setAviso('Despliegue nativo: reiniciá el media-plane a mano y volvé con L.')
        navigate('/demo')
      } else {
        setAviso('El motor todavía se está reiniciando: L funciona cuando quede fresco.')
      }
    } else if (tecla === 'r') {
      getDemoRespaldo()
        .then(({ session_id }) => navigate(`/demo/resultado/${session_id}?respaldo=1`))
        .catch(() => setAviso('No hay ninguna sesión marcada como respaldo.'))
    }
  })

  return (
    <main className="eo-demo" aria-label="Resultado de la demo">
      {detalleQ.isLoading && <p>Cargando el resultado…</p>}
      {detalleQ.isError && <p className="eo-demo-aviso" role="alert">Sesión desconocida: {sessionId}</p>}
      {detalle && <ResultView detalle={detalle} cifras={cifras} rotuloRespaldo={respaldo} />}
      {aviso && <p className="eo-demo-aviso" role="status">{aviso}</p>}
      <footer className="eo-demo__teclas" aria-label="Teclas">
        <kbd>E</kbd> evidencia · <kbd>L</kbd> volver a Listo · <kbd>R</kbd> respaldo
        {estado?.motor?.estado === 'reiniciando' ? ' · reiniciando el motor…' : ''}
      </footer>
      {capa && <EvidenceLayer sesion={detalle} onClose={() => setCapa(false)} />}
    </main>
  )
}
