import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createCamera, deleteCamera, listCameras, updateCamera } from '..'
import { qk } from '../keys'
import type { CameraPreset } from '../../types'

/** Cámaras guardadas. Se editan poco y desde una sola pantalla, así que alcanza
 *  con invalidar tras cada cambio en vez de revalidar por reloj. */
export function useCameras() {
  return useQuery<CameraPreset[]>({
    queryKey: qk.cameras.list,
    queryFn: listCameras,
    staleTime: 60_000,
  })
}

function useInvalidarCamaras() {
  const qc = useQueryClient()
  return () => {
    void qc.invalidateQueries({ queryKey: qk.cameras.all })
  }
}

export function useCreateCamera() {
  const invalidar = useInvalidarCamaras()
  return useMutation({
    mutationFn: (preset: CameraPreset) => createCamera(preset),
    onSuccess: invalidar,
  })
}

export function useUpdateCamera() {
  const invalidar = useInvalidarCamaras()
  return useMutation({
    mutationFn: ({ id, preset }: { id: string; preset: CameraPreset }) => updateCamera(id, preset),
    onSuccess: invalidar,
  })
}

export function useDeleteCamera() {
  const invalidar = useInvalidarCamaras()
  return useMutation({
    mutationFn: (id: string) => deleteCamera(id),
    onSuccess: invalidar,
  })
}
