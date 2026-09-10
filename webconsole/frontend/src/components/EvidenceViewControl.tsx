import { useState } from 'react'
import type { EvidenceInfo, EvidenceListingMeta, EvidenceView } from '../types'
import { Badge, SegmentedControl } from './ui'

export function useEvidenceView(surface: 'runs' | 'experiments') {
  const key = `eo-evidence-view-${surface}`
  const [view, setView] = useState<EvidenceView>(() => {
    try {
      const saved = localStorage.getItem(key)
      if (saved === 'todas' || saved === 'archivadas') return saved
    } catch { /* El navegador puede deshabilitar el almacenamiento. */ }
    return 'evidencia'
  })
  const changeView = (value: EvidenceView) => {
    setView(value)
    try { localStorage.setItem(key, value) } catch { /* La selección sigue funcionando. */ }
  }
  return [view, changeView] as const
}

export default function EvidenceViewControl({ view, onChange, meta, noun }: {
  view: EvidenceView
  onChange: (view: EvidenceView) => void
  meta?: EvidenceListingMeta
  noun: 'corridas' | 'ejecuciones'
}) {
  const archived = noun === 'ejecuciones' ? meta?.archivedExecutions : meta?.archived
  return (
    <div className="eo-toolbar" role="group" aria-label="Vista de evidencia">
      <SegmentedControl<EvidenceView> value={view} onChange={onChange} options={[
        { value: 'evidencia', label: 'Evidencia' },
        { value: 'archivadas', label: 'Archivadas' },
        { value: 'todas', label: 'Todas' },
      ]} />
      {meta?.available === false ? (
        <span className="eo-note">Registro de evidencia no disponible en esta máquina. Elegí Todas para ver el historial.</span>
      ) : view === 'evidencia' && archived != null && archived > 0 ? (
        <span className="eo-note">{archived} {noun} archivadas</span>
      ) : null}
    </div>
  )
}

export function EvidenceBadge({ evidence }: { evidence?: EvidenceInfo }) {
  if (!evidence?.is_evidence) return null
  const label = evidence.result_ids[0] ?? 'Evidencia'
  return <span className="eo-evidence-badge" title={evidence.result_ids.join('\n') || evidence.reason}>
    <Badge tone="neutral">{label}</Badge>
  </span>
}
