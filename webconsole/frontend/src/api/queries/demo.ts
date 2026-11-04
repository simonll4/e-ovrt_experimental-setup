import { useQuery } from '@tanstack/react-query'
import {
  getDemoCifras, getDemoModos, getDemoPreflight, getDemoSession, getDemoStack, getDemoState, listDemoCamaras,
} from '..'
import { POLL } from '../queryClient'
import { qk } from '../keys'
import type { DemoFase } from '../../types'

/** Mientras corre la pantalla mira el estado cada 500 ms (spec §6.5); al cerrar,
 *  cada segundo hasta que aparece el Resultado; quieta, no pide nada más. */
export const DEMO_POLL_MS = 500
const FASES_EN_CURSO: DemoFase[] = ['preparing', 'live']
const FASES_CERRANDO: DemoFase[] = ['finishing', 'rendering']

export function useDemoState() {
  return useQuery({
    queryKey: qk.demo.state,
    queryFn: getDemoState,
    refetchInterval: (q) => {
      const fase = q.state.data?.fase
      if (fase && FASES_EN_CURSO.includes(fase)) return DEMO_POLL_MS
      if (fase && FASES_CERRANDO.includes(fase)) return 1_000
      return 5_000
    },
    retry: false,
  })
}

/** El chequeo previo hace una ida y vuelta real por el broker: cada 5 s alcanza. Con `modo` (uno
 *  que no es el campeón) chequea además los prompts del modo; con el campeón no se pasa. */
export function useDemoPreflight(enabled: boolean, modo?: string | null) {
  return useQuery({
    queryKey: qk.demo.preflight(modo),
    queryFn: () => getDemoPreflight(modo),
    enabled,
    refetchInterval: enabled ? 5_000 : false,
    retry: false,
  })
}

export function useDemoSession(id: string | undefined) {
  return useQuery({
    queryKey: qk.demo.session(id ?? ''),
    queryFn: () => getDemoSession(id as string),
    enabled: Boolean(id),
    retry: false,
  })
}

export function useDemoCifras() {
  return useQuery({ queryKey: qk.demo.cifras, queryFn: getDemoCifras, staleTime: 60_000, retry: false })
}

export function useDemoStack(enabled: boolean) {
  return useQuery({ queryKey: qk.demo.stack, queryFn: getDemoStack, enabled, retry: false })
}

/** Las cámaras que sirven para la demo. Solo se piden en la pantalla dentro de la consola (la
 *  proyección no hace consultas más allá de `/api/demo/*`; esta lo es, pero no la necesita). */
export function useDemoCamaras(enabled = true) {
  return useQuery({
    queryKey: qk.demo.camaras, queryFn: listDemoCamaras, enabled, staleTime: 5_000, retry: false,
    // El estado de cada cámara (¿está activa?) se ve siempre y se mantiene al día solo, mientras la
    // pantalla está en Listo: sondear una RTSP es un intento de conexión, liviano.
    refetchInterval: enabled ? POLL.plataforma : false,
  })
}

/** Los modos de prompts (lista cerrada, con sus cifras de la generación 2): cambian solo al editar
 *  `modos.yaml`. Un 503 (sin `modos.yaml`) deja la pantalla como antes: solo el campeón. */
export function useDemoModos(enabled = true) {
  return useQuery({ queryKey: qk.demo.modos, queryFn: getDemoModos, enabled, staleTime: 5 * 60_000, retry: false })
}
