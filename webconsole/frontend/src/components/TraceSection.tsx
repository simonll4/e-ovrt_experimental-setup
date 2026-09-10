import { useEffect, useState } from 'react'
import FrameInspector from './FrameInspector'
import { Badge, Button, Card, EmptyState } from './ui'
import { controlTone } from '../traceview'
import { useTracePage, type TraceFilter } from '../api/queries/runs'
import { toneVar } from '../palette'
import type { TraceTotals } from '../types'

/** Cuántos cuadros trae cada página. Coincide con lo que se renderiza: una
 *  traza de miles de cuadros no puede volcarse entera, y ahora tampoco se
 *  descarga entera. */
const PAGE_SIZE = 200

/**
 * Panel de traza en maestro-detalle: la lista de cuadros a la izquierda, el
 * cuadro elegido completo a la derecha.
 *
 * Trae su propia página en vez de recibir la traza entera por props. Antes la
 * página la tenía toda en memoria (`useFullTrace` paginaba hasta 40 veces) y
 * recortaba de a 200 en el cliente; con esto se descarga solo lo que se muestra,
 * y el filtro viaja al servidor para que "solo alertas" siga significando las de
 * la corrida y no las de la página cargada.
 */
export default function TraceSection({
  runId,
  totals,
  enabled = true,
  running = false,
  jumpTo = null,
}: {
  runId: string
  totals: TraceTotals | null
  enabled?: boolean
  running?: boolean
  /** Posición global pedida desde la línea de tiempo. Al llegar una nueva, la
   *  lista salta a la página que la contiene y suelta los filtros: en una vista
   *  filtrada no se puede garantizar que ese cuadro esté. */
  jumpTo?: number | null
}) {
  const [filtro, setFiltro] = useState<TraceFilter>(null)
  const [pagina, setPagina] = useState(1)
  const [pos, setPos] = useState(0)

  useEffect(() => {
    if (jumpTo == null) return
    setFiltro(null)
    setPagina(Math.floor(jumpTo / PAGE_SIZE) + 1)
    setPos(jumpTo % PAGE_SIZE)
  }, [jumpTo])

  const consulta = useTracePage(runId, pagina, PAGE_SIZE, filtro, enabled, running)
  const frames = consulta.data?.frames ?? []
  const total = consulta.data?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const cambiarFiltro = (siguiente: TraceFilter) => {
    setFiltro(siguiente)
    setPagina(1)
    setPos(0)
  }

  const irA = (p: number) => {
    setPagina(Math.min(Math.max(1, p), paginas))
    setPos(0)
  }

  const elegido = frames[Math.min(pos, Math.max(0, frames.length - 1))] ?? null
  const desde = (pagina - 1) * PAGE_SIZE

  if (consulta.isPending && !consulta.data) {
    return <p className="eo-cap">Leyendo la traza de la corrida…</p>
  }
  if (!total && !filtro) {
    return (
      <EmptyState hint="Sin traza no se puede inspeccionar cuadro a cuadro.">
        Esta corrida no tiene traza
      </EmptyState>
    )
  }

  return (
    <div className="eo-trace">
      <Card className="eo-trace__master" flush>
        <div className="eo-trace__filters">
          <label>
            <input
              type="checkbox"
              checked={filtro === 'actividad'}
              onChange={(e) => cambiarFiltro(e.target.checked ? 'actividad' : null)}
            />{' '}
            Solo con actividad
          </label>
          <label>
            <input
              type="checkbox"
              checked={filtro === 'alertas'}
              onChange={(e) => cambiarFiltro(e.target.checked ? 'alertas' : null)}
            />{' '}
            Solo alertas
          </label>
          <span className="eo-mono">
            {total} de {totals?.frames ?? total}
          </span>
        </div>

        {pagina > 1 && (
          <div className="eo-trace__more">
            <Button onClick={() => irA(pagina - 1)}>Cuadros anteriores</Button>
          </div>
        )}

        <ul className="eo-trace__list" role="listbox" aria-label="Cuadros de la traza">
          {frames.map((f, i) => (
            <li
              key={f.unit_id ?? desde + i}
              role="option"
              aria-selected={i === pos}
              className={i === pos ? 'is-selected' : undefined}
              onClick={() => setPos(i)}
            >
              <span className="eo-trace__idx eo-mono">{f.frame_index ?? desde + i}</span>
              <span className="eo-trace__unit eo-mono">{f.unit_id}</span>
              <span className="eo-trace__dets">{f.detections?.length || '—'}</span>
              {(f.alert?.length ?? 0) > 0 ? (
                <Badge tone="alert">Alerta</Badge>
              ) : (
                <i
                  className="eo-trace__dot"
                  // `control_label` lo resuelve el backend; `control` es el
                  // código crudo y solo se usa si viene una traza vieja.
                  title={f.control_label ?? f.control}
                  style={{ background: toneVar(controlTone(f.control)) }}
                />
              )}
            </li>
          ))}
        </ul>

        {pagina < paginas && (
          <div className="eo-trace__more">
            <Button onClick={() => irA(pagina + 1)}>Cuadros siguientes</Button>
          </div>
        )}

        {total === 0 && (
          <EmptyState hint="Sacá alguno de los dos filtros.">Ningún cuadro pasa el filtro</EmptyState>
        )}
      </Card>

      <div className="eo-trace__detail">
        <FrameInspector
          frame={elegido}
          runId={runId}
          position={desde + pos}
          total={total}
          onStep={(d) => {
            const siguiente = pos + d
            // Pasar del borde de la página avanza de página en vez de frenar.
            if (siguiente < 0 && pagina > 1) {
              setPagina(pagina - 1)
              setPos(PAGE_SIZE - 1)
            } else if (siguiente >= frames.length && pagina < paginas) {
              setPagina(pagina + 1)
              setPos(0)
            } else {
              setPos(Math.min(Math.max(0, siguiente), Math.max(0, frames.length - 1)))
            }
          }}
        />
      </div>
    </div>
  )
}
