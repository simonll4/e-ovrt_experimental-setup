import { Link } from 'react-router-dom'
import { useRunsEnCurso } from '../api/queries/runs'
import { isRunning } from '../runview'

export default function LiveRunPill({ onNavigate }: { onNavigate?: () => void } = {}) {
  const run = useRunsEnCurso().data?.items.find(isRunning)
  if (!run) return null
  return (
    <Link to={`/runs/${run.run_id}`} className="eo-livepill" title={`Corrida en curso: ${run.run_id}`} aria-label={`Corrida en curso: ${run.run_id}`} onClick={onNavigate}>
      <span className="eo-livepill__dot" aria-hidden="true">●</span>
      <span className="eo-livepill__id">{run.run_id}</span>
      <span className="eo-livepill__meta">
        {run.fps_effective != null ? `${run.fps_effective} fps` : 'corriendo'}
      </span>
    </Link>
  )
}
