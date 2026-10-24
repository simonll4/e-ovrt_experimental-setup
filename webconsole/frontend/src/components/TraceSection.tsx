import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import FrameInspector from './FrameInspector'
import { Badge, Button, Card, EmptyState, ErrorBanner, LoadingState, StaleNotice } from './ui'
import { controlLabel, controlTone } from '../traceview'
import { useTracePage, type TraceFilter } from '../api/queries/runs'
import { toneVar } from '../palette'
import type { TraceFrame, TraceTotals } from '../types'

/** Cuántos cuadros trae cada página. Coincide con lo que se renderiza: una
 *  traza de miles de cuadros no puede volcarse entera, y ahora tampoco se
 *  descarga entera. */
const PAGE_SIZE = 200

/** El estado de entrega en una palabra, para la fila: el motivo completo del
 *  descarte está en el detalle del cuadro. */
const detecciones = (n: number) =>
  n ? (
    <>{n}<span className="eo-sr">{n === 1 ? ' detección,' : ' detecciones,'}</span></>
  ) : (
    <><span aria-hidden="true">—</span><span className="eo-sr">sin detecciones,</span></>
  )

const estadoCorto = (control: string) =>
  control.startsWith('dropped:') ? 'descartado' : control === 'not_received' ? 'no recibido' : controlLabel(control)

/** Pedido de salto desde la línea de tiempo: la posición global en la traza
 *  sin filtrar. `seq` distingue dos pedidos al mismo cuadro, que con un número
 *  pelado no volvían a disparar el salto. */
export interface TraceJump {
  pos: number
  seq: number
}

/**
 * Panel de traza en maestro-detalle: la lista de cuadros a la izquierda, el
 * cuadro elegido completo a la derecha.
 *
 * Trae su propia página en vez de recibir la traza entera por props, y el
 * filtro viaja al servidor para que "solo alertas" siga significando las de la
 * corrida y no las de la página cargada.
 *
 * La lista es un listbox con UNA parada de tabulación: flechas, Inicio/Fin y
 * Re Pág/Av Pág recorren con los mismos manejadores que los botones de
 * anterior/siguiente (que cruzan de página en los bordes), y la opción activa
 * se anuncia con `aria-activedescendant`. Cada cambio de cuadro se informa con
 * `onFrameChange` para que la línea de tiempo mueva su cursor al mismo lugar.
 */
