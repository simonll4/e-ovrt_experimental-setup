import type { DemoState } from '../../types'
import { numero } from './formato'

/** Indicador discreto: la antigüedad del último cuadro procesado. Más de 5 s sin
 *  cuadros = «cámara sin señal» (spec §5.2; F-101.6: la cámara se corta en ciclos). */
export default function CameraIndicator({ camara }: { camara: DemoState['camara'] }) {
  if (!camara) return null
  if (camara.sin_senal) {
    return (
      <p className="eo-demo-camara eo-demo-camara--sin-senal" role="alert">
        Cámara sin señal (último cuadro hace {numero(camara.ultimo_cuadro_hace_s, 0)} s)
      </p>
    )
  }
  return (
    <p className="eo-demo-camara" aria-label="Cámara">
      Cámara: {camara.ultimo_cuadro_hace_s == null
        ? 'esperando el primer cuadro'
        : `último cuadro hace ${numero(camara.ultimo_cuadro_hace_s)} s`} · {camara.cuadros} cuadros
      {camara.bus_perdidos > 0 ? ` · ${camara.bus_perdidos} eventos perdidos en el bus` : ''}
    </p>
  )
}
