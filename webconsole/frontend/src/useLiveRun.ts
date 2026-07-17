import { useEffect, useState } from 'react'
import { listRuns } from './api'
import { isRunning } from './runview'
import type { RunRow } from './types'

export function useLiveRun(): RunRow | null {
  const [run, setRun] = useState<RunRow | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      listRuns()
        .then((rows) => alive && setRun(rows.find(isRunning) ?? null))
        .catch(() => alive && setRun(null))
    tick()
    const timer = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  return run
}
