import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  accionPlataforma, dejarPlataformaLista, getPlataforma,
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
  return useMutation({ mutationFn: () => dejarPlataformaLista(), onSettled: refrescar })
}
