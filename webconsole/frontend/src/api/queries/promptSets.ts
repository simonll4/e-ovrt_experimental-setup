import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmFreeze, createPromptSet, deletePromptSet, derivePromptSet, getPromptSetDetail,
  listPromptSets, requestFreeze, updatePromptSet,
} from '..'
import { qk } from '../keys'
import type { PromptSetDetail, PromptSetSummary } from '../../types'

export function usePromptSetList() {
  return useQuery<PromptSetSummary[]>({
    queryKey: qk.promptSets.list,
    queryFn: listPromptSets,
    staleTime: 60_000,
  })
}

export function usePromptSetDetail(id: string | null) {
  return useQuery<PromptSetDetail>({
    queryKey: qk.promptSets.detail(id ?? ''),
    queryFn: () => getPromptSetDetail(id as string),
    enabled: Boolean(id),
  })
}

/** Todas las mutaciones de conjuntos invalidan lo mismo: el listado (cambian
 *  clases, frases o estado), el detalle tocado, y el catálogo —que expone los
 *  conjuntos del repositorio— más el contador de la barra lateral. */
function useInvalidarConjuntos() {
  const qc = useQueryClient()
  return (id?: string) => {
    void qc.invalidateQueries({ queryKey: qk.promptSets.all })
    void qc.invalidateQueries({ queryKey: qk.catalog.promptSets })
    if (id) void qc.invalidateQueries({ queryKey: qk.promptSets.detail(id) })
  }
}

export function useCreatePromptSet() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: (set: PromptSetDetail) => createPromptSet(set),
    onSuccess: (s) => invalidar(s.id),
  })
}

export function useUpdatePromptSet() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: ({ id, set }: { id: string; set: PromptSetDetail }) => updatePromptSet(id, set),
    onSuccess: (s) => invalidar(s.id),
  })
}

export function useDeletePromptSet() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: (id: string) => deletePromptSet(id),
    onSuccess: () => invalidar(),
  })
}

export function useRequestFreeze() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: (id: string) => requestFreeze(id),
    onSuccess: (s) => invalidar(s.id),
  })
}

export function useConfirmFreeze() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: (id: string) => confirmFreeze(id),
    onSuccess: (s) => invalidar(s.id),
  })
}

export function useDerivePromptSet() {
  const invalidar = useInvalidarConjuntos()
  return useMutation({
    mutationFn: ({ id, newId, changes }: { id: string; newId: string; changes: string }) =>
      derivePromptSet(id, newId, changes),
    onSuccess: (s) => invalidar(s.id),
  })
}