export default function TraceSection({
  runId,
  totals,
  enabled = true,
  running = false,
  jumpTo = null,
  onFrameChange,
}: {
  runId: string
  totals: TraceTotals | null
  enabled?: boolean
  running?: boolean
  /** Pedido de salto desde la línea de tiempo. Al llegar uno nuevo, la lista
   *  salta a la página que contiene ese cuadro y suelta los filtros: en una
   *  vista filtrada no se puede garantizar que ese cuadro esté. */
  jumpTo?: TraceJump | null
  onFrameChange?: (frame: TraceFrame | null) => void
}) {
  const [filtro, setFiltro] = useState<TraceFilter>(null)
  const [pagina, setPagina] = useState(1)
  const [pos, setPos] = useState(0)
  const listaRef = useRef<HTMLUListElement>(null)
  const auto = useId()
  const opcionId = (i: number) => `${auto}c${i}`

  useEffect(() => {
    if (jumpTo == null) return
    setFiltro(null)
    setPagina(Math.floor(jumpTo.pos / PAGE_SIZE) + 1)
    setPos(jumpTo.pos % PAGE_SIZE)
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
  const activo = Math.min(pos, Math.max(0, frames.length - 1))

  // La línea de tiempo sigue a la lista: su cursor marca el cuadro elegido,
  // venga del click, del teclado o de anterior/siguiente.
  const avisar = useRef(onFrameChange)
  avisar.current = onFrameChange
  useEffect(() => {
    avisar.current?.(elegido)
  }, [elegido?.unit_id, elegido?.frame_index]) // eslint-disable-line react-hooks/exhaustive-deps

  // La opción activa siempre a la vista dentro de la lista con scroll propio.
  useEffect(() => {
    document.getElementById(opcionId(activo))?.scrollIntoView?.({ block: 'nearest' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo, pagina])

  /** Paso relativo: el mismo manejador de los botones anterior/siguiente.
   *  Pasar del borde de la página avanza de página en vez de frenar. */
  const paso = (d: number) => {
    const siguiente = pos + d
    if (siguiente < 0 && pagina > 1) {
      setPagina(pagina - 1)
      setPos(PAGE_SIZE - 1)
    } else if (siguiente >= frames.length && pagina < paginas) {
      setPagina(pagina + 1)
      setPos(0)
    } else {
      setPos(Math.min(Math.max(0, siguiente), Math.max(0, frames.length - 1)))
    }
  }

  const tecla = (e: KeyboardEvent<HTMLUListElement>) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); paso(1) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); paso(-1) }
    else if (e.key === 'Home') { e.preventDefault(); setPos(0) }
    else if (e.key === 'End') { e.preventDefault(); setPos(Math.max(0, frames.length - 1)) }
    else if (e.key === 'PageDown') { e.preventDefault(); setPos(Math.min(frames.length - 1, pos + 10)) }
    else if (e.key === 'PageUp') { e.preventDefault(); setPos(Math.max(0, pos - 10)) }
  }

  // Sin datos todavía: la estructura se ve y espera adentro, sin presentar la
  // espera como una traza vacía.
  if (consulta.isPending && !consulta.data) {
    return <LoadingState>Leyendo la traza de la corrida…</LoadingState>
  }
  // Un fallo sin datos no es "esta corrida no tiene traza": no se sabe.
  if (consulta.error && !consulta.data) {
    return (
      <ErrorBanner
        detail={String(consulta.error)}
        onRetry={() => void consulta.refetch()}
        retrying={consulta.isFetching}
      >
        No se pudo leer la traza de esta corrida. Los cuadros no están perdidos: la consulta
        no respondió.
      </ErrorBanner>
    )
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
        {consulta.error && consulta.data && (
          <StaleNotice what="la traza" onRetry={() => void consulta.refetch()} retrying={consulta.isFetching} />
        )}
        <div className="eo-trace__filters">
          <label>
            <input
              type="checkbox"
              checked={filtro === 'actividad'}
              onChange={(e) => cambiarFiltro(e.target.checked ? 'actividad' : null)}
            />
            Solo con actividad
          </label>
          <label>
            <input
              type="checkbox"
              checked={filtro === 'alertas'}
              onChange={(e) => cambiarFiltro(e.target.checked ? 'alertas' : null)}
            />
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

        <ul
          ref={listaRef}
          className="eo-trace__list"
          role="listbox"
          aria-label="Cuadros de la traza"
          tabIndex={frames.length ? 0 : -1}
          aria-activedescendant={frames.length ? opcionId(activo) : undefined}
          onKeyDown={tecla}
        >
          {frames.map((f, i) => (
            <li
              key={f.unit_id ?? desde + i}
              id={opcionId(i)}
              role="option"
              aria-selected={i === activo}
              className={i === activo ? 'is-selected' : undefined}
              onClick={() => {
                setPos(i)
                listaRef.current?.focus()
              }}
            >
              {/* Las palabras ocultas arman una frase para el lector: «Cuadro 3,
                  obra_frame_000003, 2 detecciones, recibido». A la vista quedan
                  sólo los números. */}
              <span className="eo-trace__idx eo-mono"><span className="eo-sr">Cuadro </span>{f.frame_index ?? desde + i}<span className="eo-sr">,</span></span>
              <span className="eo-trace__unit eo-mono">{f.unit_id}<span className="eo-sr">,</span></span>
              <span className="eo-trace__dets">{detecciones(f.detections?.length ?? 0)}</span>
              {(f.alert?.length ?? 0) > 0 ? (
                <Badge tone="alert">Alerta</Badge>
              ) : (
                <>
                  <i
                    className="eo-trace__dot"
                    aria-hidden="true"
                    // `control_label` lo resuelve el backend; `control` es el
                    // código crudo y solo se usa si viene una traza vieja.
                    title={f.control_label ?? controlLabel(f.control)}
                    style={{ background: toneVar(controlTone(f.control)) }}
                  />
                  {/* El estado en texto: a la vista cuando no es la entrega
                      normal, y para el lector siempre. El color acompaña. */}
                  {f.control === 'received' ? (
                    <span className="eo-sr">recibido</span>
                  ) : (
                    <span className="eo-trace__estado">{estadoCorto(f.control)}</span>
                  )}
                </>
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
          onStep={paso}
        />
      </div>
    </div>
  )
}
