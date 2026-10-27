import { useQuery } from '@tanstack/react-query'
import {
  getDemoCifras, getDemoPreflight, getDemoSession, getDemoStack, getDemoState,
} from '..'
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

/** El chequeo previo hace una ida y vuelta real por el broker: cada 5 s alcanza. */
export function useDemoPreflight(enabled: boolean) {
  return useQuery({
    queryKey: qk.demo.preflight,
    queryFn: getDemoPreflight,
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
