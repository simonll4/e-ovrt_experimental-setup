import { artifactUrl } from '../api'
import ConditionProgress from './ConditionProgress'
import PreviewWithBoxes from './PreviewWithBoxes'
import { Badge, Banner, Button, Card, EmptyState, IconChevron } from './ui'
import { conditionLabel } from '../labels'
import Termino from './Glosario'
import { controlLabel, controlTone } from '../traceview'
import type { TraceFrame } from '../types'

const conf = (v: number) => v.toFixed(2).replace('.', ',')

/**
 * Panel derecho del maestro-detalle: todo lo que se sabe del cuadro elegido.
 *
 * Reemplaza el volcado vertical de miles de cuadros: en vez de scrollear una
 * lista infinita de miniaturas, se navega por la lista o por la línea de tiempo y
 * acá se ve uno solo, completo.
 */
export default function FrameInspector({
  frame,
  runId,
  position,
  total,
  onStep,
}: {
  frame: TraceFrame | null
  runId: string
  position: number
  total: number
  onStep: (delta: number) => void
}) {
  if (!frame) {
    return (
      <EmptyState hint="Elegí un cuadro en la lista o tocá la línea de tiempo.">
        Ningún cuadro seleccionado
      </EmptyState>
    )
  }

  const alerts = frame.alert ?? []
  const dets = frame.detections ?? []

  return (
    <div className="eo-inspector">
      {/* TraceAlert solo trae `condition_id` y `severity`: no hay alert_id. */}
      {alerts.map((a) => (
        <Banner key={`${a.condition_id}-${a.severity}`} tone="warn">
          <b>Alerta confirmada — <Termino id={a.condition_id}>{conditionLabel(a.condition_id)}</Termino></b>
          <div>Se disparó en el cuadro {frame.frame_index ?? position}.</div>
        </Banner>
      ))}

      <Card
        level={3}
        title={`Cuadro ${frame.frame_index ?? position}`}
        meta={
          <>
            <span className="eo-mono">unidad {frame.unit_id ?? '—'}</span>
            <Badge tone={controlTone(frame.control)}>{controlLabel(frame.control)}</Badge>
            <span className="eo-inspector__nav">
              <Button
                className="eo-btn--icon eo-step-prev"
                aria-label="Cuadro anterior"
                disabled={position <= 0}
                onClick={() => onStep(-1)}
              >
                <span className="eo-chev eo-chev--prev"><IconChevron /></span>
              </Button>
              <Button
                className="eo-btn--icon eo-step-next"
                aria-label="Cuadro siguiente"
                disabled={position >= total - 1}
                onClick={() => onStep(1)}
              >
                <span className="eo-chev eo-chev--next"><IconChevron /></span>
              </Button>
            </span>
          </>
        }
      >
        <div className="eo-inspector__viewer">
          <PreviewWithBoxes
            src={artifactUrl(runId, `previews/${frame.unit_id}.preview.jpg`)}
            alt={`Cuadro ${frame.frame_index ?? position} de la corrida ${runId}`}
            detections={dets}
            width={560}
            zoomable
            emptyMessage="Esta corrida se grabó sin vistas previas de cuadro. Las cajas no se pueden dibujar sin la imagen."
          />
        </div>
      </Card>

      <div className="eo-inspector__split">
        <Card level={3} title="Detecciones" meta={String(dets.length)} flush>
          {dets.length === 0 ? (
            <p className="eo-cap eo-cap--inset">Ninguna detección en este cuadro.</p>
          ) : (
            <ul className="eo-detlist">
              {dets.map((d, i) => (
                <li key={`${d.label}-${i}`}>
                  <span className="eo-mono">{d.label}</span>
                  <span className="eo-detlist__score eo-mono">{conf(d.confidence)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card level={3} title="Progreso de las condiciones" flush>
          <ConditionProgress frame={frame} />
        </Card>
      </div>
    </div>
  )
}
