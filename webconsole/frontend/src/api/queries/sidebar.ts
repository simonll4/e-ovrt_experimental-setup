import { useQuery } from '@tanstack/react-query'
import { getExperimentManifests, listPromptSets } from '..'
import { qk } from '../keys'
import { useRunsEnCurso } from './runs'

export interface SidebarCounts {
  runs: number | null
  experiments: number | null
  promptSets: number | null
}

/** Contadores de la barra lateral.
 *
 *  El de corridas cuenta las que están **en curso**, no el total: es lo que hace
 *  útil el número (el prototipo muestra "1" con nueve corridas en el listado).
 *
 *  Antes esto pedía los tres endpoints una sola vez al montar y nunca más, así
 *  que el contador quedaba desactualizado apenas lanzabas algo. Ahora el de
 *  corridas sale del total que informa el servidor —o sea, se mueve solo— y los
 *  otros dos se invalidan cuando se crea o borra un manifiesto o un conjunto.
 *
 *  El total viene del servidor y no de contar filas: con el listado paginado,
 *  contar en el cliente daría las corridas en curso *de la página actual*.
 *
 *  Un contador en `null` no se muestra: es "todavía no sé", que no es lo mismo
 *  que cero.
 */
export function useSidebarCounts(): SidebarCounts {
  const runs = useRunsEnCurso()

  const experiments = useQuery({
    queryKey: qk.experiments.manifests,
    queryFn: () => getExperimentManifests(),
    staleTime: 60_000,
  })

  const promptSets = useQuery({
    queryKey: qk.promptSets.list,
    queryFn: listPromptSets,
    staleTime: 60_000,
  })

  return {
    runs: runs.data ? runs.data.total : null,
    experiments: experiments.data?.length ?? null,
    promptSets: promptSets.data?.length ?? null,
  }
}
