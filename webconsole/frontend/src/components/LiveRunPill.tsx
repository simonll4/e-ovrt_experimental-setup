import { Link } from 'react-router-dom'
import { useLiveRun } from '../useLiveRun'

export default function LiveRunPill() {
  const run = useLiveRun()
  if (!run) return null
  return (
    <Link to={`/runs/${run.run_id}`} className="eo-livepill">
      <span className="eo-livepill__dot" aria-hidden="true">●</span>
      <span className="eo-livepill__id">{run.run_id}</span>
      <span className="eo-livepill__meta">
        {run.fps_effective != null ? `${run.fps_effective} cuadros/s` : 'en curso'}
      </span>
    </Link>
  )
}
