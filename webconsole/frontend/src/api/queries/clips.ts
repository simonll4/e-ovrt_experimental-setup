import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateClip, getClips, getMasters } from '..'
import { qk } from '../keys'
import type { ClipEntry, GenerateClipBody, MasterEntry } from '../../types'

/** Materiales: las grabaciones completas de las que se recortan los clips.
 *  Leerlos implica un `ffprobe` por archivo, así que no se revalidan por reloj. */
export function useMasters() {
  return useQuery<MasterEntry[]>({
    queryKey: qk.clips.masters,
    queryFn: async () => (await getMasters()).masters,
    staleTime: 60_000,
  })
}

export function useClips() {
  return useQuery<ClipEntry[]>({
    queryKey: qk.clips.list,
    queryFn: async () => (await getClips()).clips,
    staleTime: 60_000,
  })
}

export function useGenerateClip() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: GenerateClipBody) => generateClip(body),
    onSuccess: () => {
      // Cortar un clip cambia las dos listas: aparece el clip nuevo y el
      // material pasa a declarar que ya tiene recortes.
      void qc.invalidateQueries({ queryKey: qk.clips.all })
    },
  })
}
