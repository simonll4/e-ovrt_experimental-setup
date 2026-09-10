import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './endpoints'

/** Cada cuánto se re-consulta algo que está vivo de verdad.
 *
 *  Estos números salen del comportamiento anterior (que reagendaba `setTimeout`
 *  a mano) para no cambiar la carga sobre los servicios al migrar. Lo que sí
 *  cambia: antes varios de estos intervalos corrían **siempre**; ahora se pasan
 *  como `refetchInterval` condicional y valen `false` cuando no hay nada vivo.
 */
export const POLL = {
  /** Corrida o experimento en curso: el usuario mira el número cambiar. */
  enCurso: 4_000,
  /** Patrones de riesgo activos en el motor de reglas. */
  riesgoActivo: 2_000,
  /** Salud de los servicios: barato y no urgente. */
  salud: 10_000,
  /** Cambio de instancia: puede tardar minutos, pero el estado importa. */
  plataforma: 5_000,
  /** Grabación en curso: el contador de segundos y el tamaño del archivo. */
  grabacion: 1_000,
} as const

/** Reintentar solo lo que puede mejorar solo.
 *
 *  Un 4xx es una respuesta del servidor sobre la petición: un 404 de corrida
 *  inexistente o un 409 de conflicto no cambian por insistir, y reintentarlos
 *  solo demora el mensaje de error. Se reintenta la red caída y los 5xx.
 *
 *  El 501 es la excepción entre los 5xx: el BFF lo usa para decir "esta consola
 *  apunta a una instancia fija y la orquestación no está habilitada", que es una
 *  condición permanente y una pantalla de interfaz, no una falla. Reintentarlo
 *  dejaba Plataforma en «Cargando…» en vez de explicar por qué no hay nada.
 */
export function reintentar(fallos: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
  if (error instanceof ApiError && error.status === 501) return false
  return fallos < 2
}

export function crearQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // La consola es de monitoreo: volver a una pestaña y ver datos de hace
        // diez minutos es peor que un refetch de más.
        staleTime: 15_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: true,
        // Sin esto, cada montaje de pantalla dispara un refetch aunque el dato
        // esté fresco — justo lo que se quería sacar del polling a mano.
        refetchOnMount: true,
        retry: reintentar,
      },
      mutations: {
        // Una mutación reintentada sola puede lanzar dos corridas o borrar dos
        // veces. El error se muestra y decide la persona.
        retry: false,
      },
    },
  })
}
