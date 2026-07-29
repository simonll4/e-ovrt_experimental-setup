import { useQuery } from '@tanstack/react-query'
import { getDatasets, getExperiments, getIngestPlugins, getPromptSets } from '..'
import { qk } from '../keys'
import { useTargetModelRef } from './platform'
import type { DatasetEntry, Experiment, IngestPlugin, PromptSet } from '../../types'

/**
 * Los catálogos describen lo que la instancia activa ofrece hoy, así que
 * dependen del modelo cargado: si el servicio reinicia con otro
 * `EOVRT_MODEL_REF`, lo que había cacheado deja de valer.
 *
 * Eso se expresa metiendo la referencia del modelo **en la clave de caché**. Al
 * cambiar el modelo cambia la clave, y Query vuelve a pedir sin que nadie tenga
 * que acordarse de invalidar. Antes cada pantalla llevaba su propio
 * `useEffect(..., [modelRef])` haciendo los mismos tres fetch en paralelo —
 * `ComposePage` y `CatalogPage` duplicaban ese efecto entero.
 *
 * `staleTime` alto porque, a modelo fijo, un catálogo cambia solo si alguien
 * edita archivos del repositorio.
 */
function useCatalogo<T>(clave: readonly unknown[], fn: () => Promise<T>) {
  const modelRef = useTargetModelRef()
  return useQuery<T>({
    queryKey: [...clave, modelRef ?? null],
    queryFn: fn,
    staleTime: 60_000,
  })
}

export function useIngestPlugins() {
  return useCatalogo<IngestPlugin[]>(qk.catalog.ingestPlugins, getIngestPlugins)
}

export function useDatasets() {
  return useCatalogo<DatasetEntry[]>(qk.catalog.datasets, getDatasets)
}

/** Conjuntos de prompts tal como los ve el catálogo del repositorio (con sus
 *  clases). Distinto del resumen que consume la pantalla de gestión. */
export function useCatalogPromptSets() {
  return useCatalogo<PromptSet[]>(qk.catalog.promptSets, getPromptSets)
}

export function useCatalogExperiments() {
  return useCatalogo<Experiment[]>(qk.catalog.experiments, getExperiments)
}
