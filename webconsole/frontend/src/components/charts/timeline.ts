import type { TraceFrame } from '../../types'
import { areaPaths } from './layout'

export type LaneKind = 'dropped' | 'not_received' | 'alert'

export interface LaneMark {
  x: number
  width: number
  kind: LaneKind
  frameIndex: number
}

export interface TimelineLayout {
  line: string
  area: string
  marks: LaneMark[]
  maxDetections: number
}

/**
 * Layout de la línea de tiempo de una corrida.
 *
 * El área es la cantidad de detecciones por cuadro; las marcas son eventos
 * discretos que van en carriles separados. Esa separación espacial es la
 * codificación secundaria que hace que el significado no dependa del matiz: entre
 * el naranja de "alerta" y el rojo de "fallida" hay ΔE 8,8 en visión normal, por
 * debajo del piso de 15.
 *
 * Un mismo cuadro puede producir dos marcas: su estado de entrega y su alerta.
 */
export function timelineLayout(
  frames: TraceFrame[],
  width: number,
  plotHeight: number,
): TimelineLayout {
  if (!frames.length) return { line: '', area: '', marks: [], maxDetections: 0 }

  const counts = frames.map((fr) => fr.detections?.length ?? 0)
  const maxDetections = counts.reduce((a, b) => Math.max(a, b), 0)
  const { line, area } = areaPaths(counts, width, plotHeight)

  // Ancho mínimo de 1 px: con miles de cuadros el slot es subpíxel, y una marca de
  // ancho 0 es una marca invisible. Un descarte que no se ve es un descarte
  // silenciado.
  const slot = width / frames.length
  const markWidth = Math.max(1, slot)

  const marks: LaneMark[] = []
  frames.forEach((fr, i) => {
    const x = i * slot
    const frameIndex = fr.frame_index ?? i
    if (fr.control === 'not_received') {
      marks.push({ x, width: markWidth, kind: 'not_received', frameIndex })
    } else if (fr.control.startsWith('dropped:')) {
      marks.push({ x, width: markWidth, kind: 'dropped', frameIndex })
    }
    if ((fr.alert?.length ?? 0) > 0) {
      marks.push({ x, width: markWidth, kind: 'alert', frameIndex })
    }
  })

  return { line, area, marks, maxDetections }
}

/** Índice del cuadro bajo la coordenada x. -1 si no hay cuadros. */
export function frameAtX(x: number, width: number, count: number): number {
  if (count <= 0) return -1
  const ratio = Math.min(1, Math.max(0, x / width))
  return Math.min(count - 1, Math.floor(ratio * count))
}
