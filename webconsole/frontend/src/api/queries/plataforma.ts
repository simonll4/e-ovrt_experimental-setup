import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  accionPlataforma, correrClip, dejarPlataformaLista, getClipsDemostracion, getPlataforma, getPreparacionClip,
} from '..'
import { qk } from '../keys'
import { POLL } from '../queryClient'

/** La plataforma (plan de la consola, §7.1): los trece servicios, la GPU y el registro de acciones. */
export function usePlataforma() {
  return useQuery({ queryKey: qk.plataforma, queryFn: getPlataforma, refetchInterval: POLL.plataforma })
}

function useRefrescarPlataforma() {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: qk.plataforma })
    void qc.invalidateQueries({ queryKey: qk.platform.all })
    void qc.invalidateQueries({ queryKey: qk.target })
    void qc.invalidateQueries({ queryKey: qk.preflight })
    void qc.invalidateQueries({ queryKey: qk.preparacionClip })
  }
}

export function useAccionPlataforma() {
  const refrescar = useRefrescarPlataforma()
  return useMutation({
    mutationFn: ({ servicio, verbo, confirmar }: { servicio: string; verbo: string; confirmar?: boolean }) =>
      accionPlataforma(servicio, verbo, confirmar),
    onSettled: refrescar,
  })
}

export function useDejarLista() {
  const refrescar = useRefrescarPlataforma()
  return useMutation({ mutationFn: (confirmar: boolean = false) => dejarPlataformaLista(confirmar), onSettled: refrescar })
}

/** «Correr un clip» (§7.2): mientras corre, se mira cada segundo; si no, cada tanto. */
export function useClipsDemostracion() {
  return useQuery({
    queryKey: qk.demostracionClip,
    queryFn: getClipsDemostracion,
    refetchInterval: (q) => (q.state.data?.actual?.fase === 'corriendo' ? POLL.grabacion : POLL.salud),
  })
}

export function usePreparacionClip(enabled = true) {
  return useQuery({ queryKey: qk.preparacionClip, queryFn: getPreparacionClip, refetchInterval: POLL.salud, enabled })
}

export function useCorrerClip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => correrClip(id),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.demostracionClip })
      void qc.invalidateQueries({ queryKey: qk.preparacionClip })
    },
  })
}
