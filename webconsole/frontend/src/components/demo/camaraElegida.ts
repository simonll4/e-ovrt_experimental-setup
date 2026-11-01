import type { DemoCamara } from '../../types'

/** La cámara elegida para la demo se recuerda en este navegador: se elige en la consola y la
 *  proyección (`?proyectar=1`, que no hace consultas de más) la usa sin volver a pedir la lista.
 *  Es una preferencia del operador, no estado de la plataforma: sin almacenamiento (modo
 *  privado) la elección dura mientras la pantalla esté abierta. */
const CLAVE = 'eovrt-demo-camara'

export function leerCamaraElegida(): string | null {
  try {
    return localStorage.getItem(CLAVE)
  } catch {
    return null
  }
}

export function guardarCamaraElegida(id: string): void {
  try {
    localStorage.setItem(CLAVE, id)
  } catch {
    /* sin almacenamiento: la elección vive solo en el estado de la pantalla */
  }
}

/** La elegida si todavía existe en la lista; si no, la de la demo (la OAK-D del laboratorio). */
export function resolverCamara(camaras: DemoCamara[], guardada: string | null): string | null {
  if (guardada && camaras.some((c) => c.id === guardada)) return guardada
  return camaras.find((c) => c.por_defecto)?.id ?? camaras[0]?.id ?? null
}
