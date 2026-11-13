import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDemoSesiones } from '../api/queries/demo'
import { Card, ErrorBanner, LoadingState, MonoCell, PageHeader, SearchInput, Table, TableScroll } from '../components/ui'
import type { DemoSesionFila } from '../types'
import './DemoPage.css'

const FASE: Record<string, string> = {
  done: 'cerrada', failed: 'falló', live: 'en vivo', preparing: 'preparando',
  finishing: 'cerrando', rendering: 'armando el resultado', idle: 'sin iniciar',
}

function fecha(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'medium' })
}

/** Lo que distingue una sesión de otra, en una línea: el modo de prompts o el motor
 *  explorado. Sin ninguno de los dos, corrió con la configuración del informe. */
function configuracion(s: DemoSesionFila) {
  if (s.exploracion) return `${s.exploracion.motor} · ${s.exploracion.camara}`
  if (s.modo_prompts) return s.modo_prompts.nombre
  return 'Configuración del informe'
}

/** Las sesiones guardadas de la demo: las tomas de las jornadas en vivo y las de
 *  esta consola. Cada una abre su Resultado (video con las detecciones, alertas,
 *  mensaje del broker y log), sin cámara y con los servicios apagados. */
export default function DemoSesionesPage() {
  const q = useDemoSesiones()
  const [filtro, setFiltro] = useState('')
  const filas = useMemo(() => {
    const t = filtro.trim().toLowerCase()
    const todas = q.data ?? []
    if (!t) return todas
    return todas.filter((s) => [s.session_id, s.escena, s.variante, configuracion(s)]
      .some((x) => (x ?? '').toLowerCase().includes(t)))
  }, [q.data, filtro])
  const total = q.data?.length ?? 0
  const archivadas = (q.data ?? []).filter((s) => s.archivada).length
  return (
    <div className="eo-demo-consola" aria-label="Sesiones guardadas">
      <PageHeader
        title="Sesiones guardadas"
        meta={q.data ? `${total} ${total === 1 ? 'sesión' : 'sesiones'}${archivadas ? ` · ${archivadas} de las jornadas en vivo` : ''}` : undefined}
        bajada="Cada toma de la demo queda guardada con su video, sus alertas, el mensaje que recibió el broker y el log completo. Se abren sin cámara y con los servicios apagados."
      />
      {q.isPending && <LoadingState>Leyendo las sesiones guardadas…</LoadingState>}
      {q.error != null && (
        <ErrorBanner onRetry={() => void q.refetch()} retrying={q.isFetching}>
          No se pudieron leer las sesiones guardadas.
        </ErrorBanner>
      )}
      {q.data && total === 0 && (
        <Card title="Todavía no hay sesiones">
          <p className="eo-note">
            Una sesión se guarda al terminar una corrida de la <Link to="/demo">demo en vivo</Link>. Las de las
            jornadas se leen de las carpetas indicadas en <span className="eo-mono">EOVRT_CONSOLE_DEMO_SESSIONS_EXTRA</span>.
          </p>
        </Card>
      )}
      {total > 0 && (
        <Card title="Sesiones" meta={filtro ? `${filas.length} de ${total}` : undefined} flush>
          <div className="eo-demo-sesiones__filtro">
            <SearchInput value={filtro} onChange={setFiltro} placeholder="Escena, fecha (20261107) o motor" ariaLabel="Filtrar sesiones" />
          </div>
          <TableScroll label="Sesiones guardadas">
            <Table aria-label="Sesiones guardadas">
              <thead>
                <tr><th>Inicio</th><th>Escena</th><th>Cámara</th><th>Configuración</th><th>Estado</th><th>Origen</th><th>Sesión</th></tr>
              </thead>
              <tbody>
                {filas.map((s) => (
                  <tr key={s.session_id}>
                    <td>{fecha(s.iniciada_en)}</td>
                    <td>{s.escena ?? '—'}</td>
                    <td>{s.variante ?? '—'}</td>
                    <td>{configuracion(s)}</td>
                    <td>{FASE[s.fase] ?? s.fase}{s.respaldo ? ' · respaldo' : ''}</td>
                    <td>{s.archivada ? 'jornada en vivo' : 'esta consola'}</td>
                    {s.tiene_resultado === false
                      ? <MonoCell title="No tiene el resultado armado">{s.session_id}</MonoCell>
                      : <td><Link className="eo-mono" to={`/demo/resultado/${encodeURIComponent(s.session_id)}`}>{s.session_id}</Link></td>}
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableScroll>
        </Card>
      )}
    </div>
  )
}
