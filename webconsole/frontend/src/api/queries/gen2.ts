import { useQuery } from '@tanstack/react-query'
import { getGen2Prueba, getGen2Pruebas, getPreguntas } from '..'
import { qk } from '../keys'

/** Archivos versionados que solo cambian cuando el driver corre: sin sondeo.
 *  Un 404 de una prueba es una respuesta, no un fallo transitorio: sin reintento. */
export function usePreguntas(enabled = true) {
  return useQuery({ queryKey: qk.preguntas, queryFn: getPreguntas, retry: false, enabled })
}

export function useGen2Pruebas() {
  return useQuery({ queryKey: qk.gen2.pruebas, queryFn: getGen2Pruebas, retry: false })
}

export function useGen2Prueba(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: qk.gen2.prueba(id ?? ''),
    queryFn: () => getGen2Prueba(id!),
    enabled: Boolean(id) && enabled,
    retry: false,
  })
}
