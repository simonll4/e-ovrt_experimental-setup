import { useEffect, useState } from 'react'
import { listRuns, getExperimentManifests, listPromptSets } from './api'

export interface SidebarCounts {
  runs: number | null
  experiments: number | null
  promptSets: number | null
}

export function useSidebarCounts(): SidebarCounts {
  const [counts, setCounts] = useState<SidebarCounts>({ runs: null, experiments: null, promptSets: null })

  useEffect(() => {
    let alive = true
    listRuns()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, runs: rows.filter((r) => r.status === 'running').length }))
      })
      .catch(() => {
        /* el contador queda en null: no se muestra "0" por un fetch que fallo */
      })
    getExperimentManifests()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, experiments: rows.length }))
      })
      .catch(() => {})
    listPromptSets()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, promptSets: rows.length }))
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  return counts
}
