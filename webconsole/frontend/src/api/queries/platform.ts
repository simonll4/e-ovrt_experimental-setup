import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  activateInstance, getInstances, getPreflight, getTarget, stopPlatform,
} from '..'
import { qk } from '../keys'
import { POLL } from '../queryClient'
import type { PlatformInstance, PreflightStatus, TargetStatus } from '../../types'

/** Estado del motor de detección. Devuelve `null` mientras no se sabe, igual que
 *  el hook manual al que reemplaza: las pantallas distinguen "todavía no sé" de
 *  "respondió que no está listo". */
export function useTarget(): TargetStatus | null {
  const { data } = useQuery({
    queryKey: qk.target,
    queryFn: getTarget,
    refetchInterval: POLL.salud,
  })
  return data ?? null
}

/** Referencia del modelo activo. Varias pantallas la usan como clave para
 *  recargar catálogos cuando el servicio reinicia con otro modelo. */
export function useTargetModelRef(): string | undefined {
  return useTarget()?.model?.ref
}

export function usePreflight(): PreflightStatus | null {
  const { data } = useQuery({
    queryKey: qk.preflight,
    queryFn: getPreflight,
    refetchInterval: POLL.salud,
  })
  return data ?? null
}

export type ServiceStatus = 'ok' | 'down' | 'checking'
export interface ServiceHealth {
  media: ServiceStatus
  control: ServiceStatus
  distribution: ServiceStatus
}

/** Los tres puntos del pie de la barra lateral.
 *
 *  Antes esto tenía su propio intervalo de 10 s sobre `/api/target` y
 *  `/api/preflight`, en paralelo al de `useTarget` y al de `usePreflight`: el
 *  mismo endpoint se consultaba desde tres lugares. Ahora comparte caché con
 *  ellos y las tres pantallas se sirven de una sola petición.
 */
export function useServiceHealth(enabled = true): ServiceHealth {
  const target = useQuery({
    enabled,
    queryKey: qk.target,
    queryFn: getTarget,
    refetchInterval: enabled ? POLL.salud : false,
  })
  const preflight = useQuery({
    enabled,
    queryKey: qk.preflight,
    queryFn: getPreflight,
    refetchInterval: enabled ? POLL.salud : false,
  })

  const estado = (cargando: boolean, sano: boolean | undefined): ServiceStatus =>
    cargando ? 'checking' : sano ? 'ok' : 'down'

  return {
    media: estado(target.isPending, target.data?.healthy),
    control: estado(preflight.isPending, preflight.data?.control?.healthy),
    distribution: estado(
      preflight.isPending,
      !preflight.isError && preflight.data?.distribution?.healthy,
    ),
  }
}

/** Instancias de la plataforma. `null` mientras carga; el 501 de "orquestación
 *  no habilitada" se propaga como error para que la pantalla lo distinga de un
 *  fallo real. */
export function useInstances() {
  return useQuery<PlatformInstance[]>({
    queryKey: qk.platform.instances,
    queryFn: getInstances,
    refetchInterval: POLL.plataforma,
  })
}

export function useActivateInstance() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => activateInstance(name),
    // Cambiar de instancia cambia el modelo activo: se invalidan los catálogos,
    // que dependen de él, además del estado de la plataforma.
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.platform.all })
      void qc.invalidateQueries({ queryKey: qk.target })
      void qc.invalidateQueries({ queryKey: qk.preflight })
      void qc.invalidateQueries({ queryKey: qk.catalog.all })
    },
  })
}

export function useStopPlatform() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: stopPlatform,
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.platform.all })
      void qc.invalidateQueries({ queryKey: qk.target })
      void qc.invalidateQueries({ queryKey: qk.preflight })
    },
  })
}
